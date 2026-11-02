"""Goiko: restaurantes de la Comunidad de Madrid y su carta de alérgenos.

La carta sale de goiko.com/es/alergenos (una tabla con un círculo para
"contiene" y una T para "trazas") y los restaurantes, de la API de su web.
El local "Gluten Free" usa su propia carta (goiko.com/es/alergenos/glutenfree).

Uso:
  python3 scripts/cartas/goiko.py
"""

import html
import json
import re

from comun import get, write_sql

MENUS = {"goiko": "https://www.goiko.com/es/alergenos/",
         "goiko_glutenfree": "https://www.goiko.com/es/alergenos/glutenfree/"}
LOCATIONS = "https://www.goiko.com/es/wp-json/wp/v2/locations?per_page=100&page={page}"
# Orden de las columnas de su tabla (el mismo que sus filtros) → nuestras claves.
COLUMNS = {"Gluten": "gluten", "Crustáceos": "crustaceos", "Huevos": "huevo", "Pescado": "pescado",
           "Cacahuetes": "cacahuete", "Soja": "soja", "Lácteos": "lacteos", "Frutos de cáscara": "frutos_secos",
           "Apio": "apio", "Mostaza": "mostaza", "Granos de sésamo": "sesamo",
           "Dióxido de azufre y sulfitos": "sulfitos", "Moluscos": "moluscos", "Altramuces": "altramuces"}
CHAIN = dict(name="Goiko", like="%goiko%", cuisine="hamburguesas")


def text(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def fetch_menu(url):
    page = get(url)
    columns = [COLUMNS[html.unescape(n)] for n in re.findall(r'<li class="allergenFilter" data-name="([^"]+)"', page)]
    if len(columns) != 14:
        raise SystemExit(f"La tabla de Goiko ha cambiado: {len(columns)} columnas de alérgenos.")
    dishes = []
    for category in re.split(r'<div class="dishCategory[^"]*">', page)[1:]:
        section = text(re.search(r"<h3>(.*?)</h3>", category, re.S).group(1))
        for declared, row in re.findall(r'<tr data-allergens="([^"]*)">(.*?)</tr>', category, re.S):
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
            name = text(cells[0])
            contains = [columns[i] for i, c in enumerate(cells[1:15]) if "fa-circle" in c]
            traces = [columns[i] for i, c in enumerate(cells[1:15]) if "allergen-trace" in c]
            # Cada fila trae también la lista de sus alérgenos: sirve para comprobar la lectura.
            expected = {COLUMNS[html.unescape(a)] for a in declared.split(",") if a and a != "Ninguno"}
            if set(contains) | set(traces) != expected:
                raise SystemExit(f"Goiko: no cuadran los alérgenos de {name!r}")
            dishes.append(dict(section=section, name=name, allergens=contains, traces=traces))
    date = re.search(r"Fecha de última actualización:\s*([\d/]+)", page)
    return dict(dishes=dishes, date=date.group(1) if date else "")


def fetch_stores():
    stores = []
    for page in (1, 2, 3):
        try:
            locations = json.loads(get(LOCATIONS.format(page=page), "application/json"))
        except Exception:
            break  # no hay más páginas
        for loc in locations:
            acf = loc["acf"]
            if "locationcity-madrid" not in loc["class_list"] or acf.get("no_public") or not acf.get("lat"):
                continue
            title = html.unescape(loc["title"]["rendered"]).strip().rstrip(".")
            gluten_free = acf.get("is_glutenfree") or title.lower().startswith("gluten free")
            stores.append(dict(
                place_id=f"goiko:{loc['slug']}", name=f"Goiko {title}",
                address=re.sub(r"\s+", " ", acf["address"]).strip().rstrip("."),
                lat=float(acf["lat"]), lng=float(acf["lng"]),
                menu="goiko_glutenfree" if gluten_free else "goiko"))
        if len(locations) < 100:
            break
    return stores


def main():
    stores = fetch_stores()
    menus = {menu: fetch_menu(MENUS[menu]) for menu in sorted({s["menu"] for s in stores})}
    output = write_sql("goiko", CHAIN, stores, menus, "goiko.com/es/alergenos", "scripts/cartas/goiko.py")
    print(f"Goiko: {len(stores)} locales, cartas "
          + ", ".join(f"{m} ({len(c['dishes'])} platos)" for m, c in menus.items()) + f" → {output.name}")


if __name__ == "__main__":
    main()
