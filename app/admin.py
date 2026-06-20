from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import func
from werkzeug.security import generate_password_hash
from datetime import datetime
from app import db
from app.models import Usuario, Miembro, Actividad, AsistenciaPuntos, Rango
from app.utils import role_required, normalizar_texto, registrar_bitacora

admin_bp = Blueprint("admin", __name__)


def generar_username_unico(primer_apellido, primer_nombre):
    """Genera usuario con primerapellido.primernombre y evita duplicados."""
    base = f"{normalizar_texto(primer_apellido)}.{normalizar_texto(primer_nombre)}".strip(".")
    if not base or base == ".":
        base = "miembro"

    username = base
    contador = 2
    while Usuario.query.filter_by(username=username).first():
        username = f"{base}{contador}"
        contador += 1
    return username


def resumen_miembros():
    miembros = Miembro.query.join(Usuario).order_by(Miembro.nombre_completo.asc()).all()
    resumen = []

    for miembro in miembros:
        total_puntos = db.session.query(func.coalesce(func.sum(AsistenciaPuntos.puntos), 0)).filter_by(id_miembro=miembro.id_miembro).scalar() or 0
        asistencias = AsistenciaPuntos.query.filter_by(id_miembro=miembro.id_miembro, asistio=True).count()
        faltas = AsistenciaPuntos.query.filter_by(id_miembro=miembro.id_miembro, asistio=False).count()
        rango = miembro.rango_manual

        resumen.append({
            "miembro": miembro,
            "usuario": miembro.usuario,
            "total_puntos": int(total_puntos),
            "asistencias": asistencias,
            "faltas": faltas,
            "rango": rango
        })

    resumen.sort(key=lambda item: (-item["total_puntos"], -item["asistencias"], item["miembro"].nombre_completo))
    return resumen


@admin_bp.route("/")
@login_required
@role_required("admin")
def dashboard():
    resumen = resumen_miembros()
    total_miembros = Miembro.query.count()
    total_actividades = Actividad.query.count()
    total_puntos = sum(item["total_puntos"] for item in resumen)
    total_registros = AsistenciaPuntos.query.count()
    total_asistencias = AsistenciaPuntos.query.filter_by(asistio=True).count()
    tasa = round((total_asistencias / total_registros * 100), 1) if total_registros else 0

    ultimas_actividades = Actividad.query.order_by(Actividad.fecha_actividad.desc()).limit(5).all()
    top5 = resumen[:5]

    return render_template(
        "admin/dashboard.html",
        resumen=resumen,
        top5=top5,
        total_miembros=total_miembros,
        total_actividades=total_actividades,
        total_puntos=total_puntos,
        tasa=tasa,
        ultimas_actividades=ultimas_actividades
    )


@admin_bp.route("/miembros")
@login_required
@role_required("admin")
def miembros():
    rangos = Rango.query.order_by(Rango.id_rango.asc()).all()
    return render_template("admin/miembros.html", resumen=resumen_miembros(), rangos=rangos)


@admin_bp.route("/miembro/<int:id_miembro>/rango", methods=["POST"])
@login_required
@role_required("admin")
def actualizar_rango_miembro(id_miembro):
    miembro = Miembro.query.get_or_404(id_miembro)
    id_rango = request.form.get("id_rango_manual", "").strip()

    if id_rango:
        rango = Rango.query.get(int(id_rango))
        if not rango:
            flash("El rango seleccionado no existe.", "danger")
            return redirect(url_for("admin.miembros"))
        miembro.id_rango_manual = rango.id_rango
        detalle = f"{miembro.nombre_completo} -> {rango.nombre_rango}"
    else:
        miembro.id_rango_manual = None
        detalle = f"{miembro.nombre_completo} -> Sin rango"

    db.session.commit()
    registrar_bitacora(current_user.id_usuario, "ACTUALIZAR_RANGO", detalle)
    flash("Rango actualizado correctamente.", "success")
    return redirect(url_for("admin.miembros"))




