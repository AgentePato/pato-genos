"""Cadenas del Grupo VIPS: VIPS, VIPS Smart, Ginos, Foster's Hollywood y Starbucks.

Descarga sus cartas de alérgenos (alergenos.grupovips.com, la misma web para
todas) y sus restaurantes de la Comunidad de Madrid (de la web oficial de cada
marca), y genera un SQL por cadena en supabase/cartas/.

Uso:
  python3 scripts/cartas/grupo_vips.py              # todas
  python3 scripts/cartas/grupo_vips.py ginos        # solo una

Cada carta se guarda una sola vez (en el primer local de la lista) y el resto
de locales la comparten con restaurants.menu_from. El grupo actualiza las
cartas a menudo: vuelve a ejecutar el script y los SQL para ponerlas al día.
"""

import html
import json
import re
import sys
import time

from comun import ROOT, get, write_sql
MENUS_URL = "https://alergenos.grupovips.com/app/allergens/courses.php?brand={brand}&country=ES"
STARBUCKS_API = ("https://www.starbucks.es/api/v2/stores?filter%5Bcoordinates%5D%5Blatitude%5D={lat}"
                 "&filter%5Bcoordinates%5D%5Blongitude%5D={lng}")

ALLERGENS = {
    "ALE001": "gluten", "ALE002": "crustaceos", "ALE003": "huevo", "ALE004": "pescado",
    "ALE005": "cacahuete", "ALE006": "soja", "ALE007": "lacteos", "ALE008": "frutos_secos",
    "ALE009": "apio", "ALE010": "mostaza", "ALE011": "sesamo", "ALE012": "sulfitos",
    "ALE013": "altramuces", "ALE014": "moluscos",
}
SMALL_WORDS = {"de", "del", "la", "las", "los", "el", "y", "con", "sin", "al", "a", "en", "o"}
ACRONYMS = {"vips", "bbq", "xl", "blt", "ny", "usa", "mi", "t2"}

# like = cómo se llama esa cadena si ya estaba en el mapa (p. ej. desde OpenStreetMap).
CHAINS = {
    "vips": dict(name="VIPS", like="%vips%", cuisine="americana, hamburguesas",
                 stores_url="https://www.vips.es/restaurantes",
                 # VIPS Smart es otro formato, con su propia carta.
                 menu=lambda store: "vipsmart" if store["name"].lower().startswith("vips smart") else "vips"),
    "ginos": dict(name="Ginos", like="%ginos%", cuisine="italiana, pizza, pasta",
                  stores_url="https://www.ginos.es/restaurante-italiano", menu=lambda store: "ginos"),
    "fosters": dict(name="Foster's Hollywood", like="%foster%", cuisine="americana, hamburguesas",
                    stores_url="https://www.fostershollywood.es/restaurantes", menu=lambda store: "foster"),
    "starbucks": dict(name="Starbucks", like="%starbucks%", cuisine="cafetería", stores_url=None,
                      menu=lambda store: "starbucks"),
}


def nice(text, sentence=False):
    """'ENSALADA CÉSAR' → 'Ensalada César'; con sentence=True, 'PARA PICAR' → 'Para picar'."""
    text = re.sub(r"\s+", " ", text.strip()).lower()

    def word(m):
        w = m.group(0)
        if w in ACRONYMS:
            return w.upper()
        if m.start() > 0 and (sentence or w in SMALL_WORDS):
            return w
        return w[:1].upper() + w[1:]
    return re.sub(r"[^\W\d_]+", word, text)


def fetch_menu(brand):
    carta = json.loads(get(MENUS_URL.format(brand=brand), "application/json"))["cartas"]
    sections = sorted(carta["Region_id"][0]["SLUs"], key=lambda s: int(s["SLU_sort"]))
    dishes = []
    for section in sections:
        for item in section["SLU_menuItems"]:
            contains = [ALLERGENS[a] for a in item["allergen"]]
            dishes.append(dict(
                section=nice(section["SLU_name_es_ES"], sentence=True),
                name=nice(item["mI_name_es_ES"]),
                allergens=contains,
                traces=[ALLERGENS[a] for a in item["maycontainallergen"] if ALLERGENS[a] not in contains],
            ))
    return dict(dishes=dishes, date=carta.get("fecha", ""))


def fetch_store_finder(chain_key, chain):
    """VIPS, Ginos y Foster's comparten plataforma web: la lista va en el HTML del buscador."""
    page = get(chain["stores_url"])
    stores = []
    for store_id, body in re.findall(r'<section class="store-finder__results-item store-option" id="([^"]+)">(.*?)</section>', page, re.S):
        spans = [html.unescape(re.sub(r"\s+", " ", s)).strip() for s in re.findall(r"<span>(.*?)</span>", body, re.S)]
        spans = [s for s in spans if s and "<a" not in s]
        postcode_town = next((s for s in spans if re.match(r"^\d{5}", s)), "")
        if not postcode_town.startswith("28"):  # Comunidad de Madrid
            continue
        lat, lng = re.search(r"destination=(-?[\d.]+),(-?[\d.]+)", body).groups()
        name = html.unescape(re.search(r"<h2>(.*?)</h2>", body, re.S).group(1)).strip()
        name = re.sub(r"\s+", " ", re.sub(r"^vips\b", "VIPS", name, flags=re.I))
        postcode, _, town = postcode_town.partition(",")
        stores.append(dict(place_id=f"{chain_key}:{store_id}", name=name,
                           address=f"{spans[0].rstrip('.')}, {postcode.strip()} {town.strip()}",
                           lat=float(lat), lng=float(lng)))
    return stores


def fetch_starbucks():
    """Su API solo da los 50 locales más cercanos a un punto: se recorre Madrid en cuadrícula."""
    found = {}

    def steps(start, stop, step):
        while start <= stop + 1e-9:
            yield round(start, 4)
            start += step
    points = [(la, lo) for la in steps(39.9, 41.15, 0.12) for lo in steps(-4.55, -3.05, 0.15)]
    points += [(la, lo) for la in steps(40.30, 40.56, 0.03) for lo in steps(-3.85, -3.52, 0.035)]  # centro, más denso
    for lat, lng in points:
        for store in json.loads(get(STARBUCKS_API.format(lat=lat, lng=lng), "application/json"))["data"]:
            found[store["id"]] = store["attributes"]
        time.sleep(0.4)
    stores = []
    for store_id, a in found.items():
        address = a["address"]
        if not (address.get("postalCode") or "").startswith("28"):
            continue
        street = ", ".join(filter(None, [address.get("streetAddressLine1"), address.get("streetAddressLine2")]))
        stores.append(dict(place_id=f"starbucks:{store_id}", name=f"Starbucks {a['name']}",
                           address=f"{street}, {address['postalCode']} {address['city']}",
                           lat=a["coordinates"]["latitude"], lng=a["coordinates"]["longitude"]))
    return sorted(stores, key=lambda s: s["place_id"])


def main():
    keys = sys.argv[1:] or list(CHAINS)
    for key in keys:
        chain = CHAINS[key]
        stores = fetch_starbucks() if key == "starbucks" else fetch_store_finder(key, chain)
        for store in stores:
            store["menu"] = chain["menu"](store)
        menus = {brand: fetch_menu(brand) for brand in sorted({s["menu"] for s in stores})}
        output = write_sql(key, chain, stores, menus, "alergenos.grupovips.com", "scripts/cartas/grupo_vips.py")
        print(f"{chain['name']}: {len(stores)} locales, cartas "
              + ", ".join(f"{b} ({len(m['dishes'])} platos)" for b, m in menus.items())
              + f" → {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
