import os
from flask import Flask, render_template, session, request, redirect, url_for, flash
from werkzeug.security  import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, Wallpaper, User, AnonymousTracker
import secrets
from authlib.integrations.flask_client import OAuth
from werkzeug.middleware.proxy_fix import ProxyFix


app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

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

# --- OAUTH SETUP (GOOGLE) ---
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

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

# Route: Secure Download & IP Tracking
# Route 1: The Gateway & Timer Page
@app.route('/download/<int:wallpaper_id>')
def download_wallpaper(wallpaper_id):
    wallpaper = Wallpaper.query.get_or_404(wallpaper_id)
    
    # 1. If they are NOT logged in, check the Bouncer before wasting their time
    if not current_user.is_authenticated:
        user_ip = request.remote_addr

        tracker = AnonymousTracker.query.filter_by(ip_address=user_ip).first()

        # If they hit the limit, block them immediately
        if tracker and tracker.download_count >= 10:
            return redirect(url_for('register', limit_reached=True))

    # 2. If they pass the check (or are premium), show them the ad/timer page
    # 2. If they pass the check (or are premium), show them the ad/timer page
    return render_template('gateway.html', 
                           wallpaper=wallpaper, 
                           is_locked=False, 
                           timer_length=5, 
                           status_message="Fetching from secure vault...")


# Route 2: The Actual File Delivery (Triggered after 5 seconds)
@app.route('/serve/<int:wallpaper_id>')
def serve_wallpaper(wallpaper_id):
    wallpaper = Wallpaper.query.get_or_404(wallpaper_id)
    
    if not current_user.is_authenticated:
        if request.headers.getlist("X-Forwarded-For"):
            user_ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
        else:
            user_ip = request.remote_addr

        # Get or create the tracker
        tracker = AnonymousTracker.query.filter_by(ip_address=user_ip).first()
        if not tracker:
            tracker = AnonymousTracker(ip_address=user_ip, download_count=0)
            db.session.add(tracker)
            
        # Final safety check
        if tracker.download_count >= 10:
            return redirect(url_for('register', limit_reached=True))

        # Log the download against their IP
        tracker.download_count += 1
        
    # Increment global wallpaper stats
    wallpaper.downloads += 1
    db.session.commit()
    
    # Force the file download
    download_url = wallpaper.image_url.replace('/upload/', '/upload/fl_attachment/')
    return redirect(download_url)

@app.route('/register', methods=['GET', 'POST'])
def register():
    # 1. Grab the limit flag immediately so the template always has it
    limit_reached = request.args.get('limit_reached')

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
        
    # If they are just visiting the page, show the form and pass the flag
    return render_template('register.html', limit_reached=limit_reached)

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

# Route: Redirects to Google's consent screen
@app.route('/login/google')
def google_login():
    redirect_uri = url_for('google_auth', _external=True)
    return google.authorize_redirect(redirect_uri)

# Route: The Callback (Where Google sends them back)
@app.route('/auth/callback')
def google_auth():
    # 1. Grab the secure token Google just gave us
    token = google.authorize_access_token()
    user_info = token.get('userinfo')
    
    if not user_info:
        flash('Google login failed. Please try again.', 'error')
        return redirect(url_for('login'))
        
    email = user_info.get('email')
    
    # 2. Check if this email is already in our database
    user = User.query.filter_by(email=email).first()
    
    # 3. If they don't exist, create an account for them instantly!
    if not user:
        # Generate a random 32-character password since they use Google to log in
        random_pass = secrets.token_hex(16)
        hashed_pass = generate_password_hash(random_pass, method='pbkdf2:sha256')
        
        new_user = User(email=email, password_hash=hashed_pass)
        db.session.add(new_user)
        db.session.commit()
        user = new_user # Switch our reference to the newly created user
        
    # 4. Log them in and send them to the gallery
    login_user(user)
    return redirect(url_for('home'))

# Route: Secure Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)