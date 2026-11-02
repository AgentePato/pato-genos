-- =====================================================================
-- Directorio de Alérgenos · esquema de Supabase
-- Ejecútalo entero en Supabase → SQL Editor. Se puede volver a ejecutar.
-- Después ejecuta seed.sql para cargar los restaurantes de OpenStreetMap
-- y define la contraseña del panel (ver final de este archivo).
-- =====================================================================

create extension if not exists pgcrypto with schema extensions;

-- ---------------------------------------------------------------------
-- Tablas
-- ---------------------------------------------------------------------
create table if not exists public.restaurants (
  id              uuid primary key default gen_random_uuid(),
  place_id        text not null unique,          -- osm:node/123 · google:ChIJ… · manual:uuid
  name            text not null check (char_length(name) between 1 and 120),
  address         text not null default '',
  lat             double precision not null check (lat between -90 and 90),
  lng             double precision not null check (lng between -180 and 180),
  category        text not null default 'Restaurante',
  cuisine         text not null default '',
  maps_url        text,
  source          text not null default 'manual' check (source in ('osm', 'google', 'manual')),
  -- Carta escaneada (PDF o imágenes). La carta "en HTML" son los platos de la tabla dishes.
  menu_type       text not null default '' check (menu_type in ('', 'pdf', 'images')),
  menu_src        text[] not null default '{}',
  menu_updated_at timestamptz,
  created_at      timestamptz not null default now()
);

-- Los 14 alérgenos de declaración obligatoria (Reglamento UE 1169/2011).
create table if not exists public.dishes (
  id            uuid primary key default gen_random_uuid(),
  restaurant_id uuid not null references public.restaurants on delete cascade,
  position      int not null default 0,
  section       text not null default '',
  name          text not null check (char_length(name) between 1 and 160),
  allergens     text[] not null default '{}' check (allergens <@ array[
    'gluten', 'crustaceos', 'huevo', 'pescado', 'cacahuete', 'soja', 'lacteos',
    'frutos_secos', 'apio', 'mostaza', 'sesamo', 'sulfitos', 'altramuces', 'moluscos']::text[]),
  -- "Puede contener" (trazas), con las mismas claves que allergens.
  traces        text[] not null default '{}'
);
-- Para bases creadas antes de que existieran las trazas.
alter table public.dishes add column if not exists traces text[] not null default '{}';
create index if not exists dishes_restaurant_idx on public.dishes (restaurant_id, position);

-- Hash de la contraseña del panel. Nadie puede leer esta tabla desde la web.
create table if not exists public.admin_secret (
  id            boolean primary key default true check (id),
  password_hash text not null
);

-- ---------------------------------------------------------------------
-- Permisos: la web solo puede LEER restaurantes y platos. Todo lo que
-- escribe pasa por las funciones de abajo, que validan los datos.
-- ---------------------------------------------------------------------
alter table public.restaurants  enable row level security;
alter table public.dishes       enable row level security;
alter table public.admin_secret enable row level security;

drop policy if exists "lectura publica" on public.restaurants;
create policy "lectura publica" on public.restaurants for select using (true);
drop policy if exists "lectura publica" on public.dishes;
create policy "lectura publica" on public.dishes for select using (true);

revoke all on public.restaurants, public.dishes, public.admin_secret from anon, authenticated;
grant select on public.restaurants, public.dishes to anon, authenticated;

-- ---------------------------------------------------------------------
-- Añadir restaurante (botón público de la web)
-- ---------------------------------------------------------------------
create or replace function public.add_restaurant(
  p_name text, p_address text, p_lat double precision, p_lng double precision,
  p_place_id text, p_maps_url text, p_source text, p_category text default 'Restaurante',
  p_cuisine text default '')
returns uuid language plpgsql security definer set search_path = public as $$
declare
  v_name text := regexp_replace(btrim(coalesce(p_name, '')), '\s+', ' ', 'g');
  v_id   uuid;
begin
  if char_length(v_name) = 0 or char_length(v_name) > 120 then raise exception 'Nombre no válido'; end if;
  if p_place_id is null or char_length(p_place_id) > 300 then raise exception 'Sitio no válido'; end if;
  if p_source not in ('osm', 'google', 'manual') then raise exception 'Origen no válido'; end if;
  if p_lat is null or p_lng is null or p_lat not between -90 and 90 or p_lng not between -180 and 180 then
    raise exception 'Ubicación no válida';
  end if;
  if p_maps_url is not null and p_maps_url !~ '^https://' then raise exception 'Enlace no válido'; end if;
  if (select count(*) from restaurants where created_at > now() - interval '1 hour' and source <> 'osm') >= 60 then
    raise exception 'Se han añadido muchos restaurantes en la última hora. Prueba más tarde.';
  end if;
  -- Mismo nombre a menos de ~100 m: casi seguro que es el mismo sitio (p. ej. de OSM y de Google).
  if exists (select 1 from restaurants
             where lower(name) = lower(v_name)
               and abs(lat - p_lat) < 0.001 and abs(lng - p_lng) < 0.0013) then
    raise exception 'Ese restaurante ya está en el mapa';
  end if;

  insert into restaurants (name, address, lat, lng, place_id, maps_url, source, category, cuisine)
  values (v_name, left(btrim(coalesce(p_address, '')), 300), p_lat, p_lng, p_place_id, p_maps_url,
          p_source, left(coalesce(nullif(btrim(p_category), ''), 'Restaurante'), 60),
          left(btrim(coalesce(p_cuisine, '')), 120))
  returning id into v_id;
  return v_id;
