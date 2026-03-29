#!/usr/bin/env bash

set -e

# Make the directory for user-level service.
mkdir /home/${USER}/.config/systemd/user/
cp ultra-tracker.service /home/${USER}/.config/systemd/user/

# Enable lingering
sudo loginctl enable-linger ${USER}
systemctl --user daemon-reload
