# Sistema Web de Asistencias y Puntos

Sistema Flask para registrar asistencias, puntos por actividad y rangos de miembros: Bronce, Plata, Oro y Platino.

## Funciones principales

- Login para administrador y miembros.
- Admin:
  - Ver ranking.
  - Crear actividades.
  - Registrar asistencia con ✓ o falta con ✗.
  - Asignar puntos por miembro y por actividad.
- Miembro:
  - Ver puntos totales.
  - Ver rango actual.
  - Ver historial de actividades y puntos.
  - Subir foto de perfil.
  - Cambiar usuario, correo y contraseña.

## Usuarios iniciales

Después de ejecutar `seed_data.py`:

- Admin:
  - usuario: `admin`
  - contraseña: `admin123`

- Miembros:
  - usuario: `primerapellido.primernombre`
  - contraseña inicial: `123456`

Ejemplo: `alvarez.alejandra`

## Instalación en PowerShell

```powershell
cd C:\Users\ARIO\Desktop\asistencia_miembros_web

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Copy-Item .env.example .env
```

Edita `.env` si tu contraseña de PostgreSQL no es `123456`.

## Crear base de datos

En DBeaver crea una base llamada:

```text
asistencia_miembros
```

Puedes ejecutar `database/schema.sql`, o simplemente usar:

```powershell
python seed_data.py --reset
```

El script `seed_data.py --reset` crea las tablas y carga los miembros importados desde el Excel.

## Cargar datos iniciales

```powershell
python seed_data.py --reset
```

## Ejecutar

```powershell
python run.py
```

Abrir:

```text
http://127.0.0.1:5000/
```

## Nota

El archivo original del Excel está en:

```text
data/puntos_miembros_actualizados.xlsx
```

El sistema ya trae los datos procesados en:

```text
data/seed_data.json
```
