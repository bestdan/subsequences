from flask import Blueprint, render_template, jsonify, request, url_for, redirect
from flask_login import login_required, current_user
from flask_socketio import emit, join_room, leave_room
from app import db, socketio
from models import GameSession, PlayerGame, Sentence
import random

game_routes = Blueprint('game_routes', __name__)

@game_routes.route('/')
def index():
    return render_template('index.html')

@game_routes.route('/game/create', methods=['POST'])
@login_required
def create_game():
    game = GameSession()
    db.session.add(game)
    db.session.flush()
    
    player_game = PlayerGame(player_id=current_user.id, game_id=game.id, order=0)
    db.session.add(player_game)
    db.session.commit()
    
    return redirect(url_for('game_routes.game', game_id=game.id))

@game_routes.route('/game/<int:game_id>')
@login_required
def game(game_id):
    game = GameSession.query.get_or_404(game_id)
    return render_template('game.html', game=game)

@socketio.on('join')
def on_join(data):
    game_id = data['game_id']
    room = f"game_{game_id}"
    join_room(room)
    
    game = GameSession.query.get(game_id)
    if game and game.status == 'waiting':
        player_count = len(game.players)
        if current_user not in game.players and player_count < 6:
            player_game = PlayerGame(
                player_id=current_user.id,
                game_id=game_id,
                order=player_count
            )
            db.session.add(player_game)
            db.session.commit()
            
            emit('player_joined', {
                'username': current_user.username,
                'player_count': player_count + 1
            }, room=room)

@socketio.on('player_ready')
def on_player_ready(data):
    game_id = data['game_id']
    room = f"game_{game_id}"
    
    player_game = PlayerGame.query.filter_by(
        game_id=game_id,
        player_id=current_user.id
    ).first()
    
    if player_game:
        player_game.ready = True
        db.session.commit()
        
        game = GameSession.query.get(game_id)
        ready_count = sum(1 for pg in game.players if pg.ready)
        
        if ready_count >= 3 and ready_count == len(game.players):
            game.status = 'active'
            db.session.commit()
            emit('game_start', room=room)

@socketio.on('submit_sentence')
def on_submit_sentence(data):
    game_id = data['game_id']
    content = data['sentence']
    room = f"game_{game_id}"
    
    game = GameSession.query.get(game_id)
    if game and game.status == 'active':
        sentence = Sentence(
            game_id=game_id,
            player_id=current_user.id,
            content=content,
            order=game.current_turn
        )
        db.session.add(sentence)
        game.current_turn += 1
        
        if game.current_turn >= 12:
            game.status = 'completed'
        
        db.session.commit()
        
        last_words = ' '.join(content.split()[-10:]) if content else ''
        emit('sentence_submitted', {
            'last_words': last_words,
            'turn': game.current_turn,
            'game_status': game.status
        }, room=room)
