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
  strict: false, // evitar también las trazas ("puede contener")
  selectedId: null,
  userPos: null,
  shown: PAGE_SIZE,
};

const $ = (id) => document.getElementById(id);
let backend;
const placeSearch = createPlaceSearch(config);

// ------------------------------------------------------------------ mapa
const map = L.map('map').setView([config.searchArea.lat, config.searchArea.lng], 14);
L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', {
  attribution: 'Tiles &copy; Esri &mdash; Source: Esri, DeLorme, NAVTEQ, USGS, Intermap, iPC, NRCAN, Esri Japan, METI, Esri (Thailand), TomTom, 2012',
  maxZoom: 19,
}).addTo(map);
const markerLayer = L.layerGroup().addTo(map);
let userMarker = null;

function pinIcon(restaurant, selected) {
  const hasMenu = hasAnyMenu(restaurant);
  // Con alérgenos marcados: verde = hay platos sin ellos; naranja = solo platos que pueden llevar trazas.
  const level = restaurantLevel(restaurant);
  return L.divIcon({
    className: '',
    html: `<span class="pin${hasMenu ? ' pin--menu' : ''}${level ? ` pin--${level}` : ''}${selected ? ' pin--selected' : ''}">${hasMenu ? '🦆' : ''}</span>`,
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

const isSafe = (d) => dishIsSafe(d, state.avoid, state.strict);
const safeDishes = (r) => r.dishes.filter(isSafe);
// 'safe' = sin lo que evitas ni trazas · 'trace' = no lo lleva pero puede tener trazas · 'unsafe' = lo lleva.
function dishLevel(d) {
  if (!dishIsSafe(d, state.avoid)) return 'unsafe';
  return dishIsSafe(d, state.avoid, true) ? 'safe' : 'trace';
}
function restaurantLevel(r) {
  if (!state.avoid.size || !r.dishes.length) return null;
  const levels = new Set(r.dishes.map(dishLevel));
  if (levels.has('safe')) return 'safe';
  return levels.has('trace') && !state.strict ? 'trace' : null;
}

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
    chip('⚠️ Evitar también trazas', state.strict, () => { state.strict = !state.strict; update(); }),
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
    const icon = (a, trace) => h('span', {
      class: `allergen${trace ? ' allergen--trace' : ''}${state.avoid.has(a) ? ' allergen--hit' : ''}`,
      title: `${trace ? 'Puede contener trazas de' : 'Contiene'} ${(allergenByKey[a]?.label ?? a).toLowerCase()}`,
    }, allergenByKey[a]?.icon ?? a);
    // Cartas cortas, abiertas; las largas, plegadas por secciones.
    const openAll = r.dishes.length <= 20;

    parts.push(h('div', { class: 'dishes' },
      h('p', { class: 'dishes__legend' }, 'Icono = contiene · icono tenue con borde = puede contener trazas'),
      state.avoid.size
        ? h('p', { class: 'dishes__hint' }, dishSummary(r))
        : null,
      [...sections].map(([section, dishes]) => h('details', { class: 'dish-section', open: openAll },
        h('summary', {}, section, h('span', { class: 'dish-section__count' },
          state.avoid.size ? `${dishes.filter(isSafe).length}/${dishes.length} aptos` : `${dishes.length}`)),
        h('ul', {}, dishes.map((d) => h('li', { class: `dish${isSafe(d) ? '' : ' dish--unsafe'}${state.avoid.size && dishLevel(d) === 'trace' ? ' dish--trace' : ''}` },
          h('span', { class: 'dish__name' }, d.name,
            state.avoid.size && dishLevel(d) === 'trace' ? h('span', { class: 'trace-tag' }, '⚠️ puede contener trazas') : null),
          h('span', { class: 'dish__allergens' },
            d.allergens.length || d.traces?.length
              ? [d.allergens.map((a) => icon(a, false)), (d.traces ?? []).map((a) => icon(a, true))]
              : h('span', { class: 'muted' }, 'Sin alérgenos declarados')),
        ))),
      )),
    ));
  }

  const sources = r.menu_src.map(safeUrl).filter(Boolean);
  if (r.menu_type === 'pdf' && sources[0] && r.dishes.length) {
    // Si ya está la carta digital, el PDF queda como fuente para consultarlo.
    parts.push(h('a', { href: sources[0], target: '_blank', rel: 'noopener noreferrer', class: 'view-btn' }, '📄 Ver la tabla original (PDF)'));
  } else if (r.menu_type === 'pdf' && sources[0]) {
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

function dishSummary(r) {
  const count = (level) => r.dishes.filter((d) => dishLevel(d) === level).length;
  const traces = count('trace');
  return [
    `✅ ${count('safe')} sin lo que evitas`,
    traces ? (state.strict ? `${traces} descartados por trazas` : `⚠️ ${traces} con posibles trazas`) : null,
  ].filter(Boolean).join(' · ');
}

function renderCard(r) {
  const selected = r.id === state.selectedId;
  const meta = [r.category, r.cuisine].filter(Boolean).join(' · ');
  const km = state.userPos ? distanceKm(state.userPos, r) : null;
  const mapsUrl = safeUrl(r.maps_url);

  return h('article', { class: `restaurant-card${selected ? ' restaurant-card--open' : ''}`, id: `card-${r.id}` },
    h('button', { type: 'button', class: 'restaurant-header', 'aria-expanded': String(selected), onClick: () => select(selected ? null : r.id) },
      h('span', { class: 'restaurant-name' }, r.name,
        hasAnyMenu(r) ? h('span', { class: 'badge' }, r.dishes.length ? 'Carta digital' : 'Carta') : null,
        restaurantLevel(r) === 'trace' ? h('span', { class: 'badge badge--trace' }, '⚠️ Solo con posibles trazas') : null),
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

function update({ fit = false } = {}) {
  const list = filtered();
  renderFilters();
  $('mapLegend').hidden = !state.avoid.size;
  renderMarkers(list);
  renderList(list);
  // Al buscar, el mapa enseña todos los resultados (p. ej. todos los VIPS).
  if (fit && list.length) map.fitBounds(L.latLngBounds(list.map((r) => [r.lat, r.lng])), { padding: [30, 30], maxZoom: 16 });
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

let fitTimer;
$('searchInput').addEventListener('input', (e) => {
  state.search = e.target.value;
  state.selectedId = null;
  state.shown = PAGE_SIZE;
  update();
  // Se encuadra al dejar de escribir, para que el mapa no salte con cada letra.
  clearTimeout(fitTimer);
  if (state.search.trim()) fitTimer = setTimeout(() => update({ fit: true }), 600);
});
$('addButton').addEventListener('click', openAddDialog);
$('addSearch').addEventListener('input', runPlaceSearch);

try {
  backend = await createBackend(config);
  $('modeBadge').hidden = backend.mode !== 'demo';
  await loadRestaurants();
  // Enlace directo a una búsqueda: …/pato-genos/?q=vips
  state.search = new URLSearchParams(location.search).get('q') ?? '';
  $('searchInput').value = state.search;
  update({ fit: Boolean(state.search) });
} catch (error) {
  console.error(error);
  replaceContent($('restaurant-list'), h('div', { class: 'placeholder-message error' },
    `❌ No se pudo conectar con la base de datos. ${error.message}`));
}
