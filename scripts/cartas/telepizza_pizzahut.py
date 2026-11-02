"""Telepizza y Pizza Hut (mismo grupo, mismo formato de tabla de alérgenos).

La carta sale de su PDF oficial de alérgenos (● = contiene, ○ = puede
contener) y los locales, de OpenStreetMap, porque sus webs no publican la
lista con coordenadas.

Uso:
  python3 -m venv .venv && .venv/bin/pip install pdfplumber
  .venv/bin/python scripts/cartas/telepizza_pizzahut.py            # las dos
  .venv/bin/python scripts/cartas/telepizza_pizzahut.py telepizza

Los enlaces a los PDF cambian cuando publican una versión nueva: si falla la
descarga, busca el enlace "alérgenos" en el pie de su web y cámbialo abajo.
"""

import re
import sys
import tempfile
import urllib.request

import pdfplumber

from comun import fetch_osm_brand, nice, write_sql

KEYS = ["gluten", "crustaceos", "huevo", "pescado", "cacahuete", "soja", "lacteos",
        "frutos_secos", "apio", "mostaza", "sesamo", "sulfitos", "altramuces", "moluscos"]
CHAINS = {
    "telepizza": dict(name="Telepizza", like="%telepizza%", cuisine="pizza", brand="Telepizza",
                      pdf="https://statices.telepizza.com/static/on/demandware.static/-/Sites-TelepizzaES-Library/default/dw885284d2/documents/alergenos.pdf"),
    "pizzahut": dict(name="Pizza Hut", like="%pizza hut%", cuisine="pizza", brand="Pizza Hut",
                     pdf="https://cdn.prd01phes.solutions4delivery.com/ecom-cms/ecom-cms/assets/alergenos_ph26_3e8b6a84eb.pdf"),
}
NOISE = ("ATENCI", "alérgeno", "Para bebidas", "(*) Las", "Lasmasas", "Consultar", "Lainformaci", "PRODUCTO", "LISTADO")


def is_noise(text):
    return not text or len(text) > 70 or any(n in text for n in NOISE)


def parse_pdf(path):
    """Las pizzas van como cabecera ("Pizza Barbacoa") con una fila por masa debajo."""
    dishes, group, product, date = [], "", "", ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            if not tables:
                continue
            head = " ".join(c for row in tables[0][:3] for c in row if c)
            if "LISTADO GENERAL" not in head:
                break  # después vienen el listado específico de IFEMA y la versión en catalán
            date = date or (re.search(r"actualizaci[óo]n:\s*([\d/]+)", head) or [None, ""])[1]
            for row in tables[0]:
                cells = [(c or "").replace("\n", " ").strip() for c in row]
                if len(cells) < 16:
                    continue
                name, marks = cells[1], cells[2:16]
                if not name:
                    title = re.sub(r"^[○●\s]+", "", cells[0])
                    if is_noise(title):
                        continue
                    letters = re.sub(r"[^A-Za-zÁÉÍÓÚÑáéíóúñ]", "", title)
                    if re.match(r"^\d+º", title):            # "1º ELIGE TU MASA"
                        group, product = f"{group.split(' · ')[0]} · {nice(title, True)}", ""
                    elif sum(ch.isupper() for ch in letters) > 0.8 * len(letters):  # "ENTRANTES", "SALSAS y TARRINAS"
                        group, product = nice(re.sub(r"^\(\*+\)\s*", "", title), True), ""
                    else:                                    # "Pizza Barbacoa": sus filas son las masas
                        product = title
                        if not group or "gusto" in group.lower():
                            group = "Pizzas"
                    continue
                if is_noise(name) or not any(marks) and len(name) > 60:
                    continue
                name = re.sub(r"^[−\-–]\s*", "", name)
                contains = [KEYS[i] for i, m in enumerate(marks) if "●" in m]
                traces = [KEYS[i] for i, m in enumerate(marks) if "○" in m and KEYS[i] not in contains]
                dishes.append(dict(section=group or "Carta", name=f"{product} · {name}" if product else name,
                                   allergens=contains, traces=traces))
    return dict(dishes=dishes, date=date)


def main():
    for key in sys.argv[1:] or list(CHAINS):
        chain = CHAINS[key]
        with tempfile.NamedTemporaryFile(suffix=".pdf") as pdf:
            request = urllib.request.Request(chain["pdf"], headers={"User-Agent": "Mozilla/5.0"})
            pdf.write(urllib.request.urlopen(request, timeout=60).read())
            pdf.flush()
            menu = parse_pdf(pdf.name)
        stores = fetch_osm_brand(chain["brand"], key)
        for store in stores:
            store["menu"] = key
        output = write_sql(key, chain, stores, {key: menu}, f"PDF oficial de alérgenos ({chain['pdf']})",
                           "scripts/cartas/telepizza_pizzahut.py")
        print(f"{chain['name']}: {len(stores)} locales (OpenStreetMap), {len(menu['dishes'])} platos → {output.name}")


if __name__ == "__main__":
    main()
