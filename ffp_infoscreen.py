#! /usr/bin/env python3
"""
Multimonitor Infoscreen displaying status and emergency service related pages as well as maps.
Using WASTL (FF-Krems)
"""
import json
import logging
import multiprocessing
import os
import threading
import time
from datetime import datetime

import requests
from geopy.geocoders import Nominatim
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.command import Command

import cups

# TODO
# info queue for screens should contain json data
# add http server to print
# add http server to generate map coordinates / map html stream
# get the lat/long highway coortinates from a locally saved file


##########################################################################
# global config
##########################################################################

# use testdata (json file, derived from real emergency with masked sensitive data)
use_testdata = ""

# config file
with open("ffp_infoscreen_config.json") as config_fh:
    config = json.load(config_fh)

# logging
logfile = "".join([config["log"]["path"], "fire_mctrl", datetime.now().strftime(config["timestamp"])])

logging.basicConfig(level=logging.DEBUG,
                    filename=logfile,
                    format='%(asctime)s %(levelname)s: %(message)s')  # include timestamp
# https://docs.python.org/2/library/logging.html?highlight=logging#integration-with-the-warnings-module
logging.captureWarnings(True)
# needs warning module?


##########################################################################
# helper functions
##########################################################################

def check_wastl(url, cookie_id, cookie_data):
    """
    check WASTL / FF-Krems to get current status
    Args:
        url: url to the json status file
        cookie: access cookie to retrieve the status file
    Returns:
        status_code: classification and size in the case of an alarm (e.g. t1, s2, b4...)
            "off" in the cas of no alarm
        wastl_msg: parsed json file from wastl
    """

    # get data from WASTL with authorized cookie
    wastl_session = requests.Session()
    wastl_session.mount('https://', requests.adapters.HTTPAdapter(
        max_retries=requests.adapters.Retry(total=20, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])))

    try:
        req = requests.get(url, cookies={cookie_id: cookie_data})
        if req.status_code == 200:
            logging.debug("Kremser json: " + req.text)
            status = json.loads(req.text)
        else:
            logging.warning("get returned status code: " + str(req.status_code))

        # parse data from WASTL
        if status["CurrentState"] == "data":
            if status["EinsatzData"] == []:
                return "off", status
            else:
                return "?", status

        elif status["CurrentState"] == "token" or status["CurrentState"] == "waiting":
            retmsg = "Token not unlocked, CurrentState:" + str(status["CurrentState"])
            return retmsg, status
        else:
            retmsg = "unknown CurrentState value:" + str(status["CurrentState"])
            return retmsg, status

    except NameError:
        return "json did not contain CurrentState", status + "\n cookie correct?"
    except Exception as exceptmsg:
        logging.error(str(exceptmsg))
        return "unknown error" + str(exceptmsg), ""


def gen_mapparam(json_parsed, highway_km):
    """
    Generate coordinates from the adress and map type
    Args:
        json_parsed: config from wastl, includes address
        highway_km: highway km with matching gps coordinates
    Returns:
        status code (0 in case of success)
        map parameters as a string (e.g. /?lat=48.2206849&lon=16.3800599&theme=fire)
    """

    try:
        # Autobahn adress (km) expected
        if "A1" in json_parsed["EinsatzData"][0]["Strasse"]:
            logging.info("A1 found in \"Strasse\" key")
            nr1 = json_parsed["EinsatzData"][0]["Nummer1"]

            # shorten km number
            if nr1.endswith(".000"):
                nr1.replace(".000", "0")
            elif nr1.endswith(".500"):
                nr1.replace(".500", "5")

            # get lat and lon from local recources

        # standard adress expected
        else:
            logging.info("A1 not found in \"Strasse\" key")
            street = json_parsed["EinsatzData"][0]["Strasse"]
            nr1 = json_parsed["EinsatzData"][0]["Nummer1"]
            nr2 = json_parsed["EinsatzData"][0]["Nummer2"]
            nr3 = json_parsed["EinsatzData"][0]["Nummer3"]
            plz = json_parsed["EinsatzData"][0]["Plz"]
            town = json_parsed["EinsatzData"][0]["Ort"]

            # shorten numbers if they end with .000
            if nr1.endswith(".000"):
                logging.debug("removing .000 from number 1")
                nr1 = nr1.replace(".000", "")
            if nr2.endswith(".000"):
                logging.debug("removing .000 from number 2")
                nr2 = nr2.replace(".000", "")
            if nr3.endswith(".000"):
                logging.debug("removing .000 from number 3")
                nr3 = nr3.replace(".000", "")

            address = plz + " " + town + ", " + \
                " ".join([street, nr1, nr2, nr3])

            logging.debug("address: " + address)

            # convert adress to coordinates
            geolocator = Nominatim()
            location = geolocator.geocode(address)

            if location is None:
                logging.error("error converting into lat/long: " + address)
                return -1, ""
            else:
                lat = location.latitude
                lon = location.longitude

    except KeyError as exceptmsg:
        logging.error("Keyerror" + str(exceptmsg))
        logging.error("json: " + str(json_parsed))

    mapparam = "/?" + "lat=" + str(lat) + "&lon=" + str(lon) + "&zoom=17"
    logging.info("generated lat/long:" + mapparam)

    return 0, mapparam


