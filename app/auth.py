from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from app.models import Usuario
from app.utils import registrar_bitacora

auth_bp = Blueprint("auth", __name__)


def destino_por_rol(usuario):
    if usuario.rol == "admin":
        return url_for("admin.dashboard")
    return url_for("miembro.dashboard")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(destino_por_rol(current_user))

    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")

        usuario = Usuario.query.filter_by(username=username).first()

        if not usuario or not usuario.activo or not check_password_hash(usuario.password_hash, password):
            flash("Usuario o contraseña incorrectos.", "danger")
            return redirect(url_for("auth.login"))

        login_user(usuario)
        registrar_bitacora(usuario.id_usuario, "LOGIN", f"Inicio de sesión: {usuario.username}")
        return redirect(destino_por_rol(usuario))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    usuario_id = current_user.id_usuario
    username = current_user.username
    logout_user()
    registrar_bitacora(usuario_id, "LOGOUT", f"Cierre de sesión: {username}")
    return redirect(url_for("auth.login"))
