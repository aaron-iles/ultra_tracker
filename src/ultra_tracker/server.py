#!/usr/bin/env python3

import argparse
import datetime
import json
import hashlib
from collections import deque
import logging
import random
import time
import sys

import yaml
from flask import Flask, render_template, request, Response, session, stream_with_context
from flask import request, redirect, url_for, render_template_string, abort

from .models.caltopo import CaltopoMap, CaltopoSession
from .models.course import Course
from .models.race import Race, Runner
from .utils import format_duration

app = Flask(__name__)


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


class InMemoryLogHandler(logging.Handler):
    def __init__(self, max_logs=1000):
        super().__init__(level=logging.NOTSET)
        self.logs = deque(maxlen=max_logs)
        self.setFormatter(logging.Formatter("%(asctime)s   %(levelname)s   %(message)s", "%Y-%m-%d %H:%M:%S"))

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


def get_config_data(file_path: str) -> dict:
    """
    Reads in a yaml file and returns the dict.

    :param str file_path: The path to the file.
    :return dict: The parsed dict from the config file.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            yaml_content = yaml.safe_load(file)
        return yaml_content
    except FileNotFoundError:
        logger.info(f"Error: File '{file_path}' not found.")
        return None
    except yaml.YAMLError as e:
        logger.info(f"Error: YAML parsing error in '{file_path}': {e}")
        return None


def validate_config(config_data: dict):
    """ """
    # TODO
    mandatory_keys = {
        "admin_password_hash",
        "aid_stations",
        "caltopo_credential_id",
        "caltopo_key",
        "caltopo_map_id",
        "garmin_api_token",
        "race_name",
        "route_distance",
        "route_name",
        "runner_name",
        "start_time",
    }
    for key in mandatory_keys:
        assert key in config_data.keys(), f"Missing {key} in config file!"
    return


@app.route("/", methods=["GET"])
def get_race_stats():
    """
    Renders the webpage for the race statistics and monitoring.

    :return tuple: The rendered HTML page.
    """
    return render_template("race_stats.html", **race.html_stats)









@app.route("/login", methods=["GET", "POST"])
def login():
    """
    """
    error = None

    # Check for lockout
    if "lockout_until" in session:
        lockout_time = session["lockout_until"]
        if datetime.datetime.now(datetime.timezone.utc) < lockout_time:
            remaining = int((lockout_time - datetime.datetime.now(datetime.timezone.utc)).total_seconds())
            return render_template("login.html", error=f"Too many attempts. Try again in {remaining} seconds.")
        else:
            # Reset lockout once time has passed
            session.pop("lockout_until", None)
            session["failed_attempts"] = 0

    if request.method == "POST":
        entered_password = request.form["password"]
        entered_hash = hashlib.sha256(entered_password.encode()).hexdigest()

        if entered_hash == app.config["UT_ADMIN_PASSWORD_HASH"]:
            session["logged_in"] = True
            session.pop("failed_attempts", None)
            return redirect(url_for("get_logs"))
        else:
            session["failed_attempts"] = session.get("failed_attempts", 0) + 1
            if session["failed_attempts"] >= 5:
                session["lockout_until"] = datetime.datetime.utcnow() + datetime.timedelta(seconds=30)
                error = "Too many incorrect attempts. Login disabled for 30 seconds."
            else:
                error = f"Incorrect password. Attempts left: {5 - session['failed_attempts']}"

    return render_template("login.html", error=error)







@app.route("/logs")
def get_logs():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    log_handler = logging.root.handlers[1]  # your InMemoryLogHandler

    if request.headers.get("Accept") == "text/event-stream":
        @stream_with_context
        def event_stream():
            seen = 0
            while True:
                logs = log_handler.get_logs()
                if len(logs) > seen:
                    for line in logs[seen:]:
                        yield f"data: {line}\n\n"
                    seen = len(logs)
                time.sleep(1)

        return Response(event_stream(), mimetype="text/event-stream")
    return render_template("logs.html")

#@app.route("/logs", methods=["GET"])
#def get_logs():
#    """
#    Renders the webpage for the race statistics and monitoring.
#
#    :return tuple: The rendered HTML page.
#    """
#    if not session.get("logged_in"):
#        return redirect(url_for("login"))
#    log_output = "\n".join(logging.root.handlers[1].get_logs()[::-1])
#    return Response(log_output, mimetype="text/plain")


@app.route("/", methods=["POST"])
def post_data():
    """
    Receives a ping from the tracker, updates the race object, and logs information.

    :return tuple: The HTTP response.
    """
    if request.headers.get("x-outbound-auth-token") != app.config["UT_GARMIN_API_TOKEN"]:
        logger.error("Invalid or missing auth token in {request.headers}")
        return "Invalid or missing auth token", 401
    content_length = request.headers.get("Content-Length", 0)
    if not content_length:
        logger.error("Content-Length header is missing or zero")
        return "Content-Length header is missing or zero", 411
    payload = request.get_data(as_text=True)
    with open(f"{app.config['UT_DATA_DIR']}/post_log.txt", "a", encoding="ascii") as file:
        file.write(f"{payload}\n")
    app.config["UT_RACE"].ingest_ping(json.loads(payload))
    return "OK", 200


# Read in the config file.
args = parse_args()
# TODO: Need to validate values and keys.
config_data = get_config_data(args.config)
validate_config(config_data)
setup_logging(args.verbose)
logger = logging.getLogger(__name__)
# Create the objects to manage the race.
caltopo_session = CaltopoSession(config_data["caltopo_credential_id"], config_data["caltopo_key"])
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
