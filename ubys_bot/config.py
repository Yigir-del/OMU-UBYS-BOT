"""Configuration management for UBYS Bot."""

import os
import json
from typing import Dict, List

# Define file paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "bot_settings.json")
USERS_FILE = os.path.join(BASE_DIR, "users_config.json")

# Default values
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""
SESSION_TIMEOUT = 1800
REQUEST_DELAY = 60
TELEGRAM_ENABLED = True
AUTO_SURVEY = False

def load_settings():
    """Load settings from bot_settings.json."""
    global TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, REQUEST_DELAY, SESSION_TIMEOUT, TELEGRAM_ENABLED, AUTO_SURVEY
    
    # Try environment variables first
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
    
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                if not TELEGRAM_BOT_TOKEN:
                    TELEGRAM_BOT_TOKEN = settings.get("telegram_token", "")
                if not TELEGRAM_CHAT_ID:
                    TELEGRAM_CHAT_ID = settings.get("telegram_chat_id", "")
                
                REQUEST_DELAY = settings.get("request_delay", REQUEST_DELAY)
                SESSION_TIMEOUT = settings.get("session_timeout", SESSION_TIMEOUT)
                TELEGRAM_ENABLED = settings.get("telegram_enabled", TELEGRAM_ENABLED)
                AUTO_SURVEY = settings.get("auto_survey", AUTO_SURVEY)
        except Exception as e:
            print(f"Settings could not be loaded: {e}")

# Initial load
load_settings()

# UBYS Configuration
UBYS_BASE_URL = "https://ubys.omu.edu.tr/"
UBYS_LOGIN_URL = f"{UBYS_BASE_URL}Account/Login"

# User Configuration
USER_LIST: List[Dict[str, str]] = []

def load_users():
    """Load users from users_config.json or environment."""
    users = []
    
    # Try JSON file first
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                users = json.load(f)
                if isinstance(users, list):
                    return users
        except Exception:
            pass
            
    # Fallback to environment
    users_env = os.getenv("UBYS_USERS", "")
    if users_env:
        for user_data in users_env.split(","):
            parts = user_data.strip().split(":")
            if len(parts) == 3:
                users.append({
                    "name": parts[0],
                    "password": parts[1],
                    "sapid": parts[2]
                })
    return users

# Alias for backward compatibility
load_users_from_env = load_users

# Update USER_LIST
USER_LIST = load_users()
