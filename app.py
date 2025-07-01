from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
import random
import threading
import time
import uuid
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'spy_game_secret_key_2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Oyun odaları ve durumları
game_rooms = {}

# Ülkeler listesi (Türkçe) - GENİŞLETİLDİ
COUNTRIES = [
    # Avrupa
    "Almanya", "İngiltere", "Fransa", "İtalya", "İspanya", "Hollanda", "İsviçre", 
    "İsveç", "Norveç", "Belçika", "Danimarka", "Avusturya", "Finlandiya", "Yunanistan", 
    "Macaristan", "Portekiz", "Çek Cumhuriyeti", "Polonya", "İrlanda", "Romanya",
    "Ukrayna", "Hırvatistan", "Sırbistan", "Bulgaristan", "Slovakya", "Slovenya",
    "Estonya", "Letonya", "Litvanya", "İzlanda", "Malta", "Kıbrıs", "Lüksemburg",
    
    # Asya
    "Çin", "Japonya", "Hindistan", "Güney Kore", "Endonezya", "Tayland", "Malezya", 
    "Singapur", "Filipinler", "Vietnam", "Bangladeş", "Pakistan", "Sri Lanka", 
    "Myanmar", "Kamboçya", "Laos", "Moğolistan", "Kuzey Kore", "Nepal", "Maldivler",
    
    # Amerika
    "Amerika Birleşik Devletleri", "Kanada", "Meksika", "Brezilya", "Arjantin", 
    "Şili", "Kolombiya", "Peru", "Venezuela", "Ekvador", "Uruguay", "Paraguay",
    "Bolivya", "Küba", "Jamaika", "Trinidad ve Tobago", "Kostarika", "Panama",
    
    # Afrika ve Orta Doğu
    "Güney Afrika", "Mısır", "Nijerya", "Kenya", "Etiyopya", "Gana", "Fas", 
    "Cezayir", "Tunus", "Suudi Arabistan", "Birleşik Arap Emirlikleri", "İsrail", 
    "İran", "Irak", "Lübnan", "Jordanya", "Katar", "Kuveyt", "Bahreyn", "Umman",
    
    # Okyanusya ve Diğer
    "Avustralya", "Yeni Zelanda", "Fiji", "Papua Yeni Gine", "Rusya", "Türkiye",
    "Kazakistan", "Özbekistan", "Azerbaycan", "Gürcistan", "Ermenistan"
]

class SpyGameRoom:
    def __init__(self, room_id, room_name, max_players=8):
        self.room_id = room_id
        self.room_name = room_name
        self.max_players = max_players
        self.players = {}
        self.game_started = False
        self.discussion_phase = False
        self.voting_phase = False
        self.selected_country = None
        self.spy_player = None
        self.votes = {}  # Oylama sistemi
        self.discussion_timer = None
        self.voting_timer = None
        self.created_at = datetime.now()
        
    def add_player(self, player_id, player_name):
        if len(self.players) >= self.max_players or self.game_started:
            return False
        
        # Aynı isimde oyuncu var mı kontrol et (bağlı olanlar için)
        for existing_player in self.players.values():
            if existing_player['name'].lower() == player_name.lower() and existing_player['connected']:
                return False  # Aynı isimde bağlı oyuncu var
        
        self.players[player_id] = {
            'name': player_name,
            'is_spy': False,
            'connected': True,
            'voted': False
        }
        return True
    
    def remove_player(self, player_id):
        if player_id in self.players:
            del self.players[player_id]
        if player_id in self.votes:
            del self.votes[player_id]
    
    def start_game(self):
        # Sadece bağlı oyuncuları say
        connected_players = [p for p in self.players.values() if p['connected']]
        connected_player_ids = [pid for pid, p in self.players.items() if p['connected']]
        
        if len(connected_players) >= 3 and not self.game_started:
            self.game_started = True
            self.discussion_phase = True
            self.selected_country = random.choice(COUNTRIES)
            
            # Sadece bağlı oyuncular arasından rastgele casus seç
            spy_id = random.choice(connected_player_ids)
            self.spy_player = spy_id
            
            for player_id in self.players:
                if player_id == spy_id:
                    self.players[player_id]['is_spy'] = True
                else:
                    self.players[player_id]['is_spy'] = False
            
            return True
        return False
    
    def start_voting_phase(self):
        """2 dakika sonra oylama başlatır"""
        self.discussion_phase = False
        self.voting_phase = True
        self.votes = {}
        for player_id in self.players:
            self.players[player_id]['voted'] = False
        return True
    
    def add_vote(self, voter_id, voted_player_name):
        """Gizli oylama sistemi - sadece bağlı oyuncular oy verebilir"""
        if (self.voting_phase and voter_id in self.players and 
            self.players[voter_id]['connected'] and  # Bağlı olmalı
            not self.players[voter_id]['voted']):
            
            # Oyuncu kendisine oy veremez
            voter_name = self.players[voter_id]['name']
            if voter_name == voted_player_name:
                return False
            
            # Oy verilen oyuncunun bağlı olduğunu kontrol et
            voted_player_connected = False
            for p in self.players.values():
                if p['name'] == voted_player_name and p['connected']:
                    voted_player_connected = True
                    break
            
            if voted_player_connected:
                self.votes[voter_id] = voted_player_name
                self.players[voter_id]['voted'] = True
                return True
        return False
    
    def count_votes(self):
        """Oyları sayar ve sonucu döner"""
        vote_count = {}
        for voted_player in self.votes.values():
            vote_count[voted_player] = vote_count.get(voted_player, 0) + 1
        
        if not vote_count:
            return None
        
        max_votes = max(vote_count.values())
        winners = [player for player, votes in vote_count.items() if votes == max_votes]
        
        # Eşitlik varsa
        if len(winners) > 1:
            return {'tie': True, 'tied_players': winners, 'vote_count': vote_count}
        else:
            return {'tie': False, 'winner': winners[0], 'vote_count': vote_count}
    
    def reset_voting(self):
        """Eşitlik durumunda oylamayı sıfırlar - sadece bağlı oyuncular için"""
        self.votes = {}
        for player_id in self.players:
            if self.players[player_id]['connected']:  # Sadece bağlı oyuncuları reset et
                self.players[player_id]['voted'] = False
    
    def reset_game(self):
        """Oyunu yeniden başlatmak için sıfırlar"""
        self.game_started = False
        self.discussion_phase = False
        self.voting_phase = False
        self.selected_country = None
        self.spy_player = None
        self.votes = {}
        self.discussion_timer = None
        self.voting_timer = None
        
        # Oyuncuları sıfırla (ama odada tut)
        for player_id in self.players:
            self.players[player_id]['is_spy'] = False
            self.players[player_id]['voted'] = False
        
        return True
    
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

