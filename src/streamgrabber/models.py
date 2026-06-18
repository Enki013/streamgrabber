from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
)


@dataclass(frozen=True)
class Variant:
    index: int
    bandwidth: int
    resolution: str
    height: int
    url: str


@dataclass
class Capture:
    url: str
    kind: str
    headers: dict[str, str] = field(default_factory=dict)
    response_headers: dict[str, str] = field(default_factory=dict)
    source_url: str | None = None
    page_title: str | None = None

    @property
    def user_agent(self) -> str:
        return header_value(self.headers, "user-agent") or DEFAULT_USER_AGENT

    @property
    def referer(self) -> str | None:
        return header_value(self.headers, "referer") or self.source_url


def header_value(headers: dict[str, Any], name: str) -> str | None:
    for key, value in headers.items():
        if key.lower() == name.lower():
            return str(value)
    return None
