import asyncio
import logging
from typing import List, Dict, Any, Optional
from pyrogram import Client, filters, handlers
from pyrogram.types import Message
from .config import config

# Configure logging for the stream
logger = logging.getLogger("bot.news_stream")

class NewsStream:
    def __init__(self, queue: asyncio.Queue):
        self.queue = queue
        self.client: Optional[Client] = None
        self.target_channels = config.TELEGRAM_CHANNELS

    async def _handle_message(self, client: Client, message: Message):
        """
        Extracts text and timestamp and pushes to the processing queue.
        """
        if not message.text:
            return

        payload = {
            "source": str(message.chat.id),
            "text": message.text,
            "timestamp": message.date.timestamp() if message.date else asyncio.get_event_loop().time(),
            "chat_title": message.chat.title or "Unknown"
        }
        
        await self.queue.put(payload)

    async def start(self):
        """
        Initializes the Pyrogram client and starts listening.
        """
        if not config.TELEGRAM_API_ID or not config.TELEGRAM_API_HASH:
            raise ValueError("TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in config")

        self.client = Client(
            "bot_user_session",
            api_id=int(config.TELEGRAM_API_ID),
            api_hash=config.TELEGRAM_API_HASH,
            sleep_threshold=60
        )

        # Add handler for specific channels if provided, otherwise all text messages
        channel_filter = filters.chat(self.target_channels) if self.target_channels else filters.private | filters.group | filters.channel
        
        self.client.add_handler(
            handlers.MessageHandler(
                self._handle_message,
                filters=filters.text & channel_filter
            )
        )

        try:
            await self.client.start()
            logger.info("Telegram NewsStream started successfully.")
            # Keep the client running
            await asyncio.Event().wait()
        except Exception as e:
            logger.error(f"Error in NewsStream: {e}")
            raise
        finally:
            if self.client:
                await self.client.stop()

    async def stop(self):
        if self.client:
            await self.client.stop()
