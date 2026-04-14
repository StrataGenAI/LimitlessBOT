import aiosqlite
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from .config import config

class BotLogger:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_text_hash(self, text: str) -> str:
        normalized = " ".join(text.lower().split())
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    async def initialize(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    text_hash TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    source_channel_id TEXT,
                    source_type TEXT DEFAULT 'TELEGRAM'
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS classifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER,
                    latency_ms INTEGER,
                    market_condition TEXT,
                    direction TEXT,
                    materiality REAL,
                    confidence REAL,
                    reasoning TEXT,
                    FOREIGN KEY(event_id) REFERENCES events(id)
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    classification_id INTEGER,
                    order_id TEXT,
                    size REAL,
                    price REAL,
                    outcome TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(classification_id) REFERENCES classifications(id)
                )
            ''')
            await db.commit()

    async def is_duplicate(self, text: str, window_minutes: int = 5) -> bool:
        text_hash = self._get_text_hash(text)
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                '''SELECT COUNT(*) FROM events 
                   WHERE text_hash = ? 
                   AND timestamp > datetime('now', '-' || ? || ' minutes')''',
                (text_hash, window_minutes)
            )
            result = await cursor.fetchone()
            return result[0] > 0

    async def log_event(self, text: str, source_channel_id: Optional[str] = None, source_type: str = "TELEGRAM") -> int:
        text_hash = self._get_text_hash(text)
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO events (text, text_hash, source_channel_id, source_type) VALUES (?, ?, ?, ?)",
                (text, text_hash, source_channel_id, source_type)
            )
            await db.commit()
            return cursor.lastrowid

    async def log_classification(self, event_id: int, latency_ms: int, market_condition: str, 
                                direction: str, materiality: float, confidence: float, reasoning: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                '''INSERT INTO classifications 
                   (event_id, latency_ms, market_condition, direction, materiality, confidence, reasoning) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (event_id, latency_ms, market_condition, direction, materiality, confidence, reasoning)
            )
            await db.commit()
            return cursor.lastrowid

    async def log_trade(self, classification_id: int, order_id: str, size: float, price: float, outcome: Optional[str] = None) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                '''INSERT INTO trades (classification_id, order_id, size, price, outcome) 
                   VALUES (?, ?, ?, ?, ?)''',
                (classification_id, order_id, size, price, outcome)
            )
            await db.commit()
            return cursor.lastrowid

logger = BotLogger(config.DB_PATH)
