"""Convierte la tabla oficial de alérgenos de 100 Montaditos (PDF) en una
carta digital, descarga la lista oficial de locales de la cadena y genera un
SQL que da de alta los de la Comunidad de Madrid y les asigna la carta.

Uso:
  python3 -m venv .venv && .venv/bin/pip install pdfplumber
  .venv/bin/python scripts/cartas/100montaditos.py "100M Alérgenos. JULIO 2026.pdf"

La carta se guarda una sola vez (en el local de Tres Cantos) y el resto de
locales la comparten con restaurants.menu_from.

Lee las páginas "por producto terminado" (4-8): cada X es "contiene" y cada
* es "puede contener" (trazas). Las filas con texto girado en el PDF
(pizzas, ensaladas, postres, helados) se corrigen a mano por su posición,
así que con una tabla de otro mes revisa la salida antes de cargarla.
"""

import json
import math
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "supabase" / "cartas" / "100-montaditos.sql"
TEMPLATE_PLACE_ID = "osm:node/5134877837"  # 100 Montaditos de Tres Cantos: guarda la carta para todos
STORES_URL = "https://spain.100montaditos.com/assets/web/js/script.js"  # su buscador de locales lleva la lista dentro
REGIONS = {"COMUNIDAD DE MADRID", "MADRID"}  # la lista oficial usa las dos formas
PDF_URL = "https://spain.100montaditos.com/assets/web/docs/100M%20Al%C3%A9rgenos.%20JULIO%202026.pdf"

KEYS = ["gluten", "crustaceos", "huevo", "pescado", "cacahuete", "soja", "lacteos",
        "frutos_secos", "apio", "mostaza", "sesamo", "sulfitos", "altramuces", "moluscos"]
# Centro de cada columna de alérgeno (x) y zona del nombre del plato. La página 8 tiene otra maqueta.
LAYOUTS = {
    "A": dict(centers=[287, 324, 363, 402, 441, 480, 519, 558, 596, 635, 674, 712, 752, 791], name=(55, 240), table=265, top=62),
    "B": dict(centers=[236, 281, 323, 365, 408, 450, 492, 535, 577, 620, 662, 705, 748, 789], name=(45, 215), table=215, top=72),
}
HEADINGS = {"De la casa", "Clásicos", "Imprescindibles", "Especiales", "MontyCookie", "Montydinas",
            "Montyperros", "Montyburgers", "Montypizzas", "MontyGourmet"}
# Secciones que en el PDF van en texto vertical: (página, fila) donde empiezan.
SECTION_STARTS = {(6, 263): "Aperitivos", (6, 307): "Para picar", (6, 381): "Raciones",
                  (7, 66): "Ensaladas", (7, 102): "Postres", (7, 125): "Bebidas", (7, 214): "Otros",
                  (7, 263): "Menú del día", (8, 77): "Desayunos", (8, 395): "Helados"}
FIXED_NAMES = {
    (6, 76): "Pizza BBQ: bacon ahumado, queso mozzarella, cebolla crujiente y salsa BBQ",
    (6, 93): "Pizza Pollo: pollo kebab, queso mozzarella, salsa para pizza y orégano",
    (6, 110): "Pizza 3 Quesos: queso madurado, queso mozzarella, queso gorgonzola y orégano",
    (6, 127): "Pizza Pulled Pork: pulled pork BBQ, queso mozzarella, cebolla crujiente y salsa BBQ",
    (6, 144): "Pizza Pepperoni: pepperoni, queso mozzarella, salsa para pizza y orégano",
    (7, 66): "Ensalada Campera: lechuga, pollo, tomate, queso madurado, aceitunas, picatostes y salsa alioli",
    (7, 83): "Ensalada Texmex: lechuga, pollo kebab, tomate, maíz, aceitunas, nachos sabor TexMex y salsa mostaza y miel",
    (7, 102): "Helado cono vainilla-choco", (7, 114): "Helado dominó vainilla",
    (6, 254): "Jamón Gran Reserva y mantequilla", (5, 113): "Carrillera al vino tinto y salsa alioli",
    (8, 395): "Base de helado", (8, 405): "Topping arabeschi choco-avellana", (8, 414): "Topping cookies & cream",
}
SKIP_TEXT = ("cuadro ha sido", "métodos de", "marca disponible", "Contiene", "contener")
BREAD_SUFFIX = re.compile(r"\s+(TORTILLA\w*|TO|TORT|BRIOCHE|MINI|GOURMET)$")


