import argparse
import sys
from pathlib import Path

from app import database_connection, import_csv, initialize_db


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Importa o actualiza restaurantes en la base de datos SQLite."
    )
    parser.add_argument("csv_file", type=Path, help="Archivo CSV UTF-8 que se va a importar")
    args = parser.parse_args()

    try:
        content = args.csv_file.read_text(encoding="utf-8-sig")
        initialize_db()
        with database_connection() as connection:
            created, updated = import_csv(connection, content)
    except (OSError, UnicodeError, ValueError, RuntimeError) as error:
        print(f"Error al importar: {error}", file=sys.stderr)
        return 1

    print(f"Importación completada: {created} creados y {updated} actualizados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
