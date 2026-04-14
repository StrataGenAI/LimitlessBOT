import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Telegram Userbot
    TELEGRAM_API_ID: Optional[str] = None
    TELEGRAM_API_HASH: Optional[str] = None
    TELEGRAM_CHANNELS: list[str] = [] # List of channel IDs or usernames
    
    # Twitter/X Accounts (usernames to scrape, without @)
    TWITTER_ACCOUNTS: list[str] = []
    TWITTER_SEARCH_QUERIES: list[str] = [] # Keywords to search (e.g., "BTC", "#ETH")
    TWITTER_POLL_INTERVAL: int = 30 # Seconds between polls
    
    # Gemini API
    GEMINI_API_KEY: str = ""
    
    # Limitless & Web3
    LIMITLESS_API_KEY: Optional[str] = None
    PRIVATE_KEY: str = ""
    BASE_RPC_URL: str = "https://mainnet.base.org"
    LIMITLESS_API_BASE: str = "https://api.limitless.exchange"
    LIMITLESS_WS_URL: str = "wss://ws.limitless.exchange"
    LIMITLESS_VENUE_CONTRACT: str = os.getenv("LIMITLESS_VENUE_CONTRACT", "0x0000000000000000000000000000000000000000") # Replace with actual contract
    CHAIN_ID: int = 8453 # Base Mainnet
    
    # Trading Constraints
    MAX_BET_USD: float = 50.0
    DAILY_LOSS_LIMIT: float = 200.0
    MATERIALITY_THRESHOLD: float = 0.8
    EDGE_THRESHOLD: float = 0.05
    
    # Push Notifications
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    DISCORD_WEBHOOK_URL: Optional[str] = None
    
    # Operational
    DRY_RUN: bool = True
    DB_PATH: str = "bot_data.db"

config = Config()