def generate_room_id():
    return str(uuid.uuid4())[:8].upper()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/game/<room_id>')
def game(room_id):
    return render_template('game.html', room_id=room_id)

@socketio.on('create_room')
def handle_create_room(data):
    room_name = data.get('room_name', 'Oda')
    player_name = data.get('player_name', 'Oyuncu')
    
    # Yeni oda ID'si oluştur
    room_id = generate_room_id()
    
    # Yeni oda oluştur
    game_rooms[room_id] = SpyGameRoom(room_id, room_name)
    player_id = request.sid
    
    # Oyuncuyu odaya ekle
    if game_rooms[room_id].add_player(player_id, player_name):
        join_room(room_id)
        emit('room_created', {
            'room_id': room_id,
            'room_name': room_name,
            'player_name': player_name
        })
        emit('player_joined', {
            'players': list(game_rooms[room_id].players.values()),
            'player_count': len(game_rooms[room_id].players),
            'new_player_name': player_name
        }, room=room_id)
    else:
        emit('create_error', {'message': 'Oda oluşturma hatası!'})

@socketio.on('join_room')
def handle_join_room(data):
    room_id = data.get('room_id', '').upper()  # Büyük harf yap
    player_name = data.get('player_name', 'Oyuncu')
    player_id = request.sid
    is_reconnect = data.get('reconnect', False)
    
    print(f"DEBUG: Join room attempt - Room ID: {room_id}, Player: {player_name}, Reconnect: {is_reconnect}")
    print(f"DEBUG: Available rooms: {list(game_rooms.keys())}")
    
    if room_id in game_rooms:
        room = game_rooms[room_id]
        
        # Reconnection case - aynı isimde disconnected oyuncu var mı?
        existing_player_id = None
        if is_reconnect:
            for pid, player in room.players.items():
                if player['name'] == player_name and not player['connected']:
                    existing_player_id = pid
                    break
        
        if existing_player_id:
            # Mevcut oyuncuyu yeniden bağla
            room.players[existing_player_id]['connected'] = True
            # Eski player_id'yi yeni session ile değiştir 
            room.players[player_id] = room.players.pop(existing_player_id)
            
            join_room(room_id)
            emit('room_joined', {
                'room_id': room_id,
                'room_name': room.room_name,
                'player_name': player_name
            })
            
            print(f"DEBUG: {player_name} reconnected to room {room_id}")
            
            # Oyun durumunu gönder
            if room.game_started:
                player_info = room.get_player_info(player_id)
                if player_info:
                    emit('role_assigned', player_info)
                    emit('game_started', {
                        'message': 'Oyuna yeniden katıldınız!',
                        'phase': 'discussion' if room.discussion_phase else 'voting',
                        'timer': 0
                    })
            
            # Her durumda oyuncu listesini güncelle (sadece reconnect durumları için)
            emit('player_joined', {
                'players': list(room.players.values()),
                'player_count': len(room.players)
            }, room=room_id)
            
        elif room.add_player(player_id, player_name):
            # Yeni oyuncu ekle
            join_room(room_id)
            emit('room_joined', {
                'room_id': room_id,
                'room_name': room.room_name,
                'player_name': player_name
            })
            
            # Yeni oyuncu eklendi mesajı için
            emit('player_joined', {
                'players': list(room.players.values()),
                'player_count': len(room.players),
                'new_player_name': player_name
            }, room=room_id)
        else:
            # Hata nedeni belirleme
            if len(room.players) >= room.max_players:
                emit('join_error', {'message': 'Oda dolu! Maksimum 8 oyuncu olabilir.'})
            elif room.game_started:
                emit('join_error', {'message': 'Oyun zaten başlamış!'})
            else:
                # Aynı isimde oyuncu var kontrolü
                existing_names = [p['name'].lower() for p in room.players.values() if p['connected']]
                if player_name.lower() in existing_names:
                    emit('join_error', {'message': f'"{player_name}" ismi zaten kullanılıyor! Başka bir isim deneyin.'})
                else:
                    emit('join_error', {'message': 'Odaya katılma hatası!'})
        
    else:
        emit('join_error', {'message': 'Oda bulunamadı!'})

