// Socket.IO bağlantısı - uzun süreli mobil optimizasyonu ile
const socket = io({
    // Mobil cihazlar için optimizasyon
    transports: ['websocket', 'polling'],
    upgrade: true,
    rememberUpgrade: true,
    // Reconnection ayarları - 10+ dakika ekran kapatma için
    reconnection: true,
    reconnectionDelay: 2000,
    reconnectionDelayMax: 10000,
    maxReconnectionAttempts: 20, // Daha fazla deneme
    timeout: 30000,
    // Keep-alive - uzun süreli için optimize
    pingTimeout: 120000, // 2 dakika
    pingInterval: 60000   // 1 dakika
});

// Bağlantı durumu yönetimi
let connectionState = {
    isConnected: false,
    reconnectAttempts: 0,
    lastDisconnectTime: null,
    isReconnecting: false,
    wasGameStarted: false
};

// Visibility API için değişkenler
let isPageVisible = true;
let visibilityChangeTimeout = null;

// DOM elementleri
const loadingOverlay = document.getElementById('loadingOverlay');
const notification = document.getElementById('notification');
const roomNameEl = document.getElementById('roomName');
const roomCodeEl = document.getElementById('roomCode');
const playerCountEl = document.getElementById('playerCount');
const playersListEl = document.getElementById('playersList');
const startGameBtn = document.getElementById('startGameBtn');
const startVotingBtn = document.getElementById('startVotingBtn');
const roleCard = document.getElementById('roleCard');
const roleIcon = document.getElementById('roleIcon');
const roleTitle = document.getElementById('roleTitle');
const roleMessage = document.getElementById('roleMessage');
const countryInfo = document.getElementById('countryInfo');
const countryName = document.getElementById('countryName');
const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const votingSection = document.getElementById('votingSection');
const votingButtons = document.getElementById('votingButtons');
const gameTimer = document.getElementById('gameTimer');
const timerDisplay = document.getElementById('timerDisplay');
const gameEndModal = document.getElementById('gameEndModal');

// Oyun durumu
let gameState = {
    players: [],
    gameStarted: false,
    myRole: null,
    roomId: ROOM_ID,
    playerName: localStorage.getItem('playerName') || 'Oyuncu'
};

// Timer değişkenleri
let gameTimerInterval = null;
let gameTimeLeft = 120; // 2 dakika
let currentPhase = 'waiting'; // 'waiting', 'discussion', 'voting'

// Keep-alive ping interval
let keepAliveInterval = null;

// Her oyuncu için benzersiz renk üret
const playerColors = new Map();

function getPlayerColor(playerName) {
    if (!playerColors.has(playerName)) {
        // Deterministik renk üretimi (isimden hash)
        let hash = 0;
        for (let i = 0; i < playerName.length; i++) {
            hash = playerName.charCodeAt(i) + ((hash << 5) - hash);
        }
        
        // HSL formatında renk üret (daha canlı renkler için)
        const hue = Math.abs(hash) % 360;
        const saturation = 60 + (Math.abs(hash) % 40); // 60-100 arası
        const lightness = 45 + (Math.abs(hash) % 20);  // 45-65 arası
        
        const color = `hsl(${hue}, ${saturation}%, ${lightness}%)`;
        playerColors.set(playerName, color);
    }
    
    return playerColors.get(playerName);
}

// Utility fonksiyonlar
function showNotification(message, type = 'info') {
    notification.textContent = message;
    notification.className = `notification ${type} show`;
    
    setTimeout(() => {
        notification.className = 'notification';
    }, 4000);
}

function hideLoadingOverlay() {
    loadingOverlay.style.display = 'none';
}

