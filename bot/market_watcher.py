import asyncio
import json
import logging
import websockets
from typing import List, Dict, Optional
from .config import config

logger = logging.getLogger("bot.market_watcher")

class MarketWatcher:
    def __init__(self):
        self.ws_url = config.LIMITLESS_WS_URL
        self.active_markets = []
        # State: {market_slug: {"YES": {"bid": 0, "ask": 0}, "NO": {"bid": 0, "ask": 0}}}
        self.orderbooks: Dict[str, Dict] = {}

    async def refresh_markets(self):
        """
        Fetches active markets from Limitless API.
        """
        # Placeholder for real API call
        self.active_markets = [
            {"id": "eth-price-hourly-2500", "slug": "eth-price-hourly-2500", "question": "Will ETH be above $2500?"},
            {"id": "btc-etf-daily", "slug": "btc-etf-daily", "question": "Will BTC ETF inflows exceed $500M?"}
        ]
        for m in self.active_markets:
            if m['slug'] not in self.orderbooks:
                self.orderbooks[m['slug']] = {
                    "YES": {"bid": 0.0, "ask": 0.0},
                    "NO": {"bid": 0.0, "ask": 0.0}
                }
        logger.info(f"Refreshed {len(self.active_markets)} markets.")

    async def start(self):
        """
        Connects to Limitless WebSocket and listens for orderbook updates.
        """
        while True:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    # Subscribe to all active markets
                    for market in self.active_markets:
                        subscribe_msg = {
                            "type": "subscribe",
                            "channel": "orderbook",
                            "market": market['slug']
                        }
                        await ws.send(json.dumps(subscribe_msg))
                    
                    logger.info("Subscribed to market orderbooks.")

                    async for message in ws:
                        data = json.loads(message)
                        if data.get("type") == "orderbook_update":
                            self._update_orderbook(data)
            except Exception as e:
                logger.error(f"WebSocket error: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)

    def _update_orderbook(self, data: Dict):
        slug = data.get("market")
        outcome = data.get("outcome") # "YES" or "NO"
        bids = data.get("bids", [])
        asks = data.get("asks", [])

        if slug in self.orderbooks and outcome in self.orderbooks[slug]:
            best_bid = float(bids[0][0]) if bids else 0.0
            best_ask = float(asks[0][0]) if asks else 0.0
            self.orderbooks[slug][outcome] = {"bid": best_bid, "ask": best_ask}

    def get_best_quote(self, slug: str, outcome: str) -> Dict[str, float]:
        return self.orderbooks.get(slug, {}).get(outcome, {"bid": 0.0, "ask": 0.0})

    def get_relevant_market(self, headline: str) -> Optional[Dict]:
        headline_lower = headline.lower()
        for market in self.active_markets:
            if any(word in headline_lower for word in market['slug'].split('-')):
                return market
        return None

market_watcher = MarketWatcher()
