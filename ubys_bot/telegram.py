"""Telegram API integration for sending notifications."""

import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Handle Telegram bot notifications."""

    def __init__(self, token: str, chat_id: str):
        """Initialize Telegram notifier.
        
        Args:
            token: Telegram bot token.
            chat_id: Chat ID to send messages to.
        """
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}/sendMessage"

    def send_message(self, message: str) -> bool:
        """Telegram bot ile mesaj gönder (optional).
        
        Args:
            message: Gönderilecek metin mesajı.
            
        Returns:
            True: Başarılı, False: Başarısız
        """
        # Token ve Chat ID boşsa atla (optional)
        if not self.token or not self.chat_id:
            logger.debug("Telegram token veya chat_id boş - atlanıyor")
            return False
            
        try:
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(self.base_url, json=payload, timeout=5)
            response.raise_for_status()
            logger.info("Telegram'a mesaj başarıyla gönderildi.")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Telegram mesajı gönderilemedi: {e}")
            return False


# Legacy function wrappers for backward compatibility
def data(token: str, chat_id: str, message: str) -> bool:
    """Send data message via Telegram.
    
    Args:
        token: Telegram bot token.
        chat_id: Chat ID to send message to.
        message: Message text.
        
    Returns:
        True if successful, False otherwise.
    """
    notifier = TelegramNotifier(token, chat_id)
    return notifier.send_message(message)


def fill(token: str, chat_id: str, message: str) -> bool:
    """Send fill message via Telegram.
    
    Args:
        token: Telegram bot token.
        chat_id: Chat ID to send message to.
        message: Message text.
        
    Returns:
        True if successful, False otherwise.
    """
    notifier = TelegramNotifier(token, chat_id)
    return notifier.send_message(message)
    

