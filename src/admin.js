import { config } from './config.js';
import { createBackend } from './api/index.js';
import { allergenByKey, parseAllergenList } from './allergens.js';
import { h, replaceContent } from './ui/dom.js';

const $ = (id) => document.getElementById(id);
let backend;
let password = '';
let restaurants = [];
let editingId = null; // null = restaurante nuevo

function show(section) {
  for (const id of ['login-section', 'dashboard-section', 'form-section']) $(id).hidden = id !== section;
}

// ------------------------------------------------------------------ login
$('login-section').addEventListener('submit', async (e) => {
  e.preventDefault();
  $('login-error').textContent = '';
  try {
    backend ??= await createBackend(config);
    if (!(await backend.checkAdmin($('passInput').value))) throw new Error('Contraseña incorrecta.');
    password = $('passInput').value;
    $('adminBox').classList.replace('modo-login', 'modo-panel');
    $('admin-title').textContent = 'Panel de Control ⚙️';
    $('mode-note').hidden = backend.mode !== 'demo';
    show('dashboard-section');
    await loadList();
  } catch (error) {
    $('login-error').textContent = `❌ ${error.message}`;
    $('passInput').value = '';
  }
});

// ------------------------------------------------------------------ lista
async function loadList() {
  try {
    restaurants = await backend.listRestaurants();
    renderList();
  } catch (error) {
    replaceContent($('listaRestaurantes'), h('li', { class: 'list-empty' }, `Error al conectar con la base de datos: ${error.message}`));
  }
}

function renderList() {
  const q = $('searchAdmin').value.trim().toLowerCase();
  const shown = restaurants.filter((r) => r.name.toLowerCase().includes(q));
  if (!shown.length) {
    replaceContent($('listaRestaurantes'), h('li', { class: 'list-empty' }, 'No se encontraron restaurantes.'));
    return;
  }
  replaceContent($('listaRestaurantes'), shown.map((r) => h('li', { class: 'restaurant-item' },
    h('span', { class: 'item-name', title: r.name }, r.dishes.length || r.menu_type ? '🦆 ' : '', r.name),
    h('div', { class: 'action-btns' },
      h('button', { type: 'button', class: 'btn-small bg-orange', onClick: () => openForm(r) }, '✏️ Editar'),
      h('button', { type: 'button', class: 'btn-small bg-red', onClick: () => remove(r) }, '🗑️ Borrar'),
    ),
  )));
}

$('searchAdmin').addEventListener('input', renderList);

async function remove(r) {
  if (!confirm(`¿Borrar "${r.name}" y su carta? No se puede deshacer.`)) return;
  try {
    await backend.deleteRestaurant(password, r.id);
    await loadList();
  } catch (error) {
    alert(`Error al borrar: ${error.message}`);
  }
}

// ------------------------------------------------------------------ formulario
const labels = (keys = []) => keys.map((a) => allergenByKey[a]?.label ?? a).join(', ');
const dishesToText = (dishes) => dishes
  .map((d) => [d.section, d.name, labels(d.allergens), ...(d.traces?.length ? [labels(d.traces)] : [])].join(' | '))
  .join('\n');

function textToDishes(text) {
  return text.split('\n').map((line) => line.trim()).filter(Boolean).map((line, i) => {
    const [section = '', name = '', allergens = '', traces = ''] = line.split('|').map((s) => s.trim());
    if (!name) throw new Error(`Línea ${i + 1}: falta el nombre del plato.`);
    try {
      const contains = parseAllergenList(allergens);
      return { section, name, allergens: contains, traces: parseAllergenList(traces).filter((a) => !contains.includes(a)) };
    } catch (error) {
      throw new Error(`Línea ${i + 1}: ${error.message}`);
    }
  });
}

function openForm(r = null) {
  editingId = r?.id ?? null;
  $('f-name').value = r?.name ?? '';
  $('f-address').value = r?.address ?? '';
  $('f-lat').value = r?.lat ?? config.searchArea.lat;
  $('f-lng').value = r?.lng ?? config.searchArea.lng;
  $('f-cuisine').value = r?.cuisine ?? '';
  $('f-menuType').value = r?.menu_type ?? '';
  $('f-menuSrc').value = r?.menu_src.join(', ') ?? '';
  $('f-dishes').value = dishesToText(r?.dishes ?? []);
  $('form-error').textContent = '';
  $('admin-title').textContent = r ? `Editando: ${r.name}` : 'Nuevo restaurante';
  show('form-section');
}

function closeForm() {
  $('admin-title').textContent = 'Panel de Control ⚙️';
  show('dashboard-section');
}

$('newButton').addEventListener('click', () => openForm());
$('cancelButton').addEventListener('click', closeForm);

$('form-section').addEventListener('submit', async (e) => {
  e.preventDefault();
  $('form-error').textContent = '';
  try {
    const fields = {
      name: $('f-name').value.trim(),
      address: $('f-address').value.trim(),
      lat: Number($('f-lat').value),
      lng: Number($('f-lng').value),
      cuisine: $('f-cuisine').value.trim(),
      menu_type: $('f-menuType').value,
      menu_src: $('f-menuType').value ? $('f-menuSrc').value.split(',').map((s) => s.trim()).filter(Boolean) : [],
    };
    if (fields.menu_type && !fields.menu_src.length) throw new Error('Indica la ruta de la carta o elige "Sin carta escaneada".');
    const dishes = textToDishes($('f-dishes').value);

    let id = editingId;
    if (!id) {
      const query = encodeURIComponent(`${fields.name}, ${fields.address}`);
      id = await backend.addRestaurant({
        ...fields,
        place_id: `manual:${crypto.randomUUID()}`,
        maps_url: `https://www.google.com/maps/search/?api=1&query=${query}`,
        source: 'manual',
        category: 'Restaurante',
      });
    }
    await backend.updateRestaurant(password, id, fields);
    const before = restaurants.find((r) => r.id === id);
    if (dishesToText(before?.dishes ?? []) !== dishesToText(dishes)) await backend.setDishes(password, id, dishes);

    await loadList();
    closeForm();
  } catch (error) {
    $('form-error').textContent = `❌ ${error.message}`;
  }
});
