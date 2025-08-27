"""Retrieval utilities for open-book augmentation.

Currently uses Wikipedia open search API to fetch short summaries that can be
fed into the writing pipeline as background context.
"""
from __future__ import annotations

import copy
from functools import lru_cache
import requests
from typing import Dict, List, Tuple

@lru_cache(maxsize=128)
def _open_book_search_cached(query: str, n_results: int) -> Tuple[Dict[str, str], ...]:
    """Cached helper for ``open_book_search``.

    The function contacts the Wikipedia API and stores results in an LRU cache
    to avoid repeated network calls when the same query is requested multiple
    times within a single run. The returned tuple is treated as immutable to
    make it safe for caching.
    """
    if not query:
        return tuple()
    params = {
        "action": "opensearch",
        "search": query,
        "limit": n_results,
        "namespace": 0,
        "format": "json",
    }
    try:
        resp = requests.get(
            "https://en.wikipedia.org/w/api.php", params=params, timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return tuple()

    titles = data[1]
    urls = data[3]
    results: List[Dict[str, str]] = []
    for title, url in zip(titles, urls):
        summary = ""
        try:
            s_resp = requests.get(
                f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
                timeout=10,
            )
            if s_resp.status_code == 200:
                summary = s_resp.json().get("extract", "")
        except Exception:
            summary = ""
        results.append({"title": title, "url": url, "summary": summary})
    return tuple(results)


def open_book_search(query: str, n_results: int = 3) -> List[Dict[str, str]]:
    """Return top Wikipedia results with summaries.

    Results are cached in-memory for the duration of the process so repeated
    calls with the same arguments do not hit the network again.

    Parameters
    ----------
    query: str
        Search query.
    n_results: int, default 3
        Number of top results to fetch.
    """
    # ``copy`` ensures callers don't mutate the cached objects.
    return [copy.deepcopy(r) for r in _open_book_search_cached(query, n_results)]
