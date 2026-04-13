import asyncio
import json
import time
from datetime import datetime
from typing import List, Dict, Any
from .config import config
from .classifier import classifier
from .logger import logger

class Backtester:
    def __init__(self):
        self.results = []
        self.initial_balance = 1000.0
        self.balance = self.initial_balance
        self.trades = []

    async def run(self, historical_data: List[Dict[str, Any]]):
        """
        Runs the backtest against a list of historical news events.
        Each event should have: 'headline', 'source', 'timestamp', 'market_question', 'actual_outcome'
        """
        print(f"Starting backtest on {len(historical_data)} events...")
        self.balance = self.initial_balance
        self.trades = []
        
        for event in historical_data:
            # 1. Classify using the same logic as live bot
            analysis = await classifier.classify_event(event['market_question'], event['headline'])
            
            # 2. Simulate execution logic
            trade_executed = False
            pnl = 0.0
            
            if analysis['direction'] != 'NEUTRAL' and analysis['materiality'] >= config.MIN_MATERIALITY:
                trade_executed = True
                bet_size = config.MAX_BET_SIZE_USDC * analysis['materiality']
                
                # Check if we have enough balance
                if self.balance >= bet_size:
                    # Determine if trade was correct based on actual_outcome
                    # actual_outcome should be 'YES' or 'NO'
                    is_correct = (analysis['direction'] == event['actual_outcome'])
                    
                    if is_correct:
                        # Simplified PnL: Assume 2x return for simplicity (binary outcome)
                        # In reality, this would depend on the odds at the time
                        pnl = bet_size * 0.9  # 90% profit after fees
                    else:
                        pnl = -bet_size
                    
                    self.balance += pnl
                    self.trades.append({
                        "timestamp": event['timestamp'],
                        "headline": event['headline'],
                        "direction": analysis['direction'],
                        "outcome": event['actual_outcome'],
                        "pnl": pnl,
                        "balance": self.balance
                    })

            # 3. Log the simulated event
            logger.log_event(
                source=f"BACKTEST_{event['source']}",
                headline=event['headline'],
                classification=analysis['direction'],
                materiality=analysis['materiality'],
                reasoning=analysis['reasoning'],
                latency_ms=analysis['latency_ms'],
                trade_executed=trade_executed,
                trade_details={"pnl": pnl, "balance": self.balance} if trade_executed else None
            )

        return self.calculate_metrics()

    def calculate_metrics(self):
        if not self.trades:
            return {"error": "No trades executed during backtest"}

        total_pnl = self.balance - self.initial_balance
        wins = [t for t in self.trades if t['pnl'] > 0]
        win_rate = len(wins) / len(self.trades) if self.trades else 0
        
        # Calculate Max Drawdown
        max_balance = self.initial_balance
        max_drawdown = 0.0
        current_balance = self.initial_balance
        
        for t in self.trades:
            current_balance = t['balance']
            if current_balance > max_balance:
                max_balance = current_balance
            
            drawdown = (max_balance - current_balance) / max_balance
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        metrics = {
            "total_trades": len(self.trades),
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "final_balance": self.balance,
            "max_drawdown": max_drawdown,
            "roi": (total_pnl / self.initial_balance) * 100
        }
        
        print("\n--- Backtest Results ---")
        print(f"Total Trades: {metrics['total_trades']}")
        print(f"Win Rate: {metrics['win_rate']:.2%}")
        print(f"Total PnL: ${metrics['total_pnl']:.2f}")
        print(f"Max Drawdown: {metrics['max_drawdown']:.2%}")
        print(f"ROI: {metrics['roi']:.2f}%")
        
        return metrics

backtester = Backtester()
