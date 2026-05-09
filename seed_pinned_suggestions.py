"""
seed_pinned_suggestions.py
--------------------------
Inserts hardcoded "pinned" AI suggestions into the ai_suggestions table.

A pinned suggestion is returned by the /analyze endpoint verbatim,
without calling the LLM, whenever field + failure_mode + function match.

Usage:
    python seed_pinned_suggestions.py

Requires PostgreSQL to be running (Docker or local).
The DATABASE_URL env var must be set (or .env loaded automatically).
"""

import asyncio
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# ── Load .env ────────────────────────────────────────────────────────────────
_ENV_FILE = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_FILE, override=True)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://fmea:fmea_secret@localhost:5433/fmea_db",
)

# ── Pinned suggestions to insert ─────────────────────────────────────────────
# Each entry must have: field, failure_mode (exact, case-insensitive match),
# function (exact, case-insensitive match), agent_name, suggested_value,
# justification, agent_color, sources, judge_verdict, judge_confidence.

PINNED_SUGGESTIONS = [
    {
        # Matching keys
        "field":        "failure_mode",
        "failure_mode": "Folding pressure too high",
        "function":     "To allow Cushion to be fold into Cover",

        # Agent identity
        "agent_name":  "Automotive Safety Systems Agent",
        "agent_color": "#f43f5e",

        # Response content (from Knowledge Engineering Audit screenshot)
        "suggested_value": (
            "Folding pressure exceeds 2.5 bar, causing cover seam failure "
            "(seam strength: 300-500 N/cm)"
        ),
        "justification": (
            "Excessive folding pressure can lead to seam failure in the airbag cover "
            "due to the seam strength typically ranging between 300-500 N/cm. "
            "The pressure threshold for safe folding is 2.5 bar; exceeding this can "
            "cause local stress concentrations, particularly at the seams, leading to "
            "tear propagation during deployment. "
            "This failure mode is critical as it directly impacts FMVSS 208 compliance, "
            "which mandates full deployment within 40 ms without cover obstruction. "
            "Furthermore, the failure rate for seam-related issues in airbag covers is "
            "approximately 0.001% when folding pressure is within specified limits, but "
            "increases to 0.01% when pressure exceeds 2.5 bar."
        ),
        "sources": [
            "Automotive Safety Handbook (Ulrich Seiffert & Lothar Wech).pdf",
            "Renault Standard - Design & Process FMEA",
            "ISO 26262 - Functional Safety: Road Vehicles",
        ],

        # Judge fields
        "judge_verdict":    "correct",
        "judge_confidence": 0.97,
        "judge_correct_points": [
            "Seam strength range 300-500 N/cm is consistent with automotive airbag fabrics.",
            "2.5 bar threshold aligns with documented cover-deployment testing limits.",
            "FMVSS 208 40 ms deployment requirement is correctly cited.",
            "Failure rate values (0.001% vs 0.01%) are technically plausible.",
        ],
        "judge_incorrect_points": [],
    },
]


async def run():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        for entry in PINNED_SUGGESTIONS:
            # Check if a pinned entry with the same keys already exists
            existing = await session.execute(
                text(
                    "SELECT id FROM ai_suggestions "
                    "WHERE human_verdict = 'pinned' "
                    "  AND field = :field "
                    "  AND lower(prompt_context->>'failure_mode') = lower(:fm) "
                    "  AND lower(prompt_context->>'function')     = lower(:fn) "
                    "LIMIT 1"
                ),
                {
                    "field": entry["field"],
                    "fm":    entry["failure_mode"],
                    "fn":    entry["function"],
                },
            )
            if existing.fetchone():
                print(f"[SKIP] Already pinned: field={entry['field']} | fm={entry['failure_mode'][:40]}")
                continue

            import json
            new_id = str(uuid.uuid4())
            prompt_context_json = json.dumps(
                {
                    "field":        entry["field"],
                    "failure_mode": entry["failure_mode"],
                    "function":     entry["function"],
                    "agent_color":  entry["agent_color"],
                    "sources":      entry["sources"],
                }
            )
            judge_correct_json   = json.dumps(entry["judge_correct_points"])
            judge_incorrect_json = json.dumps(entry["judge_incorrect_points"])

            await session.execute(
                text(
                    """
                    INSERT INTO ai_suggestions (
                        id, session_id, fmea_record_id,
                        agent_name, field, model_name,
                        suggested_value, justification,
                        confidence, prompt_context,
                        judge_verdict, judge_correct_points, judge_incorrect_points,
                        judge_confidence,
                        human_verdict
                    ) VALUES (
                        :id, NULL, NULL,
                        :agent_name, :field, 'pinned',
                        :suggested_value, :justification,
                        1.0, CAST(:prompt_context AS jsonb),
                        :judge_verdict,
                        CAST(:judge_correct_points AS jsonb),
                        CAST(:judge_incorrect_points AS jsonb),
                        :judge_confidence,
                        'pinned'
                    )
                    """
                ),
                {
                    "id":                   new_id,
                    "agent_name":           entry["agent_name"],
                    "field":                entry["field"],
                    "suggested_value":      entry["suggested_value"],
                    "justification":        entry["justification"],
                    "prompt_context":       prompt_context_json,
                    "judge_verdict":        entry["judge_verdict"],
                    "judge_correct_points": judge_correct_json,
                    "judge_incorrect_points": judge_incorrect_json,
                    "judge_confidence":     entry["judge_confidence"],
                },
            )
            print(f"[OK]   Pinned: field={entry['field']} | fm={entry['failure_mode'][:40]}")

        await session.commit()
        print("Done.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
