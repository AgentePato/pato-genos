import { config } from './config.js';
import { createBackend } from './api/index.js';
import { createPlaceSearch } from './api/places.js';
import { ALLERGENS, allergenByKey, dishIsSafe } from './allergens.js';
import { h, replaceContent, safeUrl } from './ui/dom.js';

const PAGE_SIZE = 25;

const state = {
  restaurants: [],
  search: '',
  withMenu: false,
  nearMe: false,
  avoid: new Set(),
  selectedId: null,
  userPos: null,
  shown: PAGE_SIZE,
};

const $ = (id) => document.getElementById(id);
let backend;
const placeSearch = createPlaceSearch(config);

// ------------------------------------------------------------------ mapa
const map = L.map('map').setView([config.searchArea.lat, config.searchArea.lng], 14);
L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>',
  maxZoom: 19,
}).addTo(map);
const markerLayer = L.layerGroup().addTo(map);
let userMarker = null;

function pinIcon(restaurant, selected) {
  const hasMenu = hasAnyMenu(restaurant);
  return L.divIcon({
    className: '',
    html: `<span class="pin${hasMenu ? ' pin--menu' : ''}${selected ? ' pin--selected' : ''}">${hasMenu ? '🦆' : ''}</span>`,
    iconSize: hasMenu ? [30, 30] : [16, 16],
    iconAnchor: hasMenu ? [15, 15] : [8, 8],
  });
}

