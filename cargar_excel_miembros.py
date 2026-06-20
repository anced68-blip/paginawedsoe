"""
Carga miembros, actividades, asistencias y puntos desde el Excel del proyecto.

Archivo esperado:
    data/puntos_miembros_actualizados.xlsx

Usuarios generados:
    primerapellido.primernombre

Contraseñas iniciales:
    admin    -> admin123
    miembros -> 123456

Uso:
    python cargar_excel_miembros.py
    python cargar_excel_miembros.py --reset
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Tuple, Any, List

from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import Usuario, Miembro, Rango, Actividad, AsistenciaPuntos


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_EXCEL = BASE_DIR / "data" / "puntos_miembros_actualizados.xlsx"
USUARIOS_GENERADOS = BASE_DIR / "usuarios_generados.txt"

# En el Excel hay un caso donde los apellidos están primero.
# Formato: Apellido1 Apellido2 Nombre1 Nombre2
APELLIDOS_PRIMERO = {
    "castedo romero sigrid alieska",
}

SEGUNDOS_NOMBRES_COMUNES = {
    "valeria", "yetzebel", "david", "fernando", "manuel", "milena",
    "jesus", "farid", "michel", "araceyl", "belen", "belén", "nelva",
}

# Bloques detectados en tu Excel.
# title_col: columna donde está el nombre de la actividad en la fila 1.
# score_cols: columnas que se suman para calcular puntos.
# name_col: columna donde está el nombre del miembro; si es 1 usa la columna A.
ACTIVITY_BLOCKS = [
    {"title_col": 3,  "score_cols": [3, 4, 5, 6, 7],       "name_col": 1},   # Taller de Liderazgo
    {"title_col": 9,  "score_cols": [9, 10, 11, 12, 13],    "name_col": 1},   # Día del Niño
    {"title_col": 15, "score_cols": [15, 16, 17, 18, 19],   "name_col": 14},  # Glasswalking
    {"title_col": 22, "score_cols": [22, 23, 24, 25, 26],   "name_col": 21},  # Limpieza
    {"title_col": 29, "score_cols": [29, 30, 31, 32, 33],   "name_col": 28},  # Cascada
    {"title_col": 35, "score_cols": [35, 36, 37, 38, 39],   "name_col": 34},  # Quiz Game
    {"title_col": 41, "score_cols": [41, 42, 43, 44, 45],   "name_col": 40},  # Bienestar social
    {"title_col": 47, "score_cols": [47, 48, 49, 50, 51],   "name_col": 46},  # Décimo aniversario
    {"title_col": 54, "score_cols": [54, 55, 56, 57, 58],   "name_col": 53},  # Comicon SOE
]


def col_to_index(col: str) -> int:
    n = 0
    for ch in col:
        n = n * 26 + ord(ch.upper()) - 64
    return n


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto or "")
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^a-zA-Z0-9]+", "", texto.lower())
    return texto


def normalizar_clave(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto or "")
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"\s+", " ", texto.strip().lower())
    return texto


def limpiar_texto(valor: Any) -> str:
    if valor is None:
        return ""
    return str(valor).strip()


def numero(valor: Any) -> int:
    if valor is None or valor == "":
        return 0
    try:
        return int(float(valor))
    except Exception:
        return 0


def leer_xlsx(path: Path) -> Dict[Tuple[int, int], Any]:
    """Lee la primera hoja de un .xlsx sin depender de openpyxl."""
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el Excel: {path}")

    ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

    with zipfile.ZipFile(path) as z:
        shared: List[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            root_s = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root_s.findall("a:si", ns):
                shared.append("".join(t.text or "" for t in si.findall(".//a:t", ns)))

        sheet_xml = z.read("xl/worksheets/sheet1.xml")
        root = ET.fromstring(sheet_xml)

        data: Dict[Tuple[int, int], Any] = {}
        for cell in root.findall(".//a:c", ns):
            ref = cell.attrib.get("r", "")
            match = re.match(r"([A-Z]+)(\d+)", ref)
            if not match:
                continue

            col = col_to_index(match.group(1))
            row = int(match.group(2))
            cell_type = cell.attrib.get("t")
            v = cell.find("a:v", ns)

            value: Any = None
            if v is not None:
                raw = v.text
                if cell_type == "s":
                    value = shared[int(raw)] if raw is not None else ""
                else:
                    try:
                        value = int(raw) if raw and "." not in raw else float(raw)
                    except Exception:
                        value = raw

            data[(row, col)] = value

    return data


def parsear_fecha_actividad(titulo: str) -> dt.date:
    """Extrae fechas tipo 28/03 del título y usa año 2026."""
    match = re.search(r"(\d{1,2})\s*/\s*(\d{1,2})", titulo)
    if not match:
        return dt.date.today()

    dia = int(match.group(1))
    mes = int(match.group(2))
    return dt.date(2026, mes, dia)


def nombre_actividad_limpio(titulo: str) -> str:
    return re.sub(r"\s*\d{1,2}\s*/\s*\d{1,2}\s*", "", titulo).strip().title()


def dividir_nombre(nombre_completo: str) -> dict:
    partes = [p for p in re.split(r"\s+", nombre_completo.strip()) if p]

    if len(partes) == 0:
        raise ValueError("Nombre vacío")

    clave = normalizar_clave(nombre_completo)

    if clave in APELLIDOS_PRIMERO and len(partes) >= 4:
        primer_apellido = partes[0]
        segundo_apellido = partes[1]
        primer_nombre = partes[2]
        segundo_nombre = " ".join(partes[3:]) or None
    elif len(partes) == 1:
        primer_nombre = partes[0]
        segundo_nombre = None
        primer_apellido = partes[0]
        segundo_apellido = None
    elif len(partes) == 2:
        primer_nombre = partes[0]
        segundo_nombre = None
        primer_apellido = partes[1]
        segundo_apellido = None
    elif len(partes) == 3:
        # Si el segundo término parece segundo nombre, el apellido es el último.
        # Si no, asumimos: nombre + apellido1 + apellido2.
        if normalizar(partes[1]) in {normalizar(x) for x in SEGUNDOS_NOMBRES_COMUNES}:
            primer_nombre = partes[0]
            segundo_nombre = partes[1]
            primer_apellido = partes[2]
            segundo_apellido = None
        else:
            primer_nombre = partes[0]
            segundo_nombre = None
            primer_apellido = partes[1]
            segundo_apellido = partes[2]
    else:
        primer_nombre = partes[0]
        segundo_nombre = partes[1]
        primer_apellido = partes[2]
        segundo_apellido = " ".join(partes[3:]) or None

    return {
        "primer_nombre": primer_nombre.title(),
        "segundo_nombre": segundo_nombre.title() if segundo_nombre else None,
        "primer_apellido": primer_apellido.title(),
        "segundo_apellido": segundo_apellido.title() if segundo_apellido else None,
        "nombre_completo": nombre_completo.strip(),
    }


def generar_username(primer_apellido: str, primer_nombre: str) -> str:
    base = f"{normalizar(primer_apellido)}.{normalizar(primer_nombre)}"
    username = base
    contador = 2

    while Usuario.query.filter_by(username=username).first():
        username = f"{base}{contador}"
        contador += 1

    return username


def obtener_filas_miembros(data: Dict[Tuple[int, int], Any]) -> list[int]:
    filas = []
    fila = 3
    while True:
        nombre = limpiar_texto(data.get((fila, 1)))
        if not nombre:
            break
        filas.append(fila)
        fila += 1
    return filas


def ensure_rangos():
    rangos = [
        ("Bronce", 0, 199, "#CD7F32", "Miembro inicial o en integración."),
        ("Plata", 200, 499, "#C0C0C0", "Miembro con participación constante."),
        ("Oro", 500, 799, "#FFD700", "Miembro destacado por asistencia y puntos."),
        ("Platino", 800, None, "#E5E4E2", "Miembro de alto compromiso y liderazgo."),
    ]

    for nombre, minimo, maximo, color, descripcion in rangos:
        rango = Rango.query.filter_by(nombre_rango=nombre).first()
        if not rango:
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


def cargar_datos(excel_path: Path):
    data = leer_xlsx(excel_path)
    filas = obtener_filas_miembros(data)

    if not filas:
        raise RuntimeError("No se encontraron miembros en la columna A del Excel.")

    ensure_rangos()
    admin = ensure_admin()

    # 1. Crear miembros y usuarios.
    miembros_por_nombre = {}
    credenciales = []

    for fila in filas:
        nombre_completo = limpiar_texto(data.get((fila, 1)))
        estado = limpiar_texto(data.get((fila, 2))).lower() or "activo"
        estado = "activo" if estado in ("activos", "activo") else estado

        partes = dividir_nombre(nombre_completo)

        miembro = Miembro.query.filter_by(nombre_completo=nombre_completo).first()
        if miembro:
            usuario = miembro.usuario
        else:
            username = generar_username(partes["primer_apellido"], partes["primer_nombre"])
            usuario = Usuario(
                username=username,
                password_hash=generate_password_hash("123456"),
                rol="miembro",
                activo=True
            )
            db.session.add(usuario)
            db.session.flush()

            miembro = Miembro(
                id_usuario=usuario.id_usuario,
                primer_nombre=partes["primer_nombre"],
                segundo_nombre=partes["segundo_nombre"],
                primer_apellido=partes["primer_apellido"],
                segundo_apellido=partes["segundo_apellido"],
                nombre_completo=partes["nombre_completo"],
                estado=estado
            )
            db.session.add(miembro)
            db.session.flush()

        miembros_por_nombre[nombre_completo] = miembro
        credenciales.append((nombre_completo, usuario.username, "123456"))

    db.session.commit()

    # 2. Crear actividades.
    actividades_por_bloque = []
    for bloque in ACTIVITY_BLOCKS:
        titulo = limpiar_texto(data.get((1, bloque["title_col"])))
        if not titulo:
            continue

        fecha = parsear_fecha_actividad(titulo)
        nombre = nombre_actividad_limpio(titulo)

        actividad = Actividad.query.filter_by(
            nombre_actividad=nombre,
            fecha_actividad=fecha
        ).first()

        puntos_ref = sum(numero(data.get((fila, col))) for fila in filas for col in bloque["score_cols"])
        puntos_ref = int(round(puntos_ref / max(len(filas), 1)))

        if not actividad:
            actividad = Actividad(
                nombre_actividad=nombre,
                fecha_actividad=fecha,
                descripcion=f"Actividad importada desde Excel: {titulo}",
                puntos_referencia=max(puntos_ref, 0),
                creado_por=admin.id_usuario
            )
            db.session.add(actividad)
            db.session.flush()

        actividades_por_bloque.append((bloque, actividad))

    db.session.commit()

    # 3. Crear asistencias y puntos.
    registros_creados = 0
    for bloque, actividad in actividades_por_bloque:
        for fila in filas:
            nombre_global = limpiar_texto(data.get((fila, 1)))
            nombre_bloque = limpiar_texto(data.get((fila, bloque["name_col"])))
            nombre = nombre_bloque or nombre_global
            miembro = miembros_por_nombre.get(nombre) or miembros_por_nombre.get(nombre_global)

            if not miembro:
                continue

            puntos = sum(numero(data.get((fila, col))) for col in bloque["score_cols"])
            asistio = puntos > 0

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
                registros_creados += 1

            registro.asistio = asistio
            registro.puntos = int(puntos) if asistio else 0
            registro.observacion = "Importado desde Excel" if asistio else "Falta importada desde Excel"
            registro.registrado_por = admin.id_usuario

    db.session.commit()

    # 4. Guardar credenciales para revisar.
    lineas = [
        "CREDENCIALES GENERADAS",
        "========================",
        "",
        "ADMIN:",
        "usuario: admin",
        "contraseña: admin123",
        "",
        "MIEMBROS:",
        "contraseña inicial para todos: 123456",
        "",
    ]

    for nombre, username, password in sorted(credenciales, key=lambda x: x[0]):
        lineas.append(f"{nombre} -> usuario: {username} | contraseña: {password}")

    USUARIOS_GENERADOS.write_text("\n".join(lineas), encoding="utf-8")

    print("Carga completada correctamente.")
    print(f"Miembros procesados: {len(miembros_por_nombre)}")
    print(f"Actividades procesadas: {len(actividades_por_bloque)}")
    print(f"Registros de asistencia/puntos creados o actualizados: {registros_creados}")
    print(f"Credenciales guardadas en: {USUARIOS_GENERADOS}")
    print("Admin: admin / admin123")
    print("Miembros: contraseña inicial 123456")


def main():
    parser = argparse.ArgumentParser(description="Carga datos del Excel de miembros a PostgreSQL.")
    parser.add_argument("--excel", default=str(DEFAULT_EXCEL), help="Ruta del archivo .xlsx")
    parser.add_argument("--reset", action="store_true", help="Borra y recrea todas las tablas antes de cargar.")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        if args.reset:
            print("Reiniciando base de datos...")
            db.drop_all()
            db.create_all()
        else:
            db.create_all()

        cargar_datos(Path(args.excel))


if __name__ == "__main__":
    main()