function updatePlayersList(players) {
    gameState.players = players;
    const playersList = document.getElementById('playersList');
    const playerCount = document.getElementById('playerCount');
    
    playersList.innerHTML = '';
    
    players.forEach(player => {
        const li = document.createElement('li');
        li.className = 'player-item';
        
        // Kendi ismimizi vurgula
        if (player.name === gameState.playerName) {
            li.classList.add('current-player');
        }
        
        // Bağlantı durumu gösterimi
        const statusIcon = player.connected ? '🟢' : '🔴';
        const statusText = player.connected ? '' : ' (Çevrimdışı)';
        
        li.innerHTML = `
            <span>${statusIcon} ${player.name}${statusText}</span>
        `;
        
        playersList.appendChild(li);
    });
    
    // Oyuncu sayısını güncelle
    playerCount.textContent = players.length;
    
    // Sadece bağlı oyuncuları say
    const connectedPlayers = players.filter(player => player.connected);
    
    // Oyun başlatma butonu gösterimi (3+ bağlı oyuncu ve oyun başlamamışsa)
    if (connectedPlayers.length >= 3 && !gameState.gameStarted) {
        startGameBtn.classList.remove('hidden');
        console.log(`Oyun başlatma butonu gösterildi. Bağlı oyuncu sayısı: ${connectedPlayers.length}, Oyun durumu: ${gameState.gameStarted}`);
    } else {
        startGameBtn.classList.add('hidden');
        console.log(`Oyun başlatma butonu gizlendi. Bağlı oyuncu sayısı: ${connectedPlayers.length}, Oyun durumu: ${gameState.gameStarted}`);
    }
}

