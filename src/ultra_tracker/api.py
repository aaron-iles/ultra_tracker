
from flask import Blueprint, request, session, redirect, url_for, render_template, current_app
import hashlib
import logging
from flask import stream_with_context, request, Response
import time

#from .chat import CHAT_HISTORY, load_history

blueprint = Blueprint("root", __name__)



@blueprint.route("/", methods=["GET"])
def get_race_stats():
    """
    Renders the webpage for the race statistics and monitoring.

    :return tuple: The rendered HTML page.
    """
    race = current_app.config["UT_RACE"]
    return render_template("race_stats.html", **race.html_stats)


@blueprint.route("/", methods=["POST"])
def post_data():
    """
    Receives a ping from the tracker, updates the race object, and logs information.

    :return tuple: The HTTP response.
    """
    if request.headers.get("x-outbound-auth-token") != current_app.config["UT_GARMIN_API_TOKEN"]:
        logger.error("Invalid or missing auth token in {request.headers}")
        return "Invalid or missing auth token", 401
    content_length = request.headers.get("Content-Length", 0)
    if not content_length:
        logger.error("Content-Length header is missing or zero")
        return "Content-Length header is missing or zero", 411
    payload = request.get_data(as_text=True)
    with open(f"{current_app.config['UT_DATA_DIR']}/post_log.txt", "a", encoding="ascii") as file:
        file.write(f"{payload}\n")
    current_app.config["UT_RACE"].ingest_ping(json.loads(payload))
    return "OK", 200


@blueprint.route("/user", methods=["GET", "POST"])
def user():
    if request.method == "POST":
        requested_username  = request.form["username"]
        # TODO check that the username is not already taken.
        session["username"] = requested_username
        #load_history(current_app)
        return redirect(url_for("root.chat"))
    return render_template("user.html")


@blueprint.route("/chat")
def chat():
    if "username" not in session:
        return redirect(url_for("root.user"))
    return render_template("chat.html", username=session["username"])







@blueprint.route("/login", methods=["GET", "POST"])
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

        if entered_hash == current_app.config["UT_ADMIN_PASSWORD_HASH"]:
            session["logged_in"] = True
            session.pop("failed_attempts", None)
            return redirect(url_for("root.get_logs"))
        else:
            session["failed_attempts"] = session.get("failed_attempts", 0) + 1
            if session["failed_attempts"] >= 5:
                session["lockout_until"] = datetime.datetime.utcnow() + datetime.timedelta(seconds=30)
                error = "Too many incorrect attempts. Login disabled for 30 seconds."
            else:
                error = f"Incorrect password. Attempts left: {5 - session['failed_attempts']}"

    return render_template("login.html", error=error)







@blueprint.route("/logs")
def get_logs():
    if not session.get("logged_in"):
        return redirect(url_for("root.login"))
    # This is the InMemoryLogHandler
    log_handler = logging.root.handlers[1]

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
