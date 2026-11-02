"""Utilidades compartidas por los scripts de cartas de cadenas."""

import json
import re
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def get(url, accept="text/html"):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": accept})
    for attempt in range(4):
        try:
            return urllib.request.urlopen(request, timeout=40).read().decode("utf-8")
        except OSError:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))


SMALL_WORDS = {"de", "del", "la", "las", "los", "el", "y", "con", "sin", "al", "a", "en", "o"}
ACRONYMS = {"vips", "bbq", "xl", "blt", "ny", "usa", "mi", "t2"}


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


OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
            "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]


def fetch_osm_brand(brand, prefix):
    """Locales de una cadena en la Comunidad de Madrid según OpenStreetMap (etiqueta brand).

    Para cadenas cuya web no publica la lista de locales de forma aprovechable.
    Se usa curl porque el Python de macOS no negocia bien el SSL de Overpass.
    """
    query = (f'[out:json][timeout:180];area["name"="Comunidad de Madrid"]["admin_level"="4"]->.a;'
             f'nwr["amenity"~"^(restaurant|fast_food|cafe)$"]["brand"="{brand}"](area.a);out center tags;')
    for attempt in range(6):
        server = OVERPASS[attempt % len(OVERPASS)]
        result = subprocess.run(["curl", "-s", "--max-time", "200", "-A", "pato-genos/1.0", server,
                                 "--data-urlencode", f"data={query}"], capture_output=True, text=True)
        try:
            elements = json.loads(result.stdout)["elements"]
            break
        except (ValueError, KeyError):
            time.sleep(15)
    else:
        raise SystemExit(f"OpenStreetMap no responde; vuelve a intentarlo más tarde ({brand}).")
    stores = []
    for e in elements:
        tags = e["tags"]
        lat = e.get("lat") or e["center"]["lat"]
        lng = e.get("lon") or e["center"]["lon"]
        street = " ".join(filter(None, [tags.get("addr:street"), tags.get("addr:housenumber")]))
        town = tags.get("addr:city", "")
        place = street or tags.get("addr:place") or tags.get("branch") or ""
        stores.append(dict(place_id=f"{prefix}:osm-{e['type']}-{e['id']}",
                           name=f"{brand} {tags['branch']}" if tags.get("branch") else (f"{brand} {place}" if place else brand),
                           address=", ".join(filter(None, [street, town])), lat=lat, lng=lng))
    return sorted(stores, key=lambda s: s["place_id"])


def sql_text(value):
    return "'" + value.replace("'", "''") + "'"


def write_sql(chain_key, chain, stores, menus, source, script):
    """Genera supabase/cartas/<chain_key>.sql.

    chain: dict con name, like (cómo se llama si ya estaba en el mapa) y cuisine.
    stores: [{place_id, name, address, lat, lng, menu}] · menus: {menu: {dishes, date}}.
    Cada carta se guarda en el primer local que la usa y el resto la comparten (menu_from).
    """
    templates = {}  # carta → local que la guarda
    for store in stores:
        templates.setdefault(store["menu"], store["place_id"])
    rows = ",\n  ".join(
        "({}, {}, {}, {}, {}, {}, {})".format(
            sql_text(s["place_id"]), sql_text(s["name"]), sql_text(s["address"]), s["lat"], s["lng"],
            sql_text("https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(f"{s['name']}, {s['address']}")),
            sql_text(s["menu"]))
        for s in stores)
    load_menus = "".join(f"""
  -- Carta {brand}: {len(menus[brand]['dishes'])} platos, actualizada el {menus[brand]['date']}. La guarda {template}.
  select id into v_template from public.restaurants where place_id = '{template}';
  delete from public.dishes where restaurant_id = v_template;
  insert into public.dishes (restaurant_id, position, section, name, allergens, traces)
  select v_template, d.ord, d.value ->> 'section', d.value ->> 'name',
         array(select jsonb_array_elements_text(d.value -> 'allergens')),
         array(select jsonb_array_elements_text(d.value -> 'traces'))
  from jsonb_array_elements({sql_text(json_lines(menus[brand]['dishes']))}::jsonb) with ordinality as d(value, ord);
  update public.restaurants set menu_from = null, menu_updated_at = now() where id = v_template;
""" for brand, template in templates.items())
    template_rows = ", ".join(f"({sql_text(b)}, {sql_text(t)})" for b, t in templates.items())

    output = ROOT / "supabase" / "cartas" / f"{chain_key}.sql"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(f"""-- {chain['name']}: {len(stores)} locales de la Comunidad de Madrid (web oficial de la marca).
-- Carta de alérgenos: {source}.
-- Generado con {script}. Ejecútalo en Supabase → SQL Editor
-- después de schema.sql. Se puede volver a ejecutar: no duplica locales.
do $$
declare
  v_template uuid;
begin
  create temp table chain_stores (place_id text, name text, address text, lat float8, lng float8, maps_url text, menu text) on commit drop;
  insert into chain_stores values
  {rows};

  -- 1. Si el local ya estaba en el mapa (p. ej. desde OpenStreetMap) a menos de ~150 m, se reutiliza.
  update public.restaurants r
     set place_id = s.place_id, name = s.name, address = s.address
    from chain_stores s
   where r.place_id not like '{chain_key}:%' and r.name ilike {sql_text(chain['like'])}
     and abs(r.lat - s.lat) < 0.0014 and abs(r.lng - s.lng) < 0.0018
     and not exists (select 1 from public.restaurants x where x.place_id = s.place_id);

  insert into public.restaurants (place_id, name, address, lat, lng, category, cuisine, maps_url, source)
  select place_id, name, address, lat, lng, 'Restaurante', {sql_text(chain['cuisine'])}, maps_url, 'manual'
  from chain_stores
  on conflict (place_id) do update set name = excluded.name, address = excluded.address,
    lat = excluded.lat, lng = excluded.lng, maps_url = excluded.maps_url;

  -- 2. Cada carta se guarda una vez.
{load_menus}
  -- 3. El resto de locales comparten la carta de su formato.
  update public.restaurants r
     set menu_from = t.id, menu_type = '', menu_src = '{{}}'
    from chain_stores s
    join (values {template_rows}) as m(menu, template) on m.menu = s.menu
    join public.restaurants t on t.place_id = m.template
   where r.place_id = s.place_id and r.id <> t.id;
  delete from public.dishes d using public.restaurants r, chain_stores s
   where d.restaurant_id = r.id and r.place_id = s.place_id and r.menu_from is not null;
end $$;
""", encoding="utf-8")
    return output


def json_lines(dishes):
    lines = ",\n  ".join(json.dumps(d, ensure_ascii=False) for d in dishes)  # un plato por línea
    return f"[\n  {lines}\n]"


