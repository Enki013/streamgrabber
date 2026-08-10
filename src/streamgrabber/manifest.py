from __future__ import annotations

from urllib.parse import urljoin
import re

from .models import Variant


def _attr_value(attrs: str, name: str) -> str | None:
    match = re.search(rf"(?:^|,){re.escape(name)}=([^,]+)", attrs, re.I)
    return match.group(1).strip('"') if match else None


def parse_master_playlist(text: str, base_url: str) -> list[Variant]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    variants: list[Variant] = []
    for i, line in enumerate(lines):
        if not line.startswith("#EXT-X-STREAM-INF"):
            continue
        if i + 1 >= len(lines) or lines[i + 1].startswith("#"):
            continue
        attrs = line.split(":", 1)[1] if ":" in line else ""
        resolution = _attr_value(attrs, "RESOLUTION") or ""
        bandwidth = int(_attr_value(attrs, "BANDWIDTH") or 0)
        height_match = re.search(r"x(\d+)$", resolution)
        height = int(height_match.group(1)) if height_match else 0
        variants.append(
            Variant(
                index=len(variants),
                bandwidth=bandwidth,
                resolution=resolution,
                height=height,
                url=urljoin(base_url, lines[i + 1]),
            )
        )
    return variants


def choose_variant(variants: list[Variant], quality: str = "best") -> Variant | None:
    if not variants:
        return None
    ordered = sorted(variants, key=lambda v: (v.height, v.bandwidth), reverse=True)
    if quality in ("best", "auto", ""):
        return ordered[0]
    if quality == "worst":
        return sorted(variants, key=lambda v: (v.height, v.bandwidth))[0]
    if quality.isdigit():
        requested = int(quality)
        exact = [v for v in variants if v.height == requested]
        if exact:
            return sorted(exact, key=lambda v: v.bandwidth, reverse=True)[0]
        return sorted(variants, key=lambda v: (abs(v.height - requested), -v.bandwidth))[0]
    if quality.endswith("p") and quality[:-1].isdigit():
        return choose_variant(variants, quality[:-1])
    return ordered[0]
