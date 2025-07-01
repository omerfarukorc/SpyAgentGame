# 🕵️ Spy Agent Game

A real-time multiplayer web game where you try to find the spy among your friends!

## 🎮 How to Play

1. **Create a room** or **join an existing one** (3-8 players)
2. One player is randomly selected as the **spy**
3. All other players see the same **country name**, but the spy doesn't know which country it is
4. **Discuss** and try to figure out who the spy is without revealing the country
5. **Vote** for who you think is the spy!

**Goal:** 
- **Citizens:** Find and vote out the spy
- **Spy:** Avoid detection and try to guess the country

## 🚀 Live Demo

**Play now:** [spygame.up.railway.app](https://spygame.up.railway.app)

## 🛠️ Technologies Used

- **Backend:** Python Flask + Socket.IO
- **Frontend:** Vanilla JavaScript + CSS3
- **Real-time communication:** WebSockets
- **Deployment:** Railway

## 📱 Features

- Real-time chat and voting
- Mobile-friendly responsive design
- Automatic reconnection
- Turkish interface
- 70+ countries database

## 🔧 Local Development

```bash
git clone https://github.com/omerfarukorc/SpyAgentGame.git
cd SpyAgentGame
pip install -r requirements.txt
python app.py
```

Open `http://localhost:5000` in your browser.

---

Made by [Ömer Faruk](https://github.com/omerfarukorc)

