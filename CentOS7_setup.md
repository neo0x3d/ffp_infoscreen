# Installation of CentOS 7

General purpose CentOS 7 installation with basic security measures and additional setup for:

- ffp_infoscreen (this repo)
- ffp_fotoupload (comming soon)

## Basic Installation

CentOS 7 can be setup headless (without X11 and DE), but since this computer will also be used as information display the setup includes the GNOME desktop.

1. Obtain the installation media from <https://www.centos.org/download/>, verify checksum afterwards.
2. Create a bootable media via dd or <https://rufus.akeo.ie/> on Windows
3. Boot with the "Test this media & install CentOS 7" option (default)
4. Select language & Keyboard
5. Install with following options:

  - Security Policy -> Common Profile for General-Purpose systems
  - Software Selection -> Minimal Install -> Security Tools
  - Software Selection -> Minimal Install -> Smart Card Support
  - Software Selection -> Compute Node -> Hardware Monitoring Utilities
  - Software Selection -> Compute Node -> Network File System Client
  - Software Selection -> Infrastructure Server -> FTP Server
  - Software Selection -> Infrastructure Server -> E-mail Server
  - Software Selection -> Infrastructure Server -> Remote Management for Linux
  - Software Selection -> GNOME Desktop -> GNOME Applications
  - Software Selection -> GNOME Desktop -> Internet Applications
  - Software Selection -> Development and Creative Workstation -> Python
  - Software Selection -> select "Server with GUI" click Done
  - Set up automatic partitioning
  - Enable Network connection

Update all system packages after the fresh installation

## Setup root mail forwarding and test it (requires MDA, e.g. Postfix running)

/etc/aliases

```
root: user@domain.tld
```

Test the forwarding

```
$ sudo newaliases
$ echo test | mail -s "test message" root
```

## Harden SSH access

/etc/ssh/sshd_config (only changes are listed)

```
Port somerandomport
Protocol 2
AllowUsers user1 user2
PermitRootLogin no
StrictModes yes
PermitEmptyPasswords no
PasswordAuthentication no
PubkeyAuthentication yes
AuthorizedKeysFile      .ssh/authorized_keys
RhostsRSAAuthentication no
UsePAM yes
ClientAliveInterval 600
ClientAliveCountMax 3
```

And install fail2ban to automatically ban IP adresses.

```
$ sudo yum install fail2ban
```

/etc/fail2ban/jail.conf

```
[DEFAULT]
# Ban hosts for one hour:
bantime = 3600

# Override /etc/fail2ban/jail.d/00-firewalld.conf:
banaction = iptables-multiport

[sshd]
enabled = true
```

```
$ sudo systemctl enable fail2ban
$ sudo systemctl start fail2ban
```

## Automatically install security updates

Automatically install security updates via yum-cron

```
$ sudo yum install yum-cron
```

/etc/yum/yum-cron.conf

```
update_cmd = security
apply_updates = yes
```

```
$ sudo systemctl enable yum-cron
$ sudo systemctl start yum-cron
```

## Switch the system log to persistent

Switch journald to persistant logging (logs will survive reboots). [Further information](https://www.digitalocean.com/community/tutorials/how-to-use-journalctl-to-view-and-manipulate-systemd-logs)

/etc/systemd/journald.conf

```
Storage=persistent
```
