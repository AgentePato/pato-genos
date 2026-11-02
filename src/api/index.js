// Todos los backends exponen la misma interfaz:
//   listRestaurants() → [{ id, name, address, lat, lng, category, cuisine, maps_url,
//                          menu_type, menu_src: [], dishes: [{ section, name, allergens: [] }] }]
//   addRestaurant({ place_id, name, address, lat, lng, maps_url, source, category, cuisine }) → id
//   checkAdmin(password) → boolean
//   updateRestaurant(password, id, { name, address, lat, lng, cuisine, menu_type, menu_src })
//   setDishes(password, id, dishes)
//   deleteRestaurant(password, id)

export async function createBackend({ supabaseUrl, supabaseAnonKey }) {
  if (supabaseUrl && supabaseAnonKey) {
    const { createSupabaseBackend } = await import('./supabaseBackend.js');
    return createSupabaseBackend(supabaseUrl, supabaseAnonKey);
  }
  const { createDemoBackend } = await import('./demoBackend.js');
  return createDemoBackend();
}