@socketio.on('start_game')
def handle_start_game(data):
    room_id = data.get('room_id')
    player_id = request.sid
    
    if room_id in game_rooms:
        room = game_rooms[room_id]
        
        # Bağlı oyuncu sayısını kontrol et
        connected_players = [p for p in room.players.values() if p['connected']]
        print(f"DEBUG: Start game request. Connected players: {len(connected_players)}")
        
        if room.start_game():
            # Tüm oyunculara oyun başladığını bildir
            emit('game_started', {
                'message': 'Oyun başladı! Tartışın ve hazır olduğunuzda oylamayı başlatın.',
                'phase': 'discussion',
                'timer': 0  # Başlangıçta 0 (sayaç olarak çalışacak)
            }, room=room_id)
            
            # Sadece bağlı oyunculara rollerini gönder
            for pid, player in room.players.items():
                if player['connected']:
                    player_info = room.get_player_info(pid)
                    socketio.emit('role_assigned', player_info, room=pid)
        else:
            emit('start_error', {'message': f'Oyunu başlatmak için en az 3 bağlı oyuncu gerekli! Şu anda bağlı: {len(connected_players)}'})

@socketio.on('start_voting')
def handle_start_voting(data):
    room_id = data.get('room_id')
    
    if room_id in game_rooms:
        room = game_rooms[room_id]
        if room.start_voting_phase():
            # Sadece bağlı oyuncuları oylama için gönder
            connected_players = [{'name': p['name']} for p in room.players.values() if p['connected']]
            
            emit('voting_started', {
                'message': 'Oylama başladı! Casusun kim olduğunu düşünüyorsanız oy verin.',
                'phase': 'voting',
                'players': connected_players
            }, room=room_id)
            
            print(f"DEBUG: Voting started with {len(connected_players)} connected players")

@socketio.on('submit_vote')
def handle_submit_vote(data):
    room_id = data.get('room_id')
    voted_player = data.get('voted_player')
    voter_id = request.sid
    
    if room_id in game_rooms:
        room = game_rooms[room_id]
        if room.add_vote(voter_id, voted_player):
            voter_name = room.players[voter_id]['name']
            emit('vote_submitted', {
                'message': f'{voter_name} oyunu kullandı.'
            }, room=room_id)
            
            # Sadece bağlı oyuncuların hepsi oy verdiyse sonuçları hesapla
            connected_players = [pid for pid, p in room.players.items() if p['connected']]
            connected_voted = [pid for pid in connected_players if room.players[pid]['voted']]
            
            print(f"DEBUG: Connected players: {len(connected_players)}, Voted: {len(connected_voted)}")
            
            if len(connected_voted) == len(connected_players) and len(connected_players) > 0:
                handle_vote_results(room_id)

