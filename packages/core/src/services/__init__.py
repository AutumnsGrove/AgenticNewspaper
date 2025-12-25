"""Services for The Daily Clearing.

This module provides core services:
- SearchService: Article discovery via Tavily/Brave Search APIs
- ParserService: Content extraction using newspaper3k (no LLM)
- DatabaseService: Article storage and retrieval
- DeliveryService: Digest delivery via RSS, Email, Web
"""

from .search import (
    SearchService,
    SearchResult,
    SearchConfig,
    SearchProvider,
)
from .parser import (
    ParserService,
    ParsedContent,
    ParserConfig,
)

__all__ = [
    # Search
    "SearchService",
    "SearchResult",
    "SearchConfig",
    "SearchProvider",
    # Parser
    "ParserService",
    "ParsedContent",
    "ParserConfig",
]
