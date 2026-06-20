from functools import wraps
from flask import abort, request
from flask_login import current_user
from app import db
from app.models import Rango, Bitacora
import unicodedata
import re


def normalizar_texto(texto):
    texto = unicodedata.normalize("NFD", texto or "")
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^a-zA-Z0-9]+", "", texto.lower())
    return texto


def role_required(*roles):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)

            if current_user.rol == "admin":
                return func(*args, **kwargs)

            if current_user.rol not in roles:
                abort(403)

            return func(*args, **kwargs)
        return wrapper
    return decorator


def obtener_rango(total_puntos):
    total_puntos = int(total_puntos or 0)
    return (
        Rango.query
        .filter(Rango.puntos_min <= total_puntos)
        .filter((Rango.puntos_max == None) | (Rango.puntos_max >= total_puntos))
        .order_by(Rango.puntos_min.desc())
        .first()
    )


def registrar_bitacora(usuario_id, accion, detalle=""):
    try:
        db.session.add(Bitacora(
            id_usuario=usuario_id,
            accion=accion,
            detalle=detalle,
            ip=request.remote_addr
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()
