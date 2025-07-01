from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
import random
import uuid
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'spy_game_secret_key_2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Oyun odaları ve durumları
game_rooms = {}

# Ülkeler listesi (Türkçe)
COUNTRIES = [
    "Amerika Birleşik Devletleri", "Çin", "Japonya", "Almanya", "İngiltere", 
    "Fransa", "İtalya", "Kanada", "Rusya", "Brezilya", "Hindistan", "Meksika", 
    "Avustralya", "İspanya", "Hollanda", "İsviçre", "Güney Kore", "Türkiye", 
    "Suudi Arabistan", "İsveç", "Arjantin", "Norveç", "Belçika", "Danimarka", 
    "İsrail", "Güney Afrika", "Endonezya", "Polonya", "Malezya", "Singapur", 
    "İrlanda", "Yeni Zelanda", "Portekiz", "Çek Cumhuriyeti", "Avusturya", 
    "Finlandiya", "Yunanistan", "Macaristan", "Tayland", "Filipinler", "Mısır"
]

class SpyGameRoom:
    def __init__(self, room_id, room_name, max_players=8):
        self.room_id = room_id
        self.room_name = room_name
        self.max_players = max_players
        self.players = {}
        self.game_started = False
        self.selected_country = None
        self.spy_player = None
        self.created_at = datetime.now()
        
    def add_player(self, player_id, player_name):
        if len(self.players) < self.max_players and not self.game_started:
            self.players[player_id] = {
                'name': player_name,
                'is_spy': False,
                'connected': True
            }
            return True
        return False
    
    def remove_player(self, player_id):
        if player_id in self.players:
            del self.players[player_id]
    
    def start_game(self):
        if len(self.players) >= 3 and not self.game_started:
            self.game_started = True
            self.selected_country = random.choice(COUNTRIES)
            
            # Rastgele bir oyuncuyu casus yap
            spy_id = random.choice(list(self.players.keys()))
            self.spy_player = spy_id
            
            for player_id in self.players:
                if player_id == spy_id:
                    self.players[player_id]['is_spy'] = True
                else:
                    self.players[player_id]['is_spy'] = False
            
            return True
        return False
    
    def get_player_info(self, player_id):
        if player_id in self.players:
            player = self.players[player_id]
            if player['is_spy']:
                return {
                    'role': 'spy',
                    'message': '🕵️ Sen CASUSSUN! Ülkeyi tahmin etmeye çalış.',
                    'country': None
                }
            else:
                return {
                    'role': 'citizen',
                    'message': f'🌍 Ülken: {self.selected_country}',
                    'country': self.selected_country
                }
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/game/<room_id>')
def game(room_id):
    return render_template('game.html', room_id=room_id)

@socketio.on('create_room')
def handle_create_room(data):
    room_id = str(uuid.uuid4())[:8].upper()
    room_name = data.get('room_name', f'Oda {room_id}')
    player_name = data.get('player_name', 'Oyuncu')
    
    print(f"DEBUG: Creating room - Room ID: {room_id}, Player: {player_name}")
    
    game_rooms[room_id] = SpyGameRoom(room_id, room_name)
    player_id = request.sid
    
    if game_rooms[room_id].add_player(player_id, player_name):
        join_room(room_id)
        emit('room_created', {
            'room_id': room_id,
            'room_name': room_name,
            'player_name': player_name
        })
        emit('player_joined', {
            'players': list(game_rooms[room_id].players.values()),
            'player_count': len(game_rooms[room_id].players)
        }, room=room_id)

@socketio.on('join_room')
def handle_join_room(data):
    room_id = data.get('room_id', '').upper()
    player_name = data.get('player_name', 'Oyuncu')
    player_id = request.sid
    
    print(f"DEBUG: Join room attempt - Room ID: {room_id}, Player: {player_name}")
    print(f"DEBUG: Available rooms: {list(game_rooms.keys())}")
    
    if room_id in game_rooms:
        room = game_rooms[room_id]
        if room.add_player(player_id, player_name):
            join_room(room_id)
            emit('room_joined', {
                'room_id': room_id,
                'room_name': room.room_name,
                'player_name': player_name
            })
            emit('player_joined', {
                'players': list(room.players.values()),
                'player_count': len(room.players)
            }, room=room_id)
        else:
            emit('join_error', {'message': 'Oda dolu veya oyun başlamış!'})
    else:
        emit('join_error', {'message': 'Oda bulunamadı!'})

@socketio.on('start_game')
def handle_start_game(data):
    room_id = data.get('room_id')
    player_id = request.sid
    
    if room_id in game_rooms:
        room = game_rooms[room_id]
        if room.start_game():
            emit('game_started', {
                'message': 'Oyun başladı! Rollerinizi kontrol edin.'
            }, room=room_id)
            
            for pid in room.players:
                player_info = room.get_player_info(pid)
                socketio.emit('role_assigned', player_info, room=pid)
        else:
            emit('start_error', {'message': 'Oyunu başlatmak için en az 3 oyuncu gerekli!'})

@socketio.on('send_message')
def handle_message(data):
    room_id = data.get('room_id')
    message = data.get('message')
    player_id = request.sid
    
    if room_id in game_rooms and player_id in game_rooms[room_id].players:
        player_name = game_rooms[room_id].players[player_id]['name']
        emit('new_message', {
            'player_name': player_name,
            'message': message,
            'timestamp': datetime.now().strftime('%H:%M')
        }, room=room_id)

@socketio.on('vote_player')
def handle_vote(data):
    room_id = data.get('room_id')
    voted_player = data.get('voted_player')
    voter_id = request.sid
    
    if room_id in game_rooms:
        room = game_rooms[room_id]
        if room.game_started and voter_id in room.players:
            voter_name = room.players[voter_id]['name']
            
            # Oyuncu kendisine oy veremez
            if voter_name == voted_player:
                emit('vote_error', {
                    'message': 'Kendinize oy veremezsiniz!'
                })
                return
                
            emit('player_voted', {
                'voter': voter_name,
                'voted': voted_player,
                'message': f'{voter_name}, {voted_player} oyuncusuna oy verdi!'
            }, room=room_id)

@socketio.on('disconnect')
def handle_disconnect():
    player_id = request.sid
    for room_id, room in game_rooms.items():
        if player_id in room.players:
            player_name = room.players[player_id]['name']
            room.remove_player(player_id)
            leave_room(room_id)
            emit('player_left', {
                'player_name': player_name,
                'players': list(room.players.values()),
                'player_count': len(room.players)
            }, room=room_id)
            break

if __name__ == '__main__':
    # Replit için port ayarı
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port) 