"""Junta los SQL de todas las cadenas en supabase/cartas/todas.sql, para
ejecutarlos de una vez en el SQL Editor de Supabase.

Uso (después de regenerar alguna cadena):
  python3 scripts/cartas/juntar.py
"""

from pathlib import Path

FOLDER = Path(__file__).resolve().parents[2] / "supabase" / "cartas"
ORDER = ["100-montaditos", "vips", "ginos", "fosters", "starbucks", "goiko",
         "telepizza", "pizzahut", "papajohns", "pans"]


def main():
    parts = ["-- Todas las cadenas de golpe. Antes, ejecuta schema.sql.",
             "-- Se genera juntando los SQL de esta carpeta: python3 scripts/cartas/juntar.py"]
    parts += [(FOLDER / f"{name}.sql").read_text(encoding="utf-8") for name in ORDER]
    output = FOLDER / "todas.sql"
    output.write_text("\n\n".join(parts), encoding="utf-8")
    print(f"{len(ORDER)} cadenas → {output.name} ({output.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
