"""Convierte la tabla oficial de alérgenos de 100 Montaditos (PDF) en la
carta digital del restaurante y genera el SQL para cargarla en Supabase.

Uso:
  python3 -m venv .venv && .venv/bin/pip install pdfplumber
  .venv/bin/python scripts/cartas/100montaditos.py "100M Alérgenos. JULIO 2026.pdf"

Lee las páginas "por producto terminado" (4-8): cada X es "contiene" y cada
* es "puede contener" (trazas). Las filas con texto girado en el PDF
(pizzas, ensaladas, postres, helados) se corrigen a mano por su posición,
así que con una tabla de otro mes revisa la salida antes de cargarla.
"""

import json
import re
import sys
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "supabase" / "cartas" / "100-montaditos-tres-cantos.sql"
PLACE_ID = "osm:node/5134877837"  # 100 Montaditos de Tres Cantos
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


def write_sql(dishes):
    lines = ",\n  ".join(json.dumps(d, ensure_ascii=False) for d in dishes)  # un plato por línea
    payload = f"[\n  {lines}\n]".replace("'", "''")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(f"""-- Carta de alérgenos de 100 Montaditos (Tres Cantos), tabla oficial de julio de 2026.
-- Generado con scripts/cartas/100montaditos.py. Ejecútalo en Supabase → SQL Editor
-- (antes, vuelve a ejecutar schema.sql para tener la columna de trazas).
do $$
declare
  v_id uuid;
  v_dishes jsonb := '{payload}';
begin
  select id into v_id from public.restaurants where place_id = '{PLACE_ID}';
  if v_id is null then raise exception 'No encuentro el 100 Montaditos de Tres Cantos'; end if;

  update public.restaurants
     set menu_type = 'pdf',
         menu_src = array['{PDF_URL}'],
         menu_updated_at = now()
   where id = v_id;

  delete from public.dishes where restaurant_id = v_id;
  insert into public.dishes (restaurant_id, position, section, name, allergens, traces)
  select v_id, d.ord, d.value ->> 'section', d.value ->> 'name',
         array(select jsonb_array_elements_text(d.value -> 'allergens')),
         array(select jsonb_array_elements_text(d.value -> 'traces'))
  from jsonb_array_elements(v_dishes) with ordinality as d(value, ord);
end $$;
""", encoding="utf-8")


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    dishes = build_dishes(read_rows(sys.argv[1]))
    write_sql(dishes)
    print(f"{len(dishes)} platos guardados en {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
