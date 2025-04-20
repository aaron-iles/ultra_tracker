#!/usr/bin/env python3

import argparse
import os
import datetime
import logging
import random
import sys
import json
from collections import deque

import eventlet
import yaml
from flask import (
    Flask,
    Response,
    abort,
    redirect,
    render_template,
    render_template_string,
    request,
    session,
    stream_with_context,
    url_for,
)
from flask_socketio import SocketIO, send

from . import application, database
from .models.caltopo import CaltopoMap, CaltopoSession
from .models.course import Course
from .models.race import Race, Runner
from .utils import get_config_data
#from .chat import CHAT_HISTORY, load_history, save_history

log = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """
    Parses the arguments from the command line.

    :return argparse.Namespace: The namespace of the arguments that were parsed.
    """
    p = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="This is a description of my module.",
    )
    p.add_argument(
        "-c", required=True, type=str, dest="config", help="The config file for the event."
    )
    p.add_argument(
        "-d",
        required=False,
        default="/app/data",
        type=str,
        dest="data_dir",
        help="The directory in which to store data.",
    )
    p.add_argument(
        "--disable-marker-updates",
        required=False,
        action="store_true",
        dest="disable_marker_updates",
        help="Disables updating the marker location in Caltopo. Primarily used for testing.",
    )
    p.add_argument("-v", required=False, action="store_true", dest="verbose", help="Run verbosely.")
    return p.parse_args()


class InMemoryLogHandler(logging.Handler):
    def __init__(self, max_logs=1000):
        super().__init__(level=logging.NOTSET)
        self.logs = deque(maxlen=max_logs)
        self.setFormatter(
            logging.Formatter("%(asctime)s   %(levelname)s   %(message)s", "%Y-%m-%d %H:%M:%S")
        )

    def emit(self, record):
        self.logs.append(self.format(record))

    def get_logs(self):
        return list(self.logs)


def setup_logging(verbose: bool = False):
    """
    Configures the logging module to output log messages to stdout. This function sets up a stream
    handler to log messages to stdout with the specified logging format. It adds the stream handler
    to the root logger and sets the logging level.

    :param bool verbose: True if the application should be run verbosely and False otherwise.
    :return None:
    """
    # Define the logging format
    log_format = "%(asctime)s   %(levelname)s   %(message)s"
    # Create a stream handler to log to stdout since the application will log via journald.
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter(log_format, "%Y-%m-%d %H:%M:%S"))
    stream_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    # Add the stream handler to the root logger
    logging.root.addHandler(stream_handler)
    in_memory_log_handler = InMemoryLogHandler()
    logging.root.addHandler(in_memory_log_handler)
    # Set the logging level.
    logging.root.setLevel(logging.NOTSET)


args = parse_args()
database.connect(os.path.join('sqlite:///', args.data_dir, "ut_datastore.db"))
app, socketio = application.create_app(database.session)


#####################################

@app.template_filter("format_duration")
def format_duration_filter(duration: datetime.timedelta) -> str:
    """
    Formats a datetime.timedelta object to a human-friendly format.

    :param datetime.timedelta duration: The timedelta object to be formatted.
    :return str: The timedelta object as a presentable string.
    """
    return format_duration(duration)


@app.template_filter("format_time")
def format_time_filter(time_obj: datetime.datetime) -> str:
    """
    Formats a datetime.datetime object to a human-friendly format.

    :param datetime.datetime time_obj: The datetime object to be formatted.
    :return str: The human-friendly formatted time object.
    """
    if time_obj.astimezone(datetime.timezone.utc) == datetime.datetime.fromtimestamp(
        0, datetime.timezone.utc
    ):
        return "--/-- --:--"
    return time_obj.strftime("%-m/%-d %-I:%M %p")



# --- Persistence ---



#--- SocketIO Events ---



#####################

def start_application():
    config_data = get_config_data(args.config)
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    # Create the objects to manage the race.
    caltopo_session = CaltopoSession(
        config_data["caltopo_credential_id"], config_data["caltopo_key"]
    )
    logger.info("created session object...")
    caltopo_map = CaltopoMap(config_data["caltopo_map_id"], caltopo_session)
    logger.info("created map object...")
    logger.info("performing authentication test...")
    if not caltopo_map.test_authentication():
        exit(1)
    logger.info("authentication test passed...")
    course = Course(
        caltopo_map,
        config_data["aid_stations"],
        config_data["route_name"],
        config_data["route_distance"],
    )
    logger.info("created course object...")
    runner = Runner(
        caltopo_map,
        config_data["runner_name"],
        list(course.route.start_location),
        None,
        not args.disable_marker_updates,
    )
    logger.info("created runner object...")
    race = Race(
        config_data["race_name"],
        caltopo_map,
        course.timezone.localize(
            datetime.datetime.strptime(config_data["start_time"], "%Y-%m-%dT%H:%M:%S")
        ),
        f"{args.data_dir}/data_store.json",
        course,
        runner,
    )
    runner.race = race
    logger.info("created race object...")
    app.config["UT_GARMIN_API_TOKEN"] = config_data["garmin_api_token"]
    app.config["UT_RACE"] = race
    app.config["UT_DATA_DIR"] = args.data_dir
    app.config["UT_ADMIN_PASSWORD_HASH"] = config_data["admin_password_hash"]
    app.secret_key = random.randbytes(64).hex()
    #load_history()
    socketio.run(app, host="0.0.0.0", port=8080, debug=True)
    return
