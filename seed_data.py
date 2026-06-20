import json
import argparse
from pathlib import Path
from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import Usuario, Miembro, Rango, Actividad, AsistenciaPuntos


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "seed_data.json"


def reset_database():
    db.drop_all()
    db.create_all()


def ensure_ranges():
    rangos = [
        ("Bronce", 0, 199, "#CD7F32", "Miembro inicial o en integración."),
        ("Plata", 200, 499, "#C0C0C0", "Miembro con participación constante."),
        ("Oro", 500, 799, "#FFD700", "Miembro destacado por asistencia y puntos."),
        ("Platino", 800, None, "#E5E4E2", "Miembro de alto compromiso y liderazgo."),
    ]

    for nombre, minimo, maximo, color, descripcion in rangos:
        if not Rango.query.filter_by(nombre_rango=nombre).first():
            db.session.add(Rango(
                nombre_rango=nombre,
                puntos_min=minimo,
                puntos_max=maximo,
                color_hex=color,
                descripcion=descripcion
            ))

    db.session.commit()


def ensure_admin():
    admin = Usuario.query.filter_by(username="admin").first()
    if not admin:
        admin = Usuario(
            username="admin",
            password_hash=generate_password_hash("admin123"),
            rol="admin",
            activo=True
        )
        db.session.add(admin)
        db.session.commit()
    return admin


def import_seed_data():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    # Miembros
    for item in data["members"]:
        usuario = Usuario.query.filter_by(username=item["username"]).first()
        if not usuario:
            usuario = Usuario(
                username=item["username"],
                password_hash=generate_password_hash("123456"),
                rol="miembro",
                activo=True
            )
            db.session.add(usuario)
            db.session.flush()

        miembro = Miembro.query.filter_by(id_usuario=usuario.id_usuario).first()
        if not miembro:
            miembro = Miembro(
                id_usuario=usuario.id_usuario,
                primer_nombre=item["primer_nombre"],
                segundo_nombre=item.get("segundo_nombre"),
                primer_apellido=item["primer_apellido"],
                segundo_apellido=item.get("segundo_apellido"),
                nombre_completo=item["nombre_completo"],
                estado=item.get("estado", "activo")
            )
            db.session.add(miembro)

    db.session.commit()

    # Actividades
    import datetime as dt

    for item in data["activities"]:
        fecha = dt.date.fromisoformat(item["fecha"])
        actividad = Actividad.query.filter_by(
            nombre_actividad=item["nombre"],
            fecha_actividad=fecha
        ).first()

        if not actividad:
            actividad = Actividad(
                nombre_actividad=item["nombre"],
                fecha_actividad=fecha,
                descripcion=item.get("descripcion"),
                puntos_referencia=item.get("puntos_referencia", 100),
                creado_por=1
            )
            db.session.add(actividad)

    db.session.commit()

    # Registros
    miembros_por_usuario = {
        m.usuario.username: m
        for m in Miembro.query.join(Usuario).all()
    }

    actividades_por_clave = {
        (a.nombre_actividad, a.fecha_actividad.isoformat()): a
        for a in Actividad.query.all()
    }

    actividades_por_id_seed = {}
    for item in data["activities"]:
        actividades_por_id_seed[item["id"]] = actividades_por_clave[(item["nombre"], item["fecha"])]

    for item in data["attendance"]:
        miembro = miembros_por_usuario.get(item["member_username"])
        actividad = actividades_por_id_seed.get(item["activity_id"])

        if not miembro or not actividad:
            continue

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

        registro.asistio = bool(item["asistio"])
        registro.puntos = int(item["puntos"]) if item["asistio"] else 0
        registro.observacion = item.get("observacion")
        registro.registrado_por = 1

    db.session.commit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Borra y recrea todas las tablas antes de importar.")
    args = parser.parse_args()

    app = create_app()

    with app.app_context():
        if args.reset:
            reset_database()
        else:
            db.create_all()

        ensure_ranges()
        ensure_admin()
        import_seed_data()

        print("Base inicializada correctamente.")
        print("Admin: admin / admin123")
        print("Miembros: contraseña inicial 123456")


if __name__ == "__main__":
    main()