function addChatMessage(playerName, message, timestamp, isSystem = false) {
    const messageEl = document.createElement('div');
    messageEl.className = 'chat-message';
    
    if (isSystem) {
        messageEl.classList.add('system-message');
        messageEl.innerHTML = `
            <span class="system-text">ℹ️ ${message}</span>
        `;
    } else {
        const playerColor = getPlayerColor(playerName);
        const isCurrentPlayer = playerName === gameState.playerName;
        
        messageEl.innerHTML = `
            <span class="player-name" style="color: ${playerColor}; ${isCurrentPlayer ? 'font-weight: bold; text-shadow: 0 0 10px ' + playerColor + '50;' : ''}">${playerName}:</span>
            <span class="message-text">${message}</span>
            <span class="timestamp">${timestamp}</span>
        `;
        
        if (isCurrentPlayer) {
            messageEl.classList.add('own-message');
        }
    }
    
    chatMessages.appendChild(messageEl);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showRole(roleData) {
    gameState.myRole = roleData.role;
    
    // Rol kartını göster
    roleCard.classList.remove('hidden');
    roleCard.className = `role-card ${roleData.role}`;
    
    if (roleData.role === 'spy') {
        roleIcon.textContent = '🕵️';
        roleTitle.textContent = 'CASUS';
        roleMessage.textContent = roleData.message;
        countryInfo.classList.add('hidden');
    } else {
        roleIcon.textContent = '🌍';
        roleTitle.textContent = roleData.country.toUpperCase();
        roleMessage.textContent = roleData.message;
        countryName.textContent = roleData.country;
        countryInfo.classList.remove('hidden');
    }
    
    // Rol gizleme butonu ekle
    let hideRoleBtn = document.getElementById('hideRoleBtn');
    if (!hideRoleBtn) {
        hideRoleBtn = document.createElement('button');
        hideRoleBtn.id = 'hideRoleBtn';
        hideRoleBtn.className = 'btn btn-warning';
        hideRoleBtn.style.cssText = 'margin-top: 15px; width: 100%;';
        hideRoleBtn.textContent = '👁️‍🗨️ Rolü Gizle (Telefonu kapatabilirsin)';
        roleCard.appendChild(hideRoleBtn);
        
        hideRoleBtn.addEventListener('click', () => {
            hideRole();
        });
    }
    
    // Rol gösterme süresi (10 saniye sonra otomatik gizle önerisi)
    setTimeout(() => {
        if (!roleCard.classList.contains('hidden')) {
            showNotification('💡 İpucu: Rolünü gördün, artık gizleyebilirsin!', 'info');
        }
    }, 10000);
}

function hideRole() {
    roleCard.classList.add('hidden');
    
    // Rol bilgisini küçük bir göstergede tut
    let roleIndicator = document.getElementById('roleIndicator');
    if (!roleIndicator) {
        roleIndicator = document.createElement('div');
        roleIndicator.id = 'roleIndicator';
        roleIndicator.style.cssText = `
            position: fixed;
            top: 50px;
            right: 10px;
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 12px;
            z-index: 999;
            cursor: pointer;
            transition: opacity 0.3s ease;
        `;
        document.body.appendChild(roleIndicator);
        
        roleIndicator.addEventListener('click', () => {
            showRoleTemporarily();
        });
    }
    
    if (gameState.myRole === 'spy') {
        roleIndicator.textContent = '🕵️ Casus';
        roleIndicator.style.background = 'rgba(239, 68, 68, 0.9)';
    } else {
        roleIndicator.textContent = '🌍 Vatandaş';
        roleIndicator.style.background = 'rgba(34, 197, 94, 0.9)';
    }
    
    showNotification('✅ Rol gizlendi! Artık telefonu kapatabilirsin. Sağ üstteki ikona tıklayarak tekrar görebilirsin.', 'success');
}

function showRoleTemporarily() {
    roleCard.classList.remove('hidden');
    
    // 5 saniye sonra tekrar gizle
    setTimeout(() => {
        if (!roleCard.classList.contains('hidden')) {
            roleCard.classList.add('hidden');
            showNotification('Rol tekrar gizlendi.', 'info');
        }
    }, 5000);
}

function startGameTimer(duration = 120, phase = 'discussion') {
    gameTimeLeft = duration;
    currentPhase = phase;
    gameTimer.classList.remove('hidden');
    
    // Timer label'ını güncelle
    const timerLabel = document.getElementById('timerLabel');
    if (phase === 'discussion') {
        timerLabel.textContent = 'Geçen Süre:';
    } else if (phase === 'voting') {
        timerLabel.textContent = 'Oylama Süresi:';
    }
    
    if (gameTimerInterval) {
        clearInterval(gameTimerInterval);
    }
    
    gameTimerInterval = setInterval(() => {
        gameTimeLeft++;  // Artık süreyi artırıyoruz (sayaç olarak)
        
        const minutes = Math.floor(gameTimeLeft / 60);
        const seconds = gameTimeLeft % 60;
        timerDisplay.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        
        // Otomatik oylama başlatma kaldırıldı - sadece süre gösterici
    }, 1000);
}

function showVoting(players) {
    votingSection.classList.remove('hidden');
    votingButtons.innerHTML = '';
    
    // Başlık ekle
    const votingTitle = document.createElement('h4');
    votingTitle.textContent = '🤐 Gizli Oylama - Kim Casus?';
    votingTitle.style.marginBottom = '15px';
    votingButtons.appendChild(votingTitle);
    
    // Kendisi hariç diğer oyuncular için oy butonları oluştur
    players.forEach(player => {
        // Oyuncu kendisine oy veremez
        if (player.name !== gameState.playerName) {
            const voteBtn = document.createElement('button');
            voteBtn.className = 'vote-btn';
            voteBtn.textContent = `🗳️ ${player.name}`;
            voteBtn.onclick = () => submitVote(player.name);
            votingButtons.appendChild(voteBtn);
        }
    });
    
    addChatMessage('', 'Gizli oylama başladı! Casusun kim olduğunu düşünüyorsanız oy verin.', '', true);
    addChatMessage('', '⚠️ Not: Kendinize oy veremezsiniz.', '', true);
}

function submitVote(playerName) {
    socket.emit('submit_vote', {
        room_id: gameState.roomId,
        voted_player: playerName
    });
    
    // Oylama butonlarını devre dışı bırak
    const voteButtons = document.querySelectorAll('.vote-btn');
    voteButtons.forEach(btn => {
        btn.disabled = true;
        btn.style.opacity = '0.5';
        btn.textContent = btn.textContent.includes(playerName) ? 
            `✅ ${playerName} (Oylandı)` : btn.textContent;
    });
    
    showNotification(`${playerName} için oy kullandınız!`, 'success');
}

function showGameEndModal(data) {
    const gameEndModal = document.getElementById('gameEndModal');
    const gameEndTitle = document.getElementById('gameEndTitle');
    const gameEndMessage = document.getElementById('gameEndMessage');
    
    if (data.result === 'citizens_win') {
        gameEndTitle.textContent = '🎉 Vatandaşlar Kazandı!';
        gameEndTitle.style.color = '#4CAF50';
    } else {
        gameEndTitle.textContent = '🕵️ Casus Kazandı!';
        gameEndTitle.style.color = '#f44336';
    }
    
    gameEndMessage.innerHTML = `
        ${data.message}<br><br>
        <strong>🌍 Ülke:</strong> ${data.country}<br>
        <strong>🕵️ Casus:</strong> ${data.spy_player}<br>
        <strong>🗳️ Seçilen:</strong> ${data.voted_player}
    `;
    
    gameEndModal.classList.remove('hidden');
}

function resetGame() {
    // Sunucuya reset isteği gönder
    socket.emit('reset_game', {
        room_id: gameState.roomId
    });
    
    // UI'yi hemen sıfırla
    gameState.gameStarted = false;
    currentPhase = 'waiting';
    
    // UI elementlerini sıfırla
    roleCard.classList.add('hidden');
    votingSection.classList.add('hidden');
    gameTimer.classList.add('hidden');
    chatInput.classList.add('hidden');
    gameEndModal.classList.add('hidden');
    
    // Rol göstergesini temizle
    const roleIndicator = document.getElementById('roleIndicator');
    if (roleIndicator) {
        roleIndicator.remove();
    }
    
    // Timer'ı temizle
    if (gameTimerInterval) {
        clearInterval(gameTimerInterval);
        gameTimerInterval = null;
    }
    
    // Chat'i temizle
    chatMessages.innerHTML = '';
    
    // Oyun durumunu temizle
    gameState.myRole = null;
    localStorage.removeItem('gameState_' + gameState.roomId);
    
    showNotification('Oyun sıfırlandı! Yeni oyun başlatabilirsiniz.', 'success');
}

function sendChatMessage() {
    const message = messageInput.value.trim();
    if (message && gameState.gameStarted) {
        socket.emit('send_message', {
            room_id: gameState.roomId,
            message: message
        });
        messageInput.value = '';
    }
}

// Event Listeners

// Oyunu başlat
startGameBtn.addEventListener('click', () => {
    socket.emit('start_game', {
        room_id: gameState.roomId
    });
});

// Manuel oylama başlat
startVotingBtn.addEventListener('click', () => {
    socket.emit('start_voting', {
        room_id: gameState.roomId
    });
    startVotingBtn.style.display = 'none';
});

// Mesaj gönder
sendBtn.addEventListener('click', sendChatMessage);

messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendChatMessage();
    }
});

