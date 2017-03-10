# FFP_Infoscreen

# This project has been moved to Gitlab: <https://gitlab.com/users/neo0x3d/projects>

[![License: GPL v2](https://img.shields.io/badge/License-GPL%20v2-blue.svg)](https://img.shields.io/badge/License-GPL%20v2-blue.svg)

Display helpful information for the volunteer fire department depending on current WASTL status.

## TODO

- add http server to print the WASTL print page on demand (short info + map), include cookie (http server will be used to trigger the printing)
- add http server to generate html stream for custom map on demand, generating coordinates beforehand
- parse lat/long coordinates from a local file and use them for the highway (decide on a generic input format, decide how and where they should be parsed and in which format they should be handled in the script) maybe gpx?
- export external libs -> requirements.txt

## Setup

### 1\. Prepare host system

Example setup for CentOS 7 host: [here](CentOS7_setup.md)

- Add a user with minimal permissions, who will be automatically logged in (will run the infoscreen script)
- Disable screen saver and screen lock for this user

### 2\. Install Python3 dependencies

```
$ sudo pip3 install -r requirements.txt
```

### 3\. Install Firefox Geckodriver

Selenium need the Geckodriver to interact with Firefox. Download it and add the path to the environment variable. <https://github.com/mozilla/geckodriver/releases>

### 4\. Download ffp_infoscreen

Clone the github repo to the previously created users home folder.

```
$ git clone /home/infoscreen/
```

### 5\. Setup ffp_infoscreen

Visit <https://infoscreen.florian10.info/ows/infoscreen/v3/> with Firefox and enable the displayed token in the admin interface to get an access cookie (this cookie is needed for further operation, do not delete it).

- ffp_infoscreen.py

  - Change path to the json config file (absolute path)

- ffp_infoscreen.json

  - Edit the sections for the screens.
  - Add the cookie (name and value) from Firefox to the wastl section, for each screen containing the infoscreen url and printing page.
  - Change log folder path.

### 6\. Add systemd unit and start

Systemd is used to keep the script alive and restart if it crashes.

Set the path to the python script in the ffp_infoscreen@.service file, then copy it to the Systemds system folder, enable and start under the user selected before!

```
$ sudo cp ffp_infoscreen@.service /etc/systemd/system
$ sudo systemctl enable ffp_infoscreen@user.service
$ sudo systemctl start ffp_infoscreen@user.service
```
