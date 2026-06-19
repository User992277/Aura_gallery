import os
from flask import Flask, render_template, session, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, Wallpaper, User, AnonymousTracker


app = Flask(__name__)

# --- CONFIGURATION & DATABASE SETUP ---

# The Secret Key protects the user session data.
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'aura_super_secret_key_2026')

# SMART DATABASE SWITCHING:
# If Render provides a DATABASE_URL, use it (PostgreSQL). Otherwise, use local SQLite.
db_url = os.environ.get('DATABASE_URL', 'sqlite:///wallpapers.db')

# SQLAlchemy requires 'postgresql://' but Render provides 'postgres://', so we fix it here:
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database with the app
db.init_app(app)

# --- AUTHENTICATION SETUP ---
login_manager = LoginManager()
login_manager.init_app(app)
# If a user tries to access a locked route, send them to the login page
login_manager.login_view = 'login' 

# This function teaches Flask-Login how to find a user in the database
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- APPLICATION ROUTES ---

# Route 1: The Home Page (Shows everything)
@app.route('/')
def home():
    all_wallpapers = Wallpaper.query.all()
    return render_template('index.html', wallpapers=all_wallpapers, current_category="Discover")

# Route 2: The Category Filter
@app.route('/category/<string:category_name>')
def category_view(category_name):
    clean_name = category_name.capitalize()
    filtered_wallpapers = Wallpaper.query.filter_by(category=clean_name).all()
    return render_template('index.html', wallpapers=filtered_wallpapers, current_category=clean_name)

# Route 3: The Search Engine
@app.route('/search')
def search():
    # Grab the 'q' parameter from the URL (e.g., /search?q=porsche)
    query = request.args.get('q', '').strip()
    
    if query:
        # Search for the query in BOTH the title and the category
        search_term = f"%{query}%"
        filtered_wallpapers = Wallpaper.query.filter(
            (Wallpaper.title.ilike(search_term)) | (Wallpaper.category.ilike(search_term))
        ).all()
        display_category = f"Search: {query}"
    else:
        # If they search an empty string, just show everything
        filtered_wallpapers = Wallpaper.query.all()
        display_category = "Discover"
        
    return render_template('index.html', wallpapers=filtered_wallpapers, current_category=display_category)

# Route 4: The Dynamic Monetization Gateway
@app.route('/download/<int:wallpaper_id>')
def download_gateway(wallpaper_id):
    requested_wallpaper = Wallpaper.query.get_or_404(wallpaper_id)
    
    # Track their downloads in this session
    if 'download_count' not in session:
        session['download_count'] = 0
        
    session['download_count'] += 1
    count = session['download_count']
    
    is_locked = False
    timer_length = 5
    status_message = f"Generating a secure download link for '{requested_wallpaper.title}'..."
    
    if count > 10:
        # Hard limit reached
        is_locked = True
    elif count > 5:
        # Gentle Slowdown
        timer_length = 15
        status_message = "Wow, you love our art! To keep servers fast for everyone, your secure link will be ready in 15 seconds."
        
    return render_template(
        'gateway.html', 
        wallpaper=requested_wallpaper, 
        timer_length=timer_length,
        is_locked=is_locked,
        status_message=status_message
    )

@app.route('/register', methods=['GET', 'POST'])
def register():
    # If they submit the form
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Security Check: Does this email already exist?
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email address already exists. Please log in.', 'error')
            return redirect(url_for('register'))
            
        # Hash the password (PBKDF2 SHA256 is an industry standard)
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        # Create the user and save to PostgreSQL
        new_user = User(email=email, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        # Log them in automatically
        login_user(new_user)
        return redirect(url_for('home'))
        
    # If they are just visiting the page, show the form
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        # Check if user exists AND password is correct
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Please check your login details and try again.', 'error')
            return redirect(url_for('login'))
            
    return render_template('login.html')

# Route: Secure Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)