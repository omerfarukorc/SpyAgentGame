# 🕵️ Secret Agent Game

## Overview
A multiplayer secret agent game implemented in Python that randomly assigns countries and selects a secret agent among players, communicating game details via email.

## 🌟 Game Mechanics
- Randomly selects a country for most players
- Designates one player as the secret agent without country information
- Sends personalized email notifications to each player
- Supports customizable player and country lists

## 🚀 Features
- Object-oriented game design
- Secure email sending with environment variable protection
- Error handling for email transmission
- Emoji-enhanced game messages
- Easily configurable player and country lists

## 📋 Prerequisites
- Python 3.7+
- `python-dotenv` library

## 🔧 Installation

1. Clone the repository
```bash
git clone https://github.com/yourusername/secret-agent-game.git
cd secret-agent-game
```

2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

3. Install required dependencies
```bash
pip install python-dotenv
```

4. Configure Environment Variables
Create a `.env` file in the project root with:
```
SMTP_EMAIL=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

## 🔐 Gmail App Password Setup
1. Enable 2-Step Verification in your Google Account
2. Go to Security > App Passwords
3. Generate a new App Password for your application

## 🎲 How to Play
1. Modify `oyuncular` list with player email addresses
2. Customize `ulkeler` list with country names
3. Run the script to start the game

## 🛡️ Security Notes
- Never commit `.env` file to version control
- Use App Passwords instead of main account password
- Rotate App Passwords periodically

## 📝 Customization
- Add/remove players in the `oyuncular` list
- Expand country list in the `ulkeler` list
- Modify email templates as needed

## 🤝 Contributing
1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📜 License
Distributed under the MIT License. See `LICENSE` for more information.

## 📞 Contact
Your Name - your.email@example.com

Project Link: [https://github.com/yourusername/secret-agent-game](https://github.com/yourusername/secret-agent-game)