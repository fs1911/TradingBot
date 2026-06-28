"""
News & Macro Sentiment Module
────────────────────────────────────────────────────────────────────────────
Sources:
  - NewsAPI.org      → headline sentiment for specific tickers
  - Alpha Vantage    → market news with AI sentiment scores
  - Economic calendar → upcoming high-impact events (manual or API)

The module returns a sentiment score [-1, +1] per symbol or macro category.
Scores are consumed by the signal fusion layer to filter/scale signals.
"""
from __future__ import annotations
import os
import re
from datetime import datetime, timezone, timedelta
from typing import Optional
import requests
from loguru import logger


POSITIVE_WORDS = frozenset([
    "surge", "soar", "rally", "beat", "record", "strong", "upgrade",
    "bullish", "growth", "profit", "revenue", "buy", "outperform",
    "exceeds", "positive", "gain", "rise", "higher", "boost",
])

NEGATIVE_WORDS = frozenset([
    "plunge", "crash", "miss", "weak", "downgrade", "bearish", "loss",
    "decline", "fall", "lower", "cut", "sell", "underperform", "concern",
    "warning", "risk", "debt", "recession", "inflation", "fear",
])


class SentimentAnalyzer:
    """Fetch and score news sentiment for given symbols or macros."""

    def __init__(self):
        self._news_key = os.environ.get("NEWS_API_KEY", "")
        self._av_key = os.environ.get("ALPHA_VANTAGE_KEY", "")
        self._cache: dict[str, tuple[float, datetime]] = {}
        self._cache_ttl_minutes = 60

    def get_sentiment(self, symbol: str) -> float:
        """
        Return a sentiment score for the symbol in range [-1.0, +1.0].
        Positive = bullish, Negative = bearish, 0 = neutral.
        """
        cached = self._get_cached(symbol)
        if cached is not None:
            return cached

        score = 0.0
        count = 0

        if self._av_key:
            av_score = self._fetch_alpha_vantage(symbol)
            if av_score is not None:
                score += av_score
                count += 1

        if self._news_key:
            news_score = self._fetch_newsapi(symbol)
            if news_score is not None:
                score += news_score
                count += 1

        final_score = (score / count) if count > 0 else 0.0
        self._cache[symbol] = (final_score, datetime.now(timezone.utc))
        logger.debug(f"Sentiment [{symbol}]: {final_score:.3f}")
        return final_score

    def get_macro_sentiment(self) -> dict[str, float]:
        """
        Return macro sentiment for key categories.
        Uses keyword search on recent financial headlines.
        """
        topics = {
            "fed_rates": ["federal reserve", "interest rate", "rate hike", "rate cut", "fomc"],
            "inflation": ["cpi", "inflation", "pce", "core inflation"],
            "employment": ["nfp", "jobs report", "unemployment", "payrolls"],
            "geopolitics": ["war", "sanctions", "conflict", "tariff", "trade war"],
            "crypto_regulation": ["sec", "crypto regulation", "bitcoin ban", "cbdc"],
        }

        results: dict[str, float] = {}
        for topic, keywords in topics.items():
            results[topic] = self._fetch_topic_sentiment(keywords)

        return results

    def is_high_impact_event_soon(self, symbol: str, minutes_ahead: int = 15) -> bool:
        """
        Placeholder: return True if a high-impact macro event is within N minutes.
        Integrate with a proper economic calendar API (e.g. ForexFactory, Investing.com)
        for production use.
        """
        return False

    # ── Private helpers ───────────────────────────────────────────────────────

    def _fetch_alpha_vantage(self, symbol: str) -> Optional[float]:
        try:
            url = (
                f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT"
                f"&tickers={symbol}&apikey={self._av_key}&limit=20"
            )
            resp = requests.get(url, timeout=8)
            resp.raise_for_status()
            data = resp.json()
            feed = data.get("feed", [])
            if not feed:
                return None

            scores = []
            for article in feed[:20]:
                for ts in article.get("ticker_sentiment", []):
                    if ts.get("ticker", "").upper() == symbol.upper():
                        s = float(ts.get("ticker_sentiment_score", 0))
                        scores.append(s)
            return sum(scores) / len(scores) if scores else None
        except Exception as e:
            logger.debug(f"AlphaVantage sentiment failed [{symbol}]: {e}")
            return None

    def _fetch_newsapi(self, symbol: str) -> Optional[float]:
        try:
            from_dt = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
            url = (
                f"https://newsapi.org/v2/everything?q={symbol}"
                f"&from={from_dt}&language=en&sortBy=publishedAt"
                f"&pageSize=20&apiKey={self._news_key}"
            )
            resp = requests.get(url, timeout=8)
            resp.raise_for_status()
            articles = resp.json().get("articles", [])

            scores = [self._score_headline(a.get("title", "") + " " + a.get("description", ""))
                      for a in articles]
            valid = [s for s in scores if s != 0]
            return sum(valid) / len(valid) if valid else 0.0
        except Exception as e:
            logger.debug(f"NewsAPI sentiment failed [{symbol}]: {e}")
            return None

    def _fetch_topic_sentiment(self, keywords: list[str]) -> float:
        if not self._news_key:
            return 0.0
        query = " OR ".join(f'"{k}"' for k in keywords[:3])
        try:
            url = (
                f"https://newsapi.org/v2/everything?q={query}"
                f"&language=en&sortBy=publishedAt&pageSize=10&apiKey={self._news_key}"
            )
            resp = requests.get(url, timeout=8)
            resp.raise_for_status()
            articles = resp.json().get("articles", [])
            scores = [self._score_headline(a.get("title", "") + " " + a.get("description", ""))
                      for a in articles]
            valid = [s for s in scores if s != 0]
            return sum(valid) / len(valid) if valid else 0.0
        except Exception:
            return 0.0

    @staticmethod
    def _score_headline(text: str) -> float:
        """Naive bag-of-words sentiment score."""
        words = re.findall(r"\b\w+\b", text.lower())
        pos = sum(1 for w in words if w in POSITIVE_WORDS)
        neg = sum(1 for w in words if w in NEGATIVE_WORDS)
        total = pos + neg
        if total == 0:
            return 0.0
        return (pos - neg) / total

    def _get_cached(self, symbol: str) -> Optional[float]:
        if symbol not in self._cache:
            return None
        score, ts = self._cache[symbol]
        age_min = (datetime.now(timezone.utc) - ts).total_seconds() / 60
        if age_min > self._cache_ttl_minutes:
            return None
        return score
