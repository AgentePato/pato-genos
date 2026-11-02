"""Cadenas con la tabla de alérgenos en un PDF sencillo: Papa John's y Pans & Company.

Cada fila es un producto con una columna por alérgeno (en el orden habitual
del Reglamento 1169/2011). Los locales salen de OpenStreetMap.

Uso:
  python3 -m venv .venv && .venv/bin/pip install pdfplumber
  .venv/bin/python scripts/cartas/tablas_pdf.py            # todas
  .venv/bin/python scripts/cartas/tablas_pdf.py papajohns

Los enlaces a los PDF cambian cuando publican una versión nueva: si falla la
descarga, busca el enlace "alérgenos" en su web y cámbialo abajo.
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
    # name_col: columna del nombre · first: primera columna de alérgenos · contains/traces: marcas.
    "papajohns": dict(name="Papa John's", like="%papa john%", cuisine="pizza", brand="Papa John's",
                      pdf="https://cdn.new.papajohns.es/Alergenos+Espa%C3%B1a/TablaAlergenos+ED+44.pdf",
                      name_col=0, first=1, contains="C", traces="T"),
    "pans": dict(name="Pans & Company", like="%pans%company%", cuisine="bocadillos", brand="Pans & Company",
                 pdf="https://eatout.es/pdfs/guides/pans/guia_de_alergenos_es-ES.pdf",
                 name_col=1, first=2, contains="●", traces="○"),
}


def parse_pdf(path, chain):
    dishes, section = [], "Carta"
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for row in table:
                    cells = [(c or "").replace("\n", " ").strip() for c in row]
                    if len(cells) < chain["first"] + 14:
                        continue
                    name = cells[chain["name_col"]]
                    marks = cells[chain["first"]:chain["first"] + 14]
                    rest = [c for i, c in enumerate(cells) if i != chain["name_col"] and c]
                    # Fila de sección: solo un título ("PIZZAS", "Bebidas Calientes"), sin código ni marcas.
                    title = cells[0] if not name else name
                    if title and not rest or (not name and title and not any(marks)):
                        if len(title) < 50 and not re.search(r"\d{4}|INFORMACI|ALÉRGENO", title):
                            section = nice(title, sentence=True)
                        continue
                    if not name or len(name) > 80 or "ALÉRGENO" in name.upper() or re.search(r"\b20\d\d\b", name):
                        continue
                    contains = [KEYS[i] for i, m in enumerate(marks) if m.startswith(chain["contains"])]
                    traces = [KEYS[i] for i, m in enumerate(marks) if m.startswith(chain["traces"]) and KEYS[i] not in contains]
                    name = re.sub(r"\s*\(PC\)$", "", name)  # Pans: "(PC)" = precio de carta
                    dishes.append(dict(section=section, name=name, allergens=contains, traces=traces))
    return dict(dishes=dishes, date="")


def main():
    for key in sys.argv[1:] or list(CHAINS):
        chain = CHAINS[key]
        with tempfile.NamedTemporaryFile(suffix=".pdf") as pdf:
            request = urllib.request.Request(chain["pdf"], headers={"User-Agent": "Mozilla/5.0"})
            pdf.write(urllib.request.urlopen(request, timeout=60).read())
            pdf.flush()
            menu = parse_pdf(pdf.name, chain)
        stores = fetch_osm_brand(chain["brand"], key)
        for store in stores:
            store["menu"] = key
        output = write_sql(key, chain, stores, {key: menu}, f"PDF oficial de alérgenos ({chain['pdf']})",
                           "scripts/cartas/tablas_pdf.py")
        print(f"{chain['name']}: {len(stores)} locales (OpenStreetMap), {len(menu['dishes'])} platos → {output.name}")


if __name__ == "__main__":
    main()
