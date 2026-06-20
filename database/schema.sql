-- ============================================================
-- BASE DE DATOS: asistencia_miembros
-- Ejecutar en DBeaver conectado a la base asistencia_miembros
-- Este script crea las tablas principales.
-- ============================================================

DROP TABLE IF EXISTS bitacora CASCADE;
DROP TABLE IF EXISTS asistencias_puntos CASCADE;
DROP TABLE IF EXISTS actividades CASCADE;
DROP TABLE IF EXISTS miembros CASCADE;
DROP TABLE IF EXISTS rangos CASCADE;
DROP TABLE IF EXISTS usuarios CASCADE;

CREATE TABLE usuarios (
    id_usuario SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    rol VARCHAR(20) NOT NULL DEFAULT 'miembro',
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    foto_perfil TEXT,
    email VARCHAR(150),
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_rol_usuario CHECK (rol IN ('admin', 'miembro'))
);

CREATE TABLE rangos (
    id_rango SERIAL PRIMARY KEY,
    nombre_rango VARCHAR(30) UNIQUE NOT NULL,
    puntos_min INT NOT NULL,
    puntos_max INT,
    color_hex VARCHAR(20),
    descripcion TEXT,
    CONSTRAINT chk_rango_puntos CHECK (puntos_min >= 0 AND (puntos_max IS NULL OR puntos_max >= puntos_min))
);

CREATE TABLE miembros (
    id_miembro SERIAL PRIMARY KEY,
    id_usuario INT UNIQUE NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    primer_nombre VARCHAR(80) NOT NULL,
    segundo_nombre VARCHAR(80),
    primer_apellido VARCHAR(80) NOT NULL,
    segundo_apellido VARCHAR(80),
    nombre_completo VARCHAR(250) NOT NULL,
    estado VARCHAR(30) NOT NULL DEFAULT 'activo',
    id_rango_manual INT REFERENCES rangos(id_rango),
    fecha_ingreso DATE DEFAULT CURRENT_DATE,
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE actividades (
    id_actividad SERIAL PRIMARY KEY,
    nombre_actividad VARCHAR(180) NOT NULL,
    fecha_actividad DATE NOT NULL,
    descripcion TEXT,
    puntos_referencia INT NOT NULL DEFAULT 0,
    creado_por INT REFERENCES usuarios(id_usuario),
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_puntos_referencia CHECK (puntos_referencia >= 0)
);

CREATE TABLE asistencias_puntos (
    id_registro SERIAL PRIMARY KEY,
    id_actividad INT NOT NULL REFERENCES actividades(id_actividad) ON DELETE CASCADE,
    id_miembro INT NOT NULL REFERENCES miembros(id_miembro) ON DELETE CASCADE,
    asistio BOOLEAN NOT NULL DEFAULT FALSE,
    puntos INT NOT NULL DEFAULT 0,
    observacion TEXT,
    registrado_por INT REFERENCES usuarios(id_usuario),
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_asistencia_actividad_miembro UNIQUE (id_actividad, id_miembro),
    CONSTRAINT chk_puntos_no_negativos CHECK (puntos >= 0)
);

CREATE TABLE bitacora (
    id_bitacora SERIAL PRIMARY KEY,
    id_usuario INT REFERENCES usuarios(id_usuario),
    accion VARCHAR(100) NOT NULL,
    detalle TEXT,
    ip VARCHAR(80),
    fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
