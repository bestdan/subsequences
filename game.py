from flask import Blueprint, render_template, jsonify, request, url_for, redirect, flash
from flask_login import login_required, current_user
from flask_socketio import emit, join_room, leave_room
from app import db, socketio
from models import GameSession, PlayerGame, Sentence, User
import random
import string
from sqlalchemy import func, desc

game_routes = Blueprint('game_routes', __name__)

def generate_game_code():
    """Generate a unique 6-character game code"""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not GameSession.query.filter_by(code=code).first():
            return code

@game_routes.route('/')
def index():
    return render_template('index.html')

@game_routes.route('/dashboard')
@login_required
def dashboard():
    # Get user's game statistics
    user_stats = {}
    user_stats['total_games'] = PlayerGame.query.filter_by(player_id=current_user.id).count()
    user_stats['completed_games'] = PlayerGame.query.join(GameSession).filter(
        PlayerGame.player_id == current_user.id,
        GameSession.status == 'completed'
    ).count()
    
    # Get total sentences contributed
    user_stats['total_sentences'] = Sentence.query.filter_by(player_id=current_user.id).count()
    
    # Get average words per sentence
    sentences = Sentence.query.filter_by(player_id=current_user.id).all()
    total_words = sum(len(sentence.content.split()) for sentence in sentences) if sentences else 0
    user_stats['avg_words_per_sentence'] = round(total_words / len(sentences), 1) if sentences else 0
    
    # Get recent games
    recent_games = db.session.query(
        GameSession,
        func.count(Sentence.id).label('sentence_count')
    ).join(
        PlayerGame
    ).outerjoin(
        Sentence
    ).filter(
        PlayerGame.player_id == current_user.id
    ).group_by(
        GameSession.id
    ).order_by(
        desc(GameSession.created_at)
    ).limit(5).all()
    
    # Get top players (by number of completed games)
    top_players = db.session.query(
        User,
        func.count(PlayerGame.player_id).label('games_played')
    ).join(
        PlayerGame
    ).join(
        GameSession
    ).filter(
        GameSession.status == 'completed'
    ).group_by(
        User.id
    ).order_by(
        desc('games_played')
    ).limit(5).all()
    
    return render_template('dashboard.html', 
                         user_stats=user_stats, 
                         recent_games=recent_games,
                         top_players=top_players)

@game_routes.route('/game/create', methods=['POST'])
@login_required
def create_game():
    game = GameSession(code=generate_game_code())
    db.session.add(game)
    db.session.flush()
    
    player_game = PlayerGame(player_id=current_user.id, game_id=game.id, order=0)
    db.session.add(player_game)
    db.session.commit()
    
    return redirect(url_for('game_routes.game', game_code=game.code))

@game_routes.route('/game/<string:game_code>')
@login_required
def game(game_code):
    game = GameSession.query.filter_by(code=game_code).first_or_404()
    
    # Check if game is full
    if len(game.players) >= 6 and current_user not in game.players:
        flash("This game is full!", "error")
        return redirect(url_for('game_routes.index'))
    
    # Join game if not already joined
    if current_user not in game.players and game.status == 'waiting':
        player_game = PlayerGame(
            player_id=current_user.id,
            game_id=game.id,
            order=len(game.players)
        )
        db.session.add(player_game)
        db.session.commit()
    
    return render_template('game.html', game=game)

@game_routes.route('/game/<int:game_id>/story')
@login_required
def get_story(game_id):
    game = GameSession.query.get_or_404(game_id)
    sentences = []
    for sentence in game.sentences:
        author = next((player.username for player in game.players if player.id == sentence.player_id), 'Unknown')
        sentences.append({
            'author': author,
            'content': sentence.content
        })
    return jsonify({'sentences': sentences})

@socketio.on('join')
def on_join(data):
    game_id = data['game_id']
    room = f"game_{game_id}"
    join_room(room)
    
    game = GameSession.query.get(game_id)
    if game:
        emit('game_status', {
            'status': game.status,
            'player_count': len(game.players),
            'current_turn': game.current_turn,
            'players': [{'username': p.username, 'ready': any(pg.ready for pg in p.games if pg.game_id == game.id)} 
                       for p in game.players]
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
        ready_count = sum(1 for pg in PlayerGame.query.filter_by(game_id=game_id) if pg.ready)
        total_players = len(game.players)
        
        emit('player_status_update', {
            'username': current_user.username,
            'ready': True,
            'ready_count': ready_count,
            'total_players': total_players
        }, room=room)
        
        # Start game if enough players are ready
        if ready_count >= 3 and ready_count == total_players:
            game.status = 'active'
            db.session.commit()
            emit('game_start', {
                'first_turn': True,
                'current_turn': 0
            }, room=room)

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
        next_player = game.players[(game.current_turn) % len(game.players)]
        
        emit('sentence_submitted', {
            'last_words': last_words,
            'turn': game.current_turn,
            'game_status': game.status,
            'next_player': next_player.username
        }, room=room)