// Ana sayfaya dön
document.getElementById('homeBtn')?.addEventListener('click', () => {
    // Odayı terk ettiğini sunucuya bildir
    socket.emit('leave_room', {
        room_id: gameState.roomId,
        player_name: gameState.playerName
    });
    
    // localStorage'ı temizle
    localStorage.removeItem('playerName');
    localStorage.removeItem('gameState_' + gameState.roomId);
    
    window.location.href = '/';
});

// Tekrar oyna
document.getElementById('playAgainBtn')?.addEventListener('click', () => {
    console.log('Play again button clicked');
    resetGame();
});

// Socket.IO Event Listeners

// Oyuncular güncellendi  
socket.on('player_joined', (data) => {
    updatePlayersList(data.players);
    hideLoadingOverlay();
    
    // Sadece yeni katılan oyuncu mesajı varsa göster
    if (data.new_player_name && data.new_player_name !== gameState.playerName) {
        addChatMessage('', `${data.new_player_name} lobiye katıldı! 👋`, '', true);
    }
});

// Oyuncu ayrıldı
socket.on('player_left', (data) => {
    updatePlayersList(data.players);
    // Sadece gerçekten ayrılan oyuncu için mesaj göster
    if (data.player_name && data.player_name !== gameState.playerName) {
        addChatMessage('', `${data.player_name} lobiden ayrıldı 👋`, '', true);
    }
});

// Oyun başladı
socket.on('game_started', (data) => {
    gameState.gameStarted = true;
    startGameBtn.classList.add('hidden');
    startVotingBtn.classList.remove('hidden');
    chatInput.classList.remove('hidden');
    addChatMessage('', data.message, '', true);
    addChatMessage('', '🗳️ İstediğiniz zaman "Oylamayı Başlat" butonuna basabilirsiniz!', '', true);
    startGameTimer(data.timer || 120, data.phase || 'discussion');
});

// Rol atandı
socket.on('role_assigned', (data) => {
    showRole(data);
    
    setTimeout(() => {
        addChatMessage('', 'Tartışma başladı! Konuşarak casusun kim olduğunu anlamaya çalışın.', '', true);
    }, 2000);
});

// Başlatma hatası
socket.on('start_error', (data) => {
    showNotification(data.message, 'error');
});

// Yeni mesaj
socket.on('new_message', (data) => {
    addChatMessage(data.player_name, data.message, data.timestamp);
});

// Oylama başladı
socket.on('voting_started', (data) => {
    addChatMessage('', data.message, '', true);
    showVoting(data.players);
    currentPhase = 'voting';
    startVotingBtn.classList.add('hidden');
});

