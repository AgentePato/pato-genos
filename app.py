import csv
import hmac
import io
import json
import math
import os
import secrets
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional, Union
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel


ROOT = Path(__file__).resolve().parent
DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", ROOT / "data" / "restaurants.sqlite3"))
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
SESSION_TTL_SECONDS = 12 * 60 * 60
MAX_CSV_BYTES = 5 * 1024 * 1024
sessions: dict[str, float] = {}


def connect_db() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


@contextmanager
def database_connection():
    connection = connect_db()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_db() -> None:
    with database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS restaurants (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL DEFAULT '',
                lat REAL NOT NULL,
                lng REAL NOT NULL,
                has_menu INTEGER NOT NULL DEFAULT 0,
                menu_type TEXT NOT NULL DEFAULT '',
                menu_src TEXT NOT NULL DEFAULT '""'
            )
            """
        )


class LoginRequest(BaseModel):
    password: str


class RestaurantInput(BaseModel):
    name: str
    type: str = ""
    lat: float
    lng: float
    hasMenu: bool = False
    menuType: str = ""
    menuSrc: Union[str, list[str]] = ""


def validate_restaurant(data: dict[str, Any]) -> dict[str, Any]:
    name_value = data.get("name")
    name = name_value.strip() if isinstance(name_value, str) else ""
    if not name:
        raise ValueError("El nombre es obligatorio.")
    type_value = data.get("type") or ""
    if not isinstance(type_value, str):
        raise ValueError("La dirección debe ser texto.")
    restaurant_type = type_value.strip()

    try:
        lat = float(data["lat"])
        lng = float(data["lng"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Latitud y longitud deben ser números.") from error
    if not math.isfinite(lat) or not -90 <= lat <= 90:
        raise ValueError("La latitud debe estar entre -90 y 90.")
    if not math.isfinite(lng) or not -180 <= lng <= 180:
        raise ValueError("La longitud debe estar entre -180 y 180.")

    has_menu = data.get("hasMenu", False)
    if not isinstance(has_menu, bool):
        raise ValueError("hasMenu debe ser verdadero o falso.")
    menu_type = str(data.get("menuType", "")).strip() if has_menu else ""
    if has_menu and menu_type not in {"pdf", "images"}:
        raise ValueError("menuType debe ser 'pdf' o 'images' cuando hay carta.")

    menu_src = data.get("menuSrc") or ""
    if not has_menu:
        menu_src = ""
    elif menu_type == "images":
        if isinstance(menu_src, str):
            menu_src = [item.strip() for item in menu_src.split(",") if item.strip()]
        if not isinstance(menu_src, list) or not all(
            isinstance(item, str) and item.strip() for item in menu_src
        ):
            raise ValueError("menuSrc debe ser una lista de rutas de imagen.")
        menu_src = [item.strip() for item in menu_src]
        if any(not is_safe_menu_path(item) for item in menu_src):
            raise ValueError("Las rutas de las cartas solo pueden usar HTTP o HTTPS.")
    elif isinstance(menu_src, list):
        raise ValueError("menuSrc debe ser una ruta para las cartas PDF.")
    else:
        menu_src = str(menu_src).strip()
        if menu_src and not is_safe_menu_path(menu_src):
            raise ValueError("Las rutas de las cartas solo pueden usar HTTP o HTTPS.")

    return {
        "name": name,
        "type": restaurant_type,
        "lat": lat,
        "lng": lng,
        "hasMenu": has_menu,
        "menuType": menu_type,
        "menuSrc": menu_src,
    }


def is_safe_menu_path(path: str) -> bool:
    return urlsplit(path).scheme.lower() in {"", "http", "https"}


def row_to_restaurant(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "type": row["type"],
        "lat": row["lat"],
        "lng": row["lng"],
        "hasMenu": bool(row["has_menu"]),
        "menuType": row["menu_type"],
        "menuSrc": json.loads(row["menu_src"]),
    }


def write_restaurant(
    connection: sqlite3.Connection, restaurant_id: str, data: dict[str, Any]
) -> None:
    connection.execute(
        """
        INSERT INTO restaurants (id, name, type, lat, lng, has_menu, menu_type, menu_src)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            type = excluded.type,
            lat = excluded.lat,
            lng = excluded.lng,
            has_menu = excluded.has_menu,
            menu_type = excluded.menu_type,
            menu_src = excluded.menu_src
        """,
        (
            restaurant_id,
            data["name"],
            data["type"],
            data["lat"],
            data["lng"],
            int(data["hasMenu"]),
            data["menuType"],
            json.dumps(data["menuSrc"], ensure_ascii=False),
        ),
    )


def csv_bool(value: str) -> bool:
    normalized = value.strip().casefold()
    if normalized in {"true", "1", "si", "sí", "yes"}:
        return True
    if normalized in {"false", "0", "no", ""}:
        return False
    raise ValueError("hasMenu debe ser true/false, si/no o 1/0.")


def import_csv(connection: sqlite3.Connection, content: str) -> tuple[int, int]:
    reader = csv.DictReader(io.StringIO(content, newline=""))
    required = {"name", "type", "lat", "lng", "hasMenu", "menuType", "menuSrc"}
    fieldnames = reader.fieldnames or []
    if len(fieldnames) != len(set(fieldnames)):
        raise ValueError("El CSV no puede contener encabezados duplicados.")
    headers = set(fieldnames)
    missing = required - headers
    if missing:
        raise ValueError(f"Faltan columnas CSV obligatorias: {', '.join(sorted(missing))}.")

    entries: list[tuple[Optional[str], dict[str, Any], int]] = []
    seen_names_without_id: set[str] = set()
    seen_ids: set[str] = set()
    for row_number, row in enumerate(reader, start=2):
        if None in row:
            raise ValueError(f"Fila {row_number}: contiene más columnas de las indicadas.")
        if not any((value or "").strip() for value in row.values()):
            continue
        try:
            has_menu = csv_bool(row.get("hasMenu") or "")
            menu_src: Union[str, list[str]] = row.get("menuSrc") or ""
            if has_menu and (row.get("menuType") or "").strip() == "images":
                if menu_src.lstrip().startswith("["):
                    parsed = json.loads(menu_src)
                    if not isinstance(parsed, list):
                        raise ValueError("menuSrc debe ser una lista JSON de rutas.")
                    menu_src = parsed
                else:
                    menu_src = [item.strip() for item in menu_src.split(",") if item.strip()]
            data = validate_restaurant(
                {
                    "name": row.get("name"),
                    "type": row.get("type"),
                    "lat": row.get("lat"),
                    "lng": row.get("lng"),
                    "hasMenu": has_menu,
                    "menuType": row.get("menuType"),
                    "menuSrc": menu_src,
                }
            )
        except (ValueError, json.JSONDecodeError) as error:
            raise ValueError(f"Fila {row_number}: {error}") from error

        restaurant_id = (row.get("id") or "").strip() or None
        if restaurant_id:
            if restaurant_id in seen_ids:
                raise ValueError(f"Fila {row_number}: el id aparece duplicado en el CSV.")
            seen_ids.add(restaurant_id)
        else:
            normalized_name = data["name"].casefold()
            if normalized_name in seen_names_without_id:
                raise ValueError(
                    f"Fila {row_number}: el nombre aparece duplicado en el CSV."
                )
            seen_names_without_id.add(normalized_name)
        entries.append((restaurant_id, data, row_number))

    created = 0
    updated = 0
    try:
        with connection:
            for restaurant_id, data, row_number in entries:
                if restaurant_id:
                    exists = connection.execute(
                        "SELECT 1 FROM restaurants WHERE id = ?", (restaurant_id,)
                    ).fetchone()
                else:
                    matches = connection.execute(
                        "SELECT id FROM restaurants WHERE name = ? COLLATE NOCASE",
                        (data["name"],),
                    ).fetchall()
                    if len(matches) > 1:
                        raise ValueError(
                            f"Fila {row_number}: hay varios restaurantes con ese nombre; "
                            "incluye su id en el CSV."
                        )
                    exists = matches[0] if matches else None
                    restaurant_id = exists["id"] if exists else uuid.uuid4().hex

                write_restaurant(connection, restaurant_id, data)
                if exists:
                    updated += 1
                else:
                    created += 1
    except sqlite3.Error as error:
        raise RuntimeError(f"No se pudo guardar el CSV: {error}") from error
    return created, updated


def require_admin(authorization: Optional[str] = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Inicia sesión para continuar.")
    token = authorization.removeprefix("Bearer ")
    expires_at = sessions.get(token)
    if expires_at is None or expires_at < time.time():
        sessions.pop(token, None)
        raise HTTPException(status_code=401, detail="La sesión ha caducado. Vuelve a entrar.")
    return token


app = FastAPI(title="Directorio de Alérgenos API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.environ.get(
            "CORS_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000"
        ).split(",")
        if origin.strip()
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.on_event("startup")
def startup() -> None:
    initialize_db()


@app.get("/api/restaurants")
def get_restaurants() -> list[dict[str, Any]]:
    try:
        with database_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM restaurants ORDER BY name COLLATE NOCASE"
            ).fetchall()
            return [row_to_restaurant(row) for row in rows]
    except sqlite3.Error as error:
        raise HTTPException(status_code=500, detail="No se pudieron leer los restaurantes.") from error


@app.post("/api/admin/login")
def login(request: LoginRequest) -> dict[str, str]:
    if not ADMIN_PASSWORD:
        raise HTTPException(
            status_code=503, detail="Configura ADMIN_PASSWORD antes de usar el panel."
        )
    if not hmac.compare_digest(request.password, ADMIN_PASSWORD):
        raise HTTPException(status_code=401, detail="Contraseña incorrecta.")
    token = secrets.token_urlsafe(32)
    sessions[token] = time.time() + SESSION_TTL_SECONDS
    return {"token": token}


@app.post("/api/admin/restaurants", dependencies=[Depends(require_admin)], status_code=201)
def create_restaurant(restaurant: RestaurantInput) -> dict[str, Any]:
    try:
        data = validate_restaurant(restaurant.dict(by_alias=True))
        restaurant_id = uuid.uuid4().hex
        with database_connection() as connection:
            write_restaurant(connection, restaurant_id, data)
        return {"id": restaurant_id, **data}
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except sqlite3.Error as error:
        raise HTTPException(status_code=500, detail="No se pudo guardar el restaurante.") from error


@app.put(
    "/api/admin/restaurants/{restaurant_id}", dependencies=[Depends(require_admin)]
)
def update_restaurant(restaurant_id: str, restaurant: RestaurantInput) -> dict[str, Any]:
    try:
        data = validate_restaurant(restaurant.dict(by_alias=True))
        with database_connection() as connection:
            exists = connection.execute(
                "SELECT 1 FROM restaurants WHERE id = ?", (restaurant_id,)
            ).fetchone()
            if not exists:
                raise HTTPException(status_code=404, detail="Restaurante no encontrado.")
            write_restaurant(connection, restaurant_id, data)
        return {"id": restaurant_id, **data}
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except sqlite3.Error as error:
        raise HTTPException(status_code=500, detail="No se pudo actualizar el restaurante.") from error


@app.delete(
    "/api/admin/restaurants/{restaurant_id}",
    dependencies=[Depends(require_admin)],
    status_code=204,
)
def delete_restaurant(restaurant_id: str) -> Response:
    try:
        with database_connection() as connection:
            cursor = connection.execute(
                "DELETE FROM restaurants WHERE id = ?", (restaurant_id,)
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Restaurante no encontrado.")
        return Response(status_code=204)
    except sqlite3.Error as error:
        raise HTTPException(status_code=500, detail="No se pudo borrar el restaurante.") from error


@app.post("/api/admin/restaurants/import", dependencies=[Depends(require_admin)])
async def upload_csv(file: UploadFile = File(...)) -> dict[str, int]:
    if not file.filename or Path(file.filename).suffix.casefold() != ".csv":
        raise HTTPException(status_code=400, detail="Selecciona un archivo .csv.")
    content = await file.read(MAX_CSV_BYTES + 1)
    if len(content) > MAX_CSV_BYTES:
        raise HTTPException(status_code=413, detail="El CSV no puede superar 5 MB.")
    try:
        decoded = content.decode("utf-8-sig")
        with database_connection() as connection:
            created, updated = import_csv(connection, decoded)
        return {"created": created, "updated": updated}
    except UnicodeDecodeError as error:
        raise HTTPException(status_code=400, detail="El CSV debe estar codificado en UTF-8.") from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.get("/api/admin/restaurants/export", dependencies=[Depends(require_admin)])
def export_csv() -> StreamingResponse:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        ["id", "name", "type", "lat", "lng", "hasMenu", "menuType", "menuSrc"]
    )
    try:
        with database_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM restaurants ORDER BY name COLLATE NOCASE"
            ).fetchall()
            for row in rows:
                data = row_to_restaurant(row)
                menu_src = data["menuSrc"]
                if isinstance(menu_src, list):
                    menu_src = json.dumps(menu_src, ensure_ascii=False)
                writer.writerow(
                    [
                        data["id"],
                        data["name"],
                        data["type"],
                        data["lat"],
                        data["lng"],
                        str(data["hasMenu"]).lower(),
                        data["menuType"],
                        menu_src,
                    ]
                )
    except sqlite3.Error as error:
        raise HTTPException(status_code=500, detail="No se pudo exportar el CSV.") from error
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="restaurantes.csv"'},
    )


SITE_FILES = {
    name: ROOT / name
    for name in (
        "admin.html",
        "api-config.js",
        "dibujo.jpeg",
        "pato_boton.jpeg",
        "pato_fondo.jpeg",
        "style_admin.css",
        "style_index.css",
    )
}


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(ROOT / "index.html")


@app.get("/{filename}", include_in_schema=False)
def site_file(filename: str) -> FileResponse:
    file_path = SITE_FILES.get(filename)
    if file_path is None:
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")
    return FileResponse(file_path)
