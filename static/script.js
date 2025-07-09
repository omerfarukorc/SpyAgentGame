// Socket.IO bağlantısı - uzun süreli mobil optimizasyonu ile
const socket = io({
    // Mobil cihazlar için optimizasyon
    transports: ['websocket', 'polling'],
    upgrade: true,
    rememberUpgrade: true,
    // Reconnection ayarları - uzun süreli için
    reconnection: true,
    reconnectionDelay: 2000,
    reconnectionDelayMax: 10000,
    maxReconnectionAttempts: 15,
    timeout: 30000,
    // Keep-alive - uzun süreli için optimize
    pingTimeout: 120000, // 2 dakika
    pingInterval: 60000   // 1 dakika
});

// Bağlantı durumu yönetimi
let connectionState = {
    isConnected: false,
    reconnectAttempts: 0,
    isReconnecting: false
};

// Visibility API için değişkenler
let isPageVisible = true;

// DOM elementleri
const createRoomForm = document.getElementById('createRoomForm');
const joinRoomForm = document.getElementById('joinRoomForm');
const notification = document.getElementById('notification');

// Notification gösterme fonksiyonu
function showNotification(message, type = 'info') {
    notification.textContent = message;
    notification.className = `notification ${type} show`;
    
    setTimeout(() => {
        notification.className = 'notification';
    }, 4000);
}

// URL'den room ID parametresini alma
function getUrlParameter(name) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(name);
}

// Oda oluşturma form işleyicisi
createRoomForm.addEventListener('submit', (e) => {
    e.preventDefault();
    
    const playerName = document.getElementById('playerName').value.trim();
    const roomName = document.getElementById('roomName').value.trim();
    const spyCount = parseInt(document.getElementById('spyCount').value);
    
    if (!playerName) {
        showNotification('Lütfen adınızı girin!', 'error');
        return;
    }
    
    if (spyCount < 1 || spyCount > 3) {
        showNotification('Hain sayısı 1-3 arasında olmalıdır!', 'error');
        return;
    }
    
    // Oda oluşturma isteği gönder
    socket.emit('create_room', {
        player_name: playerName,
        room_name: roomName || `${playerName}'in Odası`,
        spy_count: spyCount
    });
});

// Odaya katılma form işleyicisi
joinRoomForm.addEventListener('submit', (e) => {
    e.preventDefault();
    
    const playerName = document.getElementById('joinPlayerName').value.trim();
    const roomId = document.getElementById('joinRoomId').value.trim().toUpperCase();
    
    if (!playerName) {
        showNotification('Lütfen adınızı girin!', 'error');
        return;
    }
    
    if (!roomId) {
        showNotification('Lütfen oda kodunu girin!', 'error');
        return;
    }
    
    // Odaya katılma isteği gönder
    socket.emit('join_room', {
        player_name: playerName,
        room_id: roomId
    });
});

// Socket.IO event listeners

// Oda oluşturuldu
socket.on('room_created', (data) => {
    localStorage.setItem('playerName', data.player_name);
    localStorage.setItem('isCreator', data.is_creator);
    showNotification(`Oda oluşturuldu! Kod: ${data.room_id}`, 'success');
    
    // WhatsApp paylaşım özelliği
    const whatsappText = `🕵️ Casus Oyununa Katıl!\n\nOda Kodu: ${data.room_id}\nLink: ${window.location.origin}/game/${data.room_id}\n\n${data.spy_count} hain var, çok eğlenceli olacak! 🎮`;
    
    // WhatsApp butonunu göster
    setTimeout(() => {
        const shareBtn = document.createElement('button');
        shareBtn.className = 'btn btn-whatsapp';
        shareBtn.innerHTML = '📱 WhatsApp\'ta Paylaş';
        shareBtn.onclick = () => {
            window.open(`https://wa.me/?text=${encodeURIComponent(whatsappText)}`, '_blank');
        };
        
        // Notification alanına ekle
        const notificationArea = document.querySelector('.notification');
        if (notificationArea) {
            notificationArea.appendChild(shareBtn);
        }
    }, 1000);
    
    // Oyun sayfasına yönlendir
    setTimeout(() => {
        window.location.href = `/game/${data.room_id}`;
    }, 3000);
});

