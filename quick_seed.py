import os
import cloudinary
import cloudinary.uploader
from flask import Flask
from models import db, Wallpaper
from dotenv import load_dotenv

# Load the new environment variables securely
load_dotenv()

# Configure the new Cloudinary account
cloudinary.config( 
  cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME'), 
  api_key = os.getenv('CLOUDINARY_API_KEY'), 
  api_secret = os.getenv('CLOUDINARY_API_SECRET') 
)

app = Flask(__name__)

db_url = os.environ.get('DATABASE_URL', 'sqlite:///wallpapers.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
    
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# The new folders you created
FOLDERS = ['cars', 'nature', 'space', 'anime','minimalist','surreal','cyberpunk','fluid']
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def seed_db():
    with app.app_context():
        # Creates the table if it doesn't exist
        db.create_all() 
        
        for category in FOLDERS:
            folder_path = os.path.join(BASE_DIR, category)
            if not os.path.exists(folder_path):
                print(f"Folder '{category}' not found. Skipping.")
                continue
                
            print(f"\n--- Uploading {category.capitalize()} wallpapers ---")
            
            for filename in os.listdir(folder_path):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    file_path = os.path.join(folder_path, filename)
                    
                    print(f"Uploading {filename} to Cloudinary...")
                    try:
                        response = cloudinary.uploader.upload(
                            file_path, 
                            folder=f"Aura/{category}"
                        )
                        
                        image_url = response.get('secure_url')
                        
                        # Turns "cars1" into "Cars 1" for the frontend UI
                        raw_name = filename.split('.')[0]
                        title = ''.join([c if c.isalpha() else f" {c}" for c in raw_name]).strip().title()
                        
                        # Add the data to our SQLite Database
                        new_wallpaper = Wallpaper(
                            title=title,
                            category=category.capitalize(),
                            image_url=image_url
                        )
                        db.session.add(new_wallpaper)
                        print(f"Saved '{title}' to database!")
                        
                    except Exception as e:
                        print(f"Error uploading {filename}: {e}")
        
        db.session.commit()
        print("\nAll new images uploaded and database seeded successfully!")

if __name__ == '__main__':
    seed_db()