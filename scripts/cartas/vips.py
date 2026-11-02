"""Descarga las cartas de alérgenos de VIPS y VIPS Smart (web oficial del
Grupo VIPS) y la lista de restaurantes de vips.es, y genera un SQL que da de
alta los VIPS de la Comunidad de Madrid y les asigna su carta.

Uso:
  python3 scripts/cartas/vips.py

Cada carta se guarda una sola vez (en VIPS Sol y en VIPS Smart Santa Engracia)
y el resto de locales la comparten con restaurants.menu_from. El Grupo VIPS
actualiza las cartas a menudo: vuelve a ejecutar el script y el SQL para
ponerlas al día.
"""

import html
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "supabase" / "cartas" / "vips.sql"
MENUS_URL = "https://alergenos.grupovips.com/app/allergens/courses.php?brand={brand}&country=ES"
STORES_URL = "https://www.vips.es/restaurantes"
# Carta → local que la guarda para todos los demás.
TEMPLATES = {"vips": "vips:SF016305", "vipsmart": "vips:SF016507"}  # VIPS Sol · VIPS Smart Santa Engracia

ALLERGENS = {
    "ALE001": "gluten", "ALE002": "crustaceos", "ALE003": "huevo", "ALE004": "pescado",
    "ALE005": "cacahuete", "ALE006": "soja", "ALE007": "lacteos", "ALE008": "frutos_secos",
    "ALE009": "apio", "ALE010": "mostaza", "ALE011": "sesamo", "ALE012": "sulfitos",
    "ALE013": "altramuces", "ALE014": "moluscos",
}
SMALL_WORDS = {"de", "del", "la", "las", "los", "el", "y", "con", "sin", "al", "a", "en", "o"}
ACRONYMS = {"vips", "bbq", "xl", "blt", "ny", "usa", "mi", "t2"}


