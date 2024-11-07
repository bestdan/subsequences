from app import db
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    games = db.relationship('GameSession', secondary='player_game', back_populates='players')

class GameSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(6), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='waiting')  # waiting, active, completed
    current_turn = db.Column(db.Integer, default=0)
    players = db.relationship('User', secondary='player_game', back_populates='games')
    sentences = db.relationship('Sentence', backref='game', lazy=True)

class PlayerGame(db.Model):
    __tablename__ = 'player_game'
    player_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game_session.id'), primary_key=True)
    order = db.Column(db.Integer)
    ready = db.Column(db.Boolean, default=False)

class Sentence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game_session.id'))
    player_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    content = db.Column(db.Text, nullable=False)
    order = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