@admin_bp.route("/miembro/nuevo", methods=["GET", "POST"])
@login_required
@role_required("admin")
def nuevo_miembro():
    """Crear cuentas de miembros. Esta función solo está disponible para admin."""
    if request.method == "POST":
        primer_nombre = request.form.get("primer_nombre", "").strip()
        segundo_nombre = request.form.get("segundo_nombre", "").strip()
        primer_apellido = request.form.get("primer_apellido", "").strip()
        segundo_apellido = request.form.get("segundo_apellido", "").strip()
        email = request.form.get("email", "").strip()
        estado = request.form.get("estado", "activo").strip() or "activo"
        password = request.form.get("password", "123456").strip() or "123456"
        username_manual = request.form.get("username", "").strip().lower()
        id_rango_manual = request.form.get("id_rango_manual", "").strip()

        if not primer_nombre or not primer_apellido:
            flash("El primer nombre y el primer apellido son obligatorios.", "danger")
            return redirect(url_for("admin.nuevo_miembro"))

        if len(password) < 6:
            flash("La contraseña inicial debe tener mínimo 6 caracteres.", "danger")
            return redirect(url_for("admin.nuevo_miembro"))

        username = username_manual or generar_username_unico(primer_apellido, primer_nombre)
        username = username.lower()

        if Usuario.query.filter_by(username=username).first():
            flash("Ese nombre de usuario ya existe. Usa otro usuario o deja el campo vacío para generarlo automáticamente.", "danger")
            return redirect(url_for("admin.nuevo_miembro"))

        partes_nombre = [primer_nombre, segundo_nombre, primer_apellido, segundo_apellido]
        nombre_completo = " ".join([p for p in partes_nombre if p]).strip()

        usuario = Usuario(
            username=username,
            password_hash=generate_password_hash(password),
            rol="miembro",
            activo=True,
            email=email or None
        )
        db.session.add(usuario)
        db.session.flush()

        miembro = Miembro(
            id_usuario=usuario.id_usuario,
            primer_nombre=primer_nombre.title(),
            segundo_nombre=segundo_nombre.title() if segundo_nombre else None,
            primer_apellido=primer_apellido.title(),
            segundo_apellido=segundo_apellido.title() if segundo_apellido else None,
            nombre_completo=nombre_completo.title(),
            estado=estado,
            id_rango_manual=int(id_rango_manual) if id_rango_manual else None
        )
        db.session.add(miembro)
        db.session.commit()

        registrar_bitacora(current_user.id_usuario, "CREAR_MIEMBRO", f"Cuenta creada: {username}")
        flash(f"Cuenta creada correctamente. Usuario: {username} | Contraseña inicial: {password}", "success")
        return redirect(url_for("admin.miembros"))

    rangos = Rango.query.order_by(Rango.id_rango.asc()).all()
    return render_template("admin/nuevo_miembro.html", rangos=rangos)


@admin_bp.route("/actividades")
@login_required
@role_required("admin")
def actividades():
    actividades = Actividad.query.order_by(Actividad.fecha_actividad.desc()).all()
    return render_template("admin/actividades.html", actividades=actividades)


@admin_bp.route("/actividad/nueva", methods=["GET", "POST"])
@login_required
@role_required("admin")
def nueva_actividad():
    if request.method == "POST":
        nombre = request.form.get("nombre_actividad", "").strip()
        fecha_txt = request.form.get("fecha_actividad", "")
        descripcion = request.form.get("descripcion", "").strip()
        puntos_referencia = int(request.form.get("puntos_referencia") or 0)

        if not nombre or not fecha_txt:
            flash("El nombre y la fecha son obligatorios.", "danger")
            return redirect(url_for("admin.nueva_actividad"))

        actividad = Actividad(
            nombre_actividad=nombre,
            fecha_actividad=datetime.strptime(fecha_txt, "%Y-%m-%d").date(),
            descripcion=descripcion,
            puntos_referencia=max(puntos_referencia, 0),
            creado_por=current_user.id_usuario
        )

        db.session.add(actividad)
        db.session.commit()
        registrar_bitacora(current_user.id_usuario, "CREAR_ACTIVIDAD", nombre)

        flash("Actividad creada. Ahora registra asistencias y puntos.", "success")
        return redirect(url_for("admin.registrar_asistencias", id_actividad=actividad.id_actividad))

    return render_template("admin/nueva_actividad.html")


@admin_bp.route("/actividad/<int:id_actividad>/asistencias", methods=["GET", "POST"])
@login_required
@role_required("admin")
def registrar_asistencias(id_actividad):
    actividad = Actividad.query.get_or_404(id_actividad)
    miembros = Miembro.query.order_by(Miembro.nombre_completo.asc()).all()

    if request.method == "POST":
        for miembro in miembros:
            asistio = request.form.get(f"asistio_{miembro.id_miembro}") == "on"
            puntos = int(request.form.get(f"puntos_{miembro.id_miembro}") or 0)
            observacion = request.form.get(f"observacion_{miembro.id_miembro}", "").strip()

            if not asistio:
                puntos = 0

            registro = AsistenciaPuntos.query.filter_by(
                id_actividad=actividad.id_actividad,
                id_miembro=miembro.id_miembro
            ).first()

            if not registro:
                registro = AsistenciaPuntos(
                    id_actividad=actividad.id_actividad,
                    id_miembro=miembro.id_miembro
                )
                db.session.add(registro)

            registro.asistio = asistio
            registro.puntos = max(puntos, 0)
            registro.observacion = observacion
            registro.registrado_por = current_user.id_usuario

        db.session.commit()
        registrar_bitacora(current_user.id_usuario, "REGISTRAR_ASISTENCIAS", actividad.nombre_actividad)
        flash("Asistencias y puntos guardados correctamente.", "success")
        return redirect(url_for("admin.actividades"))

    registros = {
        r.id_miembro: r
        for r in AsistenciaPuntos.query.filter_by(id_actividad=actividad.id_actividad).all()
    }

    return render_template("admin/registrar_asistencias.html", actividad=actividad, miembros=miembros, registros=registros)


@admin_bp.route("/actividad/<int:id_actividad>/eliminar", methods=["POST"])
@login_required
@role_required("admin")
def eliminar_actividad(id_actividad):
    actividad = Actividad.query.get_or_404(id_actividad)
    nombre = actividad.nombre_actividad
    db.session.delete(actividad)
    db.session.commit()
    registrar_bitacora(current_user.id_usuario, "ELIMINAR_ACTIVIDAD", nombre)
    flash("Actividad eliminada.", "success")
    return redirect(url_for("admin.actividades"))
