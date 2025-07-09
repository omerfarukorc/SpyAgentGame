from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
import random
import threading
import time
import string
import uuid
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'spy_game_secret_key_2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Oyun odaları ve durumları
game_rooms = {}

# Ülkeler listesi (Türkçe) - Daha bilinen ülkeler
COUNTRIES = [
    # Avrupa
    "Almanya", "İngiltere", "Fransa", "İtalya", "İspanya", "Hollanda", "İsviçre", 
    "İsveç", "Norveç", "Belçika", "Danimarka", "Avusturya", "Finlandiya", "Yunanistan", 
    "Macaristan", "Portekiz", "Çek Cumhuriyeti", "Polonya", "İrlanda", "Rusya",
    
    # Asya
    "Çin", "Japonya", "Hindistan", "Güney Kore", "Endonezya", "Tayland", "Malezya", 
    "Singapur", "Filipinler", "Vietnam", "Bangladeş", "Pakistan", "Türkiye",
    
    # Amerika
    "Amerika Birleşik Devletleri", "Kanada", "Meksika", "Brezilya", "Arjantin", 
    "Şili", "Kolombiya", "Küba", "Venezuela",
    
    # Afrika ve Orta Doğu
    "Güney Afrika", "Mısır", "Nijerya", "Fas", "Cezayir", "Suudi Arabistan", 
    "Birleşik Arap Emirlikleri", "İsrail", "İran", "Irak",
    
    # Okyanusya
    "Avustralya", "Yeni Zelanda"
]

