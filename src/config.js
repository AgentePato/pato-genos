// Configuración de Supabase (Project Settings → API).
// La "anon key" es pública por diseño: la seguridad la ponen las políticas
// y funciones de supabase/schema.sql. Si se dejan vacías, la web arranca en
// modo demo: lee data/restaurantes.json y los cambios se guardan solo en
// este navegador.
export const config = {
  supabaseUrl: 'https://rrqkrdtqxmrotzkljpsm.supabase.co',
  supabaseAnonKey: 'sb_publishable_boVAhDx80T5iiDpvoXrkFA_TQAJURT5',

  // Clave de Google Maps Platform con "Places API (New)" activada y
  // restringida a tu web (ver README). Si está vacía, el buscador de
  // "Añadir restaurante" usa OpenStreetMap, que es gratis pero tiene menos locales.
  googleMapsApiKey: '',

  // Centro del mapa y zona donde buscar primero (latitud, longitud, radio en metros).
  searchArea: { lat: 40.6007, lng: -3.7079, radius: 6000 },
};
