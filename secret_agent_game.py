import smtplib
import random
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SecretAgentGame:
    def __init__(self, player_list, country_list):
        """
        Initializer method for Secret Agent Game.
        
        :param player_list: List of email addresses
        :param country_list: List of country names
        """
        self.players = player_list
        self.countries = country_list
        self.selected_country = random.choice(self.countries)
        self.agent_index = random.randint(0, len(self.players) - 1)

    def send_email(self, recipient, subject, message):
        """
        Email sending function.
        
        :param recipient: Recipient email address
        :param subject: Email subject
        :param message: Email content
        """
        fromaddr = os.getenv('SMTP_EMAIL')
        toaddr = recipient
        
        msg = MIMEMultipart()
        msg['From'] = fromaddr
        msg['To'] = toaddr
        msg['Subject'] = subject
        
        msg.attach(MIMEText(message, 'plain'))
        
        try:
            # Email server settings
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(fromaddr, os.getenv('SMTP_PASSWORD'))
            
            text = msg.as_string()
            server.sendmail(fromaddr, toaddr, text)
            server.quit()
            
            print(f"Email successfully sent to {recipient}.")
        
        except Exception as e:
            print(f"Email sending error: {e}")

    def start_game(self):
        """
        Method to start the game and send emails to players.
        """
        for i, player in enumerate(self.players):
            if i == self.agent_index:
                message = "🕵️ You are the AGENT! No country information."
            else:
                message = f"🌍 Your Country: {self.selected_country}"
            
            self.send_email(player, "🎲 Secret Agent Game Notification", message)

def main():
    # Player list and country list
    players = [
        "player1@example.com", 
        "player2@example.com", 
        "player3@example.com", 
        "player4@example.com"
    ]
    
    countries = [
        "United States", "China", "Japan", "Germany", "United Kingdom", 
        "France", "Italy", "Canada", "Russia", "Brazil", "India", "Mexico", 
        "Australia", "Spain", "Netherlands", "Switzerland", "South Korea", "Turkey", 
        "Saudi Arabia", "Sweden", "Argentina", "Norway", "Belgium", "Denmark", 
        "Israel", "South Africa", "Indonesia", "Poland", "Malaysia", "Singapore", 
        "Ireland", "New Zealand", "Portugal", "Czech Republic", "Austria", 
        "Finland", "Greece", "Hungary", "Thailand", "Philippines", "Egypt"
    ]
    
    game = SecretAgentGame(players, countries)
    game.start_game()

if __name__ == "__main__":
    main()