def test_register_success(client):
    response = client.post('/register', data={
        'username': 'testuser',
        'email': 'test@test.com',
        'password': 'Password123'
    }, follow_redirects=True)
    assert b'Registration successful' in response.data

def test_register_empty_fields(client):
    response = client.post('/register', data={
        'username': '',
        'email': '',
        'password': ''
    }, follow_redirects=True)
    assert b'All fields are required' in response.data

def test_register_short_password(client):
    response = client.post('/register', data={
        'username': 'user',
        'email': 'user@test.com',
        'password': '123'
    }, follow_redirects=True)

    assert b'Password must be at least' in response.data

def test_register_duplicate_user(client):
    client.post('/register', data={
        'username': 'dup',
        'email': 'dup@test.com',
        'password': 'Password123'
    })
    response = client.post('/register', data={
        'username': 'dup',
        'email': 'dup@test.com',
        'password': 'Password123'
    }, follow_redirects=True)
    assert b'already exist' in response.data

def test_login_success(client):
    # Register user first
    client.post('/register', data={
        'username': 'loginuser',
        'email': 'login@test.com',
        'password': 'Password123'
    })
    # Login
    client.post('/login', data={
        'username': 'loginuser',
        'password': 'Password123'
    }, follow_redirects=True)

    with client.session_transaction() as session:
        assert session['username'] == 'loginuser'
        assert session['role'] == 'customer'
        assert session['user_id'] is not None