// Oy kullanıldı
socket.on('vote_submitted', (data) => {
    addChatMessage('', data.message, '', true);
});

// Eşitlik durumu
socket.on('vote_tie', (data) => {
    addChatMessage('', data.message, '', true);
    
    // Oy sonuçlarını göster
    let resultText = '📊 Oy Dağılımı:\n';
    for (const [player, votes] of Object.entries(data.vote_count)) {
        resultText += `${player}: ${votes} oy\n`;
    }
    addChatMessage('', resultText, '', true);
    
    // Yeniden oylama
    setTimeout(() => {
        showVoting(data.tied_players.map(name => ({name})));
        addChatMessage('', '🔄 Eşitlik nedeniyle yeniden oylama!', '', true);
    }, 2000);
});

// Oyun bitti
socket.on('game_ended', (data) => {
    clearInterval(gameTimerInterval);
    gameTimer.classList.add('hidden');
    votingSection.classList.add('hidden');
    
    // Sonuç mesajını göster
    addChatMessage('', data.message, '', true);
    
    // Oy sonuçlarını göster
    let resultText = '📊 Final Oy Dağılımı:\n';
    for (const [player, votes] of Object.entries(data.vote_count)) {
        resultText += `${player}: ${votes} oy\n`;
    }
    addChatMessage('', resultText, '', true);
    addChatMessage('', `🌍 Ülke: ${data.country}`, '', true);
    
    // Modal göster
    setTimeout(() => {
        showGameEndModal(data);
    }, 3000);
});

// Eski oylama sistemi (uyumluluk için)
socket.on('player_voted', (data) => {
    addChatMessage('', data.message, '', true);
});

// Bağlantı kuruldu
socket.on('connect', () => {
    console.log('Oyun sunucusuna bağlanıldı');
    connectionState.isConnected = true;
    connectionState.isReconnecting = false;
    connectionState.reconnectAttempts = 0;
    
    updateConnectionStatus(true);
    startKeepAlive();
    
    // Reconnection ise durumu bildir
    if (connectionState.lastDisconnectTime) {
        const disconnectDuration = Date.now() - connectionState.lastDisconnectTime;
        if (disconnectDuration > 2000) { // 2 saniyeden uzun disconnect
            showNotification('Bağlantı yeniden kuruldu! 🎉', 'success');
        }
        connectionState.lastDisconnectTime = null;
    }
    
    // Oyuncunun adını localStorage'dan al
    const savedPlayerName = localStorage.getItem('playerName');
    if (savedPlayerName) {
        gameState.playerName = savedPlayerName;
        
        // Kaydedilen oyun durumunu yükle
        loadGameState();
        
        // Otomatik olarak odaya katıl
        socket.emit('join_room', {
            room_id: gameState.roomId,
            player_name: savedPlayerName,
            reconnect: true,
            game_state: {
                was_in_game: connectionState.wasGameStarted,
                current_phase: currentPhase
            }
        });
    } else {
        // Eğer kayıtlı isim yoksa ana sayfaya yönlendir
        window.location.href = '/?room=' + gameState.roomId;
    }
});

// Bağlantı koptu
socket.on('disconnect', (reason) => {
    console.log('Bağlantı koptu:', reason);
    connectionState.isConnected = false;
    connectionState.lastDisconnectTime = Date.now();
    
    updateConnectionStatus(false);
    stopKeepAlive();
    
    // Oyun durumunu kaydet
    saveGameState();
    
    // Mobil cihazlarda otomatik reconnect için farklı mesaj
    if (reason === 'transport close' || reason === 'ping timeout') {
        showNotification('Bağlantı koptu. Yeniden bağlanıyor...', 'warning');
    } else {
        showNotification('Sunucu bağlantısı koptu!', 'error');
    }
});

// Reconnect attempt
socket.on('reconnect_attempt', (attemptNumber) => {
    connectionState.isReconnecting = true;
    connectionState.reconnectAttempts = attemptNumber;
    console.log(`Yeniden bağlanma denemesi: ${attemptNumber}`);
    
    if (attemptNumber <= 3) {
        showNotification(`Yeniden bağlanıyor... (${attemptNumber}/10)`, 'info');
    }
});

