#!/usr/bin/env python3

import hashlib
import logging
import time
import eventlet
from flask import (
    Blueprint,
    Response,
    current_app,
    redirect,
    render_template,
    request,
    session,
    stream_with_context,
    url_for,
)


URL_PREFIX = "/logs"


blueprint = Blueprint("logs", __name__)

@blueprint.route("/")
def get_logs():
    if not session.get("logged_in"):
        return redirect(url_for("logs.login"))
    for handler in logging.root.handlers:
        if handler.name == 'InMemoryLogHandler':
            log_handler = handler

    if request.headers.get("Accept") == "text/event-stream":

        @stream_with_context
        def event_stream():
            seen = 0
            try:
                while True:
                    logs = log_handler.get_logs()
                    if len(logs) > seen:
                        for line in logs[seen:]:
                            yield f"data: {line}\n\n"
                        seen = len(logs)
                    eventlet.sleep(1)
            except GeneratorExit:
                # Client disconnected
                return


           # while True:
           #     logs = log_handler.get_logs()
           #     if len(logs) > seen:
           #         for line in logs[seen:]:
           #             yield f"data: {line}\n\n"
           #         seen = len(logs)
           #     time.sleep(1)

        return Response(event_stream(), mimetype="text/event-stream")
    return render_template("logs.html")



@blueprint.route("/login", methods=["GET", "POST"])
def login():
    """ """
    error = None

    # Check for lockout
    if "lockout_until" in session:
        lockout_time = session["lockout_until"]
        if datetime.datetime.now(datetime.timezone.utc) < lockout_time:
            remaining = int(
                (lockout_time - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
            )
            return render_template(
                "login.html", error=f"Too many attempts. Try again in {remaining} seconds."
            )
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
            return redirect(url_for("logs.get_logs"))
        else:
            session["failed_attempts"] = session.get("failed_attempts", 0) + 1
            if session["failed_attempts"] >= 5:
                session["lockout_until"] = datetime.datetime.utcnow() + datetime.timedelta(
                    seconds=30
                )
                error = "Too many incorrect attempts. Login disabled for 30 seconds."
            else:
                error = f"Incorrect password. Attempts left: {5 - session['failed_attempts']}"

    return render_template("login.html", error=error)



