import csv
import io
import tempfile
import unittest
from pathlib import Path

import app


class CsvImportTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        app.DATABASE_PATH = Path(self.temp_dir.name) / "test.sqlite3"
        app.initialize_db()

    def tearDown(self):
        self.temp_dir.cleanup()

    def make_csv(self, rows):
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(
            ["id", "name", "type", "lat", "lng", "hasMenu", "menuType", "menuSrc"]
        )
        writer.writerows(rows)
        return output.getvalue()

    def get_restaurants(self):
        with app.database_connection() as connection:
            rows = connection.execute("SELECT * FROM restaurants").fetchall()
            return [app.row_to_restaurant(row) for row in rows]

    def import_content(self, content):
        with app.database_connection() as connection:
            return app.import_csv(connection, content)

    def test_imports_restaurants_and_updates_by_id(self):
        content = self.make_csv(
            [["abc123", "Café", "Centro", "40.6", "-3.7", "true", "images", '["a.jpg","b.jpg"]']]
        )
        self.assertEqual(self.import_content(content), (1, 0))

        updated = self.make_csv(
            [["abc123", "Café Nuevo", "Centro", "40.7", "-3.8", "false", "", ""]]
        )
        self.assertEqual(self.import_content(updated), (0, 1))
        restaurant = self.get_restaurants()[0]
        self.assertEqual(restaurant["name"], "Café Nuevo")
        self.assertEqual(restaurant["menuSrc"], "")

    def test_import_without_id_updates_by_name(self):
        first = self.make_csv([["", "Restaurante", "Dirección", "40", "-3", "no", "", ""]])
        self.import_content(first)
        second = self.make_csv([["", "restaurante", "Nueva dirección", "41", "-4", "no", "", ""]])

        self.assertEqual(self.import_content(second), (0, 1))
        self.assertEqual(len(self.get_restaurants()), 1)
        self.assertEqual(self.get_restaurants()[0]["type"], "Nueva dirección")

    def test_invalid_csv_does_not_partially_import(self):
        content = self.make_csv(
            [
                ["", "Válido", "Dirección", "40", "-3", "no", "", ""],
                ["", "Inválido", "Dirección", "95", "-3", "no", "", ""],
            ]
        )

        with self.assertRaisesRegex(ValueError, "Fila 3"):
            self.import_content(content)
        self.assertEqual(self.get_restaurants(), [])

    def test_rejects_missing_required_columns(self):
        with self.assertRaisesRegex(ValueError, "Faltan columnas"):
            self.import_content("name,lat\nRestaurante,40\n")

    def test_allows_same_name_when_rows_have_distinct_ids(self):
        content = self.make_csv(
            [
                ["branch-1", "Café", "Centro", "40.6", "-3.7", "no", "", ""],
                ["branch-2", "Café", "Norte", "40.7", "-3.8", "no", "", ""],
            ]
        )

        self.assertEqual(self.import_content(content), (2, 0))
        self.assertEqual(len(self.get_restaurants()), 2)

    def test_rejects_missing_names_and_script_urls(self):
        missing_name = self.make_csv([["", "", "Dirección", "40", "-3", "no", "", ""]])
        with self.assertRaisesRegex(ValueError, "El nombre es obligatorio"):
            self.import_content(missing_name)

        with self.assertRaisesRegex(ValueError, "HTTP o HTTPS"):
            app.validate_restaurant(
                {
                    "name": "Restaurante",
                    "lat": 40,
                    "lng": -3,
                    "hasMenu": True,
                    "menuType": "pdf",
                    "menuSrc": "javascript:alert(1)",
                }
            )


if __name__ == "__main__":
    unittest.main()