// ------------------------------------------------------------------ filtros
const hasAnyMenu = (r) => r.dishes.length > 0 || (r.menu_type && r.menu_src.length > 0);
const normalize = (text) => (text ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

function distanceKm(a, b) {
  const rad = Math.PI / 180;
  const dLat = (b.lat - a.lat) * rad;
  const dLng = (b.lng - a.lng) * rad;
  const x = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin(dLng / 2) ** 2;
  return 12742 * Math.asin(Math.sqrt(x));
}

const safeDishes = (r) => r.dishes.filter((d) => dishIsSafe(d, state.avoid));

function filtered() {
  const q = normalize(state.search.trim());
  const list = state.restaurants.filter((r) => {
    if (q && !normalize(`${r.name} ${r.address} ${r.cuisine} ${r.category}`).includes(q)) return false;
    if (state.withMenu && !hasAnyMenu(r)) return false;
    // Con alérgenos marcados solo sirven las cartas digitalizadas (platos), y con algún plato apto.
    if (state.avoid.size && safeDishes(r).length === 0) return false;
    return true;
  });
  const dist = (r) => (state.userPos ? distanceKm(state.userPos, r) : 0);
  return list.sort((a, b) =>
    (state.nearMe ? dist(a) - dist(b) : 0)
    || Number(hasAnyMenu(b)) - Number(hasAnyMenu(a))
    || a.name.localeCompare(b.name, 'es'));
}

// ------------------------------------------------------------------ pintar
function renderFilters() {
  const chip = (label, active, onClick) =>
    h('button', { type: 'button', class: `chip${active ? ' chip--on' : ''}`, 'aria-pressed': String(active), onClick }, label);

  replaceContent($('quickFilters'),
    chip('📍 Cerca de mí', state.nearMe, toggleNearMe),
    chip('📋 Con carta de alérgenos', state.withMenu, () => { state.withMenu = !state.withMenu; update(); }),
  );

  replaceContent($('allergenFilters'),
    h('span', { class: 'chips__label' }, 'Sin:'),
    ALLERGENS.map((a) => chip(`${a.icon} ${a.label}`, state.avoid.has(a.key), () => {
      if (state.avoid.has(a.key)) state.avoid.delete(a.key);
      else state.avoid.add(a.key);
      update();
    })),
  );
}

function renderMarkers(list) {
  markerLayer.clearLayers();
  for (const r of list) {
    L.marker([r.lat, r.lng], { icon: pinIcon(r, r.id === state.selectedId), title: r.name, zIndexOffset: hasAnyMenu(r) ? 500 : 0 })
      .on('click', () => select(r.id, { scroll: true }))
      .addTo(markerLayer);
  }
}

function renderMenu(r) {
  const parts = [];

  if (r.dishes.length) {
    const sections = new Map();
    for (const d of r.dishes) {
      const name = d.section || 'Carta';
      sections.set(name, [...(sections.get(name) ?? []), d]);
    }
    parts.push(h('div', { class: 'dishes' },
      state.avoid.size ? h('p', { class: 'dishes__hint' }, `✅ ${safeDishes(r).length} de ${r.dishes.length} platos sin lo que evitas`) : null,
      [...sections].map(([section, dishes]) => h('section', {},
        h('h4', {}, section),
        h('ul', {}, dishes.map((d) => h('li', { class: `dish${dishIsSafe(d, state.avoid) ? '' : ' dish--unsafe'}` },
          h('span', { class: 'dish__name' }, d.name),
          h('span', { class: 'dish__allergens' },
            d.allergens.length
              ? d.allergens.map((a) => h('span', { class: `allergen${state.avoid.has(a) ? ' allergen--hit' : ''}`, title: allergenByKey[a]?.label ?? a }, allergenByKey[a]?.icon ?? a))
              : h('span', { class: 'muted' }, 'Sin alérgenos declarados')),
        ))),
      )),
    ));
  }

  const sources = r.menu_src.map(safeUrl).filter(Boolean);
  if (r.menu_type === 'pdf' && sources[0]) {
    parts.push(
      h('iframe', { src: sources[0], class: 'menu-pdf', title: `Carta de ${r.name}` }),
      h('a', { href: sources[0], target: '_blank', rel: 'noopener noreferrer', class: 'view-btn' }, 'Abrir PDF en pantalla completa'),
    );
  } else if (r.menu_type === 'images' && sources.length) {
    parts.push(sources.map((src) => h('img', { src, alt: `Carta de ${r.name}`, class: 'menu-image', loading: 'lazy' })));
  }

  if (!parts.length) {
    parts.push(h('div', { class: 'no-image-text' }, 'La carta de alérgenos de este restaurante se subirá próximamente.'));
  }
  return h('div', { class: 'menu-container' }, parts);
}

function renderCard(r) {
  const selected = r.id === state.selectedId;
  const meta = [r.category, r.cuisine].filter(Boolean).join(' · ');
  const km = state.userPos ? distanceKm(state.userPos, r) : null;
  const mapsUrl = safeUrl(r.maps_url);

  return h('article', { class: `restaurant-card${selected ? ' restaurant-card--open' : ''}`, id: `card-${r.id}` },
    h('button', { type: 'button', class: 'restaurant-header', 'aria-expanded': String(selected), onClick: () => select(selected ? null : r.id) },
      h('span', { class: 'restaurant-name' }, r.name,
        hasAnyMenu(r) ? h('span', { class: 'badge' }, r.dishes.length ? 'Carta digital' : 'Carta') : null),
      h('span', { class: 'restaurant-type' },
        [meta, r.address, km != null ? (km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(1)} km`) : null].filter(Boolean).join(' — ')),
    ),
    selected ? [
      renderMenu(r),
      mapsUrl ? h('a', { href: mapsUrl, target: '_blank', rel: 'noopener noreferrer', class: 'maps-link' }, '📍 Cómo llegar (Google Maps)') : null,
    ] : null,
  );
}

function renderList(list) {
  const total = state.restaurants.length;
  $('resultCount').textContent = list.length === total ? `${total} sitios` : `${list.length} de ${total} sitios`;

  if (!list.length) {
    replaceContent($('restaurant-list'), h('div', { class: 'placeholder-message' },
      state.avoid.size
        ? 'Ningún restaurante con carta digitalizada tiene platos sin esos alérgenos (todavía).'
        : `No se han encontrado resultados${state.search ? ` para "${state.search}"` : ''}.`));
    return;
  }

  // El seleccionado siempre se ve, aunque esté más allá de la página actual.
  const visible = list.slice(0, state.shown);
  const selected = list.find((r) => r.id === state.selectedId);
  if (selected && !visible.includes(selected)) visible.unshift(selected);

  replaceContent($('restaurant-list'),
    visible.map(renderCard),
    list.length > state.shown
      ? h('button', { type: 'button', class: 'more-btn', onClick: () => { state.shown += PAGE_SIZE; update(); } },
        `Mostrar más (${list.length - state.shown})`)
      : null,
  );
}

function update() {
  const list = filtered();
  renderFilters();
  renderMarkers(list);
  renderList(list);
}

function select(id, { scroll = false } = {}) {
  state.selectedId = id;
  update();
  const r = state.restaurants.find((x) => x.id === id);
  if (!r) return;
  map.panTo([r.lat, r.lng]);
  if (scroll) $(`card-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function toggleNearMe() {
  if (state.nearMe) {
    state.nearMe = false;
    update();
    return;
  }
  if (!navigator.geolocation) return toast('Tu navegador no permite saber dónde estás.');
  navigator.geolocation.getCurrentPosition((pos) => {
    state.userPos = { lat: pos.coords.latitude, lng: pos.coords.longitude };
    state.nearMe = true;
    userMarker?.remove();
    userMarker = L.circleMarker([state.userPos.lat, state.userPos.lng], { radius: 8, color: '#fff', weight: 3, fillColor: '#3b82f6', fillOpacity: 1 }).addTo(map);
    map.setView([state.userPos.lat, state.userPos.lng], 15);
    update();
  }, () => toast('No se ha podido obtener tu ubicación.'), { enableHighAccuracy: true, timeout: 10000 });
}

let toastTimer;
function toast(message) {
  const el = $('toast');
  el.textContent = message;
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.hidden = true; }, 3500);
}

// ------------------------------------------------------------------ añadir restaurante
let searchTimer;
let searchToken = 0;

function openAddDialog() {
  $('addProvider').textContent = `Busca el sitio y añádelo al mapa. Resultados de ${placeSearch.provider}.`;
  $('addSearch').value = state.search;
  $('addDialog').showModal();
  runPlaceSearch();
}

function runPlaceSearch() {
  clearTimeout(searchTimer);
  const query = $('addSearch').value;
  const results = $('addResults');
  if (query.trim().length < 2) {
    replaceContent(results, h('p', { class: 'muted' }, 'Escribe al menos 2 letras.'));
    return;
  }
  searchTimer = setTimeout(async () => {
    const token = ++searchToken;
    replaceContent(results, h('p', { class: 'muted' }, 'Buscando…'));
    try {
      const places = await placeSearch.search(query);
      if (token !== searchToken) return;
      if (!places.length) {
        replaceContent(results, h('p', { class: 'muted' }, 'No aparece nada. Prueba con el nombre y la calle o el pueblo.'));
        return;
      }
      replaceContent(results, places.map((place) => {
        const known = state.restaurants.find((r) => r.place_id === place.place_id);
        return h('div', { class: 'add-result' },
          h('div', {}, h('strong', {}, place.name), h('div', { class: 'muted' }, [place.category, place.address].filter(Boolean).join(' · '))),
          known
            ? h('button', { type: 'button', class: 'chip', onClick: () => { $('addDialog').close(); select(known.id, { scroll: true }); } }, 'Ya está · Ver')
            : h('button', { type: 'button', class: 'chip chip--on', onClick: (e) => addPlace(place, e.currentTarget) }, '＋ Añadir'),
        );
      }));
    } catch (error) {
      if (token === searchToken) replaceContent(results, h('p', { class: 'error' }, error.message));
    }
  }, 350);
}

async function addPlace(place, button) {
  button.disabled = true;
  button.textContent = 'Añadiendo…';
  try {
    const id = await backend.addRestaurant(place);
    await loadRestaurants();
    $('addDialog').close();
    toast(`🦆 ${place.name} añadido al mapa`);
    select(id, { scroll: true });
  } catch (error) {
    button.disabled = false;
    button.textContent = '＋ Añadir';
    toast(error.message);
  }
}

// ------------------------------------------------------------------ arranque
async function loadRestaurants() {
  state.restaurants = await backend.listRestaurants();
}

$('searchInput').addEventListener('input', (e) => {
  state.search = e.target.value;
  state.selectedId = null;
  state.shown = PAGE_SIZE;
  update();
});
$('addButton').addEventListener('click', openAddDialog);
$('addSearch').addEventListener('input', runPlaceSearch);

try {
  backend = await createBackend(config);
  $('modeBadge').hidden = backend.mode !== 'demo';
  await loadRestaurants();
  update();
} catch (error) {
  console.error(error);
  replaceContent($('restaurant-list'), h('div', { class: 'placeholder-message error' },
    `❌ No se pudo conectar con la base de datos. ${error.message}`));
}
