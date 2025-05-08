#!/usr/bin/env python3

import hashlib
import logging
import time

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
URL_PREFIX = "/chat"

blueprint = Blueprint("chat", __name__)



@blueprint.route("/")
def run_chat():
    if "username" not in session:
        return redirect(url_for("chat.make_user"))
    return render_template("chat.html", username=session["username"])




@blueprint.route("/login", methods=["GET", "POST"])
def make_user():
    if request.method == "POST":
        requested_username = request.form["username"]
        # TODO check that the username is not already taken.
        session["username"] = requested_username
        # load_history(current_app)
        return redirect(url_for("chat.run_chat"))
    return render_template("user.html")



