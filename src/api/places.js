// Buscador para "Añadir restaurante". Con clave de Google usa Google Places
// (nombres y direcciones exactos de Google Maps); sin clave, OpenStreetMap (Photon).
// Todos los resultados tienen la misma forma:
//   { place_id, name, address, lat, lng, maps_url, source, category, cuisine }

const googleMapsLink = (name, address, googlePlaceId) => {
  const query = encodeURIComponent([name, address].filter(Boolean).join(', '));
  const id = googlePlaceId ? `&query_place_id=${encodeURIComponent(googlePlaceId)}` : '';
  return `https://www.google.com/maps/search/?api=1&query=${query}${id}`;
};

const GOOGLE_FOOD_TYPES = ['restaurant', 'cafe', 'bar', 'bakery', 'meal_takeaway', 'food'];
const OSM_CATEGORIES = { restaurant: 'Restaurante', fast_food: 'Comida rápida', cafe: 'Cafetería', bar: 'Bar', pub: 'Bar' };

async function searchGoogle(query, { googleMapsApiKey, searchArea }) {
  const res = await fetch('https://places.googleapis.com/v1/places:searchText', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Goog-Api-Key': googleMapsApiKey,
      'X-Goog-FieldMask': 'places.id,places.displayName,places.formattedAddress,places.location,places.googleMapsUri,places.types,places.primaryTypeDisplayName',
    },
    body: JSON.stringify({
      textQuery: query,
      languageCode: 'es',
      regionCode: 'ES',
      pageSize: 8,
      locationBias: {
        circle: { center: { latitude: searchArea.lat, longitude: searchArea.lng }, radius: searchArea.radius },
      },
    }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(`Google Maps no responde (${detail?.error?.status ?? res.status}). Revisa la clave.`);
  }
  const data = await res.json();
  return (data.places ?? [])
    .filter((p) => p.types?.some((t) => GOOGLE_FOOD_TYPES.includes(t) || t.endsWith('_restaurant')))
    .map((p) => ({
      place_id: `google:${p.id}`,
      name: p.displayName?.text ?? '',
      address: p.formattedAddress ?? '',
      lat: p.location.latitude,
      lng: p.location.longitude,
      maps_url: p.googleMapsUri ?? googleMapsLink(p.displayName?.text, p.formattedAddress, p.id),
      source: 'google',
      category: p.primaryTypeDisplayName?.text ?? 'Restaurante',
      cuisine: '',
    }));
}

async function searchOpenStreetMap(query, { searchArea }) {
  const params = new URLSearchParams({ q: query, limit: '8', lat: searchArea.lat, lon: searchArea.lng, lang: 'es' });
  for (const value of Object.keys(OSM_CATEGORIES)) params.append('osm_tag', `amenity:${value}`);
  const res = await fetch(`https://photon.komoot.io/api/?${params}`);
  if (!res.ok) throw new Error('El buscador de mapas no responde. Inténtalo en un rato.');
  const data = await res.json();
  return data.features
    .filter((f) => f.properties.name)
    .map((f) => {
      const p = f.properties;
      const street = [p.street, p.housenumber].filter(Boolean).join(' ');
      const address = [street, p.city ?? p.town ?? p.village].filter(Boolean).join(', ');
      const [lng, lat] = f.geometry.coordinates;
      const osmType = { N: 'node', W: 'way', R: 'relation' }[p.osm_type] ?? p.osm_type;
      return {
        place_id: `osm:${osmType}/${p.osm_id}`,
        name: p.name,
        address,
        lat,
        lng,
        maps_url: googleMapsLink(p.name, address),
        source: 'osm',
        category: OSM_CATEGORIES[p.osm_value] ?? 'Restaurante',
        cuisine: '',
      };
    });
}

export function createPlaceSearch(config) {
  const useGoogle = Boolean(config.googleMapsApiKey);
  return {
    provider: useGoogle ? 'Google Maps' : 'OpenStreetMap',
    async search(query) {
      const q = query.trim();
      if (q.length < 2) return [];
      try {
        return await (useGoogle ? searchGoogle(q, config) : searchOpenStreetMap(q, config));
      } catch (e) {
        if (e instanceof TypeError) throw new Error('No hay conexión con el buscador de mapas.');
        throw e;
      }
    },
  };
}
