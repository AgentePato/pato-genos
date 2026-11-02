// Los 14 alérgenos de declaración obligatoria en la UE (Reglamento 1169/2011).
// La clave es la que se guarda en la base de datos (dishes.allergens).
export const ALLERGENS = [
  { key: 'gluten', label: 'Gluten', icon: '🌾' },
  { key: 'lacteos', label: 'Lácteos', icon: '🥛' },
  { key: 'huevo', label: 'Huevo', icon: '🥚' },
  { key: 'frutos_secos', label: 'Frutos secos', icon: '🌰' },
  { key: 'cacahuete', label: 'Cacahuete', icon: '🥜' },
  { key: 'pescado', label: 'Pescado', icon: '🐟' },
  { key: 'crustaceos', label: 'Crustáceos', icon: '🦐' },
  { key: 'moluscos', label: 'Moluscos', icon: '🦑' },
  { key: 'soja', label: 'Soja', icon: '🫘' },
  { key: 'sesamo', label: 'Sésamo', icon: '⚪' },
  { key: 'apio', label: 'Apio', icon: '🥬' },
  { key: 'mostaza', label: 'Mostaza', icon: '🟡' },
  { key: 'sulfitos', label: 'Sulfitos', icon: '🍷' },
  { key: 'altramuces', label: 'Altramuces', icon: '🫛' },
];

export const allergenByKey = Object.fromEntries(ALLERGENS.map((a) => [a.key, a]));

const normalize = (text) => text.normalize('NFD').replace(/[̀-ͯ]/g, '').trim().toLowerCase();
const byName = Object.fromEntries(ALLERGENS.flatMap((a) => [[a.key, a.key], [normalize(a.label), a.key]]));
Object.assign(byName, { leche: 'lacteos', lactosa: 'lacteos', huevos: 'huevo', marisco: 'crustaceos' });

// "gluten, Lácteos, huevos" → ['gluten', 'lacteos', 'huevo']. Lanza error si hay alguno desconocido.
export function parseAllergenList(text) {
  const keys = [];
  for (const part of text.split(',').map(normalize).filter(Boolean)) {
    const key = byName[part];
    if (!key) throw new Error(`Alérgeno desconocido: "${part}"`);
    if (!keys.includes(key)) keys.push(key);
  }
  return keys;
}

// Un plato es apto si no contiene ninguno de los alérgenos que quieres evitar
// (y, en modo estricto, si tampoco puede llevar trazas de ellos).
export const dishIsSafe = (dish, avoid, strict = false) =>
  !dish.allergens.some((a) => avoid.has(a)) && !(strict && (dish.traces ?? []).some((a) => avoid.has(a)));