def get(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(request, timeout=60).read().decode("utf-8")


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
    carta = json.loads(get(MENUS_URL.format(brand=brand)))["cartas"]
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
    return dishes, carta.get("fecha", "")


def fetch_stores():
    page = get(STORES_URL)
    stores = []
    for store_id, body in re.findall(r'<section class="store-finder__results-item store-option" id="([^"]+)">(.*?)</section>', page, re.S):
        spans = [html.unescape(re.sub(r"\s+", " ", s)).strip() for s in re.findall(r"<span>(.*?)</span>", body, re.S)]
        spans = [s for s in spans if s and "<a" not in s]
        postcode_town = next((s for s in spans if re.match(r"^\d{5}", s)), "")
        if not postcode_town.startswith("28"):  # Comunidad de Madrid
            continue
        lat, lng = re.search(r"destination=(-?[\d.]+),(-?[\d.]+)", body).groups()
        name = re.sub(r"^vips\b", "VIPS", html.unescape(re.search(r"<h2>(.*?)</h2>", body, re.S).group(1)).strip(), flags=re.I)
        postcode, _, town = postcode_town.partition(",")
        stores.append(dict(
            place_id=f"vips:{store_id}", name=re.sub(r"\s+", " ", name),
            address=f"{spans[0]}, {postcode.strip()} {town.strip()}", lat=float(lat), lng=float(lng),
        ))
    return stores


def sql_text(value):
    return "'" + value.replace("'", "''") + "'"


def sql_json(dishes):
    lines = ",\n  ".join(json.dumps(d, ensure_ascii=False) for d in dishes)  # un plato por línea
    return sql_text(f"[\n  {lines}\n]")


def write_sql(menus, stores):
    rows = ",\n  ".join(
        "({}, {}, {}, {}, {}, {})".format(
            sql_text(s["place_id"]), sql_text(s["name"]), sql_text(s["address"]), s["lat"], s["lng"],
            sql_text("https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(f"{s['name']}, {s['address']}")))
        for s in stores)
    load_menus = "\n".join(f"""
  -- Carta {brand} ({len(dishes)} platos, actualizada el {date}).
  select id into v_template from public.restaurants where place_id = '{TEMPLATES[brand]}';
  if v_template is null then raise exception 'No encuentro el local {TEMPLATES[brand]}'; end if;
  delete from public.dishes where restaurant_id = v_template;
  insert into public.dishes (restaurant_id, position, section, name, allergens, traces)
  select v_template, d.ord, d.value ->> 'section', d.value ->> 'name',
         array(select jsonb_array_elements_text(d.value -> 'allergens')),
         array(select jsonb_array_elements_text(d.value -> 'traces'))
  from jsonb_array_elements({sql_json(dishes)}::jsonb) with ordinality as d(value, ord);
  update public.restaurants set menu_from = null, menu_updated_at = now() where id = v_template;
""" for brand, (dishes, date) in menus.items())

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(f"""-- VIPS: {len(stores)} restaurantes de la Comunidad de Madrid (lista oficial de vips.es)
-- y las cartas de alérgenos de VIPS y VIPS Smart (alergenos.grupovips.com).
-- Generado con scripts/cartas/vips.py. Ejecútalo en Supabase → SQL Editor
-- después de schema.sql. Se puede volver a ejecutar: no duplica locales.
do $$
declare
  v_template uuid;
begin
  -- 1. Un VIPS que ya estuviera en el mapa (p. ej. de OpenStreetMap) a menos de ~150 m
  --    es el mismo local: se le pone el nombre oficial en vez de duplicarlo.
  create temp table vips_stores (place_id text, name text, address text, lat float8, lng float8, maps_url text) on commit drop;
  insert into vips_stores values
  {rows};

  update public.restaurants r
     set name = s.name, address = s.address
    from vips_stores s
   where r.place_id not like 'vips:%' and r.name ilike '%vips%'
     and abs(r.lat - s.lat) < 0.0014 and abs(r.lng - s.lng) < 0.0018;

  insert into public.restaurants (place_id, name, address, lat, lng, category, cuisine, maps_url, source)
  select s.place_id, s.name, s.address, s.lat, s.lng, 'Restaurante', 'americana, hamburguesas', s.maps_url, 'manual'
  from vips_stores s
  where not exists (
    select 1 from public.restaurants r
    where r.place_id not like 'vips:%' and r.name ilike '%vips%'
      and abs(r.lat - s.lat) < 0.0014 and abs(r.lng - s.lng) < 0.0018)
  on conflict (place_id) do update set name = excluded.name, address = excluded.address,
    lat = excluded.lat, lng = excluded.lng, maps_url = excluded.maps_url;

  -- 2. Cada carta se guarda una vez.
{load_menus}
  -- 3. Los demás locales comparten la carta de su formato.
  update public.restaurants r
     set menu_from = case when r.name ilike 'vips smart%'
                          then (select id from public.restaurants where place_id = '{TEMPLATES["vipsmart"]}')
                          else (select id from public.restaurants where place_id = '{TEMPLATES["vips"]}') end
   where r.name ilike 'vips%' and r.place_id not in ('{TEMPLATES["vips"]}', '{TEMPLATES["vipsmart"]}');
  delete from public.dishes d using public.restaurants r
   where d.restaurant_id = r.id and r.name ilike 'vips%' and r.menu_from is not null;
end $$;
""", encoding="utf-8")


def main():
    menus = {brand: fetch_menu(brand) for brand in TEMPLATES}
    stores = fetch_stores()
    if not any(s["place_id"] == TEMPLATES["vips"] for s in stores) or not any(s["place_id"] == TEMPLATES["vipsmart"] for s in stores):
        raise SystemExit("Ya no están VIPS Sol o VIPS Smart Santa Engracia en la lista: cambia TEMPLATES.")
    write_sql(menus, stores)
    print(f"{len(stores)} locales y cartas de " + ", ".join(f"{b} ({len(d)} platos)" for b, (d, _) in menus.items())
          + f" guardados en {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
