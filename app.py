from flask import Flask, render_template, session, request
from models import db, Wallpaper
import os

app = Flask(__name__)

# --- CONFIGURATION & DATABASE SETUP ---

# The Secret Key protects the user session data.
# It tries to find a secure key on Render, but falls back to this local key if not found.
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

# NEW Route 4: The Search Engine
@app.route('/search')
def search():
    # Grab the 'q' parameter from the URL (e.g., /search?q=porsche)
    query = request.args.get('q', '').strip()
    
    if query:
        # Search for the query in BOTH the title and the category using 'ilike' (case-insensitive)
        search_term = f"%{query}%"
        filtered_wallpapers = Wallpaper.query.filter(
            (Wallpaper.title.ilike(search_term)) | (Wallpaper.category.ilike(search_term))
        ).all()
        # Update the UI to show they are looking at search results
        display_category = f"Search: {query}"
    else:
        # If they search an empty string, just show everything
        filtered_wallpapers = Wallpaper.query.all()
        display_category = "Discover"
        
    return render_template('index.html', wallpapers=filtered_wallpapers, current_category=display_category)

# Route 3: The Dynamic Monetization Gateway
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
        is_locked = True
    elif count > 5:
        timer_length = 15
        status_message = "Wow, you love our art! To keep servers fast for everyone, your secure link will be ready in 15 seconds."
        
    return render_template(
        'gateway.html', 
        wallpaper=requested_wallpaper, 
        timer_length=timer_length,
        is_locked=is_locked,
        status_message=status_message
    )

if __name__ == '__main__':
    app.run(debug=True)