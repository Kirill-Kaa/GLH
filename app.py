from flask import Flask, render_template, redirect, url_for, request, session, flash, current_app, abort
import sqlite3
import os
from datetime import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

from PIL import Image

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret_key" #must be changed in production

DATABASE = "GLH_store.db"



def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f): # Decorator to request uesr login when it's needed
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))

        if session.get('role') != 'admin':
            abort(403)

        return f(*args, **kwargs)
    return decorated

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            category TEXT NOT NULL,
            image_url TEXT,
            in_stock INTEGER DEFAULT 1
        )
    ''')
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            phone TEXT,
            address TEXT,
            city TEXT,
            postal_code TEXT,
            loyalty_points INTEGER DEFAULT 0,
            role TEXT DEFAULT 'customer',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (product_id) REFERENCES products (id),
            UNIQUE(user_id, product_id)
        )
    ''')
    #full order information
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total_amount REAL NOT NULL,
            points_redeemed INTEGER DEFAULT 0,
            points_earned INTEGER DEFAULT 0,
            discount_percent INTEGER DEFAULT 0,
            discount_amount REAL DEFAULT 0,
            final_amount REAL NOT NULL,
            voucher_id INTEGER,
            status TEXT DEFAULT 'pending',
            delivery_address TEXT,
            delivery_city TEXT,
            delivery_postal_code TEXT,
            phone TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (voucher_id) REFERENCES vouchers (id)
        )
    ''')

    #show list of product on order page, like in receipt 
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')
    
    

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vouchers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            discount_percent INTEGER NOT NULL,
            is_used INTEGER DEFAULT 0,
            used_order_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS loyalty_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            points INTEGER NOT NULL,
            description TEXT,
            transaction_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS food_producers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_url TEXT,
            name TEXT NOT NULL,
            description TEXT,
            location TEXT,
            founded_year TEXT,
            specialty TEXT
        )
    ''')

    cursor.execute('SELECT COUNT(*) FROM food_producers')
    if cursor.fetchone()[0] == 0:
        producers = [
            ("Green Valley Farms","A family-run farm focused on sustainable agriculture, producing fresh seasonal vegetables and free-range eggs for local communities.","Somerset, UK","Vegetables & Eggs",1998, "/static/img/producers/GreenValleyFarms.jpg"),
            ("Bristol Artisan Dairy","An independent dairy producing handcrafted cheeses and yogurts using traditional methods and locally sourced milk.","Bristol, UK","Cheese & Dairy",2012, "/static/img/producers/BristolArtisanDairy.jpg"),
            ("Riverford Orchard Co.","Specialists in heritage apples and small-batch cider production, committed to preserving traditional orchard varieties.","Gloucestershire, UK","Cider & Apples",2005, "/static/img/producers/RiverfordOrchardCo.jpg"),
            ("Golden Grain Bakery","A community-focused bakery producing organic breads, pastries, and baked goods using stone-ground flour.","Bath, UK","Bakery Products",2015, "/static/img/producers/GoldenGrainBakery.jpg"),
            ("Severn Seafoods","A sustainable seafood supplier offering fresh, responsibly caught fish sourced from local coastal fisheries.","Weston-super-Mare, UK","Fresh Seafood",2008, "/static/img/producers/SevernSeafoods.jpg"),
            ("Honeywood Apiaries","Producers of raw, unfiltered honey and beeswax products, supporting pollinator health and biodiversity.","Wiltshire, UK","Honey & Bee Products",2010, "/static/img/producers/HoneywoodApiaries.jpg")
        ]

        cursor.executemany('''
            INSERT INTO food_producers (name, description, location, specialty, founded_year, image_url)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', producers)

    
    
    cursor.execute('SELECT COUNT(*) FROM products')
    if cursor.fetchone()[0] == 0: #insert some example products, can be added new or deleted in admin dashboard
        products = [
            ('Baked Bread', 'Localy baked bread from local plants', 12.99, 'Bakery', '/static/img/products/bread.jpg', 32),
            ('Read Apples', 'Read apples grown under pure sun with love and care.', 4.50, 'Fruits', '/static/img/products/apples.jpg', 18),
            ('Craft Cheese', 'Made by our local experts in dark cave with modern technology and traditional flavour.', 3.99, 'Cheese', '/static/img/products/cheese.jpg', 54),
            ('Fresh Sourdough Loaf', 'Handcrafted sourdough baked daily using organic flour', 3.99, 'Bakery', '/static/img/products/sourdough.jpg', 32),
            ('Free-Range Eggs', 'Locally sourced free-range eggs from happy hens', 4.25, 'Dairy', '/static/img/products/eggs.jpg', 23),
            ('Organic Whole Milk', 'Creamy whole milk from grass-fed cows in the West Country', 2.10, 'Dairy', '/static/img/products/milk.jpg', 43),
            ('Sausages', 'Traditional pork sausages made from Gloucester Old Spot pigs', 6.99, 'Meat', '/static/img/products/sausages.jpg', 312),
            ('Farmhouse Butter', 'Rich and creamy salted butter churned locally', 2.75, 'Dairy', '/static/img/products/butter.jpg', 53),
            ('Seasonal Veg Box', 'A selection of fresh, seasonal vegetables from local farms', 9.99, 'Vegetables', '/static/img/products/vegbox.jpg', 76),
            ('Apple Juice', 'Pressed from locally grown apples with no added sugar', 3.49, 'Drinks', '/static/img/products/applejuice.jpg',32),
            ('Ham Slices', 'Cured and sliced Wiltshire ham with a classic flavour', 5.99, 'Meat', '/static/img/products/ham.jpg', 45),
        ]
        
        cursor.executemany('''
            INSERT INTO products (name, description, price, category, image_url, in_stock)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', products)

    cursor.execute("SELECT * FROM users WHERE username = ?", ("admin",))
    admin = cursor.fetchone()
    if not admin:
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, role)
            VALUES (?, ?, ?, ?)
        """, ("admin","admin@glh.com",generate_password_hash("1234"),"admin"))

    conn.commit()
    conn.close()

@app.route("/")
def home():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products WHERE in_stock >= 1 ORDER BY name')
    products = cursor.fetchall()
    conn.close()

    if products is None:
        return "Product not found", 404
    return render_template('index.html', products=products)

@app.route("/about") #add local producers to db
def about():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM food_producers ORDER BY name')
    producers = cursor.fetchall()
    conn.close()

    return render_template("about.html", producers=producers)

@app.route("/catalogue") #catalogue with list of products
def catalogue():
    conn = get_db()
    cursor = conn.cursor()
    category = request.args.get("category", "all")

    if category == 'all':
        cursor.execute('SELECT * FROM products WHERE in_stock >= 1 ORDER BY category, name') #all proucts
    else:
        cursor.execute('SELECT * FROM products WHERE category = ? AND in_stock >= 1 ORDER BY name', (category,))#products with selected category
    
    products = cursor.fetchall()
    
    cursor.execute('SELECT DISTINCT category FROM products ORDER BY category') # shows all unique categories in left side list
    categories = [row['category'] for row in cursor.fetchall()]
    
    conn.close()
    
    return render_template('catalogue.html', products=products, categories=categories, selected_category=category)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    conn.close()
    
    if product is None:
        return "Product not found", 404
    
    return render_template('product.html', product=product)


@app.route('/register', methods=['GET','POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if not username or not email or not password:
            flash("All fields are required!", 'danger')
            return redirect(url_for('register'))
        
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute('SELECT id FROM users WHERE username = ? OR email = ?', (username, email))
        if cursor.fetchone():
            flash("User or email already exist!", 'danger')
            conn.close()
            return redirect(url_for('register'))
        
        if len(password) < 8:
            flash(f"Password must be at least {8} characters long.", 'danger')
            return redirect(url_for('register'))
        
        password_hash = generate_password_hash(password)
        cursor.execute('''
            INSERT INTO users (username, email, password_hash)
            VALUES (?, ?, ?)
        ''', (username, email, password_hash))
        
        conn.commit()
        conn.close()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user[10]
            flash(f'Welcome back, {user["username"]}!', 'success')
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password!", 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))

@app.route("/account")
@login_required
def account():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    
    #show order hitory
    cursor.execute('''
        SELECT o.id, o.total_amount, o.final_amount,o.status, o.created_at, COUNT(oi.id) as item_count
        FROM orders o
        LEFT JOIN order_items oi ON o.id = oi.order_id
        WHERE o.user_id = ?
        GROUP BY o.id
        ORDER BY o.created_at DESC
    ''', 
    (session['user_id'],))
    orders = cursor.fetchall()
    
    conn.close()
    
    return render_template('account.html', user=user, orders=orders)

#update account info, full name, address, phone number
@app.route('/account/update', methods=['POST'])
@login_required
def update_account():
    full_name = request.form.get('full_name')
    phone = request.form.get('phone')
    address = request.form.get('address')
    city = request.form.get('city')
    postal_code = request.form.get('postal_code')
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users 
        SET full_name = ?, phone = ?, address = ?, city = ?, postal_code = ?
        WHERE id = ?
    ''', (full_name, phone, address, city, postal_code, session['user_id']))
    
    conn.commit()
    conn.close()
    
    flash("Account information updated successfully!", 'success')
    return redirect(url_for('account'))


@app.route('/cart')
@login_required
def cart():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT c.id, c.quantity, p.id as product_id, p.name, p.price, p.image_url
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = ?
    ''', (session['user_id'],))
    
    cart_items = cursor.fetchall()
    
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    
    conn.close()
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    quantity = int(request.form.get('quantity', 1))
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM cart WHERE user_id = ? AND product_id = ?', 
                   (session['user_id'], product_id))
    existing_item = cursor.fetchone()
    
    if existing_item:
        new_quantity = existing_item['quantity'] + quantity
        cursor.execute('UPDATE cart SET quantity = ? WHERE id = ?', 
                       (new_quantity, existing_item['id']))
    else:
        cursor.execute('INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)',
                       (session['user_id'], product_id, quantity))
    
    conn.commit()
    conn.close()
    return redirect(url_for('cart'))

@app.route('/cart/update/<int:cart_id>', methods=['POST'])
@login_required
def update_cart(cart_id):
    quantity = int(request.form.get('quantity', 1))
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('UPDATE cart SET quantity = ? WHERE id = ? AND user_id = ?',
                   (quantity, cart_id, session['user_id']))
    
    conn.commit()
    conn.close()
    
    flash("Cart updated!", "success")
    return redirect(url_for('cart'))

@app.route('/cart/remove/<int:cart_id>')
@login_required
def remove_from_cart(cart_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM cart WHERE id = ? AND user_id = ?',
                   (cart_id, session['user_id']))
    
    conn.commit()
    conn.close()
    
    flash("Item removed from cart!", "info")
    return redirect(url_for('cart'))

@app.route('/cart/clear')
@login_required
def clear_cart():

    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM cart WHERE user_id = ?', (session['user_id'],))
    
    conn.commit()
    conn.close()
    
    flash("Cart cleared!", "info")
    return redirect(url_for('cart'))


@app.route('/checkout')
@login_required
def checkout():
    conn = get_db()
    cursor = conn.cursor()
    
    #load products from cart to checkout page
    cursor.execute('''
        SELECT c.id, c.quantity, p.id as product_id, p.name, p.price, p.image_url
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = ?
    ''', (session['user_id'],))
    cart_items = cursor.fetchall()
    
    if not cart_items:
        flash("Your cart is empty, add  products to purchause", 'info')
        return redirect(url_for('catalogue'))
    
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    
    cursor.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    
    # Get available vouchers
    cursor.execute('''
        SELECT * FROM vouchers
        WHERE user_id = ? AND is_used = 0
        ORDER BY discount_percent DESC
    ''', (session['user_id'],))
    vouchers = cursor.fetchall()
    
    points = user['loyalty_points']
    max_points_usable = int(total * 100)
    
    conn.close()
    
    return render_template('checkout.html', cart_items=cart_items, total=total, 
                         user=user, points=points, max_points_usable=max_points_usable,
                         vouchers=vouchers)

@app.route('/checkout/process', methods=['POST'])
@login_required
def process_checkout():

    order_type = request.form.get('order_type', 'delivery')
    full_name = request.form.get('full_name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    payment_method = request.form.get('payment_method', 'cash_on_delivery')


    # Delivery/Collection specific
    if order_type == 'delivery':
        delivery_address = request.form.get('address')
        delivery_city = request.form.get('city')
        delivery_postal_code = request.form.get('postal_code')
        notes = request.form.get('notes', '')
        
        if not delivery_address or not delivery_city or not delivery_postal_code:
            flash('Please fill in all required delivery information!', 'danger')
            return redirect(url_for('checkout'))
    else:  # collection
        delivery_address = 'COLLECTION'
        delivery_city = 'Store Pickup'
        delivery_postal_code = 'N/A'
        collection_time = request.form.get('collection_time', 'asap')
        notes = f"Collection Time: {collection_time}. " + request.form.get('notes', '')
    
    if not phone or not full_name:
        flash('Please fill in all required information!', 'danger')
        return redirect(url_for('checkout'))
    
    points_to_redeem = int(request.form.get('points_to_redeem', 0))
    voucher_id = request.form.get('voucher_id')
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Get cart items
        cursor.execute('''
            SELECT c.id, c.quantity, p.id as product_id, p.name, p.price
            FROM cart c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_id = ?
        ''', (session['user_id'],))
        
        cart_items = cursor.fetchall()
        
        if not cart_items:
            flash('Your cart is empty!', 'warning')
            conn.close()
            return redirect(url_for('catalog'))
        
        # Get user points
        cursor.execute('SELECT loyalty_points FROM users WHERE id = ?', (session['user_id'],))
        current_points = cursor.fetchone()['loyalty_points']
        
        # Calculate totals
        total = sum(item['price'] * item['quantity'] for item in cart_items)
        total_pennies = int(total * 100)
        
        # Handle voucher discount
        discount_percent = 0
        voucher_id_final = None
        
        if voucher_id and voucher_id != '':
            cursor.execute('''
                SELECT * FROM vouchers 
                WHERE id = ? AND user_id = ? AND is_used = 0
            ''', (voucher_id, session['user_id']))
            voucher = cursor.fetchone()
            
            if voucher:
                discount_percent = voucher['discount_percent']
                voucher_id_final = voucher['id']
        
        # Calculate discount from voucher
        voucher_discount = (total * discount_percent / 100) if discount_percent > 0 else 0
        
        # Validate points redemption
        if points_to_redeem > current_points:
            flash('You don\'t have enough points!', 'danger')
            conn.close()
            return redirect(url_for('checkout'))
        
        if points_to_redeem > total_pennies:
            flash('You can\'t use more points than the order total!', 'danger')
            conn.close()
            return redirect(url_for('checkout'))
        
        # Calculate final amount
        points_discount = points_to_redeem / 100
        total_discount = voucher_discount + points_discount
        final_amount = max(0, total - total_discount)
        
        # Calculate points earned (1 penny = 1 point, based on final amount paid)
        points_earned = int(final_amount * 100)
        
        # Create order with order_type and payment_method
        cursor.execute('''
            INSERT INTO orders (user_id, total_amount, points_redeemed, points_earned,
                              discount_percent, discount_amount, final_amount, voucher_id,
                              status, delivery_address, delivery_city, delivery_postal_code, 
                              phone, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?)
        ''', (session['user_id'], total, points_to_redeem, points_earned, discount_percent,
              total_discount, final_amount, voucher_id_final, delivery_address, 
              delivery_city, delivery_postal_code, phone, 
              f"{order_type.upper()} | Payment: {payment_method} | {notes}"))
        
        order_id = cursor.lastrowid
        
        # Create order items
        for item in cart_items:
            cursor.execute('''
                INSERT INTO order_items (order_id, product_id, product_name, price, quantity)
                VALUES (?, ?, ?, ?, ?)
            ''', (order_id, item['product_id'], item['name'], item['price'], item['quantity']))
        
        # Mark voucher as used
        if voucher_id_final:
            cursor.execute('''
                UPDATE vouchers SET is_used = 1, used_order_id = ? WHERE id = ?
            ''', (order_id, voucher_id_final))
        
        # Update user points
        net_points_change = points_earned - points_to_redeem
        cursor.execute('''
            UPDATE users SET loyalty_points = loyalty_points + ? WHERE id = ?
        ''', (net_points_change, session['user_id']))
        
        # Record redemption transaction if points were used
        if points_to_redeem > 0:
            cursor.execute('''
                INSERT INTO loyalty_transactions (user_id, points, description, transaction_type)
                VALUES (?, ?, ?, ?)
            ''', (session['user_id'], -points_to_redeem, f'Redeemed for Order #{order_id}', 'redeemed'))
        
        # Record earning transaction if points were earned
        if points_earned > 0:
            cursor.execute('''
                INSERT INTO loyalty_transactions (user_id, points, description, transaction_type)
                VALUES (?, ?, ?, ?)
            ''', (session['user_id'], points_earned, f'Earned from Order #{order_id}', 'earned'))
        
        # Clear cart
        cursor.execute('DELETE FROM cart WHERE user_id = ?', (session['user_id'],))
        
        # Commit all changes together
        conn.commit()
        
        if order_type == 'collection':
            flash(f'Order #{order_id} confirmed for collection! We\'ll have it ready soon.', 'success')
        else:
            flash(f'Order #{order_id} placed successfully! We\'ll deliver it soon.', 'success')
            
        if points_earned > 0:
            flash(f'You earned {points_earned} loyalty points!', 'success')
        
        return redirect(url_for('order_detail', order_id=order_id))
        
    except Exception as e:
        conn.rollback()
        flash(f'An error occurred: {str(e)}', 'danger')
        return redirect(url_for('checkout'))
    finally:
        conn.close()


@app.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    """View order details"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get order
    cursor.execute('''
        SELECT * FROM orders 
        WHERE id = ? AND user_id = ?
    ''', (order_id, session['user_id']))
    order = cursor.fetchone()
    
    if not order:
        flash('Order not found!', 'danger')
        return redirect(url_for('account'))
    
    # Get order items
    cursor.execute('''
        SELECT * FROM order_items
        WHERE order_id = ?
    ''', (order_id,))
    items = cursor.fetchall()
    
    conn.close()
    
    return render_template('order_details.html', order=order, items=items)


