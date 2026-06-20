from app import db
from flask_login import UserMixin
from datetime import datetime, date


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id_usuario = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    rol = db.Column(db.String(20), nullable=False, default="miembro")
    activo = db.Column(db.Boolean, nullable=False, default=True)
    foto_perfil = db.Column(db.Text)
    email = db.Column(db.String(150))
    fecha_creacion = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    miembro = db.relationship("Miembro", back_populates="usuario", uselist=False, cascade="all, delete")

    def get_id(self):
        return str(self.id_usuario)

    @property
    def is_admin(self):
        return self.rol == "admin"

    @property
    def is_miembro(self):
        return self.rol == "miembro"


class Miembro(db.Model):
    __tablename__ = "miembros"

    id_miembro = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), unique=True, nullable=False)

    primer_nombre = db.Column(db.String(80), nullable=False)
    segundo_nombre = db.Column(db.String(80))
    primer_apellido = db.Column(db.String(80), nullable=False)
    segundo_apellido = db.Column(db.String(80))

    nombre_completo = db.Column(db.String(250), nullable=False)
    estado = db.Column(db.String(30), nullable=False, default="activo")
    id_rango_manual = db.Column(db.Integer, db.ForeignKey("rangos.id_rango"), nullable=True)
    fecha_ingreso = db.Column(db.Date, default=date.today)
    fecha_registro = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    usuario = db.relationship("Usuario", back_populates="miembro")
    rango_manual = db.relationship("Rango")
    asistencias = db.relationship("AsistenciaPuntos", back_populates="miembro", cascade="all, delete")


class Rango(db.Model):
    __tablename__ = "rangos"

    id_rango = db.Column(db.Integer, primary_key=True)
    nombre_rango = db.Column(db.String(30), unique=True, nullable=False)
    puntos_min = db.Column(db.Integer, nullable=False)
    puntos_max = db.Column(db.Integer)
    color_hex = db.Column(db.String(20))
    descripcion = db.Column(db.Text)


class Actividad(db.Model):
    __tablename__ = "actividades"

    id_actividad = db.Column(db.Integer, primary_key=True)
    nombre_actividad = db.Column(db.String(180), nullable=False)
    fecha_actividad = db.Column(db.Date, nullable=False)
    descripcion = db.Column(db.Text)
    puntos_referencia = db.Column(db.Integer, nullable=False, default=0)
    creado_por = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"))
    fecha_creacion = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    asistencias = db.relationship("AsistenciaPuntos", back_populates="actividad", cascade="all, delete")


class AsistenciaPuntos(db.Model):
    __tablename__ = "asistencias_puntos"

    id_registro = db.Column(db.Integer, primary_key=True)
    id_actividad = db.Column(db.Integer, db.ForeignKey("actividades.id_actividad", ondelete="CASCADE"), nullable=False)
    id_miembro = db.Column(db.Integer, db.ForeignKey("miembros.id_miembro", ondelete="CASCADE"), nullable=False)

    asistio = db.Column(db.Boolean, nullable=False, default=False)
    puntos = db.Column(db.Integer, nullable=False, default=0)
    observacion = db.Column(db.Text)

    registrado_por = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"))
    fecha_registro = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    actividad = db.relationship("Actividad", back_populates="asistencias")
    miembro = db.relationship("Miembro", back_populates="asistencias")

    __table_args__ = (
        db.UniqueConstraint("id_actividad", "id_miembro", name="uq_asistencia_actividad_miembro"),
    )


class Bitacora(db.Model):
    __tablename__ = "bitacora"

    id_bitacora = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"))
    accion = db.Column(db.String(100), nullable=False)
    detalle = db.Column(db.Text)
    ip = db.Column(db.String(80))
    fecha_hora = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
