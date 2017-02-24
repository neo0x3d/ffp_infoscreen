# FFP_Infoscreen

NOTE: Not all components are published yet!

Display helpful information for the volunteer fire department depending on current WASTL status.

## Setup

### 1\. Install Python3 dependencies

```
$ sudo pip3 install requirements.txt
```

### 2\. Prepare host system

Example setup for CentOS 7 host: [here](CentOS7_setup.md)

- Add a user with minimal permissions, who will be automatically logged in (will run the infoscreen script)
- Disable screen saver and screen lock for this user

### 3\. Download ffp_infoscreen

Clone the github repo to the previously created users home folder.

```
$ git clone /home/infoscreen/
```

### 4\. Setup ffp_infoscreen

Visit <https://infoscreen.florian10.info/ows/infoscreen/v3/> with Firefox and enable the displayed token in the admin interface to get an access cookie (this cookie is needed for further operation, do not delete it).

- ffp_infoscreen.py

  - Change path to the json config file (absolute path)

- ffp_infoscreen.json

  - Add the cookie (name and value) from Firefox to the wastl section.
  - Change log folder path.
  - Edit the sections for die screens.

### 5\. Add systemd unit and start

Systemd is used to keep the script alive and restart if it crashes.

Set the path to the python script in the ffp_infoscreen@.service file, then copy it to the systemds system folder, enable and start under the user selected before.

```
$ sudo cp ffp_infoscreen@.service /etc/systemd/system
$ sudo systemctl enable ffp_infoscreen@user.service
$ sudo systemctl start ffp_infoscreen@user.service
```
