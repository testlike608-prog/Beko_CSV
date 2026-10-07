from flask import Blueprint
from flask import render_template, request, redirect, url_for, session



flash = Blueprint(
    "flash",
    __name__,
    static_folder="static",
    template_folder="templates"
)

@flash.route("/loading")
def loading():
    return render_template("page_splash_HTML.html")