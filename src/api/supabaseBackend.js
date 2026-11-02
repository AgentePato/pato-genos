import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.49.4/+esm';

function friendlyError(error) {
  const msg = error?.message ?? '';
  if (/fetch|network|Failed to/i.test(msg)) return 'No hay conexión. Revisa tu internet e inténtalo de nuevo.';
  return msg || 'Algo ha fallado. Inténtalo de nuevo.';
}

export function createSupabaseBackend(url, anonKey) {
  const client = createClient(url, anonKey, { auth: { persistSession: false } });

  async function run(promise) {
    let result;
    try {
      result = await promise;
    } catch (e) {
      throw new Error(friendlyError(e));
    }
    if (result.error) throw new Error(friendlyError(result.error));
    return result.data;
  }

  const rpc = (fn, args) => run(client.rpc(fn, args));

  return {
    mode: 'supabase',

    async listRestaurants() {
      const rows = await run(
        client.from('restaurants')
          .select('*, dishes(section, name, allergens, position)')
          .order('name')
          .range(0, 4999),
      );
      for (const r of rows) r.dishes.sort((a, b) => a.position - b.position);
      return rows;
    },

    addRestaurant: (place) => rpc('add_restaurant', {
      p_name: place.name, p_address: place.address, p_lat: place.lat, p_lng: place.lng,
      p_place_id: place.place_id, p_maps_url: place.maps_url, p_source: place.source,
      p_category: place.category ?? 'Restaurante', p_cuisine: place.cuisine ?? '',
    }),

    checkAdmin: (password) => rpc('check_admin', { p_password: password }),

    updateRestaurant: (password, id, r) => rpc('admin_update_restaurant', {
      p_password: password, p_id: id, p_name: r.name, p_address: r.address, p_lat: r.lat, p_lng: r.lng,
      p_cuisine: r.cuisine, p_menu_type: r.menu_type, p_menu_src: r.menu_src,
    }),

    setDishes: (password, id, dishes) =>
      rpc('admin_set_dishes', { p_password: password, p_restaurant: id, p_dishes: dishes }),

    deleteRestaurant: (password, id) => rpc('admin_delete_restaurant', { p_password: password, p_id: id }),
  };
}
