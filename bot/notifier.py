"""
Asynchronous Push Notification Layer for Limitless MEV Trading Bot.

Supports Telegram Bot API and Discord Webhooks for real-time alerts.
"""

import asyncio
import logging
from typing import Literal, Optional

import aiohttp
from pydantic import BaseModel

from .config import config

logger = logging.getLogger("bot.notifier")


class Notifier(BaseModel):
    """Asynchronous notifier using aiohttp for non-blocking HTTP POST requests."""

    model_config = {"extra": "ignore"}

    _session: Optional[aiohttp.ClientSession] = None
    _provider: Literal["telegram", "discord", "none"] = "none"

    def __init__(self) -> None:
        super().__init__()
        self._resolve_provider()

    def _resolve_provider(self) -> None:
        """Determine which notification provider is configured."""
        if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID:
            self._provider = "telegram"
            logger.info("Notifier initialized: Telegram bot")
        elif config.DISCORD_WEBHOOK_URL:
            self._provider = "discord"
            logger.info("Notifier initialized: Discord webhook")
        else:
            self._provider = "none"
            logger.warning("Notifier disabled: No TELEGRAM_BOT_TOKEN or DISCORD_WEBHOOK_URL configured")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )
        return self._session

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _send_telegram(self, text: str) -> bool:
        """Send message via Telegram Bot API."""
        if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
            return False

        url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        }

        try:
            session = await self._get_session()
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    logger.debug(f"Telegram notification sent: {text[:50]}...")
                    return True
                else:
                    logger.error(f"Telegram API error: {resp.status} {await resp.text()}")
                    return False
        except asyncio.TimeoutError:
            logger.error("Telegram notification timeout")
            return False
        except Exception as e:
            logger.error(f"Telegram notification failed: {e}")
            return False

    async def _send_discord(self, text: str) -> bool:
        """Send message via Discord webhook."""
        if not config.DISCORD_WEBHOOK_URL:
            return False

        payload = {"content": text}

        try:
            session = await self._get_session()
            async with session.post(config.DISCORD_WEBHOOK_URL, json=payload) as resp:
                if resp.status in (200, 204):
                    logger.debug(f"Discord notification sent: {text[:50]}...")
                    return True
                else:
                    logger.error(f"Discord webhook error: {resp.status} {await resp.text()}")
                    return False
        except asyncio.TimeoutError:
            logger.error("Discord notification timeout")
            return False
        except Exception as e:
            logger.error(f"Discord notification failed: {e}")
            return False

    async def _send(self, text: str) -> bool:
        """Send notification via configured provider (fail-safe)."""
        if self._provider == "none":
            return True  # Not configured, count as success

        if self._provider == "telegram":
            return await self._send_telegram(text)
        elif self._provider == "discord":
            return await self._send_discord(text)

        return False

    async def alert_trade(
        self,
        market: str,
        side: str,
        size: float,
        price: float
    ) -> None:
        """
        Notify on successful Limitless CLOB trade fill.

        Args:
            market: Market identifier (e.g., "ETH-2500")
            side: "YES" or "NO"
            size: Order size in USDC
            price: Fill price
        """
        text = (
            f"🟢 **TRADE FILLED**\n"
            f"Market: **{market}**\n"
            f"Side: **{side}** | Size: **${size:.2f}** @ **{price:.4f}**"
        )
        await self._send(text)

    async def alert_signal(
        self,
        market: str,
        materiality: float,
        price: float,
        threshold: float
    ) -> None:
        """
        Notify on high materiality signal with insufficient edge.

        Args:
            market: Market identifier
            materiality: Gemini materiality score (0.0-1.0)
            price: Current orderbook price
            threshold: Required edge threshold
        """
        text = (
            f"🟡 **ALPHA SIGNAL**\n"
            f"Market: **{market}**\n"
            f"Materiality: **{materiality:.2f}** | Price: **{price:.4f}**\n"
            f"Edge insufficient (need > {threshold:.4f})"
        )
        await self._send(text)

    async def alert_error(
        self,
        component: str,
        error_msg: str,
        critical: bool = False
    ) -> None:
        """
        Notify on system error or failure.

        Args:
            component: Source component (e.g., "market_watcher", "twscrape")
            error_msg: Error description
            critical: If True, marks as critical alert
        """
        emoji = "🚨" if critical else "🔴"
        text = (
            f"{emoji} **ERROR** {'(CRITICAL)' if critical else ''}\n"
            f"Component: **{component}**\n"
            f"Error: {error_msg}"
        )
        await self._send(text)


notifier = Notifier()