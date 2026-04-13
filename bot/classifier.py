import json
import time
import logging
import google.generativeai as genai
from typing import Dict, Any, Optional
from .config import config

# Configure logging
logger = logging.getLogger("bot.classifier")

class EventClassifier:
    def __init__(self):
        if not config.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not set. Classifier will fail.")
        genai.configure(api_key=config.GEMINI_API_KEY)
        
        # System instruction for deterministic parsing
        self.system_instruction = """
        You are an elite quantitative analyst and deterministic parser for prediction markets.
        Your task is to parse raw Telegram crypto news against a specific market condition.
        
        CRYPTO SLANG DICTIONARY:
        - "nukes", "dump", "rekt", "rug": BEARISH (Decreases 'YES' probability)
        - "god candle", "pamp", "moon", "listing": BULLISH (Increases 'YES' probability)
        - "whale moving to exchange": Often BEARISH (potential sell pressure)
        - "whale moving to cold storage": Often BULLISH (reduced sell pressure)
        
        MATERIALITY MATRIX (Actionable Thresholds):
        - SEC/Regulatory Approvals or Denials: 0.9 - 1.0
        - Major Exchange Hacks (> $50M): 0.85 - 0.95
        - Tier-1 Listings (Binance, Coinbase): 0.8 - 0.9
        - Major Partnership/Protocol Upgrades: 0.6 - 0.8
        - General Market Sentiment/Rumors: 0.1 - 0.5
        
        OUTPUT RULES:
        1. Direction: 'YES' if the news increases the probability of the condition being true.
           'NO' if it decreases the probability.
           'NEUTRAL' if no clear impact.
        2. Materiality: Float [0.0, 1.0] based on the Matrix.
        3. Confidence: Float [0.0, 1.0] reflecting your certainty in the parse.
        4. Reasoning: Concise string explaining the logic.
        
        STRICT JSON OUTPUT ONLY. No markdown, no preamble.
        """
        
        self.model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            generation_config={"response_mime_type": "application/json"}
        )

    async def classify_event(self, market_condition: str, telegram_text: str) -> Dict[str, Any]:
        """
        Asynchronously classifies a news event against a market condition.
        """
        prompt = f"Market Condition: {market_condition}\nTelegram News: {telegram_text}"
        
        start_time = time.perf_counter()
        try:
            # Note: google-generativeai is synchronous, but we can run it in a thread if needed.
            # For this pipeline, we'll call it directly.
            response = self.model.generate_content(
                contents=[{"role": "user", "parts": [{"text": self.system_instruction + "\n\n" + prompt}]}]
            )
            
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            
            try:
                result = json.loads(response.text)
                # Validate schema
                required_keys = ["direction", "materiality", "confidence_in_parse", "reasoning"]
                if not all(k in result for k in required_keys):
                    raise ValueError("Missing keys in LLM response")
                
                result['latency_ms'] = latency_ms
                return result
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse LLM response: {response.text}. Error: {e}")
                return self._get_fallback_result(latency_ms, f"Parse Error: {str(e)}")

        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(f"LLM API Error: {e}")
            return self._get_fallback_result(latency_ms, f"API Error: {str(e)}")

    def _get_fallback_result(self, latency_ms: int, error_msg: str) -> Dict[str, Any]:
        return {
            "direction": "NEUTRAL",
            "materiality": 0.0,
            "confidence_in_parse": 0.0,
            "reasoning": f"Fallback triggered: {error_msg}",
            "latency_ms": latency_ms
        }

classifier = EventClassifier()