@app.route('/offers')
@login_required
def offers():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT loyalty_points FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    points = user['loyalty_points']
    
    # Get recent transactions
    cursor.execute('''
        SELECT * FROM loyalty_transactions
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 20
    ''', (session['user_id'],))
    transactions = cursor.fetchall()
    
    # Get active vouchers
    cursor.execute('''
        SELECT * FROM vouchers
        WHERE user_id = ? AND is_used = 0
        ORDER BY created_at DESC
    ''', (session['user_id'],))
    vouchers = cursor.fetchall()
    
    conn.close()
    
    # Calculate points value
    points_value = points / 100
    
    return render_template('offers.html', points=points, points_value=points_value, 
                         transactions=transactions, vouchers=vouchers)

@app.route('/offers/buy-voucher/<int:discount>', methods=['POST'])
@login_required
def buy_voucher(discount):

    voucher_prices = {
        15: 1500,  # 15% discount costs 1500 points
        20: 2000   # 20% discount costs 2000 points
    }
    
    if discount not in voucher_prices:
        flash('Invalid voucher type!', 'danger')
        return redirect(url_for('loyalty'))
    
    points_cost = voucher_prices[discount]
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Get user points
        cursor.execute('SELECT loyalty_points FROM users WHERE id = ?', (session['user_id'],))
        current_points = cursor.fetchone()['loyalty_points']
        
        if current_points < points_cost:
            flash(f'Not enough points! You need {points_cost} points for this voucher.', 'danger')
            conn.close()
            return redirect(url_for('loyalty'))
        
        # Deduct points
        cursor.execute('''
            UPDATE users SET loyalty_points = loyalty_points - ? WHERE id = ?
        ''', (points_cost, session['user_id']))
        
        # Create voucher
        cursor.execute('''
            INSERT INTO vouchers (user_id, discount_percent, is_used)
            VALUES (?, ?, 0)
        ''', (session['user_id'], discount))
        
        # Record transaction
        cursor.execute('''
            INSERT INTO loyalty_transactions (user_id, points, description, transaction_type)
            VALUES (?, ?, ?, ?)
        ''', (session['user_id'], -points_cost, f'Bought {discount}% discount voucher', 'redeemed'))
        
        conn.commit()
        flash(f'Successfully purchased {discount}% discount voucher!', 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'An error occurred: {str(e)}', 'danger')
    finally:
        conn.close()
    
    return redirect(url_for('offers'))

