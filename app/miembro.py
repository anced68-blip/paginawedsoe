from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from app import db
from app.models import Miembro, AsistenciaPuntos, Actividad, Usuario
from app.utils import role_required, normalizar_texto, registrar_bitacora

miembro_bp = Blueprint("miembro", __name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def archivo_permitido(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def datos_miembro(usuario):
    miembro = usuario.miembro
    total_puntos = db.session.query(func.coalesce(func.sum(AsistenciaPuntos.puntos), 0)).filter_by(id_miembro=miembro.id_miembro).scalar() or 0
    asistencias = AsistenciaPuntos.query.filter_by(id_miembro=miembro.id_miembro, asistio=True).count()
    faltas = AsistenciaPuntos.query.filter_by(id_miembro=miembro.id_miembro, asistio=False).count()
    rango = miembro.rango_manual

    historial = (
        db.session.query(AsistenciaPuntos, Actividad)
        .join(Actividad, Actividad.id_actividad == AsistenciaPuntos.id_actividad)
        .filter(AsistenciaPuntos.id_miembro == miembro.id_miembro)
        .order_by(Actividad.fecha_actividad.desc())
        .all()
    )

    return miembro, int(total_puntos), asistencias, faltas, rango, historial


@miembro_bp.route("/")
@login_required
@role_required("miembro")
def dashboard():
    miembro, total_puntos, asistencias, faltas, rango, historial = datos_miembro(current_user)
    return render_template(
        "miembro/dashboard.html",
        miembro=miembro,
        total_puntos=total_puntos,
        asistencias=asistencias,
        faltas=faltas,
        rango=rango,
        historial=historial
    )


@miembro_bp.route("/perfil", methods=["GET", "POST"])
@login_required
@role_required("miembro")
def perfil():
    miembro = current_user.miembro

    if request.method == "POST":
        accion = request.form.get("accion")

        if accion == "datos":
            nuevo_username = request.form.get("username", "").strip().lower()
            email = request.form.get("email", "").strip()

            if not nuevo_username:
                flash("El usuario no puede estar vacío.", "danger")
                return redirect(url_for("miembro.perfil"))

            existe = Usuario.query.filter(Usuario.username == nuevo_username, Usuario.id_usuario != current_user.id_usuario).first()
            if existe:
                flash("Ese nombre de usuario ya está en uso.", "danger")
                return redirect(url_for("miembro.perfil"))

            current_user.username = nuevo_username
            current_user.email = email
            db.session.commit()
            registrar_bitacora(current_user.id_usuario, "ACTUALIZAR_PERFIL", "Datos de usuario actualizados")
            flash("Datos actualizados correctamente.", "success")

        elif accion == "password":
            actual = request.form.get("password_actual", "")
            nueva = request.form.get("password_nueva", "")
            repetir = request.form.get("password_repetir", "")

            if not check_password_hash(current_user.password_hash, actual):
                flash("La contraseña actual no es correcta.", "danger")
                return redirect(url_for("miembro.perfil"))

            if len(nueva) < 6 or nueva != repetir:
                flash("La nueva contraseña debe tener mínimo 6 caracteres y coincidir.", "danger")
                return redirect(url_for("miembro.perfil"))

            current_user.password_hash = generate_password_hash(nueva)
            db.session.commit()
            registrar_bitacora(current_user.id_usuario, "CAMBIAR_PASSWORD", "Contraseña actualizada")
            flash("Contraseña actualizada correctamente.", "success")

        elif accion == "foto":
            archivo = request.files.get("foto_perfil")

            if not archivo or archivo.filename == "":
                flash("Selecciona una imagen.", "danger")
                return redirect(url_for("miembro.perfil"))

            if not archivo_permitido(archivo.filename):
                flash("Formato no permitido. Usa PNG, JPG, JPEG o WEBP.", "danger")
                return redirect(url_for("miembro.perfil"))

            ext = archivo.filename.rsplit(".", 1)[1].lower()
            filename = secure_filename(f"perfil_{current_user.id_usuario}.{ext}")
            ruta = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            archivo.save(ruta)

            current_user.foto_perfil = f"uploads/{filename}"
            db.session.commit()
            registrar_bitacora(current_user.id_usuario, "SUBIR_FOTO", "Foto de perfil actualizada")
            flash("Foto de perfil actualizada.", "success")

        return redirect(url_for("miembro.perfil"))

    return render_template("miembro/perfil.html", miembro=miembro)
