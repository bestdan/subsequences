import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
socketio = SocketIO()
login_manager = LoginManager()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

db.init_app(app)
socketio.init_app(app)
login_manager.init_app(app)
login_manager.login_view = "google_auth.login"

with app.app_context():
    import models
    from google_auth import google_auth
    from game import game_routes
    
    app.register_blueprint(google_auth)
    app.register_blueprint(game_routes)
    
    # Drop all tables and recreate to fix schema
    db.drop_all()
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return models.User.query.get(int(user_id))
