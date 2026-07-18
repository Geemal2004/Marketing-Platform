"""
Static pricing / revenue-flow description (no metering or payments yet).
"""
from fastapi import APIRouter

from app.billing_pricing import plans_catalog, quote_simulation, quote_vlm

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.get("/plans")
def get_plans():
    """Plan comparison and how credits will work when payments are wired."""
    return {
        "payments_enabled": False,
        "message": "Payments are not enabled yet. This describes the planned revenue model.",
        "plans": plans_catalog(),
        "pricing": {
            "signup_grant_free": 200,
            "vlm_text_paste": 0,
            "vlm_text_file": 5,
            "vlm_image_or_audio": 15,
            "vlm_video": "20 + 2 credits per 15 seconds of video",
            "simulation": "1 credit × number of agents × simulation days",
        },
        "examples": [
            {
                "label": "Small free-tier run",
                "detail": "10 agents × 5 days = 50 credits (plus media analysis if needed)",
                "simulation_credits": quote_simulation(10, 5),
            },
            {
                "label": "Typical image campaign",
                "detail": "Image VLM + 50 agents × 7 days",
                "vlm_credits": quote_vlm("image")[0],
                "simulation_credits": quote_simulation(50, 7),
            },
            {
                "label": "60-second video",
                "detail": "Video analysis cost only",
                "vlm_credits": quote_vlm("video", duration_seconds=60)[0],
            },
        ],
    }