def handle_vote_results(room_id):
    if room_id in game_rooms:
        room = game_rooms[room_id]
        results = room.count_votes()
        
        if results and results['tie']:
            # Eşitlik durumu - sadece bağlı oyuncular arasında eşitlik varsa
            connected_tied_players = []
            for tied_player in results['tied_players']:
                for pid, player in room.players.items():
                    if player['name'] == tied_player and player['connected']:
                        connected_tied_players.append({'name': tied_player})
                        break
            
            emit('vote_tie', {
                'message': f'Eşitlik! {", ".join(results["tied_players"])} arasında tekrar oylama.',
                'tied_players': connected_tied_players,
                'vote_count': results['vote_count']
            }, room=room_id)
            
            # Oylamayı sıfırla
            room.reset_voting()
            
        elif results and not results['tie']:
            # Kazanan belirlendi
            winner = results['winner']
            spy_name = room.players[room.spy_player]['name']
            
            if winner == spy_name:
                # Casus yakalandı
                emit('game_ended', {
                    'result': 'citizens_win',
                    'message': f'🎉 Vatandaşlar kazandı! Casus {spy_name} yakalandı!',
                    'voted_player': winner,
                    'spy_player': spy_name,
                    'country': room.selected_country,
                    'vote_count': results['vote_count']
                }, room=room_id)
            else:
                # Yanlış kişi seçildi
                emit('game_ended', {
                    'result': 'spy_wins',
                    'message': f'🕵️ Casus kazandı! Yanlış kişiyi seçtiniz. Casus: {spy_name}',
                    'voted_player': winner,
                    'spy_player': spy_name,
                    'country': room.selected_country,
                    'vote_count': results['vote_count']
                }, room=room_id)

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

@socketio.on('leave_room')
def handle_leave_room(data):
    room_id = data.get('room_id')
    player_id = request.sid
    
    print(f"DEBUG: Leave room request - Room ID: {room_id}, Player: {player_id}")
    
    if room_id in game_rooms:
        room = game_rooms[room_id]
        if player_id in room.players:
            player_name = room.players[player_id]['name']
            room.remove_player(player_id)
            leave_room(room_id)
            
            emit('player_left', {
                'player_name': player_name,
                'players': list(room.players.values()),
                'player_count': len(room.players)
            }, room=room_id)
            
            print(f"DEBUG: {player_name} left room {room_id}")

@socketio.on('reset_game')
def handle_reset_game(data):
    room_id = data.get('room_id')
    player_id = request.sid
    
    print(f"DEBUG: Reset game request - Room ID: {room_id}, Player: {player_id}")
    
    if room_id in game_rooms:
        room = game_rooms[room_id]
        if player_id in room.players:
            # Oyunu sıfırla
            room.reset_game()
            
            print(f"DEBUG: Game reset in room {room_id}. Active players: {len(room.players)}")
            
            # Tüm oyunculara reset bildir
            emit('game_reset', {
                'message': f'{room.players[player_id]["name"]} oyunu sıfırladı!',
                'players': list(room.players.values()),
                'player_count': len(room.players)
            }, room=room_id)
            
            # Yeniden oyun başlatma butonunu göster
            emit('player_joined', {
                'players': list(room.players.values()),
                'player_count': len(room.players)
            }, room=room_id)
        else:
            emit('join_error', {'message': 'Bu odada değilsiniz!'})
    else:
        emit('join_error', {'message': 'Oda bulunamadı!'})

@socketio.on('ping')
def handle_ping(data):
    """Keep-alive ping from client"""
    room_id = data.get('roomId') if data else None
    player_id = request.sid
    
    # Ping'e pong ile yanıt ver
    emit('pong', {'timestamp': time.time()})
    
    # Debug
    if room_id and room_id in game_rooms and player_id in game_rooms[room_id].players:
        print(f"DEBUG: Ping received from {game_rooms[room_id].players[player_id]['name']} in room {room_id}")

@socketio.on('disconnect')
def handle_disconnect():
    player_id = request.sid
    print(f"DEBUG: Player {player_id} disconnected")
    
    # Oyuncuyu tüm odalardan çıkar
    for room_id, room in game_rooms.items():
        if player_id in room.players:
            player_name = room.players[player_id]['name']
            
            # Oyuncuyu disconnected olarak işaretle (hemen silme)
            room.players[player_id]['connected'] = False
            
            print(f"DEBUG: {player_name} marked as disconnected in room {room_id}")
            
            # Diğer oyunculara bildir
            emit('player_left', {
                'player_name': player_name,
                'players': list(room.players.values()),
                'player_count': len(room.players)
            }, room=room_id)
            
            # 15 dakika sonra oyuncuyu tamamen sil (uzun ekran kapatma için)
            def remove_player_delayed():
                if room_id in game_rooms and player_id in game_rooms[room_id].players:
                    if not game_rooms[room_id].players[player_id]['connected']:
                        print(f"DEBUG: Removing {player_name} permanently from room {room_id} after 15 minutes")
                        game_rooms[room_id].remove_player(player_id)
                        emit('player_left', {
                            'player_name': player_name,
                            'players': list(game_rooms[room_id].players.values()),
                            'player_count': len(game_rooms[room_id].players)
                        }, room=room_id)
            
            # 15 dakika (900 saniye) sonra çalıştır
            socketio.start_background_task(target=lambda: time.sleep(900) or remove_player_delayed())
            break

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True) 