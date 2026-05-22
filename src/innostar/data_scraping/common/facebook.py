from __future__ import annotations

from .text import clean_text


def canonical_facebook_url(url) -> str:
    url = clean_text(url)
    if not url:
        return ""

    replacements = {
        "http://facebook.com/": "https://www.facebook.com/",
        "https://facebook.com/": "https://www.facebook.com/",
        "http://www.facebook.com/": "https://www.facebook.com/",
        "https://m.facebook.com/": "https://www.facebook.com/",
        "http://m.facebook.com/": "https://www.facebook.com/",
        "https://fb.com/": "https://www.facebook.com/",
        "http://fb.com/": "https://www.facebook.com/",
    }

    for old, new in replacements.items():
        url = url.replace(old, new)

    return url.split("?")[0].split("#")[0].rstrip("/")


def is_facebook_url(url) -> bool:
    url = clean_text(url).lower()
    return any(host in url for host in ["facebook.com", "fb.com", "m.facebook.com"])

