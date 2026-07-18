"""
Credit pricing and tier caps for the hybrid billing model.
All amounts are in whole credits. Tunable without schema changes.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Optional, Tuple

# Monthly / signup grants by subscription_tier
TIER_GRANTS: Dict[str, int] = {
    "FREE": 200,
    "PRO": 1000,
    "ENTERPRISE": 5000,
}

# Hard caps enforced at API edge
TIER_CAPS: Dict[str, Dict[str, int]] = {
    "FREE": {"max_agents": 50, "max_days": 7, "max_video_seconds": 300},       # 5 min
    "PRO": {"max_agents": 500, "max_days": 14, "max_video_seconds": 900},      # 15 min
    "ENTERPRISE": {"max_agents": 5000, "max_days": 30, "max_video_seconds": 1800},  # 30 min
}

VLM_TEXT_PASTE = 0
VLM_TEXT_FILE = 5
VLM_IMAGE = 15
VLM_AUDIO = 15
VLM_VIDEO_BASE = 20
VLM_VIDEO_PER_15S = 2

# Rough bytes-per-second for video duration estimate before OpenCV
VIDEO_BYTES_PER_SECOND_ESTIMATE = 500_000
DEFAULT_VIDEO_ESTIMATE_SECONDS = 60


def normalize_tier(tier: Optional[str]) -> str:
    t = (tier or "FREE").upper()
    return t if t in TIER_GRANTS else "FREE"


def grant_for_tier(tier: Optional[str]) -> int:
    return TIER_GRANTS[normalize_tier(tier)]


def caps_for_tier(tier: Optional[str]) -> Dict[str, int]:
    return dict(TIER_CAPS[normalize_tier(tier)])


def quote_simulation(num_agents: int, simulation_days: int) -> int:
    return max(0, int(num_agents) * int(simulation_days))


def quote_video_duration(duration_seconds: int) -> int:
    secs = max(0, int(duration_seconds))
    blocks = math.ceil(secs / 15) if secs > 0 else 0
    return VLM_VIDEO_BASE + VLM_VIDEO_PER_15S * blocks


def estimate_video_seconds(file_size_bytes: Optional[int] = None) -> int:
    if file_size_bytes and file_size_bytes > 0:
        return max(1, int(file_size_bytes / VIDEO_BYTES_PER_SECOND_ESTIMATE))
    return DEFAULT_VIDEO_ESTIMATE_SECONDS


def quote_vlm(
    modality: str,
    *,
    paste_only: bool = False,
    duration_seconds: Optional[int] = None,
    file_size_bytes: Optional[int] = None,
) -> Tuple[int, Dict[str, Any]]:
    """
    Return (credits, metadata) for a VLM / media-processing charge.
    """
    mod = (modality or "video").lower()
    meta: Dict[str, Any] = {"modality": mod, "paste_only": paste_only}

    if paste_only or (mod == "text" and paste_only):
        return VLM_TEXT_PASTE, {**meta, "pricing": "text_paste"}

    if mod == "text":
        return VLM_TEXT_FILE, {**meta, "pricing": "text_file"}

    if mod == "image":
        return VLM_IMAGE, {**meta, "pricing": "image"}

    if mod == "audio":
        return VLM_AUDIO, {**meta, "pricing": "audio"}

    # video (including display_banner resolved to video)
    if duration_seconds is not None:
        secs = int(duration_seconds)
        estimated = False
    else:
        secs = estimate_video_seconds(file_size_bytes)
        estimated = True
    cost = quote_video_duration(secs)
    meta.update({
        "pricing": "video",
        "duration_seconds": secs,
        "duration_estimated": estimated,
    })
    return cost, meta


def plans_catalog() -> list:
    """Public plan comparison payload for billing UI."""
    plans = []
    for tier in ("FREE", "PRO", "ENTERPRISE"):
        caps = TIER_CAPS[tier]
        plans.append({
            "tier": tier,
            "monthly_credits": TIER_GRANTS[tier],
            "max_agents": caps["max_agents"],
            "max_days": caps["max_days"],
            "max_video_seconds": caps["max_video_seconds"],
        })
    return plans