// Reconnect failed
socket.on('reconnect_failed', () => {
    connectionState.isReconnecting = false;
    showNotification('Bağlantı kurulamadı. Sayfayı yenileyin.', 'error');
    
    // 5 saniye sonra sayfayı yenile
    setTimeout(() => {
        window.location.reload();
    }, 5000);
});

// Ping response
socket.on('pong', () => {
    // Ping başarılı - bağlantı aktif
    console.log('Ping başarılı');
});

// Oyun sıfırlandı
socket.on('game_reset', (data) => {
    console.log('Game reset received:', data);
    
    // Oyun durumunu sıfırla
    gameState.gameStarted = false;
    gameState.myRole = null;
    currentPhase = 'waiting';
    
    // UI elementlerini sıfırla
    roleCard.classList.add('hidden');
    votingSection.classList.add('hidden');
    gameTimer.classList.add('hidden');
    chatInput.classList.add('hidden');
    startVotingBtn.classList.add('hidden');
    
    // Rol göstergesini temizle
    const roleIndicator = document.getElementById('roleIndicator');
    if (roleIndicator) {
        roleIndicator.remove();
    }
    
    // Timer'ı temizle
    if (gameTimerInterval) {
        clearInterval(gameTimerInterval);
        gameTimerInterval = null;
    }
    
    // UI'yi güncelle
    updatePlayersList(data.players);
    
    // Chat'e bilgi mesajı ekle
    addChatMessage('', data.message, '', true);
    addChatMessage('', '🎮 Yeni oyun başlatmaya hazır! Minimum 3 oyuncu gerekli.', '', true);
    
    // Oyun bitirme modalını kapat
    gameEndModal.classList.add('hidden');
    
    // Oyun durumunu localStorage'dan temizle
    localStorage.removeItem('gameState_' + gameState.roomId);
});

// Oda bulunamadı hatası
socket.on('join_error', (data) => {
    console.log('Join error received:', data.message);
    showNotification(data.message, 'error');
    
    // Eğer daha önce bu odada bulunmuşsa (localStorage'da isim varsa) tekrar dene
    const savedPlayerName = localStorage.getItem('playerName');
    const hasRetried = localStorage.getItem('join_retry_' + gameState.roomId);
    
    if (savedPlayerName && !hasRetried && (data.message.includes('Oda bulunamadı') || data.message.includes('kullanılıyor'))) {
        // Sayfa yenileme durumunda tekrar dene
        console.log('Retrying connection for saved player...');
        localStorage.setItem('join_retry_' + gameState.roomId, 'true');
        
        setTimeout(() => {
            socket.emit('join_room', {
                room_id: gameState.roomId,
                player_name: savedPlayerName,
                reconnect: true
            });
        }, 2000);
        
        // 10 saniye sonra retry flag'ini temizle
        setTimeout(() => {
            localStorage.removeItem('join_retry_' + gameState.roomId);
        }, 10000);
    } else {
        // Gerçek hatalar veya retry başarısız olursa anasayfaya yönlendir
        setTimeout(() => {
            localStorage.removeItem('playerName');
            localStorage.removeItem('join_retry_' + gameState.roomId);
            window.location.href = '/';
        }, 4000);
    }
});

// Sayfa yüklendiğinde
window.addEventListener('load', () => {
    // Room code'u göster
    roomCodeEl.textContent = gameState.roomId;
    
    // Focus input
    setTimeout(() => {
        if (messageInput) {
            messageInput.focus();
        }
    }, 1000);
});

// Sayfa kapatılırken oyun durumunu kaydet - ama localStorage'ı temizleme (sayfa yenileme için)
window.addEventListener('beforeunload', () => {
    // Oyun durumunu kaydet ama playerName'i koru (sayfa yenileme için)
    saveGameState();
});

// Paylaş butonu ekle (mobil için)
function shareRoom() {
    const shareData = {
        title: 'Casus Oyunu',
        text: `Casus oyununa katıl! Oda kodu: ${gameState.roomId}`,
        url: window.location.href
    };
    
    if (navigator.share) {
        navigator.share(shareData);
    } else {
        // Fallback: clipboard'a kopyala
        navigator.clipboard.writeText(`Casus oyununa katıl! ${window.location.href}`).then(() => {
            showNotification('Oda linki panoya kopyalandı!', 'success');
        });
    }
}

// Oda koduna tıklayınca kopyala
roomCodeEl.addEventListener('click', () => {
    navigator.clipboard.writeText(gameState.roomId).then(() => {
        showNotification('Oda kodu panoya kopyalandı!', 'success');
    });
});

