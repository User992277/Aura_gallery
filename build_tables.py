import os
from dotenv import load_dotenv

# 1. Load the Render Database URL from your .env file
load_dotenv()

from app import app
from models import db, Wallpaper, User, AnonymousTracker

def upgrade_vault():
    with app.app_context():
        # 2. Because all models are imported above, SQLAlchemy sees them now!
        db.create_all()
        print("Vault upgraded! New tables successfully forged in PostgreSQL.")

if __name__ == '__main__':
    upgrade_vault()