exception when unique_violation then
  raise exception 'Ese restaurante ya está en el mapa';
end $$;

-- ---------------------------------------------------------------------
-- Panel de administración (protegido con contraseña)
-- ---------------------------------------------------------------------
create or replace function public.check_admin(p_password text)
returns boolean language plpgsql security definer set search_path = public, extensions as $$
declare v_hash text;
begin
  select password_hash into v_hash from admin_secret;
  if v_hash is null then raise exception 'Falta definir la contraseña del panel en Supabase'; end if;
  return crypt(coalesce(p_password, ''), v_hash) = v_hash;
end $$;

create or replace function public.require_admin(p_password text)
returns void language plpgsql security definer set search_path = public as $$
begin
  if not check_admin(p_password) then
    perform pg_sleep(1); -- frena a quien intente adivinarla
    raise exception 'Contraseña incorrecta';
  end if;
end $$;

create or replace function public.admin_update_restaurant(
  p_password text, p_id uuid, p_name text, p_address text, p_lat double precision,
  p_lng double precision, p_cuisine text, p_menu_type text, p_menu_src text[])
returns void language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_password);
  if exists (select 1 from unnest(coalesce(p_menu_src, '{}')) s where s ~* '^\s*(javascript|data):') then
    raise exception 'Las rutas de la carta solo pueden ser enlaces http(s) o rutas del sitio';
  end if;
  update restaurants set
    name = btrim(p_name), address = btrim(coalesce(p_address, '')), lat = p_lat, lng = p_lng,
    cuisine = btrim(coalesce(p_cuisine, '')),
    menu_type = coalesce(p_menu_type, ''), menu_src = coalesce(p_menu_src, '{}'),
    menu_updated_at = case
      when menu_type is distinct from coalesce(p_menu_type, '') or menu_src is distinct from coalesce(p_menu_src, '{}')
      then now() else menu_updated_at end
  where id = p_id;
  if not found then raise exception 'Restaurante no encontrado'; end if;
end $$;

-- Sustituye todos los platos del restaurante.
-- p_dishes = [{"section": "Entrantes", "name": "Croquetas", "allergens": ["gluten", "lacteos"], "traces": ["soja"]}, …]
create or replace function public.admin_set_dishes(p_password text, p_restaurant uuid, p_dishes jsonb)
returns void language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_password);
  delete from dishes where restaurant_id = p_restaurant;
  insert into dishes (restaurant_id, position, section, name, allergens, traces)
  select p_restaurant, d.ord, coalesce(d.value ->> 'section', ''), d.value ->> 'name',
         coalesce(array(select jsonb_array_elements_text(d.value -> 'allergens')), '{}'),
         coalesce(array(select jsonb_array_elements_text(d.value -> 'traces')), '{}')
  from jsonb_array_elements(coalesce(p_dishes, '[]')) with ordinality as d(value, ord);
  update restaurants set menu_updated_at = now() where id = p_restaurant;
end $$;

create or replace function public.admin_delete_restaurant(p_password text, p_id uuid)
returns void language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_password);
  delete from restaurants where id = p_id;
end $$;

revoke execute on function public.check_admin(text), public.require_admin(text) from public, anon, authenticated;
grant execute on function public.check_admin(text) to anon, authenticated;
revoke execute on function
  public.add_restaurant(text, text, double precision, double precision, text, text, text, text, text),
  public.admin_update_restaurant(text, uuid, text, text, double precision, double precision, text, text, text[]),
  public.admin_set_dishes(text, uuid, jsonb),
  public.admin_delete_restaurant(text, uuid)
from public;
grant execute on function
  public.add_restaurant(text, text, double precision, double precision, text, text, text, text, text),
  public.admin_update_restaurant(text, uuid, text, text, double precision, double precision, text, text, text[]),
  public.admin_set_dishes(text, uuid, jsonb),
  public.admin_delete_restaurant(text, uuid)
to anon, authenticated;

-- ---------------------------------------------------------------------
-- Contraseña del panel: cambia el texto y ejecuta SOLO estas líneas.
-- ---------------------------------------------------------------------
-- insert into public.admin_secret (password_hash)
-- values (extensions.crypt('cambia-esta-contraseña', extensions.gen_salt('bf')))
-- on conflict (id) do update set password_hash = excluded.password_hash;