class SpyGameRoom:
    def __init__(self, room_id, room_name, creator_id, max_players=8):
        self.room_id = room_id
        self.room_name = room_name
        self.creator_id = creator_id  # Odayı kuran kişinin ID'si
        self.max_players = max_players
        self.players = {}
        self.game_started = False
        self.discussion_phase = False
        self.voting_phase = False
        self.selected_country = None
        self.spy_player = None
        self.spy_count = 1  # Varsayılan hain sayısı
        self.votes = {}
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
        
        if len(connected_players) >= self.spy_count + 2 and not self.game_started:
            self.game_started = True
            self.discussion_phase = True
            self.selected_country = random.choice(COUNTRIES)
            
            # Spy sayısına göre casusları seç
            spy_ids = random.sample(connected_player_ids, self.spy_count)
            
            for player_id in self.players:
                if player_id in spy_ids:
                    self.players[player_id]['is_spy'] = True
                else:
                    self.players[player_id]['is_spy'] = False
            
            # İlk casusun ID'sini kaydet (geriye uyumluluk için)
            self.spy_player = spy_ids[0]
            
            return True
        return False
    
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
    
    def check_instant_majority(self):
        """Anlık çoğunluk kontrolü - herkesin oy vermesini beklemeden"""
        if not self.votes:
            return None
            
        # Bağlı oyuncu sayısı
        connected_players = [p for p in self.players.values() if p['connected']]
        total_connected = len(connected_players)
        
        # Oy dağılımı
        vote_count = {}
        for voted_player in self.votes.values():
            vote_count[voted_player] = vote_count.get(voted_player, 0) + 1
        
        if not vote_count:
            return None
            
        # Çoğunluk hesaplaması (yarıdan fazla)
        majority_threshold = (total_connected // 2) + 1
        
        for player, votes in vote_count.items():
            if votes >= majority_threshold:
                return {
                    'instant_win': True,
                    'winner': player,
                    'vote_count': vote_count,
                    'total_votes': len(self.votes),
                    'total_connected': total_connected
                }
        
        return None
    
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
                # Casus sayısı bilgisini ver
                spy_count = sum(1 for p in self.players.values() if p['is_spy'])
                return {
                    'role': 'spy',
                    'message': f'🕵️ Sen CASUSSUN! Toplam {spy_count} casus var. Ülkeyi tahmin etmeye çalış.',
                    'country': None,
                    'spy_count': spy_count
                }
            else:
                return {
                    'role': 'citizen',
                    'message': f'🌍 Ülken: {self.selected_country}',
                    'country': self.selected_country,
                    'spy_count': self.spy_count
                }
        return None

def generate_room_id():
    """4 karakterli kısa oda kodu üret"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

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
    spy_count = data.get('spy_count', 1)  # Hain sayısı
    
    # Yeni oda ID'si oluştur
    room_id = generate_room_id()
    
    # Aynı ID yoksa emin ol
    while room_id in game_rooms:
        room_id = generate_room_id()
    
    # Yeni oda oluştur
    player_id = request.sid
    game_rooms[room_id] = SpyGameRoom(room_id, room_name, player_id)
    game_rooms[room_id].spy_count = spy_count
    
    # Oyuncuyu odaya ekle
    if game_rooms[room_id].add_player(player_id, player_name):
        join_room(room_id)
        emit('room_created', {
            'room_id': room_id,
            'room_name': room_name,
            'player_name': player_name,
            'is_creator': True,
            'spy_count': spy_count
        })
        emit('player_joined', {
            'players': list(game_rooms[room_id].players.values()),
            'player_count': len(game_rooms[room_id].players),
            'new_player_name': player_name
        }, room=room_id)
    else:
        emit('create_error', {'message': 'Oda oluşturma hatası!'})

@socketio.on('heartbeat')
def handle_heartbeat(data):
    """Heartbeat from client to keep connection alive"""
    room_id = data.get('roomId')
    player_name = data.get('playerName')
    is_background = data.get('background', False)
    
    # Heartbeat'e response ver
    emit('heartbeat_response', {
        'timestamp': time.time(),
        'status': 'alive'
    })
    
    # Debug - background mode'da daha az log
    if not is_background:
        print(f"DEBUG: Heartbeat received from {player_name} in room {room_id}")
    
    # Oyuncunun bağlantı durumunu güncelle
    if room_id in game_rooms:
        room = game_rooms[room_id]
        player_id = request.sid
        if player_id in room.players:
            room.players[player_id]['connected'] = True
            room.players[player_id]['last_heartbeat'] = time.time()

@socketio.on('join_room')
def handle_join_room(data):
    room_id = data.get('room_id', '').upper()
    player_name = data.get('player_name', 'Oyuncu')
    player_id = request.sid
    is_reconnect = data.get('reconnect', False)
    game_state = data.get('game_state', {})
    
    print(f"DEBUG: Join room attempt - Room ID: {room_id}, Player: {player_name}, Reconnect: {is_reconnect}")
    print(f"DEBUG: Available rooms: {list(game_rooms.keys())}")
    
    if room_id in game_rooms:
        room = game_rooms[room_id]
        
        # Reconnection case - aynı isimde disconnected oyuncu var mı?
        existing_player_id = None
        if is_reconnect:
            for pid, player in room.players.items():
                if player['name'] == player_name:
                    existing_player_id = pid
                    break
        
        if existing_player_id:
            # Mevcut oyuncuyu yeniden bağla
            room.players[existing_player_id]['connected'] = True
            room.players[existing_player_id]['last_heartbeat'] = time.time()
            
            # Eski player_id'yi yeni session ile değiştir 
            room.players[player_id] = room.players.pop(existing_player_id)
            
            join_room(room_id)
            emit('room_joined', {
                'room_id': room_id,
                'room_name': room.room_name,
                'player_name': player_name,
                'is_creator': (player_id == room.creator_id)
            })
            
            print(f"DEBUG: {player_name} reconnected to room {room_id}")
            
            # Oyun durumunu gönder
            if room.game_started:
                player_info = room.get_player_info(player_id)
                if player_info:
                    emit('role_assigned', player_info)
                    emit('game_started', {
                        'message': f'Oyuna yeniden katıldınız! {room.spy_count} hain var.',
                        'phase': 'discussion' if room.discussion_phase else 'voting',
                        'timer': 0,
                        'spy_count': room.spy_count
                    })
            
            # Her durumda oyuncu listesini güncelle
            emit('player_joined', {
                'players': list(room.players.values()),
                'player_count': len(room.players)
            }, room=room_id)
            
        elif room.add_player(player_id, player_name):
            # Yeni oyuncu ekle
            room.players[player_id]['last_heartbeat'] = time.time()
            
            join_room(room_id)
            emit('room_joined', {
                'room_id': room_id,
                'room_name': room.room_name,
                'player_name': player_name,
                'is_creator': (player_id == room.creator_id)
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
                # Aynı isimde bağlı oyuncu var kontrolü
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
        
        # Sadece oda kurucusu oyunu başlatabilir
        if player_id != room.creator_id:
            emit('start_error', {'message': 'Sadece oda kurucusu oyunu başlatabilir!'})
            return
        
        # Bağlı oyuncu sayısını kontrol et
        connected_players = [p for p in room.players.values() if p['connected']]
        min_players = room.spy_count + 2  # En az spy_count + 2 oyuncu gerekli
        
        print(f"DEBUG: Start game request. Connected players: {len(connected_players)}, Required: {min_players}")
        
        if len(connected_players) >= min_players and room.start_game():
            # Oyun başlatıldığında direkt oylama moduna geç
            room.voting_phase = True
            
            # Tüm oyunculara oyun başladığını bildir
            emit('game_started', {
                'message': f'Oyun başladı! {room.spy_count} hain var. Oylama açık - istediğiniz zaman oy verebilirsiniz.',
                'phase': 'voting',
                'timer': 0,
                'spy_count': room.spy_count
            }, room=room_id)
            
            # Sadece bağlı oyunculara rollerini gönder
            for pid, player in room.players.items():
                if player['connected']:
                    player_info = room.get_player_info(pid)
                    socketio.emit('role_assigned', player_info, room=pid)
        else:
            emit('start_error', {'message': f'Oyunu başlatmak için en az {min_players} bağlı oyuncu gerekli! Şu anda bağlı: {len(connected_players)}'})

@socketio.on('submit_vote')
def handle_submit_vote(data):
    room_id = data.get('room_id')
    voted_player = data.get('voted_player')
    voter_id = request.sid
    
    if room_id in game_rooms:
        room = game_rooms[room_id]
        
        # Oyuncu kendisine oy veriyor mu kontrol et
        if voter_id in room.players and room.players[voter_id]['name'] == voted_player:
            return  # Kendine oy verme engellenmiş
        
        if room.add_vote(voter_id, voted_player):
            voter_name = room.players[voter_id]['name']
            emit('vote_submitted', {
                'message': f'{voter_name} oyunu kullandı.'
            }, room=room_id)
            
            # Anlık çoğunluk kontrolü
            instant_result = room.check_instant_majority()
            if instant_result:
                # Çoğunluk sağlandı, oyunu bitir
                handle_game_end(room_id, instant_result)
                return
            
            # Sadece bağlı oyuncuların hepsi oy verdiyse final sonuçları hesapla
            connected_players = [pid for pid, p in room.players.items() if p['connected']]
            connected_voted = [pid for pid in connected_players if room.players[pid]['voted']]
            
            print(f"DEBUG: Connected players: {len(connected_players)}, Voted: {len(connected_voted)}")
            
            if len(connected_voted) == len(connected_players) and len(connected_players) > 0:
                handle_vote_results(room_id)

def handle_game_end(room_id, result):
    """Oyunu bitir - anlık çoğunluk veya final sonuç"""
    if room_id in game_rooms:
        room = game_rooms[room_id]
        
        winner = result['winner']
        
        # Tüm casusları bul
        spy_players = [p['name'] for p in room.players.values() if p['is_spy']]
        spy_names = ', '.join(spy_players)
        
        # Casuslardan herhangi biri yakalandı mı?
        if winner in spy_players:
            # Casus yakalandı
            emit('game_ended', {
                'result': 'citizens_win',
                'message': f'🎉 Vatandaşlar kazandı! Casus {winner} yakalandı!',
                'voted_player': winner,
                'spy_player': spy_names,
                'spy_players': spy_players,
                'country': room.selected_country,
                'vote_count': result['vote_count']
            }, room=room_id)
        else:
            # Yanlış kişi seçildi
            emit('game_ended', {
                'result': 'spy_wins',
                'message': f'🕵️ Casuslar kazandı! Yanlış kişiyi seçtiniz. Casuslar: {spy_names}',
                'voted_player': winner,
                'spy_player': spy_names,
                'spy_players': spy_players,
                'country': room.selected_country,
                'vote_count': result['vote_count']
            }, room=room_id)

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
            handle_game_end(room_id, results)

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
                'players': list(room.players.values())
            }, room=room_id)
            
        else:
            emit('join_error', {'message': 'Bu odada değilsiniz!'})
    else:
        emit('join_error', {'message': 'Oda bulunamadı!'})

# Ping handler kaldırıldı - heartbeat sistemi kullanılıyor

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
            room.players[player_id]['disconnect_time'] = time.time()
            
            print(f"DEBUG: {player_name} marked as disconnected in room {room_id}")
            
            # Diğer oyunculara bildir
            emit('player_left', {
                'player_name': player_name,
                'players': list(room.players.values()),
                'player_count': len(room.players)
            }, room=room_id)
            
            # 10 dakika sonra oyuncuyu tamamen sil (uzun ekran kapatma için)
            def remove_player_delayed():
                time.sleep(600)  # 10 dakika
                if room_id in game_rooms and player_id in game_rooms[room_id].players:
                    if not game_rooms[room_id].players[player_id]['connected']:
                        print(f"DEBUG: Removing {player_name} permanently from room {room_id} after 10 minutes")
                        game_rooms[room_id].remove_player(player_id)
                        socketio.emit('player_left', {
                            'player_name': player_name,
                            'players': list(game_rooms[room_id].players.values()),
                            'player_count': len(game_rooms[room_id].players)
                        }, room=room_id)
            
            # Background task olarak çalıştır
            socketio.start_background_task(target=remove_player_delayed)
            break

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True) 