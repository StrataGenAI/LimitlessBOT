import aiosqlite
import json
from datetime import datetime
from typing import Optional, Dict, Any
from .config import config

class BotLogger:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def initialize(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    source_channel_id TEXT
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

    async def log_event(self, text: str, source_channel_id: Optional[str] = None) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO events (text, source_channel_id) VALUES (?, ?)",
                (text, source_channel_id)
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