def check_screen_p(status_qeue, screen_parameter):
    """
    Startup and control a single webdriver instance.

    Args:
        status_qeue: queue which will provide status updates for the screen, triggers updates
        screen_parameter: paramter (urls, positions, reload settings) for this screen
    """

    # max_x, max_y, is F11 maximized
    max_status = [0, 0, False]

    def webdriver_isalive(driver):
        """
        Check if the webdriver is still alive or already dead?

        Args:
            driver: webdriver instance
        Returns:
            bool: alive/not alive
        """
        try:
            driver.execute(Command.STATUS)
            return True
        except Exception:
            return False

    def checkscreen(selenium_handler, position, url, force_reload, maximized):
        """
        Check if the webdriver is workig as supposed (url, position, size/fullscreen)

        Args:
            selenium_handler: webdriver instance
            position: (tuple), x, y pixel coordinates
            url: url to display
            force_reload: url should be reloaded
        """
        try:
            if not webdriver_isalive(selenium_handler[0]):
                logging.warning("{} webdriver not alive, hard reset".format(os.getpid()))
                try:  # try to quit the webdriver, may fail if the instance is already dead
                    selenium_handler[0].quit()
                    maximized[2] = False
                except Exception:
                    pass
                selenium_handler[0] = webdriver.Firefox()

            # check if url has changed
            cur_url = selenium_handler[0].current_url
            if url == cur_url:
                if force_reload:
                    logging.debug("{} enforced reloading of url".format(os.getpid()))
                    selenium_handler[0].get(url)
            else:
                logging.debug("{} url incorrect, changing from: {} to: {}".format(os.getpid(), cur_url, url))
                selenium_handler[0].get(url)

            # check if position has changed
            currentpos = selenium_handler[0].get_window_position()
            if (currentpos['x'], currentpos['y']) != position:
                if (0, 0) == position:
                    if not ((position[0] + 60 <= currentpos['x']) or (position[1] + 60 <= currentpos['y'])):
                        # it is expected that the first screen (with coordinates 0,0) has a task bar at the top or
                        # left side and thus the window will be moved away from (0,0)
                        logging.debug(
                            "{} main screen  (probably taskbar) not changing position".format(os.getpid()))
                    else:
                        logging.debug("{} main screen position off, changing position from: {}, to: {}".format(
                            os.getpid(), str(currentpos), str(position)))
                        selenium_handler[0].set_window_position(position[0], position[1])
                else:
                    logging.debug("{} changing position from: {}, to: {}".format(
                        os.getpid(), str(currentpos), str(position)))
                    selenium_handler[0].set_window_position(position[0], position[1])

            # check if maximized
            current_size = selenium_handler[0].get_window_size()
            if not (current_size["width"] == maximized[0] and current_size["height"] == maximized[1]):
                logging.debug("{} current size does not match previous maximized size x: {} y:{} , maximizing".format(
                    os.getpid(), maximized[0], maximized[1]))
                selenium_handler[0].maximize_window()
                maximized[2] = False

            # check if F11 fullscreen
            if not maximized[2]:
                logging.warning("{} emulating f11".format(os.getpid()))
                selenium_handler[0].find_element_by_tag_name("html").send_keys(Keys.F11)
                maximized[2] = True

            # update maximized size (wait 1 second or size will be not correct)
            time.sleep(1)
            current_size = selenium_handler[0].get_window_size()
            maximized[0] = current_size["width"]
            maximized[1] = current_size["height"]

        # instance has closed or is unresponsive
        except Exception as exceptmsg:
            logging.warning("{} cannot communicate with browser, closing instance (will be restarted upon next check): {}".format(
                os.getpid(), exceptmsg))
            try:  # try to quit the webdriver, may fail if the instance is already dead
                selenium_handler[0].quit()
                maximized[2] = False
            except:
                pass

    # entry point event driven service routine
    sel_instance = [webdriver.Firefox()]
    reload_counter = 0

    while True:
        current_status = status_qeue.get(True)
        logging.debug("{} status update: {}".format(os.getpid(), str(current_status)))
        # parse status info

        # check if screen has to be reloaded
        reload_en = False
        if screen_parameter["always_reload"]:
            reload_en = True
        else:
            if reload_counter >= screen_parameter["periodic_reload"]:
                reload_en = True
                reload_counter = 0
            else:
                reload_counter += 1

        # set url according to status code
        if current_status == "normal":
            url = screen_parameter["url_normal"]
        elif current_status == "alarm":
            url = screen_parameter["url_alarm"]
        else:
            url = "https://isitdns.com/"

        checkscreen(sel_instance, (screen_parameter["pos_x"],
                                   screen_parameter["pos_y"]), url, reload_en, max_status)

        reload_en = False


