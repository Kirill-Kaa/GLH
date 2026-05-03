import sqlite3

def add_test_product(client, name="Test Product", price=10.0):
    db_path = client.application.config['DATABASE']
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO products (name, description, price, category, in_stock)
        VALUES (?, ?, ?, ?, ?)
        """,
        (name, "Test description", price, "Test", 1)
    )
    conn.commit()
    product_id = cursor.lastrowid
    conn.close()
    return product_id

def register_and_login(client, username="user", email="user@test.com", password="Password123"):

    client.post("/register", data={"username": username, "email": email, "password": password})
    client.post("/login", data={"username": username, "password": password})
    return client

def test_empty_cart(client):
    client = register_and_login(client)
    response = client.get("/cart")
    assert response.status_code == 200
    assert b"cart is empty" in response.data.lower()  # message in template

def test_add_to_cart(client):
    client = register_and_login(client)
    product_id = add_test_product(client)

    response = client.post(
        f"/cart/add/{product_id}",
        data={"quantity": 2},
        follow_redirects=True
    )
    import sqlite3
    db_path = client.application.config['DATABASE']
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM cart")
    items = cursor.fetchall()
    assert len(items) == 1
    assert response.status_code == 200
    assert b"shopping cart" in response.data.lower()


def test_update_cart_quantity(client):
    client = register_and_login(client)
    product_id = add_test_product(client)

    # Add first
    client.post(f"/cart/add/{product_id}", data={"quantity": 1})
    # Update quantity
    response = client.post(f"/cart/update/{product_id}", data={"quantity": 5}, follow_redirects=True)
    assert response.status_code == 200
    assert b"cart updated" in response.data.lower()


def test_remove_from_cart(client):
    client = register_and_login(client)
    product_id = add_test_product(client)

    # Add first
    client.post(f"/cart/add/{product_id}", data={"quantity": 1})
    # Remove
    response = client.get(f"/cart/remove/{product_id}", follow_redirects=True)
    assert response.status_code == 200
    assert b"item removed" in response.data.lower()


def test_clear_cart(client):
    client = register_and_login(client)
    p1 = add_test_product(client, "Product 1")
    p2 = add_test_product(client, "Product 2")
    # Add multiple items
    client.post(f"/cart/add/{p1}", data={"quantity": 1})
    client.post(f"/cart/add/{p2}", data={"quantity": 1})

    # Clear cart
    response = client.get("/cart/clear", follow_redirects=True)
    assert response.status_code == 200
    assert b"cart cleared" in response.data.lower()