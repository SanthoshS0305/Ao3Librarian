"""Configuration management for AO3 Discord RSS Tracker Bot."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Bot configuration from environment variables."""
    
    # Discord Bot Token
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    if not DISCORD_TOKEN:
        raise ValueError("DISCORD_TOKEN environment variable is required")
    
    # PostgreSQL Database Configuration
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "ao3_tracker")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    
    @property
    def database_url(self) -> str:
        """Get PostgreSQL connection URL."""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # Bot Configuration
    COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "!")
    POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "3600"))  # Default: 1 hour in seconds
    
    # Configurable Limits
    MAX_SUBSCRIPTIONS_PER_CHANNEL = int(os.getenv("MAX_SUBSCRIPTIONS_PER_CHANNEL", "50"))
    MAX_FEEDS_GLOBAL = int(os.getenv("MAX_FEEDS_GLOBAL", "1000"))
    COMMAND_COOLDOWN_SECONDS = int(os.getenv("COMMAND_COOLDOWN_SECONDS", "5"))
    FEED_FETCH_TIMEOUT = int(os.getenv("FEED_FETCH_TIMEOUT", "30"))
    CIRCUIT_BREAKER_FAILURE_THRESHOLD = int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "3"))
    
    # Discord Intents
    MESSAGE_CONTENT_INTENT = os.getenv("MESSAGE_CONTENT_INTENT", "true").lower() == "true"


config = Config()