##########################################################################
# main process
##########################################################################

def update_routine():
    """
    Update routine, fetch WASTL status periodically and forward information to screen processes.
    """

    # check if testdata file should be used to emulate emergency
    if use_testdata:
        wastl_msg = json.load(open(use_testdata))
        alarm_code = wastl_msg["EinsatzData"][0]["Alarmstufe"]
    else:
        # fetch current WASTL status
        alarm_code, status = check_wastl(config["wastl"]["url"],
                                         config["wastl"]["cookie_id"], config["wastl"]["cookie_data"])

    # check if WASTL status is valid
    if alarm_code in config["wastl"]["valid_alarmcodes"]:
        logging.debug("valid WASTL alarm code: " + str(alarm_code))
        code_for_screen = "alarm"
    else:
        logging.error("check_wastl() non valid alarmcode: " + str(alarm_code))
        code_for_screen = "normal"

    # update all screens
    for i in range(0, count):
        print("sending update: {}, {}".format(i, code_for_screen))
        screenstatus_q_l[i].put(code_for_screen)

    # schedule restart after specified time
    threadobj = threading.Timer(config["service_routine_period"], update_routine)
    threadobj.start()


if __name__ == '__main__':
    # initial setup of screen checker processes
    nr_screens = len(config["screen"])
    status_q = []
    screen_param = config["screen"]
    for i in range(0, nr_screens):
        print("starting screen: {}".format(i))
        print(str(len(status_q)))
        status_q.append(multiprocessing.Queue())
        multiprocessing.Process(target=check_screen_p, args=(status_q[i], screen_param[i])).start()

    screenstatus_q_l = status_q
    count = nr_screens
    update_routine()


##########################################################################
# http server
##########################################################################
#
# def print_infopage(url):
#     """
#     Print WASTL info page with detailed current status, map and nearby hydrants.
#
#     """
#
#     cups_session = cups.Connection()
#     printers = cups_session.getPrinters()
#     with open('m.txt', 'w')as output:
#         output.write('some text')
#         print ("done")  # debugging
#         prin = cups_session.getDefault()
#         output.close()
#     # add script print after close file
#     printfile = os.path.abspath("m.txt")
#     cups_session.printFile(prin, printfile, 'm.txt', {})
#
#
# def g
#
#
# @get('/map')
# def map():
#     """
#     Generate job specific map and deliver it.
#     """
#     mapparam_dict =
#     return template(config["template_standard"], mapparam_dict)
#
#
# @post('/')
# def action():
#     """
#     Receive and parse POST request.
#     Start printing info page if required
#     """
#     print ("POST received")
#     # possibly use request from bottle
#
#
# threading.Thread(target=run, kwargs=dict(host='localhost',
#                                          port=config["http_server"]["port"])).start()
