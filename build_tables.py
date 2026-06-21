import os
from dotenv import load_dotenv

# 1. Load environment variables securely
load_dotenv()

from app import app
from models import db

def upgrade_vault():
    with app.app_context():
        print("Connecting to PostgreSQL to inject security patch...")
        # 2. Inject the column safely using raw SQL text execution
        db.session.execute(db.text(
            'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS auth_provider VARCHAR(20) DEFAULT \'password\' NOT NULL;'
        ))
        db.session.commit()
        print("Vault upgraded safely! The 'auth_provider' column is now active, and zero data was lost.")

if __name__ == '__main__':
    upgrade_vault()