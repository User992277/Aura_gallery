from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin

db = SQLAlchemy()

class Wallpaper(db.Model):
    __tablename__ = 'wallpapers' 
    
    # CHANGED: set to String(255) to support your random string wallpaper IDs safely
    id = db.Column(db.String(255), primary_key=True) 
    title = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    image_url = db.Column(db.String(255), nullable=False)
    
    # CHANGED: set to String(50) to support string tracking increments safely
    downloads = db.Column(db.String(50), default='0') 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    # CHANGED: set to String(255) to support hex token string IDs securely
    id = db.Column(db.String(255), primary_key=True) 
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    auth_provider = db.Column(db.String(20), default='password', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AnonymousTracker(db.Model):
    __tablename__ = 'anonymous_tracker' # Explicitly mapped
    
    # CHANGED: set to String/SERIAL sequence handling patterns matching your hotfix layout
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ip_address = db.Column(db.String(45), unique=True, nullable=False) 
    
    # CHANGED: set to String(50) to support text counter validations securely
    download_count = db.Column(db.String(50), default='0') 
    last_download = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)