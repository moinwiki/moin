# Install Moin2 as systemd managed user service (podman quadlet)

Assumption: you've already created a container image with the tag `moin2` (see [../docker/Notes.md](../docker/Notes.md)).

Edit file `moin2.container` and adjust the configuration to your needs.

* path to the local wiki data folder (Volume)
* ...

Run this script to install the systemd user service `moin2`:

```bash
cp -p contrib/podman/moin2.container ~/.config/containers/systemd/moin2.container

systemctl --user daemon-reload
systemctl --user start moin2.service
systemctl --user status moin2.service
journalctl --user -xeu moin2.service
```
