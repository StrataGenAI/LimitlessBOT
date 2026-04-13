import asyncio
import click
import logging
import signal
from .config import config
from .news_stream import NewsStream
from .market_watcher import market_watcher
from .classifier import classifier
from .executor import executor
from .logger import logger
from .backtester import backtester

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
sys_logger = logging.getLogger("bot.orchestrator")

async def process_news_worker(worker_id: int, queue: asyncio.Queue):
    """
    Worker task that pulls news from the queue and processes it.
    """
    sys_logger.info(f"Worker {worker_id} started.")
    while True:
        payload = await queue.get()
        source = payload["source"]
        headline = payload["text"]
        
        try:
            # 1. Find relevant market
            market = market_watcher.get_relevant_market(headline)
            if not market:
                sys_logger.debug(f"No relevant market found for: {headline}")
                continue

            sys_logger.info(f"Analyzing market: {market['question']}")

            # 2. Classify with LLM
            analysis = await classifier.classify_event(market['question'], headline)
            confidence = analysis.get('confidence_in_parse', 0.0)
            materiality = analysis.get('materiality', 0.0)
            
            sys_logger.info(f"Analysis: {analysis['direction']} (Mat: {materiality}, Conf: {confidence})")

            # 3. Decision Logic
            trade_executed = False
            trade_details = None
            price_paid = 0.0
            
            # Thresholds: Materiality > 0.8 (from config) and Confidence > 0.6
            if (analysis['direction'] in ['YES', 'NO'] and 
                materiality >= config.MATERIALITY_THRESHOLD and 
                confidence >= 0.6):
                
                # Check Market Watcher for Price Edge
                quote = market_watcher.get_best_quote(market['slug'], analysis['direction'])
                market_price = quote['ask']
                
                if market_price > 0:
                    # Edge = Perceived Probability (Materiality) - Market Price
                    edge = materiality - market_price
                    
                    if edge >= config.EDGE_THRESHOLD:
                        sys_logger.info(f"Edge found: {edge:.4f}. Executing trade...")
                        trade_details = await executor.execute_trade(
                            market['id'], 
                            analysis['direction'], 
                            materiality
                        )
                        trade_executed = True
                        price_paid = market_price
                    else:
                        sys_logger.info(f"Insufficient edge: {edge:.4f} < {config.EDGE_THRESHOLD}")
                else:
                    sys_logger.warning(f"No liquidity found for {market['slug']} {analysis['direction']}")
            else:
                sys_logger.info("Thresholds not met. Skipping trade.")

            # 4. Log to SQLite
            event_id = await logger.log_event(text=headline, source_channel_id=source)
            
            classification_id = await logger.log_classification(
                event_id=event_id,
                latency_ms=analysis['latency_ms'],
                market_condition=market['question'],
                direction=analysis['direction'],
                materiality=materiality,
                confidence=confidence,
                reasoning=analysis['reasoning']
            )

            if trade_executed:
                await logger.log_trade(
                    classification_id=classification_id,
                    order_id=trade_details.get('tx_hash', 'unknown'),
                    size=config.MAX_BET_USD * materiality,
                    price=price_paid,
                    outcome=None
                )
        except Exception as e:
            sys_logger.error(f"Error in worker {worker_id}: {e}", exc_info=True)
        finally:
            queue.task_done()

@click.group()
def cli():
    pass

@cli.command()
@click.option('--live', is_flag=True, help="Run in live mode (requires API keys)")
@click.option('--workers', default=3, help="Number of concurrent processing workers")
def watch(live, workers):
    """Start the news watcher and trading pipeline."""
    if live:
        config.DRY_RUN = False
        sys_logger.warning("!!! RUNNING IN LIVE MODE !!! Real funds may be used.")
    else:
        sys_logger.info("Running in DRY RUN mode.")

    async def run_pipeline():
        # Initialize async logger
        await logger.initialize()
        
        # Initial market refresh
        await market_watcher.refresh_markets()
        
        # Create processing queue
        queue = asyncio.Queue()
        
        # Start worker pool
        worker_tasks = []
        for i in range(workers):
            task = asyncio.create_task(process_news_worker(i, queue))
            worker_tasks.append(task)
        
        # Start market watcher WebSocket
        watcher_task = asyncio.create_task(market_watcher.start())
        
        # Start news stream (this blocks until stopped)
        stream = NewsStream(queue)
        
        sys_logger.info(f"Pipeline initialized with {workers} workers. Listening for news...")
        
        try:
            await stream.start()
        except asyncio.CancelledError:
            sys_logger.info("Stream cancelled.")
        finally:
            # Cleanup
            sys_logger.info("Cleaning up resources...")
            watcher_task.cancel()
            for t in worker_tasks:
                t.cancel()
            await stream.stop()

    def handle_exit(sig, frame):
        sys_logger.info("Shutdown signal received...")
        loop = asyncio.get_event_loop()
        for task in asyncio.all_tasks(loop):
            task.cancel()

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    try:
        asyncio.run(run_pipeline())
    except (KeyboardInterrupt, asyncio.CancelledError):
        sys_logger.info("Bot stopped gracefully.")

@cli.command()
@click.option('--file', default='bot/historical_data.json', help="Path to historical news JSON")
def backtest(file):
    """Simulate the pipeline on historical data."""
    import json
    import os

    if not os.path.exists(file):
        sys_logger.error(f"Backtest file not found: {file}")
        return

    with open(file, 'r') as f:
        data = json.load(f)

    sys_logger.info(f"Loaded {len(data)} events for backtesting.")
    asyncio.run(backtester.run(data))

if __name__ == "__main__":
    cli()