def read_rows(pdf_path):
    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for index in range(3, 8):
            page = pdf.pages[index]
            layout = LAYOUTS["B" if index == 7 else "A"]
            lines = {}
            for w in page.extract_words():
                if layout["top"] < w["top"] < 520 and layout["name"][0] <= w["x0"] < layout["name"][1] and w["upright"]:
                    key = next((k for k in lines if abs(k - w["top"]) < 2.5), w["top"])
                    lines.setdefault(key, []).append(w)
            marks = [c for c in page.chars
                     if c["text"] in "X*" and c["x0"] > layout["table"] and layout["top"] < c["top"] < 520]
            for top, words in sorted(lines.items()):
                row = dict(page=index + 1, top=round(top), contains=[], traces=[],
                           name=" ".join(w["text"] for w in sorted(words, key=lambda w: w["x0"])))
                for c in marks:
                    if abs(c["top"] - top) < 4:
                        center = (c["x0"] + c["x1"]) / 2
                        column = min(range(14), key=lambda i: abs(layout["centers"][i] - center))
                        (row["contains"] if c["text"] == "X" else row["traces"]).append(KEYS[column])
                rows.append(row)
    return rows


def build_dishes(rows):
    dishes, section, number = [], None, 0
    for r in rows:
        key = (r["page"], r["top"])
        if r["name"] in HEADINGS:
            section = r["name"]
            continue
        section = SECTION_STARTS.get(key, section)
        if key in FIXED_NAMES:
            name = FIXED_NAMES[key]
        elif (r["page"] == 6 and r["top"] < 160) or key == (7, 91):
            continue  # segundas líneas de nombres partidos
        elif not (r["contains"] or r["traces"]) and not re.match(r"^[A-ZÁÉÍÓÚ1-2]", r["name"]):
            continue  # restos de texto girado
        else:
            name = BREAD_SUFFIX.sub("", r["name"]).strip()
        if any(s in name for s in SKIP_TEXT) or name in ("Cereales", "Frutos", "EMPOTRAITO"):
            continue  # pie de página
        if section in HEADINGS:
            number += 1
            name = f"{number}. {name}"
        name = re.sub(r"^(\d)º (\d)\.?\s*", r"\1.º plato · ", name)
        name = name.replace(" (1)", " (según marca)").rstrip(".").replace("Albondigas", "Albóndigas")
        contains = list(dict.fromkeys(r["contains"]))
        traces = [t for t in dict.fromkeys(r["traces"]) if t not in contains]
        dishes.append(dict(section=section, name=name, allergens=contains, traces=traces))
    return dishes


def fetch_stores():
    """Lista oficial de locales: va como JSON dentro del JavaScript de su web."""
    request = urllib.request.Request(STORES_URL, headers={"User-Agent": "Mozilla/5.0"})
    script = urllib.request.urlopen(request, timeout=60).read().decode("utf-8")
    lists = [json.loads(m.group(1).encode().decode("unicode_escape").encode("latin-1").decode("utf-8"))
             for m in re.finditer(r"JSON\.parse\('(\[.*?\])'\)", script, re.S) if '"codigo_restalia"' in m.group(1)]
    if not lists:
        raise SystemExit("No encuentro la lista de locales en la web de 100 Montaditos.")
    stores = []
    for store in max(lists, key=len):
        if store["comunidad"] not in REGIONS:
            continue
        lat, lng = float(store["latitud"]), float(store["longitud"])
        # La lista oficial repite algún local con dos fichas casi en el mismo punto.
        if any(math.dist((lat, lng * 0.76), (s["lat"], s["lng"] * 0.76)) * 111_000 < 80 for s in stores):
            continue
        code = store["codigo_restalia"].strip()
        stores.append(dict(lat=lat, lng=lng, code=code if re.fullmatch(r"[A-Z]*\d+", code) else "",
                           address=pretty_address(store["direccion"], store["ciudad"])))
    return stores


SMALL_WORDS = {"de", "del", "la", "las", "los", "el", "y", "en"}


