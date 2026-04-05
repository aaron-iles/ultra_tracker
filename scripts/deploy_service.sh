#!/usr/bin/env bash

set -e

# Make the directory for user-level service.
mkdir -p ~/.config/systemd/user/
cp ultra-tracker.service ~/.config/systemd/user/

# Enable lingering
sudo loginctl enable-linger ${USER}
systemctl --user daemon-reload

systemctl --user enable ultra-tracker
