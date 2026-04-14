import asyncio
import logging
import hashlib
from typing import Set, Optional
from twscrape import API, gather
from twscrape.logger import set_log_level
from .config import config

logger = logging.getLogger("bot.twitter_stream")

class TwitterStream:
    def __init__(self, queue: asyncio.Queue, seen_hashes: Optional[set] = None):
        self.queue = queue
        self.api: Optional[API] = None
        self.target_accounts = config.TWITTER_ACCOUNTS
        self.target_queries = config.TWITTER_SEARCH_QUERIES
        self.poll_interval = config.TWITTER_POLL_INTERVAL
        self.seen_hashes = seen_hashes or set()
        self._running = False

    def _normalize_text(self, text: str) -> str:
        return " ".join(text.lower().split())

    def _get_hash(self, text: str) -> str:
        normalized = self._normalize_text(text)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    async def _scrape_account_tweets(self, username: str, limit: int = 10):
        try:
            tweets = await gather(self.api.user_tweets(username, limit=limit))
            for tweet in tweets:
                yield tweet
        except Exception as e:
            logger.error(f"Error scraping {username}: {e}")

    async def _scrape_search(self, query: str, limit: int = 10):
        try:
            tweets = await gather(self.api.search(query, limit=limit))
            for tweet in tweets:
                yield tweet
        except Exception as e:
            logger.error(f"Error searching {query}: {e}")

    async def _handle_tweet(self, tweet, source_type: str):
        tweet_hash = self._get_hash(tweet.content)
        
        if tweet_hash in self.seen_hashes:
            logger.debug(f"Duplicate tweet skipped: {tweet_hash}")
            return
        
        self.seen_hashes.add(tweet_hash)
        
        payload = {
            "source": f"twitter_{source_type}",
            "text": tweet.content,
            "timestamp": tweet.date.timestamp() if hasattr(tweet, 'date') and tweet.date else asyncio.get_event_loop().time(),
            "chat_title": tweet.user.username if hasattr(tweet, 'user') else source_type,
            "tweet_id": str(tweet.id) if hasattr(tweet, 'id') else None,
            "tweet_url": f"https://x.com/{tweet.user.username}/status/{tweet.id}" if hasattr(tweet, 'id') and hasattr(tweet, 'user') else None,
            "likes": tweet.likes if hasattr(tweet, 'likes') else 0,
            "retweets": tweet.retweets if hasattr(tweet, 'retweets') else 0,
        }
        
        await self.queue.put(payload)

    async def start(self):
        if not self.target_accounts and not self.target_queries:
            logger.warning("No Twitter accounts or queries configured. Twitter stream will not run.")
            return

        self._running = True
        logger.info(f"Twitter stream starting - accounts: {self.target_accounts}, queries: {self.target_queries}")
        
        db_path = "twitter_accounts.db"
        self.api = API(db_path)
        
        if len(self.api.accounts) == 0:
            logger.error("No Twitter accounts configured in twscrape. Run 'twscrape add_accounts' first.")
            return

        await self.api.pool.login_all()
        logger.info("Twitter accounts login successful.")

        while self._running:
            try:
                for username in self.target_accounts:
                    if not self._running:
                        break
                    async for tweet in self._scrape_account_tweets(username, limit=5):
                        await self._handle_tweet(tweet, username)

                for query in self.target_queries:
                    if not self._running:
                        break
                    async for tweet in self._scrape_search(query, limit=5):
                        await self._handle_tweet(tweet, f"search:{query}")

                await asyncio.sleep(self.poll_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Twitter stream error: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)

    async def stop(self):
        self._running = False
        logger.info("Twitter stream stopped.")

def create_twitter_stream(queue: asyncio.Queue, seen_hashes: set = None) -> TwitterStream:
    return TwitterStream(queue, seen_hashes)