@app.route('/dashboard')
@admin_required
def dashboard():
    conn = get_db()
    cursor = conn.cursor()
    
    products= cursor.execute('SELECT * FROM products ORDER BY category, name').fetchall()
    
    cursor.execute('''
        SELECT o.*, u.username, u.email,
               COUNT(oi.id) as item_count
        FROM orders o
        JOIN users u ON o.user_id = u.id
        LEFT JOIN order_items oi ON o.id = oi.order_id
        GROUP BY o.id
        ORDER BY o.created_at DESC
        LIMIT 50
    ''')
    orders = cursor.fetchall()
    
    cursor.execute('SELECT COUNT(*) as total FROM orders')
    total_orders = cursor.fetchone()['total']
    
    cursor.execute('SELECT COUNT(*) as total FROM products WHERE in_stock >= 1')
    in_stock_products = cursor.fetchone()['total']
    
    cursor.execute('SELECT COUNT(*) as total FROM products WHERE in_stock <= 0')
    out_of_stock_products = cursor.fetchone()['total']
    
    cursor.execute('SELECT SUM(final_amount) as total FROM orders WHERE status = "pending"')
    pending_revenue = cursor.fetchone()['total'] or 0

    categories = cursor.execute( 'SELECT DISTINCT category FROM products').fetchall()
    conn.close()
    
    return render_template('dashboard.html', 
                         products=products, 
                         orders=orders,
                         total_orders=total_orders,
                         in_stock_products=in_stock_products,
                         out_of_stock_products=out_of_stock_products,
                         pending_revenue=pending_revenue, categories=categories)


