# Directorio de Alérgenos 🦆

Mapa de restaurantes con sus cartas de alérgenos. Es una web estática (HTML + JS, sin compilar) que se publica en GitHub Pages, con la base de datos en Supabase, igual que [Patagenda](https://agentepato.github.io/Patagenda/).

- **Mapa primero** con filtros rápidos: *Cerca de mí*, *Con carta de alérgenos* y los 14 alérgenos obligatorios (*Sin gluten*, *Sin lácteos*…).
- **＋ Añadir restaurante**: cualquiera busca un sitio (Google Maps u OpenStreetMap) y lo añade al mapa. La base de datos se actualiza al momento.
- **Panel del pato** (`admin.html`, botón del pato con bufanda): editar datos, subir la carta en PDF/imágenes o escribirla como **carta digital** plato a plato, que es la que permite filtrar.

## Estructura

```text
index.html, styles.css      Página pública (mapa, filtros, lista)
admin.html, admin.css       Panel de administración
img/                        Los dibujos de los patos
src/config.js               Claves de Supabase y Google Maps
src/main.js                 Lógica del mapa y del botón "Añadir restaurante"
src/admin.js                Lógica del panel
src/allergens.js            Los 14 alérgenos (claves, nombres, iconos)
src/api/                    Supabase, modo demo y buscador de sitios
data/restaurantes.json      Restaurantes iniciales (sacados de OpenStreetMap)
supabase/schema.sql         Tablas, permisos y funciones de la base de datos
supabase/seed.sql           Los mismos restaurantes iniciales, para Supabase
scripts/importar_osm.py     Regenera data/ y seed.sql desde OpenStreetMap
```

## Probar en local

```bash
python3 -m http.server 8000
```

Abre <http://localhost:8000>. Sin claves en `src/config.js` la web funciona en **modo demo**: lee `data/restaurantes.json` y lo que añadas o edites se guarda solo en tu navegador. En el panel, cualquier contraseña vale en modo demo.

## Poner la base de datos (Supabase, gratis)

1. Crea un proyecto en [supabase.com](https://supabase.com).
2. En **SQL Editor**, pega y ejecuta `supabase/schema.sql`, y después `supabase/seed.sql`.
3. Define la contraseña del panel ejecutando (cambiando el texto):
   ```sql
   insert into public.admin_secret (password_hash)
   values (extensions.crypt('tu-contraseña', extensions.gen_salt('bf')))
   on conflict (id) do update set password_hash = excluded.password_hash;
   ```
4. En **Project Settings → API**, copia la *Project URL* y la *anon/publishable key* en `src/config.js`. La clave anónima es pública por diseño: la web solo puede leer, y todo lo que escribe pasa por funciones que validan los datos (`add_restaurant`) o piden la contraseña (`admin_*`).

## Buscar en Google Maps al añadir (opcional)

Sin clave, el buscador de *Añadir restaurante* usa OpenStreetMap, que es gratis pero no tiene todos los locales. Para buscar en Google Maps:

1. En [Google Cloud Console](https://console.cloud.google.com/) crea un proyecto y activa **Places API (New)**.
2. Crea una clave de API y **restríngela** a *Places API (New)* y a tu dominio (`https://agentepato.github.io/*` y `http://localhost:8000/*`).
3. Pégala en `googleMapsApiKey` de `src/config.js`.

Google da un crédito mensual gratuito; revisa los precios actuales antes de activarlo.

## Los restaurantes iniciales

Google Maps no permite descargar ni copiar su base de datos de sitios, así que la carga inicial sale de **OpenStreetMap** (datos libres, licencia ODbL). Para regenerarla o cambiar de municipio:

```bash
python3 scripts/importar_osm.py "Tres Cantos"
```

Después vuelve a ejecutar `supabase/seed.sql` en Supabase (no duplica los que ya estén). OpenStreetMap no tiene todos los locales: los que falten se añaden desde el botón de la web, buscando en Google Maps si hay clave configurada. Si un sitio ya está (mismo nombre a menos de ~100 m), no se duplica.

## Cartas de alérgenos

Cada restaurante puede tener dos tipos de carta, y se pueden combinar:

- **Carta escaneada**: un PDF o varias imágenes. Sube los archivos a una carpeta `cartas/` del repositorio y pon la ruta en el panel (`cartas/vips.pdf`), o un enlace `https://`.
- **Carta digital**: en el panel, una línea por plato con el formato `Sección | Plato | alérgenos`:
  ```text
  Entrantes | Croquetas de jamón | gluten, lácteos, huevo
  Principales | Entrecot a la brasa |
  Postres | Tarta de queso | lácteos, huevo, gluten
  ```
  Solo las cartas digitales se pueden filtrar: al marcar *Sin gluten*, el mapa muestra los restaurantes con algún plato sin gluten y, dentro de la carta, tacha los que lo llevan.

Los platos se guardan en la tabla `dishes` de Supabase (`allergens` es una lista con las claves de `src/allergens.js`), así que también se pueden cargar en bloque con SQL o con un script.

## Publicar

Sube el repositorio a GitHub y activa **Settings → Pages** sobre la rama `main` (carpeta raíz). No hace falta servidor.