// Odaya katılındı
socket.on('room_joined', (data) => {
    localStorage.setItem('playerName', data.player_name);
    showNotification(`${data.room_name} odasına katıldınız!`, 'success');
    
    // Oyun sayfasına yönlendir
    setTimeout(() => {
        window.location.href = `/game/${data.room_id}`;
    }, 1500);
});

// Katılma hatası
socket.on('join_error', (data) => {
    showNotification(data.message, 'error');
});

// Bağlantı kuruldu
socket.on('connect', () => {
    console.log('Ana sayfa sunucusuna bağlanıldı');
    connectionState.isConnected = true;
    connectionState.isReconnecting = false;
    connectionState.reconnectAttempts = 0;
    
    updateConnectionStatus(true);
    
    // Reconnection ise bildir
    if (connectionState.reconnectAttempts > 0) {
        showNotification('Bağlantı yeniden kuruldu! 🎉', 'success');
    }
});

// Bağlantı koptu
socket.on('disconnect', (reason) => {
    console.log('Bağlantı koptu:', reason);
    connectionState.isConnected = false;
    updateConnectionStatus(false);
    
    // Mobil cihazlarda otomatik reconnect için farklı mesaj
    if (reason === 'transport close' || reason === 'ping timeout') {
        showNotification('Bağlantı koptu. Yeniden bağlanıyor...', 'warning');
    } else {
        showNotification('Sunucu bağlantısı koptu. Tekrar deneyin.', 'error');
    }
});

// Reconnect attempt
socket.on('reconnect_attempt', (attemptNumber) => {
    connectionState.isReconnecting = true;
    connectionState.reconnectAttempts = attemptNumber;
    console.log(`Yeniden bağlanma denemesi: ${attemptNumber}`);
    
    if (attemptNumber <= 3) {
        showNotification(`Yeniden bağlanıyor... (${attemptNumber}/5)`, 'info');
    }
});

// Reconnect failed
socket.on('reconnect_failed', () => {
    connectionState.isReconnecting = false;
    showNotification('Bağlantı kurulamadı. Sayfayı yenileyin.', 'error');
});

// Enter tuşu ile form gönderme
document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        const activeElement = document.activeElement;
        
        // Hangi form alanındaysak o formu gönder
        if (activeElement.closest('#createRoomForm')) {
            createRoomForm.dispatchEvent(new Event('submit'));
        } else if (activeElement.closest('#joinRoomForm')) {
            joinRoomForm.dispatchEvent(new Event('submit'));
        }
    }
});

// Sayfa yüklendiğinde URL'den room ID kontrol et
window.addEventListener('load', () => {
    const roomId = getUrlParameter('room');
    if (roomId) {
        document.getElementById('joinRoomId').value = roomId.toUpperCase();
    }
});

// Input alanlarını büyük harfe çevir (oda kodu için)
document.getElementById('joinRoomId').addEventListener('input', (e) => {
    e.target.value = e.target.value.toUpperCase();
});

// Auto-focus first input on page load
window.addEventListener('load', () => {
    const firstInput = document.getElementById('playerName');
    if (firstInput) {
        firstInput.focus();
    }
});

// Bağlantı durumu göstergesi
function updateConnectionStatus(connected) {
    connectionState.isConnected = connected;
    
    // Header'a bağlantı durumu ekle
    let statusEl = document.querySelector('.connection-status');
    if (!statusEl) {
        statusEl = document.createElement('div');
        statusEl.className = 'connection-status';
        statusEl.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            padding: 5px 10px;
            border-radius: 20px;
            background: rgba(0,0,0,0.8);
            color: white;
            font-size: 12px;
            z-index: 1000;
            transition: opacity 0.3s ease;
        `;
        document.body.appendChild(statusEl);
    }
    
    if (connected) {
        statusEl.innerHTML = '🟢 Bağlı';
        statusEl.style.opacity = '0.5';
    } else {
        statusEl.innerHTML = '🔴 Bağlantı Kopuk';
        statusEl.style.opacity = '1';
    }
}

// Visibility API - sayfa durumunu izle
function handleVisibilityChange() {
    if (document.hidden) {
        isPageVisible = false;
        console.log('Ana sayfa arka plana gitti');
    } else {
        isPageVisible = true;
        console.log('Ana sayfa ön plana geldi');
        
        // Bağlantıyı kontrol et
        if (!connectionState.isConnected && !connectionState.isReconnecting) {
            console.log('Sayfa geri geldi, bağlantı kopuk - yeniden bağlanmaya çalışıyor...');
            socket.connect();
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