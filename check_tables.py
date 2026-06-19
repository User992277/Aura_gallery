import os
from dotenv import load_dotenv

# 1. Give the script its glasses so it can see the Render URL!
load_dotenv()

from app import app
from models import db
from sqlalchemy import inspect

def check_tables():
    with app.app_context():
        # Print out exactly which database we are looking at to be absolutely sure
        print(f"\n[Connecting to: {app.config['SQLALCHEMY_DATABASE_URI'][:15]}...]")
        
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        print("\n--- SECURE CLOUD VAULT CONTENTS ---")
        for table in tables:
            print(f"✅ Found table: {table}")
        print("-----------------------------------\n")

if __name__ == '__main__':
    check_tables()