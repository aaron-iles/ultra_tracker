#!/usr/bin/env python3


import datetime
import os



import os
import json

CHAT_HISTORY = []


def load_history(app):
    if os.path.exists(f"{app.config['UT_DATA_DIR']}/chat_history.json"):
        with open(f"{app.config['UT_DATA_DIR']}/chat_history.json") as f:
            CHAT_HISTORY = json.load(f)


def save_history(app):
    with open(f"{app.config['UT_DATA_DIR']}/chat_history.json", "w") as f:
        json.dump(CHAT_HISTORY, f)