def pretty_address(street, town):
    """'CALLE DE LA PRINCESA 7' + 'MADRID' → 'Calle de la Princesa 7, Madrid'."""
    def title(text):
        text = re.sub(r"\s+", " ", text.strip()).lower()
        def word(m):
            w = m.group(0)
            if w in ROMAN:
                return w.upper()
            if w in SMALL_WORDS and m.start() > 0:
                return w
            return w[:1].upper() + w[1:]
        return re.sub(r"[^\W\d_]+", word, text)
    street, town = title(street), title(town)
    street = re.sub(r"\b(Cc|C\.c\.|S/N|Km)(?=\W|$)", lambda m: {"Cc": "CC", "C.c.": "CC", "S/N": "s/n", "Km": "km"}[m.group(1)], street)
    return street if town.lower() in street.lower() else f"{street}, {town}"


ROMAN = {"ii", "iii", "iv", "vi"}


def sql_text(value):
    return "'" + value.replace("'", "''") + "'"


def write_sql(dishes, stores):
    lines = ",\n  ".join(json.dumps(d, ensure_ascii=False) for d in dishes)  # un plato por línea
    payload = f"[\n  {lines}\n]".replace("'", "''")
    def place_id(store):
        # Algunos locales nuevos no tienen código interno; entonces se identifican por coordenadas.
        return f"restalia:{store['code']}" if store["code"] else f"restalia:{store['lat']:.5f},{store['lng']:.5f}"

    rows = ",\n  ".join(
        "({}, {}, {}, {}, {})".format(
            sql_text(place_id(s)), sql_text(s["address"]), s["lat"], s["lng"],
            sql_text("https://www.google.com/maps/search/?api=1&query="
                     + urllib.parse.quote(f"100 Montaditos, {s['address']}")))
        for s in stores)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(f"""-- 100 Montaditos: {len(stores)} locales de la Comunidad de Madrid (lista oficial de su web)
-- y su carta de alérgenos (tabla oficial de julio de 2026, {len(dishes)} platos).
-- Generado con scripts/cartas/100montaditos.py. Ejecútalo en Supabase → SQL Editor
-- después de schema.sql. Se puede volver a ejecutar: no duplica locales.
do $$
declare
  v_template uuid;
  v_pdf text := '{PDF_URL}';
  v_dishes jsonb := '{payload}';
begin
  -- 1. Locales que faltan (si ya hay un 100 Montaditos a menos de ~150 m, es el mismo).
  insert into public.restaurants (place_id, name, address, lat, lng, category, cuisine, maps_url, source)
  select s.place_id, '100 Montaditos', s.address, s.lat, s.lng, 'Restaurante', 'montaditos, tapas', s.maps_url, 'manual'
  from (values
  {rows}
  ) as s(place_id, address, lat, lng, maps_url)
  where not exists (
    select 1 from public.restaurants r
    where r.name ilike '%montadito%' and abs(r.lat - s.lat) < 0.0014 and abs(r.lng - s.lng) < 0.0018)
  on conflict (place_id) do nothing;

  -- 2. La carta se guarda una vez, en el local de Tres Cantos.
  select id into v_template from public.restaurants where place_id = '{TEMPLATE_PLACE_ID}';
  if v_template is null then raise exception 'No encuentro el 100 Montaditos de Tres Cantos'; end if;
  delete from public.dishes where restaurant_id = v_template;
  insert into public.dishes (restaurant_id, position, section, name, allergens, traces)
  select v_template, d.ord, d.value ->> 'section', d.value ->> 'name',
         array(select jsonb_array_elements_text(d.value -> 'allergens')),
         array(select jsonb_array_elements_text(d.value -> 'traces'))
  from jsonb_array_elements(v_dishes) with ordinality as d(value, ord);

  -- 3. Todos los 100 Montaditos usan esa carta y enlazan el PDF oficial.
  update public.restaurants
     set menu_type = 'pdf', menu_src = array[v_pdf], menu_updated_at = now(),
         menu_from = case when id = v_template then null else v_template end
   where name ilike '100 montaditos%';
  delete from public.dishes d using public.restaurants r
   where d.restaurant_id = r.id and r.menu_from = v_template;
end $$;
""", encoding="utf-8")


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    dishes = build_dishes(read_rows(sys.argv[1]))
    stores = fetch_stores()
    write_sql(dishes, stores)
    print(f"{len(dishes)} platos y {len(stores)} locales guardados en {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
