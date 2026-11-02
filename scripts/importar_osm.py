"""Descarga de OpenStreetMap todos los restaurantes, cafeterías y sitios de
comida rápida de un municipio y genera:

  data/restaurantes.json  → datos que usa la web en modo demo
  supabase/seed.sql       → los mismos datos para cargarlos en Supabase

Uso:
  python3 scripts/importar_osm.py                  # Tres Cantos
  python3 scripts/importar_osm.py "Alcobendas"     # otro municipio

Los datos de OpenStreetMap son libres (licencia ODbL) y se pueden guardar.
Google Maps no permite copiar su base de datos; desde la web, el botón
"Añadir restaurante" sí busca en Google si hay clave configurada.
"""

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
AMENITIES = {"restaurant": "Restaurante", "fast_food": "Comida rápida", "cafe": "Cafetería"}
CUISINES = {
    "spanish": "española", "regional": "regional", "mediterranean": "mediterránea",
    "italian": "italiana", "pizza": "pizza", "burger": "hamburguesas", "chinese": "china",
    "japanese": "japonesa", "sushi": "sushi", "asian": "asiática", "mexican": "mexicana",
    "indian": "india", "american": "americana", "kebab": "kebab", "tapas": "tapas",
    "seafood": "marisco", "chicken": "pollo", "sandwich": "bocadillos", "coffee_shop": "café",
    "ice_cream": "heladería", "peruvian": "peruana", "argentinian": "argentina",
    "steak_house": "carnes", "vegetarian": "vegetariana", "vegan": "vegana", "thai": "tailandesa",
    "greek": "griega", "lebanese": "libanesa", "venezuelan": "venezolana", "korean": "coreana",
}


def overpass(query: str) -> dict:
    body = urllib.parse.urlencode({"data": query}).encode()
    for attempt in range(4):
        for server in SERVERS:
            request = urllib.request.Request(
                server, data=body, headers={"User-Agent": "pato-genos/1.0", "Accept": "application/json"}
            )
            try:
                with urllib.request.urlopen(request, timeout=120) as response:
                    return json.load(response)
            except Exception as error:  # servidor saturado, timeout, HTML de error…
                print(f"  {server}: {error}", file=sys.stderr)
        time.sleep(10 * (attempt + 1))
    raise SystemExit("Ningún servidor de Overpass ha respondido. Inténtalo más tarde.")


def to_restaurant(element: dict) -> dict:
    tags = element["tags"]
    lat = element.get("lat") or element["center"]["lat"]
    lng = element.get("lon") or element["center"]["lon"]
    street = " ".join(filter(None, [tags.get("addr:street"), tags.get("addr:housenumber")]))
    address = ", ".join(filter(None, [street, tags.get("addr:city")]))
    cuisine = ", ".join(
        CUISINES.get(c.strip(), c.strip().replace("_", " "))
        for c in tags.get("cuisine", "").split(";") if c.strip()
    )
    query = urllib.parse.quote(f"{tags['name']}, {address or f'{lat},{lng}'}")
    return {
        "place_id": f"osm:{element['type']}/{element['id']}",
        "name": tags["name"].strip(),
        "address": address,
        "lat": round(lat, 7),
        "lng": round(lng, 7),
        "category": AMENITIES[tags["amenity"]],
        "cuisine": cuisine,
        "maps_url": f"https://www.google.com/maps/search/?api=1&query={query}",
        "source": "osm",
        "menu_type": "",
        "menu_src": [],
        "dishes": [],
    }


def sql_text(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def write_seed(restaurants: list[dict], town: str) -> None:
    lines = [
        f"-- Restaurantes de {town} sacados de OpenStreetMap (© colaboradores de OSM, ODbL).",
        "-- Generado con scripts/importar_osm.py. Se puede ejecutar varias veces: no duplica.",
        "insert into public.restaurants (place_id, name, address, lat, lng, category, cuisine, maps_url, source) values",
    ]
    rows = [
        "  ({}, {}, {}, {}, {}, {}, {}, {}, 'osm')".format(
            sql_text(r["place_id"]), sql_text(r["name"]), sql_text(r["address"]), r["lat"], r["lng"],
            sql_text(r["category"]), sql_text(r["cuisine"]), sql_text(r["maps_url"]),
        )
        for r in restaurants
    ]
    lines.append(",\n".join(rows))
    lines.append("on conflict (place_id) do nothing;\n")
    (ROOT / "supabase" / "seed.sql").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    town = sys.argv[1] if len(sys.argv) > 1 else "Tres Cantos"
    print(f"Descargando restaurantes de {town}…")
    data = overpass(
        f'[out:json][timeout:90];'
        f'area["name"="{town}"]["boundary"="administrative"]->.a;'
        f'nwr["amenity"~"^({"|".join(AMENITIES)})$"]["name"](area.a);'
        f'out center tags;'
    )
    restaurants = sorted(
        (to_restaurant(e) for e in data["elements"]), key=lambda r: r["name"].casefold()
    )
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "restaurantes.json").write_text(
        json.dumps(restaurants, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (ROOT / "supabase").mkdir(exist_ok=True)
    write_seed(restaurants, town)
    print(f"{len(restaurants)} sitios guardados en data/restaurantes.json y supabase/seed.sql")


if __name__ == "__main__":
    main()
