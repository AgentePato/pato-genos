// Modo demo: parte de data/restaurantes.json y guarda los cambios en este
// navegador (localStorage). Sirve para probar la web sin configurar Supabase.
// En demo cualquier contraseña vale para el panel.

const STORAGE_KEY = 'alergenos-demo-v1';

function loadChanges() {
  try {
    return { added: [], edits: {}, deleted: [], ...JSON.parse(localStorage.getItem(STORAGE_KEY)) };
  } catch {
    return { added: [], edits: {}, deleted: [] };
  }
}

function saveChanges(changes) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(changes));
  } catch {
    // Navegación privada o almacenamiento lleno: los cambios duran hasta recargar.
  }
}

const sameSpot = (a, b) =>
  a.name.trim().toLowerCase() === b.name.trim().toLowerCase()
  && Math.abs(a.lat - b.lat) < 0.001 && Math.abs(a.lng - b.lng) < 0.0013;

export async function createDemoBackend() {
  const res = await fetch(new URL('../../data/restaurantes.json', import.meta.url));
  if (!res.ok) throw new Error('No se pudo cargar data/restaurantes.json');
  const seed = (await res.json()).map((r) => ({ ...r, id: r.place_id }));
  const changes = loadChanges();

  function current() {
    return [...seed, ...changes.added]
      .filter((r) => !changes.deleted.includes(r.id))
      .map((r) => ({ ...r, ...changes.edits[r.id] }))
      .sort((a, b) => a.name.localeCompare(b.name, 'es'));
  }

  function edit(id, patch) {
    if (!current().some((r) => r.id === id)) throw new Error('Restaurante no encontrado');
    changes.edits[id] = { ...changes.edits[id], ...patch };
    saveChanges(changes);
  }

  return {
    mode: 'demo',

    listRestaurants: async () => structuredClone(current()),

    async addRestaurant(place) {
      const all = current();
      if (all.some((r) => r.place_id === place.place_id || sameSpot(r, place))) {
        throw new Error('Ese restaurante ya está en el mapa');
      }
      const restaurant = {
        category: 'Restaurante', cuisine: '', ...place,
        id: place.place_id, menu_type: '', menu_src: [], dishes: [],
      };
      changes.added.push(restaurant);
      saveChanges(changes);
      return restaurant.id;
    },

    checkAdmin: async () => true,

    updateRestaurant: async (_password, id, fields) => edit(id, fields),

    setDishes: async (_password, id, dishes) => edit(id, { dishes }),

    async deleteRestaurant(_password, id) {
      changes.deleted.push(id);
      saveChanges(changes);
    },
  };
}
