import pytest
from app import app, init_db
import sqlite3

def add_test_product(client, name="Test Product", price=10.0):

    db_path = client.application.config['DATABASE']
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (name, description, price, category, in_stock) VALUES (?, ?, ?, ?, ?)",
        (name, "Test description", price, "Test", 1)
    )
    conn.commit()
    return cursor.lastrowid

@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / "test.db"

    def get_test_db():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # Override DB
    app.config['TESTING'] = True
    app.config['DATABASE'] = str(db_path)

    import app as app_module
    app_module.get_db = get_test_db

    with app.test_client() as client:
        with app.app_context():
            init_db()

        yield client