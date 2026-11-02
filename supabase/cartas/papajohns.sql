-- Papa John's: 33 locales de la Comunidad de Madrid (web oficial de la marca).
-- Carta de alérgenos: PDF oficial de alérgenos (https://cdn.new.papajohns.es/Alergenos+Espa%C3%B1a/TablaAlergenos+ED+44.pdf).
-- Generado con scripts/cartas/tablas_pdf.py. Ejecútalo en Supabase → SQL Editor
-- después de schema.sql. Se puede volver a ejecutar: no duplica locales.
do $$
declare
  v_template uuid;
begin
  -- El SQL Editor ejecuta todo en una transacción: la tabla de la cadena anterior puede seguir ahí.
  drop table if exists chain_stores;
  create temp table chain_stores (place_id text, name text, address text, lat float8, lng float8, maps_url text, menu text);
  insert into chain_stores values
  ('papajohns:osm-node-11161442316', 'Papa John''s', '', 40.4271578, -3.5543306, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%2C%20', 'papajohns'),
  ('papajohns:osm-node-11220870879', 'Papa John''s Avenida de la Reina Victoria 68', 'Avenida de la Reina Victoria 68, Madrid', 40.4461032, -3.7142936, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%20Avenida%20de%20la%20Reina%20Victoria%2068%2C%20Avenida%20de%20la%20Reina%20Victoria%2068%2C%20Madrid', 'papajohns'),
  ('papajohns:osm-node-11290566325', 'Papa John''s', '', 40.6120797, -3.7122502, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%2C%20', 'papajohns'),
  ('papajohns:osm-node-11412763792', 'Papa John''s', '', 40.3487443, -3.5186569, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%2C%20', 'papajohns'),
  ('papajohns:osm-node-11486849623', 'Papa John''s Avenida del Sistema Solar 9', 'Avenida del Sistema Solar 9, Parla', 40.2229376, -3.760525, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%20Avenida%20del%20Sistema%20Solar%209%2C%20Avenida%20del%20Sistema%20Solar%209%2C%20Parla', 'papajohns'),
  ('papajohns:osm-node-12053415021', 'Papa John''s', '', 40.3874952, -3.7006512, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%2C%20', 'papajohns'),
  ('papajohns:osm-node-12247906356', 'Papa John''s', '', 40.4416001, -3.6403694, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%2C%20', 'papajohns'),
  ('papajohns:osm-node-12265668641', 'Papa John''s Calle Gran Vía 14', 'Calle Gran Vía 14, Majadahonda', 40.4726655, -3.8720308, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%20Calle%20Gran%20V%C3%ADa%2014%2C%20Calle%20Gran%20V%C3%ADa%2014%2C%20Majadahonda', 'papajohns'),
  ('papajohns:osm-node-12653700005', 'Papa John''s', '', 40.3536925, -3.6886194, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%2C%20', 'papajohns'),
  ('papajohns:osm-node-12778869680', 'Papa John''s', '', 40.4960141, -3.3632732, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%2C%20', 'papajohns'),
  ('papajohns:osm-node-13064064370', 'Papa John''s', '', 40.3909985, -3.6491483, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%2C%20', 'papajohns'),
  ('papajohns:osm-node-1457689168', 'Papa John''s', '', 40.4016583, -3.7075241, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%2C%20', 'papajohns'),
  ('papajohns:osm-node-2100673955', 'Papa John''s', '', 40.3618878, -3.752856, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%2C%20', 'papajohns'),
  ('papajohns:osm-node-2182367954', 'Papa John''s', '', 40.4625518, -3.6371803, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%2C%20', 'papajohns'),
  ('papajohns:osm-node-2718702009', 'Papa John''s Calle de la Antracita 10', 'Calle de la Antracita 10, Madrid', 40.3901461, -3.6902288, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%20Calle%20de%20la%20Antracita%2010%2C%20Calle%20de%20la%20Antracita%2010%2C%20Madrid', 'papajohns'),
  ('papajohns:osm-node-4651496892', 'Papa John''s Calle de Galileo 15', 'Calle de Galileo 15, Madrid', 40.4316091, -3.7105702, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%20Calle%20de%20Galileo%2015%2C%20Calle%20de%20Galileo%2015%2C%20Madrid', 'papajohns'),
  ('papajohns:osm-node-4734862923', 'Papa John''s Avenida del Ingeniero Emilio Herrera 13', 'Avenida del Ingeniero Emilio Herrera 13, Madrid', 40.4917928, -3.6538512, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%20Avenida%20del%20Ingeniero%20Emilio%20Herrera%2013%2C%20Avenida%20del%20Ingeniero%20Emilio%20Herrera%2013%2C%20Madrid', 'papajohns'),
  ('papajohns:osm-node-4930503557', 'Papa John''s', '', 40.3361696, -3.8629816, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%2C%20', 'papajohns'),
  ('papajohns:osm-node-5051787307', 'Papa John''s', '', 40.3167377, -3.7020086, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%2C%20', 'papajohns'),
  ('papajohns:osm-node-5217022190', 'Papa John''s', '', 40.4604083, -3.4590764, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%2C%20', 'papajohns'),
  ('papajohns:osm-node-5232643654', 'Papa John''s Paseo de Fuente Lucha', 'Paseo de Fuente Lucha', 40.551654, -3.6603884, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%20Paseo%20de%20Fuente%20Lucha%2C%20Paseo%20de%20Fuente%20Lucha', 'papajohns'),
  ('papajohns:osm-node-5806606953', 'Papa John''s', '', 40.4870098, -3.3501828, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%2C%20', 'papajohns'),
  ('papajohns:osm-node-5830703820', 'Papa John''s', '', 40.4925952, -3.8743991, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%2C%20', 'papajohns'),
  ('papajohns:osm-node-6092307685', 'Papa John''s Calle de Valderrebollo 1', 'Calle de Valderrebollo 1', 40.3738627, -3.6275137, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%20Calle%20de%20Valderrebollo%201%2C%20Calle%20de%20Valderrebollo%201', 'papajohns'),
  ('papajohns:osm-node-6227519631', 'Papa John''s', 'Getafe', 40.3276125, -3.7286645, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%2C%20Getafe', 'papajohns'),
  ('papajohns:osm-node-7102357029', 'Papa John''s', '', 40.4472673, -3.8015652, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%2C%20', 'papajohns'),
  ('papajohns:osm-node-8018125974', 'Papa John''s', '', 40.486953, -3.7195592, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%2C%20', 'papajohns'),
  ('papajohns:osm-node-8690408174', 'Papa John''s Calle Ruiz de Alarcón 6', 'Calle Ruiz de Alarcón 6, Collado Villalba', 40.626759, -4.0024501, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%20Calle%20Ruiz%20de%20Alarc%C3%B3n%206%2C%20Calle%20Ruiz%20de%20Alarc%C3%B3n%206%2C%20Collado%20Villalba', 'papajohns'),
  ('papajohns:osm-node-9443076712', 'Papa John''s', '', 40.3878487, -3.7324923, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%2C%20', 'papajohns'),
  ('papajohns:osm-node-9524051528', 'Papa John''s Calle del Marqués de Viana 76', 'Calle del Marqués de Viana 76', 40.4641036, -3.7049731, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%20Calle%20del%20Marqu%C3%A9s%20de%20Viana%2076%2C%20Calle%20del%20Marqu%C3%A9s%20de%20Viana%2076', 'papajohns'),
  ('papajohns:osm-node-9726284830', 'Papa John''s', '', 40.3903663, -3.7517546, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%2C%20', 'papajohns'),
  ('papajohns:osm-node-9747019334', 'Papa John''s Calle Mediterraneo 8', 'Calle Mediterraneo 8', 40.3305608, -3.8375191, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%20Calle%20Mediterraneo%208%2C%20Calle%20Mediterraneo%208', 'papajohns'),
  ('papajohns:osm-node-9998156162', 'Papa John''s', '', 40.3662974, -3.7106836, 'https://www.google.com/maps/search/?api=1&query=Papa%20John%27s%2C%20', 'papajohns');

  -- 1. Si el local ya estaba en el mapa (p. ej. desde OpenStreetMap) a menos de ~150 m, se reutiliza.
  update public.restaurants r
     set place_id = s.place_id, name = s.name, address = s.address
    from chain_stores s
   where r.place_id not like 'papajohns:%' and r.name ilike '%papa john%'
     and abs(r.lat - s.lat) < 0.0014 and abs(r.lng - s.lng) < 0.0018
     and not exists (select 1 from public.restaurants x where x.place_id = s.place_id);

  insert into public.restaurants (place_id, name, address, lat, lng, category, cuisine, maps_url, source)
  select place_id, name, address, lat, lng, 'Restaurante', 'pizza', maps_url, 'manual'
  from chain_stores
  on conflict (place_id) do update set name = excluded.name, address = excluded.address,
    lat = excluded.lat, lng = excluded.lng, maps_url = excluded.maps_url;

  -- 2. Cada carta se guarda una vez.

  -- Carta papajohns: 134 platos, actualizada el . La guarda papajohns:osm-node-11161442316.
  select id into v_template from public.restaurants where place_id = 'papajohns:osm-node-11161442316';
  delete from public.dishes where restaurant_id = v_template;
  insert into public.dishes (restaurant_id, position, section, name, allergens, traces)
  select v_template, d.ord, d.value ->> 'section', d.value ->> 'name',
         array(select jsonb_array_elements_text(d.value -> 'allergens')),
         array(select jsonb_array_elements_text(d.value -> 'traces'))
  from jsonb_array_elements('[
  {"section": "Pizzas", "name": "Barbacoa", "allergens": ["gluten", "soja", "lacteos", "mostaza", "sulfitos"], "traces": ["huevo", "apio"]},
  {"section": "Pizzas", "name": "Barbacoa Crema", "allergens": ["gluten", "soja", "lacteos", "mostaza", "sulfitos"], "traces": []},
  {"section": "Pizzas", "name": "Bbq Veggie", "allergens": ["gluten", "soja", "lacteos", "sulfitos"], "traces": ["mostaza"]},
  {"section": "Pizzas", "name": "Carbonara", "allergens": ["gluten", "soja", "lacteos"], "traces": ["mostaza"]},
  {"section": "Pizzas", "name": "CarBrienara", "allergens": ["gluten", "soja", "lacteos"], "traces": ["mostaza"]},
  {"section": "Pizzas", "name": "Carnívora", "allergens": ["gluten", "lacteos", "mostaza"], "traces": ["huevo", "soja", "apio"]},
  {"section": "Pizzas", "name": "Crispy BBQ-Bacon", "allergens": ["gluten", "lacteos", "sulfitos"], "traces": ["soja", "mostaza"]},
  {"section": "Pizzas", "name": "Crispy BBQ & ribs", "allergens": ["gluten", "lacteos", "sulfitos"], "traces": ["soja", "mostaza"]},
  {"section": "Pizzas", "name": "Crispy Carbo-Bacon", "allergens": ["gluten", "soja", "lacteos"], "traces": ["mostaza"]},
  {"section": "Pizzas", "name": "Especial de John", "allergens": ["gluten", "lacteos", "mostaza"], "traces": ["huevo", "cacahuete", "soja", "apio"]},
  {"section": "Pizzas", "name": "Hawaiana", "allergens": ["gluten", "lacteos"], "traces": ["soja", "mostaza"]},
  {"section": "Pizzas", "name": "Hot Honey Pepperoni", "allergens": ["gluten", "lacteos", "mostaza"], "traces": ["soja"]},
  {"section": "Pizzas", "name": "Italiana Ranch", "allergens": ["gluten", "lacteos", "mostaza"], "traces": ["cacahuete", "soja", "apio"]},
  {"section": "Pizzas", "name": "Margarita", "allergens": ["gluten", "lacteos"], "traces": ["cacahuete", "soja", "apio", "mostaza"]},
  {"section": "Pizzas", "name": "Marinera", "allergens": ["gluten", "pescado", "lacteos"], "traces": ["soja", "mostaza"]},
  {"section": "Pizzas", "name": "Philly cheesesteak", "allergens": ["gluten", "lacteos", "mostaza", "sulfitos"], "traces": ["crustaceos", "soja", "frutos_secos", "moluscos"]},
  {"section": "Pizzas", "name": "Pollo BBQ", "allergens": ["gluten", "soja", "lacteos", "mostaza", "sulfitos"], "traces": []},
  {"section": "Pizzas", "name": "Pollo caprese", "allergens": ["gluten", "huevo", "soja", "lacteos", "apio", "mostaza"], "traces": ["sulfitos"]},
  {"section": "Pizzas", "name": "Pollo Philadelphia", "allergens": ["gluten", "soja", "lacteos", "mostaza"], "traces": []},
  {"section": "Pizzas", "name": "Ranchera Veggie", "allergens": ["gluten", "soja", "lacteos", "mostaza"], "traces": []},
  {"section": "Pizzas", "name": "Seis quesos", "allergens": ["gluten", "lacteos"], "traces": ["cacahuete", "soja", "apio", "mostaza"]},
  {"section": "Pizzas", "name": "Super papa", "allergens": ["gluten", "lacteos", "mostaza"], "traces": ["huevo", "pescado", "soja", "apio"]},
  {"section": "Pizzas", "name": "Super pepperoni", "allergens": ["gluten", "lacteos", "mostaza"], "traces": ["soja"]},
  {"section": "Pizzas", "name": "Vegetariana", "allergens": ["gluten", "lacteos"], "traces": ["pescado", "soja", "mostaza"]},
  {"section": "Entrantes", "name": "Alitas de pollo", "allergens": ["gluten", "apio"], "traces": []},
  {"section": "Entrantes", "name": "Aros de cebolla", "allergens": ["gluten"], "traces": []},
  {"section": "Entrantes", "name": "Hot Cheddar Bites", "allergens": ["gluten", "lacteos"], "traces": ["crustaceos", "huevo", "pescado", "soja", "mostaza"]},
  {"section": "Entrantes", "name": "Mozzarella sticks", "allergens": ["gluten", "lacteos"], "traces": []},
  {"section": "Entrantes", "name": "Muslitos de pollo picantes", "allergens": ["gluten"], "traces": []},
  {"section": "Entrantes", "name": "Nacho Cheddar Bites", "allergens": ["gluten", "lacteos"], "traces": []},
  {"section": "Entrantes", "name": "Pan de ajo mozzarella", "allergens": ["gluten", "lacteos"], "traces": ["soja", "mostaza"]},
  {"section": "Entrantes", "name": "Papas", "allergens": [], "traces": []},
  {"section": "Entrantes", "name": "Pechuguitas de pollo", "allergens": ["gluten", "soja", "lacteos", "apio"], "traces": []},
  {"section": "Entrantes", "name": "Pechuguitas Korean BBQ", "allergens": ["gluten", "soja", "lacteos", "apio"], "traces": []},
  {"section": "Entrantes", "name": "Pechuguitas Sweet Chili", "allergens": ["gluten", "apio"], "traces": []},
  {"section": "Papa rolls", "name": "Papa Rolls Crispy Bacon", "allergens": ["gluten", "lacteos", "sulfitos"], "traces": ["soja", "mostaza"]},
  {"section": "Papa rolls", "name": "Papa rolls Milkybar", "allergens": ["gluten", "lacteos"], "traces": ["huevo", "soja", "frutos_secos", "mostaza"]},
  {"section": "Papa rolls", "name": "Papa Rolls Pepperoni", "allergens": ["gluten", "lacteos", "mostaza"], "traces": ["soja"]},
  {"section": "Papa rolls", "name": "Papa Rolls BBQ RIBS", "allergens": ["gluten", "lacteos", "sulfitos"], "traces": ["crustaceos", "soja", "frutos_secos", "mostaza", "moluscos"]},
  {"section": "Papa rolls", "name": "Papa Rolls York", "allergens": ["gluten", "lacteos"], "traces": ["soja", "mostaza"]},
  {"section": "Pizzas individuales ts5", "name": "PEPPERONI ESTELAR", "allergens": ["gluten", "lacteos", "mostaza"], "traces": ["soja"]},
  {"section": "Pizzas individuales ts5", "name": "VAQUERA BBQ", "allergens": ["gluten", "soja", "lacteos", "mostaza", "sulfitos"], "traces": []},
  {"section": "Pizzas individuales ts5", "name": "RODEO PEPPERS", "allergens": ["gluten", "lacteos", "mostaza"], "traces": ["huevo", "soja", "apio"]},
  {"section": "Peque johns", "name": "BBQ BACON", "allergens": ["gluten", "lacteos", "sulfitos"], "traces": ["soja", "mostaza"]},
  {"section": "Peque johns", "name": "Margarita", "allergens": ["gluten", "lacteos"], "traces": ["cacahuete", "soja", "apio", "mostaza"]},
  {"section": "Peque johns", "name": "YORKESO", "allergens": ["gluten", "lacteos"], "traces": ["soja", "mostaza"]},
  {"section": "Papito", "name": "Papito Margarita", "allergens": ["gluten", "lacteos"], "traces": ["cacahuete", "soja", "apio", "mostaza"]},
  {"section": "Papito", "name": "Papito Pollo y Bacon", "allergens": ["gluten", "soja", "lacteos", "mostaza"], "traces": []},
  {"section": "Papito", "name": "Papito Ternera y Cebolla", "allergens": ["gluten", "lacteos"], "traces": ["huevo", "soja", "apio", "mostaza"]},
  {"section": "Papito", "name": "Papito York y champiñón", "allergens": ["gluten", "lacteos"], "traces": ["soja", "mostaza"]},
  {"section": "Sin gluten", "name": "Sin Gluten Bacon XL", "allergens": ["lacteos"], "traces": ["soja"]},
  {"section": "Sin gluten", "name": "Sin Gluten Pepperoni", "allergens": ["lacteos", "mostaza"], "traces": ["soja"]},
  {"section": "Postres", "name": "Choco Cookie", "allergens": ["gluten", "huevo", "lacteos"], "traces": ["cacahuete", "soja", "frutos_secos", "sesamo"]},
  {"section": "Postres", "name": "La Monstrua de las Galletas", "allergens": ["gluten", "huevo", "lacteos"], "traces": ["cacahuete", "soja", "frutos_secos", "sesamo"]},
  {"section": "Helados", "name": "B&J Choco Fudge Brownie (100/465ml)", "allergens": ["gluten", "huevo", "lacteos"], "traces": []},
  {"section": "Helados", "name": "B&J Chunky Monkey (465ml)", "allergens": ["huevo", "soja", "lacteos", "frutos_secos"], "traces": []},
  {"section": "Helados", "name": "B&J Cookie Dough (100/465ml)", "allergens": ["gluten", "huevo", "soja", "lacteos"], "traces": []},
  {"section": "Helados", "name": "B&J Sundae Dulce-Delish (427ML)", "allergens": ["gluten", "huevo", "soja", "lacteos"], "traces": []},
  {"section": "Helados", "name": "B&J Sweet Mango (465ML)", "allergens": ["huevo", "soja", "lacteos"], "traces": []},
  {"section": "Helados", "name": "B&J Vainilla Pecan (100ml)", "allergens": ["huevo", "lacteos", "frutos_secos"], "traces": []},
  {"section": "Helados", "name": "B&J Strawberry Cheesecake (100ML)", "allergens": ["gluten", "huevo", "soja", "lacteos"], "traces": []},
  {"section": "Helados", "name": "BONBON SALTED CARAMEL & ALMOND", "allergens": ["lacteos", "frutos_secos"], "traces": ["gluten", "huevo", "soja"]},
  {"section": "Helados", "name": "Bonbon White Chocolate & Cookies", "allergens": ["gluten", "soja", "lacteos"], "traces": ["frutos_secos"]},
  {"section": "Helados", "name": "MAGNUM White Chocolate & Cookies", "allergens": ["gluten", "soja", "lacteos"], "traces": ["frutos_secos"]},
  {"section": "Helados", "name": "MAGNUM BONBON FRUIT", "allergens": ["lacteos"], "traces": ["soja", "frutos_secos"]},
  {"section": "Helados", "name": "Magnum White CHOCO COOKIES (440ml)", "allergens": ["gluten", "soja", "lacteos"], "traces": ["frutos_secos"]},
  {"section": "Helados", "name": "Magnum Almond (440ml)", "allergens": ["lacteos", "frutos_secos"], "traces": []},
  {"section": "Ingredientes", "name": "Aceitunas Negras", "allergens": [], "traces": ["pescado", "lacteos"]},
  {"section": "Ingredientes", "name": "Atún", "allergens": ["pescado"], "traces": []},
  {"section": "Ingredientes", "name": "Bacon", "allergens": [], "traces": ["soja"]},
  {"section": "Ingredientes", "name": "Bacon crunchy", "allergens": [], "traces": ["soja", "lacteos", "mostaza"]},
  {"section": "Ingredientes", "name": "Brie", "allergens": ["lacteos"], "traces": []},
  {"section": "Ingredientes", "name": "Borde queso tipo Mozzarella", "allergens": ["lacteos"], "traces": []},
  {"section": "Ingredientes", "name": "Carne de vacuno picante", "allergens": ["gluten", "lacteos"], "traces": ["huevo", "soja", "apio", "mostaza"]},
  {"section": "Ingredientes", "name": "Carne de cerdo especiada", "allergens": ["mostaza"], "traces": ["gluten", "huevo", "soja", "lacteos", "apio"]},
  {"section": "Ingredientes", "name": "Carne de costilla baja de ternera", "allergens": ["gluten"], "traces": []},
  {"section": "Ingredientes", "name": "Cebolla Caramelizada", "allergens": [], "traces": []},
  {"section": "Ingredientes", "name": "Cebolla Crispy", "allergens": ["gluten"], "traces": ["soja", "mostaza"]},
  {"section": "Ingredientes", "name": "Cinco Quesos", "allergens": ["lacteos"], "traces": []},
  {"section": "Ingredientes", "name": "Guanciale", "allergens": [], "traces": ["soja"]},
  {"section": "Ingredientes", "name": "Jalapeños", "allergens": [], "traces": []},
  {"section": "Ingredientes", "name": "Masa", "allergens": ["gluten"], "traces": ["soja", "mostaza"]},
  {"section": "Ingredientes", "name": "MASA PADRE", "allergens": ["gluten", "soja", "lacteos"], "traces": ["sesamo"]},
  {"section": "Ingredientes", "name": "Mezcla de especias", "allergens": [], "traces": ["gluten", "cacahuete", "apio", "mostaza"]},
  {"section": "Ingredientes", "name": "Mozzarella", "allergens": ["lacteos"], "traces": []},
  {"section": "Ingredientes", "name": "Peperonccini", "allergens": ["sulfitos"], "traces": []},
  {"section": "Ingredientes", "name": "Pepperoni", "allergens": ["mostaza"], "traces": ["soja", "lacteos"]},
  {"section": "Ingredientes", "name": "Piña", "allergens": [], "traces": []},
  {"section": "Ingredientes", "name": "Philadelphia (queso crema)", "allergens": ["lacteos"], "traces": []},
  {"section": "Ingredientes", "name": "Pulled Beef", "allergens": [], "traces": ["soja", "lacteos", "mostaza"]},
  {"section": "Ingredientes", "name": "Queso cheddar rallado", "allergens": ["lacteos"], "traces": []},
  {"section": "Ingredientes", "name": "Salsa BBQ", "allergens": ["sulfitos"], "traces": []},
  {"section": "Ingredientes", "name": "Salsa Carbonara", "allergens": ["soja", "lacteos"], "traces": []},
  {"section": "Ingredientes", "name": "Salsa Cheddar", "allergens": ["lacteos"], "traces": []},
  {"section": "Ingredientes", "name": "Salsa de Ajo (Bolsa)", "allergens": [], "traces": []},
  {"section": "Ingredientes", "name": "Salsa Hot Honey", "allergens": [], "traces": []},
  {"section": "Ingredientes", "name": "Salsa Miel y Mostaza", "allergens": ["gluten", "mostaza"], "traces": []},
  {"section": "Ingredientes", "name": "Salsa Milkybar", "allergens": ["lacteos"], "traces": ["frutos_secos"]},
  {"section": "Ingredientes", "name": "Salsa de tomate", "allergens": [], "traces": []},
  {"section": "Ingredientes", "name": "Salsa Pesto", "allergens": ["gluten", "huevo", "lacteos", "apio"], "traces": ["sulfitos"]},
  {"section": "Ingredientes", "name": "Salsa Ranch", "allergens": ["mostaza"], "traces": []},
  {"section": "Ingredientes", "name": "Salsa sticky korean", "allergens": ["gluten", "soja"], "traces": []},
  {"section": "Ingredientes", "name": "Salsa sweet chili", "allergens": [], "traces": []},
  {"section": "Ingredientes", "name": "Sémola de maíz", "allergens": [], "traces": []},
  {"section": "Ingredientes", "name": "Tiras de pechuga de pollo a la parrilla", "allergens": ["soja", "mostaza"], "traces": []},
  {"section": "Ingredientes", "name": "Topping Milkybar Troceado", "allergens": ["lacteos"], "traces": ["gluten", "huevo", "soja", "frutos_secos"]},
  {"section": "Ingredientes", "name": "Vegetales (Tomates, pimiento verde/amarillo, champiñón, cebolla y tomate cherry)", "allergens": [], "traces": []},
  {"section": "Ingredientes", "name": "York", "allergens": [], "traces": ["soja"]},
  {"section": "Ingredientes veganos", "name": "Bocados Veganos", "allergens": ["soja"], "traces": ["gluten"]},
  {"section": "Ingredientes veganos", "name": "Topping rallado vegano", "allergens": [], "traces": []},
  {"section": "Bebidas", "name": "ABSOLUT RASPBERRY LEMONADE", "allergens": [], "traces": []},
  {"section": "Bebidas", "name": "Alhambra Especial", "allergens": ["gluten"], "traces": []},
  {"section": "Bebidas", "name": "Aquabona agua mineral", "allergens": [], "traces": []},
  {"section": "Bebidas", "name": "Aquarius limón", "allergens": [], "traces": []},
  {"section": "Bebidas", "name": "Aquarius naranja", "allergens": [], "traces": []},
  {"section": "Bebidas", "name": "Aquarius Melocotón Rojo", "allergens": [], "traces": []},
  {"section": "Bebidas", "name": "BATIDO CHOCOLATE PULEVA", "allergens": ["lacteos"], "traces": []},
  {"section": "Bebidas", "name": "Budweiser", "allergens": ["gluten"], "traces": []},
  {"section": "Bebidas", "name": "Capri Sun", "allergens": [], "traces": []},
  {"section": "Bebidas", "name": "Coca Cola", "allergens": [], "traces": []},
  {"section": "Bebidas", "name": "Coca Cola Zero", "allergens": [], "traces": []},
  {"section": "Bebidas", "name": "Coca Cola Zero Zero", "allergens": [], "traces": []},
  {"section": "Bebidas", "name": "Corona", "allergens": ["gluten"], "traces": []},
  {"section": "Bebidas", "name": "Fanta naranja", "allergens": [], "traces": []},
  {"section": "Bebidas", "name": "Fuze Tea", "allergens": [], "traces": []},
  {"section": "Bebidas", "name": "Fuze Tea Maracuyá", "allergens": [], "traces": []},
  {"section": "Bebidas", "name": "Mahou Mixta", "allergens": ["gluten"], "traces": []},
  {"section": "Bebidas", "name": "Mahou Tostada 0´0", "allergens": ["gluten"], "traces": []},
  {"section": "Bebidas", "name": "MALIBU PIÑA COLADA", "allergens": [], "traces": []},
  {"section": "Bebidas", "name": "Monster", "allergens": [], "traces": []},
  {"section": "Bebidas", "name": "Monster Mango Loco", "allergens": [], "traces": []},
  {"section": "Bebidas", "name": "Monster Ultra White", "allergens": [], "traces": []},
  {"section": "Bebidas", "name": "MONSTER VIKING BERRY", "allergens": [], "traces": []},
  {"section": "Bebidas", "name": "Sprite", "allergens": [], "traces": []}
]'::jsonb) with ordinality as d(value, ord);
  update public.restaurants set menu_from = null, menu_updated_at = now() where id = v_template;

  -- 3. El resto de locales comparten la carta de su formato.
  update public.restaurants r
     set menu_from = t.id, menu_type = '', menu_src = '{}'
    from chain_stores s
    join (values ('papajohns', 'papajohns:osm-node-11161442316')) as m(menu, template) on m.menu = s.menu
    join public.restaurants t on t.place_id = m.template
   where r.place_id = s.place_id and r.id <> t.id;
  delete from public.dishes d using public.restaurants r, chain_stores s
   where d.restaurant_id = r.id and r.place_id = s.place_id and r.menu_from is not null;
  drop table chain_stores;
end $$;