// Oyuncuların ismini localStorage'a kaydet (diğer sayfalarda kullanmak için)
socket.on('room_joined', (data) => {
    localStorage.setItem('playerName', data.player_name);
});

// Bağlantı durumu göstergesi
function updateConnectionStatus(connected) {
    connectionState.isConnected = connected;
    
    // Header'a bağlantı durumu ekle
    let statusEl = document.querySelector('.connection-status');
    if (!statusEl) {
        statusEl = document.createElement('div');
        statusEl.className = 'connection-status';
        document.querySelector('.game-header').appendChild(statusEl);
    }
    
    if (connected) {
        statusEl.innerHTML = '<span style="color: #4ade80;">🟢 Bağlı</span>';
        statusEl.style.opacity = '0.7';
    } else {
        statusEl.innerHTML = '<span style="color: #ef4444;">🔴 Bağlantı Kopuk</span>';
        statusEl.style.opacity = '1';
    }
}

// Otomatik reconnection için oyun durumunu kaydet
function saveGameState() {
    const gameData = {
        roomId: gameState.roomId,
        playerName: gameState.playerName,
        gameStarted: gameState.gameStarted,
        myRole: gameState.myRole,
        currentPhase: currentPhase,
        timestamp: Date.now()
    };
    localStorage.setItem('gameState_' + gameState.roomId, JSON.stringify(gameData));
}

// Kaydedilen oyun durumunu yükle
function loadGameState() {
    const savedData = localStorage.getItem('gameState_' + gameState.roomId);
    if (savedData) {
        try {
            const gameData = JSON.parse(savedData);
            // 20 dakikadan eski veriler geçersiz (uzun ekran kapatma için)
            if (Date.now() - gameData.timestamp < 20 * 60 * 1000) {
                gameState.gameStarted = gameData.gameStarted;
                gameState.myRole = gameData.myRole;
                currentPhase = gameData.currentPhase;
                connectionState.wasGameStarted = gameData.gameStarted;
                
                // Rol bilgisini hatırla ve gizlenmiş şekilde göster
                if (gameData.myRole && gameData.gameStarted) {
                    setTimeout(() => {
                        hideRole(); // Direkt gizlenmiş şekilde başlat
                    }, 1000);
                }
                
                return true;
            }
        } catch (e) {
            console.error('Game state yüklenirken hata:', e);
        }
    }
    return false;
}

// Keep-alive ping gönder
function startKeepAlive() {
    if (keepAliveInterval) clearInterval(keepAliveInterval);
    
    keepAliveInterval = setInterval(() => {
        if (connectionState.isConnected) {
            socket.emit('ping', { roomId: gameState.roomId });
            console.log('Keep-alive ping sent');
        }
    }, 45000); // 45 saniyede bir ping (daha az sıklık)
}

function stopKeepAlive() {
    if (keepAliveInterval) {
        clearInterval(keepAliveInterval);
        keepAliveInterval = null;
    }
}

// Visibility API - sayfa durumunu izle
function handleVisibilityChange() {
    if (document.hidden) {
        isPageVisible = false;
        console.log('Sayfa arka plana gitti - bağlantı korunuyor');
        
        // Arka planda da bağlantıyı koru, sadece UI güncellemelerini durdur
        // Keep-alive devam etsin (ping gönderimi sürsün)
        
    } else {
        isPageVisible = true;
        console.log('Sayfa ön plana geldi');
        
        // Bağlantıyı kontrol et
        if (!connectionState.isConnected && !connectionState.isReconnecting) {
            console.log('Sayfa geri geldi, bağlantı kopuk - yeniden bağlanmaya çalışıyor...');
            showNotification('Yeniden bağlanıyor...', 'info');
            socket.connect();
        }
        
        // Keep-alive zaten çalışıyor olmalı ama emin olmak için
        if (!keepAliveInterval) {
            startKeepAlive();
        }
    }
}

// Visibility API'yi dinle
if (typeof document.hidden !== "undefined") {
    document.addEventListener("visibilitychange", handleVisibilityChange);
} else if (typeof document.msHidden !== "undefined") {
    document.addEventListener("msvisibilitychange", handleVisibilityChange);
} else if (typeof document.webkitHidden !== "undefined") {
    document.addEventListener("webkitvisibilitychange", handleVisibilityChange);
} 