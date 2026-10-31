# Directorio de Alérgenos

Web estática con un mapa Leaflet y un panel de administración. Los datos se guardan en SQLite mediante una API propia en FastAPI; Firebase ya no forma parte del funcionamiento de la aplicación.

## Ejecutar localmente

Se necesita Python 3.9 o posterior.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ADMIN_PASSWORD='elige-una-clave-segura' uvicorn app:app --reload
```

Abre <http://127.0.0.1:8000>. La base de datos se crea automáticamente en `data/restaurants.sqlite3`. El panel está en `/admin.html`. La contraseña solo se configura en el servidor mediante `ADMIN_PASSWORD`; no se guarda en el HTML.

## Importar y mantener los datos

El panel permite descargar el CSV actual e importar un CSV. Usa las columnas siguientes:

```text
id,name,type,lat,lng,hasMenu,menuType,menuSrc
```

- `id` puede quedar vacío para crear un restaurante. Para actualizar uno ya existente, exporta la base actual y conserva su `id`; si no se proporciona, se actualizará por nombre exacto sin distinguir mayúsculas.
- `name`, `lat` y `lng` son obligatorios; `type` contiene la dirección o zona que muestra la web.
- `hasMenu` acepta `true`/`false`, `si`/`no` o `1`/`0`. `menuType` es `pdf` o `images`.
- Para `menuType=images`, `menuSrc` puede ser una lista JSON, por ejemplo `["cartas/pagina1.jpg","cartas/pagina2.jpg"]`, o rutas separadas por comas. Para PDF es una sola ruta o URL.
- Importar añade o actualiza filas; no borra restaurantes que no estén en el archivo. Una importación inválida se rechaza sin aplicar cambios parciales.

Puedes usar [example_restaurants.csv](./example_restaurants.csv) como plantilla. También puedes importar directamente desde Python en el servidor:

```bash
python import_csv.py restaurantes.csv
```

Ese comando y la API utilizan la misma base SQLite. Para cambiar su ubicación define `DATABASE_PATH`, por ejemplo `/var/data/restaurants.sqlite3`. Haz copias de seguridad regulares de ese archivo.

## Publicación

GitHub Pages solo sirve archivos estáticos: no puede ejecutar FastAPI ni guardar una SQLite persistente. Para publicar la web en GitHub Pages, aloja `app.py` en un servicio que permita ejecutar Python y conservar un volumen/archivo persistente, y configura:

1. `ADMIN_PASSWORD` como secreto del servicio; usa HTTPS en producción.
2. `DATABASE_PATH` en un disco persistente del servicio. No uses una ruta efímera ni varias instancias que escriban cada una en su propia copia de SQLite.
3. `CORS_ORIGINS` con el origen exacto de GitHub Pages (por ejemplo, `https://usuario.github.io`).
4. `API_BASE_URL` en [api-config.js](./api-config.js) con la URL HTTPS de la API, sin barra final.

Como alternativa, el backend sirve también los archivos de esta carpeta: ejecuta Uvicorn y publica el sitio junto con la API desde el mismo servicio, usando la URL local/de producción en `api-config.js`.

## Datos que estaban en Firebase

Esta carpeta no contiene los registros de Firestore; únicamente contiene el código que los consultaba. Por tanto, la nueva SQLite empieza vacía. Antes de retirar o borrar el proyecto de Firebase, exporta los restaurantes, conviértelos al formato CSV anterior e impórtalos desde el panel o con `import_csv.py`. Las rutas de `menuSrc` deben seguir apuntando a archivos accesibles por la web.

## Pruebas

```bash
python -m unittest discover -s tests
```
