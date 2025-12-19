from flask import Blueprint, render_template, request, redirect, session, url_for

auth_bp = Blueprint("auth", __name__)

# mock users
USERS = {
    "viewer": {"password": "1111", "role": "viewer"},
    "editor": {"password": "1234", "role": "editor"},
    "admin": {"password": "2121", "role": "admin"},
}

@auth_bp.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = USERS.get(username)
        if user and user["password"] == password:
            session["user"] = username
            session["role"] = user["role"]
            return redirect(url_for("home"))

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
