from werkzeug.security import generate_password_hash

from app import create_app
from app.models import db, Usuario


def colocar_password(usuario, password_plano):
    nuevo_hash = generate_password_hash(password_plano)

    if hasattr(usuario, "password_hash"):
        usuario.password_hash = nuevo_hash
    elif hasattr(usuario, "contrasena_hash"):
        usuario.contrasena_hash = nuevo_hash
    elif hasattr(usuario, "password"):
        usuario.password = nuevo_hash
    else:
        raise AttributeError(
            "No se encontró columna de contraseña. Revisa si el modelo Usuario usa password_hash, contrasena_hash o password."
        )


app = create_app()

with app.app_context():
    # Resetear o crear admin
    admin = Usuario.query.filter_by(username="admin").first()

    if admin is None:
        admin = Usuario(
            username="admin",
            rol="admin",
            activo=True
        )
        db.session.add(admin)

    colocar_password(admin, "admin123")
    admin.rol = "admin"
    admin.activo = True

    # Resetear usuarios miembros existentes a 123456
    usuarios = Usuario.query.all()

    for usuario in usuarios:
        if usuario.username != "admin":
            colocar_password(usuario, "123456")
            usuario.activo = True

    db.session.commit()

    print("Contraseñas reseteadas correctamente.")
    print("Admin:")
    print("  usuario: admin")
    print("  contraseña: admin123")
    print("")
    print("Miembros:")
    print("  contraseña general: 123456")