@app.route('/dashboard/product/update/<int:product_id>', methods=['GET','POST'])
@admin_required
def update_product(product_id):
    name = request.form.get('name')
    description = request.form.get('description')
    price = float(request.form.get('price'))
    category = request.form.get('new_category') or request.form.get('category')
    in_stock = int(request.form.get('in_stock'))

    conn = get_db()
    cursor = conn.cursor()
    

    # Use custom URL if provided
    custom_url = request.form.get('image_url')
    if custom_url and custom_url.strip():
        image_url = custom_url.strip()
    
    if image_url:
        cursor.execute('''
            UPDATE products 
            SET name = ?, description = ?, price = ?, category = ?, image_url = ?, in_stock = ?
            WHERE id = ?
        ''', (name, description, price, category, image_url, in_stock, product_id))
    else:
        cursor.execute('''
            UPDATE products 
            SET name = ?, description = ?, price = ?, category = ?, in_stock = ?
            WHERE id = ?
        ''', (name, description, price, category, in_stock, product_id))

    conn.commit()
    conn.close()
    
    flash('Product updated successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/dashboard/product/stock/<int:product_id>/<int:status>')
@admin_required
def toggle_stock(product_id, status):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('UPDATE products SET in_stock = ? WHERE id = ?', (status, product_id))
    
    conn.commit()
    conn.close()
    
    flash('Stock status updated!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/dashboard/product/add', methods=['POST']) #add new proudct
