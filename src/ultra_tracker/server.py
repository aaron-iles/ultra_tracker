#!/usr/bin/env python3

import argparse
import datetime
import json
import logging
import sys


import yaml
from flask import Flask, render_template, request
from .models.caltopo import CaltopoMap, CaltopoSession
from .models.course import Course
from .models.race import Race, Runner
from .utils import format_duration

app = Flask(__name__)


@app.template_filter("format_duration")
def format_duration_filter(duration):
    return format_duration(duration)


@app.template_filter("format_time")
def format_time(time_obj: datetime.datetime) ->str:
    """
    """
    if time_obj == datetime.datetime.fromtimestamp(0):
        return "--/-- --:--"
    return time_obj.strftime("%m/%d %H:%M")


def setup_logging(verbose: bool = False):
    """
    Configures the logging module to output log messages to stdout. This function sets up a stream
    handler to log messages to stdout with the specified logging format. It adds the stream handler
    to the root logger and sets the logging level.

    :param bool verbose: True if the application should be run verbosely and False otherwise.
    :return None:
    """
    # Define the logging format
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    # Create a stream handler to log to stdout since the application will log via journald.
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter(log_format))
    # Add the stream handler to the root logger
    logging.root.addHandler(stream_handler)
    # Set the logging level.
    logging.root.setLevel(logging.DEBUG if verbose else logging.INFO)


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
        with open(file_path, "r") as file:
            yaml_content = yaml.safe_load(file)
        return yaml_content
    except FileNotFoundError:
        logger.info(f"Error: File '{file_path}' not found.")
        return None
    except yaml.YAMLError as e:
        logger.info(f"Error: YAML parsing error in '{file_path}': {e}")
        return None


@app.route("/", methods=["GET"])
def get_race_stats():
    """
    Renders the webpage for the race statistics and monitoring.

    :return tuple: The rendered HTML page.
    """
    return render_template("race_stats.html", **race.html_stats)


@app.route("/", methods=["POST"])
def post_data():
    """
    Receives a ping from the tracker, updates the race object, and logs information.

    :return tuple: The HTTP response.
    """
    if request.headers.get("x-outbound-auth-token") != app.config["UT_GARMIN_API_TOKEN"]:
        return "Invalid or missing auth token", 401
    content_length = request.headers.get("Content-Length", 0)
    if not content_length:
        return "Content-Length header is missing or zero", 411
    payload = request.get_data(as_text=True)
    with open(f"{app.config['UT_DATA_DIR']}/post_log.txt", "a") as file:
        file.write(f"{payload}\n")
    app.config["UT_RACE"].ingest_ping(json.loads(payload))
    return "OK", 200


# TODO do race restoration here using pickle






# Read in the config file.
args = parse_args()
# TODO: Need to validate values and keys.
config_data = get_config_data(args.config)
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
course = Course(caltopo_map, config_data["aid_stations"], config_data["route_name"])
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
