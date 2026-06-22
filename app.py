import os
from flask import Flask, render_template, session, request, redirect, url_for, flash
from werkzeug.security  import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, Wallpaper, User, AnonymousTracker
import secrets
from authlib.integrations.flask_client import OAuth
from werkzeug.middleware.proxy_fix import ProxyFix
import time
from flask_wtf.csrf import CSRFProtect
import re
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
limiter = Limiter(app=app, key_func=get_remote_address, default_limits=[])

# --- CONFIGURATION & DATABASE SETUP ---
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'aura_super_secret_key_2026')

# MOBILE COMPATIBILITY COOKIE HEADERS:
# Forces mobile in-app browsers (Instagram, Facebook) to persist session variables safely.
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

db_url = os.environ.get('DATABASE_URL', 'sqlite:///wallpapers.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
csrf = CSRFProtect(app)

# --- AUTHENTICATION SETUP ---
login_manager = LoginManager()
login_manager.init_app(app)
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

# FIX 1: Strip out the 'int()' typecast. Neon user table records are indexed by String keys!
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(str(user_id))


# --- APPLICATION ROUTES ---

@app.route('/')
def home():
    all_wallpapers = Wallpaper.query.all()
    history = []
    if current_user.is_authenticated:
        res = db.session.execute(
            db.text("SELECT w.* FROM wallpapers w JOIN user_downloads d ON w.id = d.wallpaper_id WHERE d.user_id = :u_id ORDER BY d.downloaded_at DESC"),
            {"u_id": current_user.id}
        )
        history = res.fetchall()
    return render_template('index.html', wallpapers=all_wallpapers, current_category="Discover", history=history)

@app.route('/category/<string:category_name>')
def category_view(category_name):
    clean_name = category_name.capitalize()
    filtered_wallpapers = Wallpaper.query.filter_by(category=clean_name).all()
    history = []
    if current_user.is_authenticated:
        res = db.session.execute(
            db.text("SELECT w.* FROM wallpapers w JOIN user_downloads d ON w.id = d.wallpaper_id WHERE d.user_id = :u_id ORDER BY d.downloaded_at DESC"),
            {"u_id": current_user.id}
        )
        history = res.fetchall()
    return render_template('index.html', wallpapers=filtered_wallpapers, current_category=clean_name, history=history)

@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    history = []
    if current_user.is_authenticated:
        res = db.session.execute(
            db.text("SELECT w.* FROM wallpapers w JOIN user_downloads d ON w.id = d.wallpaper_id WHERE d.user_id = :u_id ORDER BY d.downloaded_at DESC"),
            {"u_id": current_user.id}
        )
        history = res.fetchall()
        
    if query:
        search_term = f"%{query}%"
        filtered_wallpapers = Wallpaper.query.filter(
            (Wallpaper.title.ilike(search_term)) | (Wallpaper.category.ilike(search_term))
        ).all()
        display_category = f"Search: {query}"
    else:
        filtered_wallpapers = Wallpaper.query.all()
        display_category = "Discover"
    return render_template('index.html', wallpapers=filtered_wallpapers, current_category=display_category, history=history)

@app.route('/download/<string:wallpaper_id>')
def download_wallpaper(wallpaper_id):
    wallpaper = Wallpaper.query.get_or_404(str(wallpaper_id))
    
    if not current_user.is_authenticated:
        user_ip = request.remote_addr
        tracker = AnonymousTracker.query.filter_by(ip_address=user_ip).first()
        if tracker and int(tracker.download_count) >= 10:
            return redirect(url_for('register', limit_reached=True))

    session[f'gate_{wallpaper_id}'] = time.time()
    return render_template('gateway.html', 
                           wallpaper=wallpaper, 
                           is_locked=False, 
                           timer_length=5, 
                           status_message="Fetching from secure vault...")

@app.route('/serve/<string:wallpaper_id>')
def serve_wallpaper(wallpaper_id):
    wallpaper = Wallpaper.query.get_or_404(str(wallpaper_id))
    
    gate_time = session.get(f'gate_{wallpaper_id}')
    if not gate_time or (time.time() - gate_time) < 5:
        flash("Please wait for the timer to complete before downloading.", "error")
        return redirect(url_for('download_wallpaper', wallpaper_id=wallpaper_id))

    session.pop(f'gate_{wallpaper_id}', None)
    
    if current_user.is_authenticated:
        # Save to User's Download History Vault using raw SQL execution to prevent model alignment breaks
        try:
            db.session.execute(
                db.text("INSERT INTO user_downloads (user_id, wallpaper_id) VALUES (:u_id, :w_id) ON CONFLICT DO NOTHING"),
                {"u_id": current_user.id, "w_id": wallpaper.id}
            )
        except Exception as e:
            db.session.rollback()
    else:
        user_ip = request.remote_addr
        tracker = AnonymousTracker.query.filter_by(ip_address=user_ip).first()
        if not tracker:
            tracker = AnonymousTracker(ip_address=user_ip, download_count=0)
            db.session.add(tracker)
            
        if int(tracker.download_count) >= 10:
            return redirect(url_for('register', limit_reached=True))

        tracker.download_count = str(int(tracker.download_count) + 1)
        
    wallpaper.downloads = str(int(wallpaper.downloads) + 1)
    db.session.commit()
    
    download_url = wallpaper.image_url.replace('/upload/', '/upload/fl_attachment/')
    return redirect(download_url)

@app.route('/register', methods=['GET', 'POST'])
def register():
    limit_reached = request.args.get('limit_reached')

    if request.method == 'POST':
        EMAIL_REGEX = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not EMAIL_REGEX.match(email):
            flash('Please enter a valid email address structure.', 'error')
            return redirect(url_for('register'))

        if len(password) < 8:
            flash('Security standard: Password must be at least 8 characters long.', 'error')
            return redirect(url_for('register'))
        
        # FIX 2: Ensure we check the correct model structure mapping context
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email address already exists. Please log in.', 'error')
            return redirect(url_for('register'))
            
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        # Generate custom string string ID to align with Neon structure parameters
        new_user = User(id=str(secrets.token_hex(8)), email=email, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user)
        return redirect(url_for('home'))
        
    return render_template('register.html', limit_reached=limit_reached)

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute; 50 per hour")
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # FIX 3: Queries match exact model table references securely
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Please check your login details and try again.', 'error')
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.route('/login/google')
def google_login():
    redirect_uri = url_for('google_auth', _external=True)
    
    # Force the generated URL scheme to strictly use HTTPS for production environments
    if redirect_uri.startswith("http://"):
        redirect_uri = redirect_uri.replace("http://", "https://", 1)
        
    return google.authorize_redirect(redirect_uri)



@app.route('/auth/callback')
def google_auth():
    # 3. Google bounces them back here with the authorization tokens. 
    # We parse the incoming tokens to read their identity data:
    token = google.authorize_access_token()
    user_info = token.get('userinfo')
    
    if not user_info:
        flash('Google login failed. Please try again.', 'error')
        return redirect(url_for('login'))
        
    email = user_info.get('email')
    user = User.query.filter_by(email=email).first()
    
    if user:
        if user.auth_provider == 'password':
            flash('An account with this email already exists via standard password login. Please log in using your password.', 'error')
            return redirect(url_for('login'))
    else:
        random_pass = secrets.token_hex(16)
        hashed_pass = generate_password_hash(random_pass, method='pbkdf2:sha256')
        
        # Explicit String user mapping identity setup
        new_user = User(id=str(secrets.token_hex(8)), email=email, password_hash=hashed_pass, auth_provider='google')
        db.session.add(new_user)
        db.session.commit()
        user = new_user  
        
    # 4. Log the user into Flask-Login session state and send them home!
    login_user(user)
    return redirect(url_for('home'))

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)