@login_required
def add_product():
    name = request.form.get('name')
    description = request.form.get('description')
    price = float(request.form.get('price'))
    category = request.form.get('category')
    in_stock = int(request.form.get('in_stock', 1))
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Create product first to get ID
    cursor.execute('''
        INSERT INTO products (name, description, price, category, in_stock, image_url)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, description, price, category, in_stock, 'https://via.placeholder.com/400'))
    
    product_id = cursor.lastrowid
    
    # Use custom URL if provided
    custom_url = request.form.get('image_url')
    if custom_url and custom_url.strip():
        image_url = custom_url.strip()
    
    # Update with actual image URL
    if image_url:
        cursor.execute('UPDATE products SET image_url = ? WHERE id = ?', 
                      (image_url, product_id))
    
    conn.commit()
    conn.close()
    
    flash('Product added successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/dashboard/product/delete/<int:product_id>')
@login_required
def delete_product(product_id):
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Get product name for confirmation message
        cursor.execute('SELECT name FROM products WHERE id = ?', (product_id,))
        product = cursor.fetchone()
        
        if not product:
            flash('Product not found!', 'danger')
            return redirect(url_for('dashboard'))
        
        product_name = product['name']
        
        # Check if product is in any active carts
        cursor.execute('SELECT COUNT(*) as count FROM cart WHERE product_id = ?', (product_id,))
        cart_count = cursor.fetchone()['count']
        
        if cart_count > 0:
            flash(f'Cannot delete {product_name}. It is currently in {cart_count} user cart(s). Please mark it as out of stock instead.', 'warning')
            return redirect(url_for('dashboard'))
        
        # Check if product is in any orders
        cursor.execute('SELECT COUNT(*) as count FROM order_items WHERE product_id = ?', (product_id,))
        order_count = cursor.fetchone()['count']
        
        if order_count > 0:
            flash(f'Cannot delete {product_name}. It exists in {order_count} order(s). Please mark it as out of stock instead.', 'warning')
            return redirect(url_for('dashboard'))
        
        # Safe to delete - no references in cart or orders
        cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
        conn.commit()
        
        flash(f'Product "{product_name}" deleted successfully!', 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting product: {str(e)}', 'danger')
    finally:
        conn.close()
    
    return redirect(url_for('dashboard'))

@app.route('/dashboard/order/status/<int:order_id>/<status>')
@admin_required
def update_order_status(order_id, status):
    """Update order status"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
    
    conn.commit()
    conn.close()
    
    flash('Order status updated!', 'success')
    return redirect(url_for('dashboard'))

if __name__ == "__main__":
    if not os.path.exists(DATABASE):
        init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
        