from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Wallpaper(db.Model):
    __tablename__ = 'wallpapers'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    downloads = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AnonymousTracker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # 45 characters is enough to store both standard and complex IPv6 addresses safely
    ip_address = db.Column(db.String(45), unique=True, nullable=False) 
    download_count = db.Column(db.Integer, default=0)
    last_download = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)