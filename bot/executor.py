import json
import asyncio
import aiohttp
import time
import logging
import os
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_typed_data
from .config import config

logger = logging.getLogger("bot.executor")

class TradeExecutor:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(config.BASE_RPC_URL))
        self.account = Account.from_key(config.PRIVATE_KEY) if config.PRIVATE_KEY else None
        self.api_key = os.getenv("LIMITLESS_API_KEY", "")
        self.venue_contract = config.LIMITLESS_VENUE_CONTRACT
        self.chain_id = config.CHAIN_ID

    def _get_eip712_payload(self, market_id: str, outcome: str, price: float, amount: float, side: str):
        """
        Constructs the EIP-712 payload for a Limitless order.
        """
        domain = {
            "name": "LimitlessExchange",
            "version": "1",
            "chainId": self.chain_id,
            "verifyingContract": self.venue_contract
        }

        # Simplified order type - adjust based on real Limitless schema
        types = {
            "Order": [
                {"name": "market", "type": "string"},
                {"name": "outcome", "type": "string"},
                {"name": "price", "type": "uint256"},
                {"name": "amount", "type": "uint256"},
                {"name": "side", "type": "string"},
                {"name": "nonce", "type": "uint256"},
                {"name": "expiration", "type": "uint256"}
            ]
        }

        # Convert floats to fixed-point integers (e.g., 6 decimals for USDC)
        price_int = int(price * 10**6)
        amount_int = int(amount * 10**6)
        nonce = int(time.time() * 1000)
        expiration = nonce + 3600000 # 1 hour

        message = {
            "market": market_id,
            "outcome": outcome,
            "price": price_int,
            "amount": amount_int,
            "side": side,
            "nonce": nonce,
            "expiration": expiration
        }

        return domain, types, message

    async def execute_trade(self, market_id: str, direction: str, materiality: float) -> dict:
        """
        Signs and executes a trade on Limitless Exchange.
        """
        if not self.account:
            logger.error("Private key not configured.")
            return {"status": "error", "message": "No private key"}

        # Determine size based on materiality
        amount = config.MAX_BET_USD * materiality
        # For simplicity, assume price is 0.5 or fetch from market_watcher
        price = 0.5 
        side = "BUY" # Usually we buy the outcome

        domain, types, message = self._get_eip712_payload(market_id, direction, price, amount, side)
        
        # Sign the order
        signable_data = encode_typed_data(domain_data=domain, message_types=types, message_data=message)
        signed_msg = self.account.sign_message(signable_data)
        
        order_payload = {
            **message,
            "signature": signed_msg.signature.hex(),
            "user": self.account.address
        }

        if config.DRY_RUN:
            logger.info(f"[DRY RUN] Signed order for {market_id}: {json.dumps(order_payload)}")
            return {"status": "success", "tx_hash": "0x_dry_run_hash", "order": order_payload}

        # Submit to API
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{config.LIMITLESS_API_BASE}/orders",
                    json=order_payload,
                    headers=headers
                ) as resp:
                    if resp.status == 201:
                        result = await resp.json()
                        logger.info(f"Order submitted successfully: {result.get('orderId')}")
                        return {"status": "success", "tx_hash": result.get("orderId"), "order": order_payload}
                    else:
                        error_text = await resp.text()
                        logger.error(f"Order submission failed: {resp.status} - {error_text}")
                        return {"status": "error", "message": error_text}
        except Exception as e:
            logger.error(f"Execution error: {e}")
            return {"status": "error", "message": str(e)}

executor = TradeExecutor()
