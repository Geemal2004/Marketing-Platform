"""
Seed mock data for the Veyra database.

Run from the repo root:
    py backend/backend/seed_mock_data.py
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from app.config import get_settings
from app.database import SessionLocal
from app.models import AgentLog, CustomAgent, Project, RiskFlag, SimulationRun, User
from app.services.auth_service import hash_password


def _print_header(title: str) -> None:
    print("=" * 72)
    print(title)
    print("=" * 72)


def _ensure_user(db, email: str, password: str, subscription_tier: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user:
        print(f"User exists: {email}")
        return user

    user = User(
        email=email,
        password_hash=hash_password(password),
        subscription_tier=subscription_tier,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"Created user: {email}")
    return user


def _ensure_custom_agent(db, user_id, name: str, payload: dict) -> CustomAgent:
    agent = (
        db.query(CustomAgent)
        .filter(CustomAgent.user_id == user_id, CustomAgent.name == name)
        .first()
    )
    if agent:
        print(f"Custom agent exists: {name}")
        return agent

    agent = CustomAgent(user_id=user_id, name=name, **payload)
    db.add(agent)
    db.commit()
    db.refresh(agent)
    print(f"Created custom agent: {name}")
    return agent


def _ensure_project(db, user_id, title: str, payload: dict) -> Project:
    project = (
        db.query(Project)
        .filter(Project.user_id == user_id, Project.title == title)
        .first()
    )
    if project:
        print(f"Project exists: {title}")
        return project

    project = Project(user_id=user_id, title=title, **payload)
    db.add(project)
    db.commit()
    db.refresh(project)
    print(f"Created project: {title}")
    return project


def _build_simulation_payload(seed_prefix: str):
    agents = [
        {
            "agent_id": f"{seed_prefix}-001",
            "coordinates": [6.93, 79.86],
            "opinion": "POSITIVE",
            "emotion": "happy",
            "emotion_intensity": 0.82,
            "reasoning": "The ad feels authentic and aligns with my values.",
            "friends": [f"{seed_prefix}-002", f"{seed_prefix}-003"],
            "profile": {
                "name": "Ravi Perera",
                "age": 28,
                "gender": "Male",
                "location": "Colombo",
                "occupation": "Digital marketer",
                "education": "Bachelor's",
                "income_level": "Mid",
                "religion": "Buddhist",
                "ethnicity": "Sinhalese",
                "social_media_usage": "High",
                "political_leaning": "Moderate",
                "values": ["Innovation", "Transparency"],
                "personality_traits": ["Curious", "Analytical"],
            },
        },
        {
            "agent_id": f"{seed_prefix}-002",
            "coordinates": [7.29, 80.63],
            "opinion": "NEUTRAL",
            "emotion": "neutral",
            "emotion_intensity": 0.35,
            "reasoning": "The message is clear but I need more proof before I decide.",
            "friends": [f"{seed_prefix}-001"],
            "profile": {
                "name": "Anjali Jayasinghe",
                "age": 33,
                "gender": "Female",
                "location": "Kandy",
                "occupation": "Teacher",
                "education": "Master's",
                "income_level": "Mid",
                "religion": "Buddhist",
                "ethnicity": "Sinhalese",
                "social_media_usage": "Medium",
                "political_leaning": "Neutral",
                "values": ["Family", "Stability"],
                "personality_traits": ["Calm", "Thoughtful"],
            },
        },
        {
            "agent_id": f"{seed_prefix}-003",
            "coordinates": [6.05, 80.22],
            "opinion": "NEGATIVE",
            "emotion": "sad",
            "emotion_intensity": 0.68,
            "reasoning": "The ad overlooks local concerns and feels out of touch.",
            "friends": [f"{seed_prefix}-001"],
            "profile": {
                "name": "Sahan Fernando",
                "age": 41,
                "gender": "Male",
                "location": "Galle",
                "occupation": "Business owner",
                "education": "Diploma",
                "income_level": "High",
                "religion": "Christian",
                "ethnicity": "Sinhalese",
                "social_media_usage": "Low",
                "political_leaning": "Conservative",
                "values": ["Tradition", "Community"],
                "personality_traits": ["Direct", "Protective"],
            },
        },
        {
            "agent_id": f"{seed_prefix}-004",
            "coordinates": [9.66, 80.02],
            "opinion": "POSITIVE",
            "emotion": "surprised",
            "emotion_intensity": 0.74,
            "reasoning": "Unexpected but compelling story arc; it caught my attention.",
            "friends": [],
            "profile": {
                "name": "Thivya Kumar",
                "age": 24,
                "gender": "Female",
                "location": "Jaffna",
                "occupation": "Designer",
                "education": "Bachelor's",
                "income_level": "Low",
                "religion": "Hindu",
                "ethnicity": "Tamil",
                "social_media_usage": "High",
                "political_leaning": "Progressive",
                "values": ["Creativity", "Equity"],
                "personality_traits": ["Expressive", "Empathetic"],
            },
        },
        {
            "agent_id": f"{seed_prefix}-005",
            "coordinates": [7.71, 81.70],
            "opinion": "NEUTRAL",
            "emotion": "neutral",
            "emotion_intensity": 0.3,
            "reasoning": "It is informative but does not stand out yet.",
            "friends": [f"{seed_prefix}-004"],
            "profile": {
                "name": "Mohamed Rizwan",
                "age": 37,
                "gender": "Male",
                "location": "Batticaloa",
                "occupation": "Logistics manager",
                "education": "Bachelor's",
                "income_level": "Mid",
                "religion": "Muslim",
                "ethnicity": "Muslim",
                "social_media_usage": "Medium",
                "political_leaning": "Moderate",
                "values": ["Efficiency", "Trust"],
                "personality_traits": ["Practical", "Reserved"],
            },
        },
    ]

    map_data = [
        {
            "agent_id": agent["agent_id"],
            "coordinates": agent["coordinates"],
            "opinion": agent["opinion"],
            "friends": agent["friends"],
        }
        for agent in agents
    ]

    opinion_trajectory = {
        agents[0]["agent_id"]: [
            {"day": 1, "opinion": "NEUTRAL"},
            {"day": 2, "opinion": "POSITIVE"},
            {"day": 3, "opinion": "POSITIVE"},
        ],
        agents[1]["agent_id"]: [
            {"day": 1, "opinion": "NEUTRAL"},
            {"day": 2, "opinion": "NEUTRAL"},
            {"day": 3, "opinion": "POSITIVE"},
        ],
        agents[2]["agent_id"]: [
            {"day": 1, "opinion": "NEGATIVE"},
            {"day": 2, "opinion": "NEGATIVE"},
            {"day": 3, "opinion": "NEGATIVE"},
        ],
        agents[3]["agent_id"]: [
            {"day": 1, "opinion": "NEUTRAL"},
            {"day": 2, "opinion": "POSITIVE"},
            {"day": 3, "opinion": "POSITIVE"},
        ],
        agents[4]["agent_id"]: [
            {"day": 1, "opinion": "NEUTRAL"},
            {"day": 2, "opinion": "NEUTRAL"},
            {"day": 3, "opinion": "NEUTRAL"},
        ],
    }

    agent_logs = [
        {
            "agent_id": agents[0]["agent_id"],
            "event_type": "ENDORSEMENT",
            "event_data": {
                "opinion": "POSITIVE",
                "details": "Shared the campaign with friends on social media.",
            },
        },
        {
            "agent_id": agents[2]["agent_id"],
            "event_type": "BOYCOTT",
            "event_data": {
                "opinion": "NEGATIVE",
                "details": "Flagged the message as insensitive to local concerns.",
            },
        },
        {
            "agent_id": agents[1]["agent_id"],
            "event_type": "OPINION_CHANGE",
            "event_data": {
                "opinion": "POSITIVE",
                "details": "Shifted to positive after peer feedback.",
            },
        },
    ]

    risk_flags = [
        {
            "flag_type": "Cultural sensitivity",
            "severity": "HIGH",
            "description": "Risk of misalignment with regional cultural context.",
            "affected_demographics": {"region": "Southern Province"},
            "sample_agent_reactions": [
                {
                    "agent_id": agents[2]["agent_id"],
                    "reaction": "Feels out of touch with local realities.",
                }
            ],
        },
        {
            "flag_type": "Price perception",
            "severity": "LOW",
            "description": "Some agents perceive the offer as premium priced.",
            "affected_demographics": {"income_level": "Low"},
            "sample_agent_reactions": [
                {
                    "agent_id": agents[4]["agent_id"],
                    "reaction": "Interested but cost might be a hurdle.",
                }
            ],
        },
    ]

    sentiment_breakdown = {"positive": 2, "neutral": 2, "negative": 1}

    return agents, map_data, opinion_trajectory, agent_logs, risk_flags, sentiment_breakdown


def _ensure_simulation(db, project: Project, payload: dict) -> SimulationRun:
    simulation = (
        db.query(SimulationRun)
        .filter(SimulationRun.project_id == project.id)
        .first()
    )
    if simulation:
        print(f"Simulation exists for project: {project.title}")
        return simulation

    simulation = SimulationRun(project_id=project.id, **payload)
    db.add(simulation)
    db.commit()
    db.refresh(simulation)
    print(f"Created simulation for project: {project.title}")
    return simulation


def _ensure_agent_logs(db, simulation_id, logs: list) -> None:
    existing = db.query(AgentLog).filter(AgentLog.simulation_run_id == simulation_id).first()
    if existing:
        print(f"Agent logs already exist for simulation: {simulation_id}")
        return

    for log in logs:
        db.add(
            AgentLog(
                simulation_run_id=simulation_id,
                agent_id=log["agent_id"],
                event_type=log["event_type"],
                event_data=log["event_data"],
            )
        )
    db.commit()
    print(f"Inserted {len(logs)} agent logs")


def _ensure_risk_flags(db, simulation_id, flags: list) -> None:
    existing = db.query(RiskFlag).filter(RiskFlag.simulation_run_id == simulation_id).first()
    if existing:
        print(f"Risk flags already exist for simulation: {simulation_id}")
        return

    for flag in flags:
        db.add(
            RiskFlag(
                simulation_run_id=simulation_id,
                flag_type=flag["flag_type"],
                severity=flag["severity"],
                description=flag["description"],
                affected_demographics=flag.get("affected_demographics"),
                sample_agent_reactions=flag.get("sample_agent_reactions"),
            )
        )
    db.commit()
    print(f"Inserted {len(flags)} risk flags")


def seed():
    settings = get_settings()
    _print_header("Seeding mock data")
    print(f"Database URL: {settings.database_url}")

    db = SessionLocal()
    try:
        admin_user = _ensure_user(
            db,
            email="admin@veyra.com",
            password="admin123",
            subscription_tier="PRO",
        )
        _ensure_user(
            db,
            email="analyst@veyra.com",
            password="analyst123",
            subscription_tier="FREE",
        )

        custom_agent_a = _ensure_custom_agent(
            db,
            admin_user.id,
            "Urban Trendsetter",
            {
                "age": 29,
                "gender": "Female",
                "location": "Colombo",
                "occupation": "Brand strategist",
                "education": "Master's",
                "income_level": "High",
                "religion": "Buddhist",
                "ethnicity": "Sinhalese",
                "social_media_usage": "High",
                "political_leaning": "Progressive",
                "values": ["Sustainability", "Quality"],
                "personality_traits": ["Bold", "Analytical"],
                "bio": "Early adopter who influences peer purchase decisions.",
            },
        )
        custom_agent_b = _ensure_custom_agent(
            db,
            admin_user.id,
            "Pragmatic Parent",
            {
                "age": 38,
                "gender": "Male",
                "location": "Kandy",
                "occupation": "Operations manager",
                "education": "Bachelor's",
                "income_level": "Mid",
                "religion": "Buddhist",
                "ethnicity": "Sinhalese",
                "social_media_usage": "Medium",
                "political_leaning": "Moderate",
                "values": ["Security", "Family"],
                "personality_traits": ["Practical", "Reserved"],
                "bio": "Focused on value and reliability for family decisions.",
            },
        )

        project_a = _ensure_project(
            db,
            admin_user.id,
            "The Drift of a Lifetime",
            {
                "video_path": "https://storage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
                "video_duration_seconds": 123,
                "vlm_generated_context": "A cinematic journey that highlights freedom, speed, and modern luxury.",
                "demographic_filter": {"age_range": "18-34", "regions": ["Colombo", "Kandy"]},
                "status": "READY",
            },
        )
        project_b = _ensure_project(
            db,
            admin_user.id,
            "Sri Lankan Airlines",
            {
                "video_path": "https://storage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
                "video_duration_seconds": 109,
                "vlm_generated_context": "A warm, scenic story showcasing hospitality and heritage.",
                "demographic_filter": {"age_range": "25-45", "regions": ["Galle", "Jaffna"]},
                "status": "READY",
            },
        )
        _ensure_project(
            db,
            admin_user.id,
            "Future of Mobility",
            {
                "video_path": "https://storage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4",
                "video_duration_seconds": 92,
                "vlm_generated_context": "Teaser in processing with an emphasis on sustainable transit.",
                "demographic_filter": {"age_range": "18-40", "regions": ["Colombo"]},
                "status": "PROCESSING",
            },
        )

        agents_a, map_a, trajectory_a, logs_a, flags_a, sentiment_a = _build_simulation_payload("AG")
        simulation_a = _ensure_simulation(
            db,
            project_a,
            {
                "id": uuid.uuid4(),
                "status": "COMPLETED",
                "num_agents": len(agents_a),
                "simulation_days": 3,
                "engagement_score": 72.4,
                "sentiment_breakdown": sentiment_a,
                "map_data": map_a,
                "agent_states": agents_a,
                "opinion_trajectory": trajectory_a,
                "started_at": datetime.utcnow() - timedelta(days=3, hours=4),
                "completed_at": datetime.utcnow() - timedelta(days=3, hours=2),
                "use_custom_agents_only": False,
                "agent_ids": None,
            },
        )
        _ensure_agent_logs(db, simulation_a.id, logs_a)
        _ensure_risk_flags(db, simulation_a.id, flags_a)

        agents_b, map_b, trajectory_b, logs_b, flags_b, sentiment_b = _build_simulation_payload("BA")
        simulation_b = _ensure_simulation(
            db,
            project_b,
            {
                "id": uuid.uuid4(),
                "status": "COMPLETED",
                "num_agents": len(agents_b),
                "simulation_days": 4,
                "engagement_score": 64.8,
                "sentiment_breakdown": sentiment_b,
                "map_data": map_b,
                "agent_states": agents_b,
                "opinion_trajectory": trajectory_b,
                "started_at": datetime.utcnow() - timedelta(days=1, hours=6),
                "completed_at": datetime.utcnow() - timedelta(days=1, hours=5),
                "use_custom_agents_only": True,
                "agent_ids": [str(custom_agent_a.id), str(custom_agent_b.id)],
            },
        )
        _ensure_agent_logs(db, simulation_b.id, logs_b)
        _ensure_risk_flags(db, simulation_b.id, flags_b)

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    _print_header("Seed complete")


if __name__ == "__main__":
    seed()
