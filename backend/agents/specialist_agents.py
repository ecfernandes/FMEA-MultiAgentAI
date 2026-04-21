"""
backend/agents/specialist_agents.py
-------------------------------------
Multi-specialist AI orchestrator for FMEA 5.0.

Each agent maps to a reference engineering domain and a reference book.
The router selects the best-matching specialist by keyword scoring against
the combined (function + failure_mode) text, then makes a single structured
LLM call to the UTC platform.

Usage (from FastAPI endpoint):
    from backend.agents.specialist_agents import route_and_call
    result = await route_and_call(request, api_key)
"""

from __future__ import annotations

import json
import os
import re
from typing import Optional

from openai import AsyncOpenAI

from backend.schemas import AgentRequest, AgentResponse


# ============================================================================
# SPECIALIST REGISTRY
# ============================================================================

SPECIALIST_MAP: dict = {
    "Assembly Technologies Agent": {
        "file": "Assembly-Handbook of Joining Technologies (M. Kutz).pdf",
        "description": (
            "Joining technology expert: welding, riveting, fasteners, adhesives, "
            "press-fit, clinching, self-pierce riveting and their failure modes."
        ),
        "keywords": [
            "assembly", "weld", "joining", "fastener", "bolt", "rivet",
            "adhesive", "bond", "insert", "press fit", "torque", "crimp", "clinch",
            "screw", "thread", "nut",
        ],
    },
    "Corrosion Agent": {
        "file": "Chemical - Corrosion Engineering Principles and Practice (Pierre Roberge).pdf",
        "description": (
            "Corrosion engineering: galvanic, crevice, pitting, uniform corrosion, "
            "oxidation, electrochemical degradation, protective coatings."
        ),
        "keywords": [
            "corrosion", "rust", "oxidation", "chemical", "galvanic", "electrolytic",
            "coating", "degradation", "electrochemical", "pitting", "crevice",
            "zinc", "protection", "paint",
        ],
    },
    "Fatigue Agent": {
        "file": "Fatigue-Metal Fatigue in Engineering (Stephens and Fuchs).pdf",
        "description": (
            "Metal fatigue expert: S-N curves, Paris Law crack propagation, "
            "cyclic loading, fatigue life estimation, weld fatigue, high-cycle fatigue."
        ),
        "keywords": [
            "fatigue", "crack", "fracture", "cyclic", "propagation",
            "wöhler", "paris", "rupture", "break", "broken", "overload",
            "fatigue crack", "crack initiation",
        ],
    },
    "FEA Specialist": {
        "file": "FEA - finite-element-method-its-basis-and-fundamentals.pdf",
        "description": (
            "Finite element analysis: structural simulation, stress concentration "
            "factors Kt, deflection, buckling, load path analysis."
        ),
        "keywords": [
            "fea", "finite element", "simulation", "mesh", "stress concentration",
            "deformation", "structural", "deflection", "buckling", "load path",
            "analysis", "element",
        ],
    },
    "Materials Agent": {
        "file": "Materials - Materials Selection in Mechanical Design (Michael Ashby).pdf",
        "description": (
            "Material selection expert: mechanical properties (UTS, yield, hardness), "
            "Ashby charts, creep, thermal properties, failure from wrong material choice."
        ),
        "keywords": [
            "material", "alloy", "polymer", "composite", "yield", "tensile",
            "hardness", "stiffness", "thermal expansion", "creep", "modulus",
            "selection", "property",
        ],
    },
    "Dynamics Agent": {
        "file": "MBS-Dynamics of Multibody Systems (Ahmed Shabana).pdf",
        "description": (
            "Multibody dynamics: kinematic chains, inertia, dynamic loads, "
            "rigid body motion, linkage mechanisms, impact loads."
        ),
        "keywords": [
            "dynamic", "kinematics", "inertia", "multibody", "motion",
            "acceleration", "velocity", "linkage", "kinematic", "rigid body",
            "impact", "load spectrum",
        ],
    },
    "Mechanical Design Agent": {
        "file": "Mechanical-Cinematic--MechanicalEngineeringDesign-Shigley.pdf",
        "description": (
            "Shigley-based mechanical design: shafts, bearings, gears, springs, "
            "bending/torsion stress, keys, couplings, design for strength."
        ),
        "keywords": [
            "shaft", "bearing", "gear", "spring", "mechanical design",
            "torque", "bending", "torsion", "key", "coupling", "pulley",
            "stress", "shigley",
        ],
    },
    "Mechatronics Agent": {
        "file": "Mechatronics-Automotive Mechatronics Operational and Practical Issues (BT Fijalkowski).pdf",
        "description": (
            "Automotive mechatronics: sensors, actuators, ECU, CAN bus, "
            "PWM motor control, encoder feedback, short-circuit, signal loss."
        ),
        "keywords": [
            "mechatronics", "sensor", "actuator", "ecu", "can bus", "signal",
            "electronic", "control unit", "motor driver", "pwm", "encoder",
            "electrical", "short circuit", "open circuit", "voltage",
        ],
    },
    "Metal Stamping Agent": {
        "file": "MetalStamping-Handbook of Metal Forming (Kurt Lange).pdf",
        "description": (
            "Sheet metal forming: stamping, deep drawing, springback, "
            "tool wear, thinning, blanking, piercing, press force."
        ),
        "keywords": [
            "stamping", "forming", "sheet metal", "drawing", "punch", "die",
            "springback", "thinning", "blanking", "piercing", "press",
            "metal forming", "deep drawing",
        ],
    },
    "NVH Agent": {
        "file": "NVH_vehicle-noise-and-vibration-refinement(XuHang).pdf",
        "description": (
            "Noise, vibration, harshness: resonance, acoustic isolation, "
            "rattle, squeak, vibration damping, structure-borne noise, modal analysis."
        ),
        "keywords": [
            "noise", "vibration", "nvh", "harshness", "resonance", "acoustic",
            "rattle", "squeak", "frequency", "damper", "isolation", "buzz",
            "modal", "decibel",
        ],
    },
    "Plastic Injection Agent": {
        "file": "Plastic Injection - Injection Molding Handbook (Dominick Rosato).pdf",
        "description": (
            "Plastic injection molding: sink marks, warpage, flash, weld lines, "
            "shrinkage, gate location, thermoplastic defects, mold design."
        ),
        "keywords": [
            "plastic", "injection", "molding", "polymer", "sink", "warp",
            "gate", "shrinkage", "flash", "void", "weld line", "thermoplastic",
            "overmold", "mold",
        ],
    },
    "Dimensioning and Tolerancing Agent": {
        "file": "Tolerance-Geometric Dimensioning and Tolerancing (James D. Meadows).pdf",
        "description": (
            "GD&T specialist: geometric tolerances, datum references, "
            "tolerance stack-up, clearance fits, runout, flatness, concentricity."
        ),
        "keywords": [
            "tolerance", "gdt", "dimensional", "clearance", "fit", "datum",
            "runout", "flatness", "concentricity", "perpendicularity", "stack-up",
            "position", "profile",
        ],
    },
    "Tribology Agent": {
        "file": "Tribology-Engineering Tribology (Stachowiak & Batchelor).pdf",
        "description": (
            "Tribology expert: friction, lubrication, abrasive/adhesive wear, "
            "surface contact stress, Hertz theory, lubricant breakdown, galling."
        ),
        "keywords": [
            "wear", "friction", "lubrication", "tribology", "abrasion", "adhesion",
            "sliding", "contact", "surface", "lubricant", "oil", "grease",
            "galling", "scoring",
        ],
    },
}

_AGENT_COLORS: dict = {
    "Assembly Technologies Agent":        "#8b5cf6",
    "Corrosion Agent":                    "#f59e0b",
    "Fatigue Agent":                      "#ef4444",
    "FEA Specialist":                     "#10b981",
    "Materials Agent":                    "#84cc16",
    "Dynamics Agent":                     "#06b6d4",
    "Mechanical Design Agent":            "#f97316",
    "Mechatronics Agent":                 "#a78bfa",
    "Metal Stamping Agent":               "#e879f9",
    "NVH Agent":                          "#fb923c",
    "Plastic Injection Agent":            "#34d399",
    "Dimensioning and Tolerancing Agent": "#60a5fa",
    "Tribology Agent":                    "#fbbf24",
}

_FIELD_LABEL: dict = {
    "failure_mode":                 "Potential Failure Mode",
    "effect":                       "Potential Effect on Customer / System",
    "cause":                        "Root Cause / Failure Mechanism",
    "severity":                     "Severity (S) — integer 1-10",
    "occurrence":                   "Occurrence (O) — integer 1-10",
    "detection":                    "Detection (D) — integer 1-10",
    "current_controls_prevention":  "Current Design Controls — Prevention (actions that prevent the cause from occurring)",
    "current_controls_detection":   "Current Design Controls — Detection (actions that detect the failure before it reaches the customer)",
    "recommended_action":           "Recommended Action(s) to reduce risk (corrective or preventive)",
}

_FIELD_IS_NUMERIC = {"severity", "occurrence", "detection"}

BOOKS_PATH = "Books/"


# ============================================================================
# ROUTING
# ============================================================================

def route_agent(function: str, failure_mode: str) -> str:
    """Score all specialists against combined input text; return best match name."""
    combined = f"{function} {failure_mode}".lower()
    best_agent = next(iter(SPECIALIST_MAP))
    best_score = 0
    for agent_name, spec in SPECIALIST_MAP.items():
        score = sum(1 for kw in spec["keywords"] if kw in combined)
        if score > best_score:
            best_score = score
            best_agent = agent_name
    return best_agent


# ============================================================================
# ASYNC AGENT CALL
# ============================================================================

async def route_and_call(request: AgentRequest, api_key: str) -> AgentResponse:
    """
    Select the best-matching specialist for the request and call the UTC LLM.

    This is the async version of the legacy get_ai_suggestion() function in
    ai_agents.py — designed for use inside FastAPI async endpoints.

    Args:
        request:  Validated AgentRequest from the HTTP body.
        api_key:  UTC platform API key (sk-... format).

    Returns:
        AgentResponse with suggested value, justification and sources.
    """
    agent_name  = route_agent(request.function, request.failure_mode)
    spec        = SPECIALIST_MAP[agent_name]
    book_file   = spec["file"]
    book_domain = spec["description"]
    field_label = _FIELD_LABEL.get(request.field, request.field.replace("_", " ").title())
    is_numeric  = request.field in _FIELD_IS_NUMERIC

    system_prompt = (
        f"You are a senior FMEA engineer. Your domain of expertise: {book_domain}\n"
        f"Reference document: {book_file}\n\n"
        f'Return a valid JSON object with exactly these two keys:\n'
        f'  "suggested_value": '
        + ('"an integer between 1 and 10 — no quotes, no explanation inline"'
           if is_numeric else '"a concise technical string, maximum 150 characters"')
        + '\n  "justification":   "3 to 5 sentences of dense engineering reasoning"\n\n'
        "STRICT RULES:\n"
        '- Do NOT write "Based on the book", "According to", "The agent suggests", "As per..."\n'
        "- Write as a direct engineering technical verdict in first person\n"
        "- Cite quantitative data where applicable (failure rates, stress limits, detection thresholds)\n"
        "- Every sentence must carry technical content — no padding\n"
        "- Return ONLY the raw JSON object — no markdown fences, no commentary"
    )

    rag_chunks = []

    user_prompt = (
        f"Part / component context: {request.context}\n"
        f"Item function: {request.function}\n"
        f"Failure mode: {request.failure_mode}\n"
        f"\nProvide your expert assessment for the FMEA field: {field_label}"
    )

    base_url = os.getenv("LLM_BASE_URL", "https://ia.beta.utc.fr/api/v1")
    model    = request.model_name or os.getenv("LLM_DEFAULT_MODEL", "qwen3527b-no-think")

    val: Optional[str | int] = None
    justification = "Agent call failed — check API key and connection."

    try:
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=512,
        )
        raw = response.choices[0].message.content.strip()

        # 1. Strip <think>...</think> blocks (reasoning models: Magistral, Olmo Think, etc.)
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

        # 2. Strip markdown code fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        if raw.endswith("```"):
            raw = raw[: raw.rfind("```")].strip()

        # 3. Regex fallback: extract first {...} block in case the model added preamble text
        if not raw.startswith("{"):
            m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
            if m:
                raw = m.group(0)

        data = json.loads(raw)
        val  = data.get("suggested_value")

        if is_numeric and val is not None:
            try:
                val = int(val)
            except (ValueError, TypeError):
                val = None

        justification = data.get("justification", "No justification returned.")

    except Exception as exc:
        val           = None if is_numeric else "Unable to generate suggestion"
        justification = (
            f"Model '{model}' failed to return valid structured JSON. "
            f"Small models (< 7B) often cannot follow strict JSON output instructions — "
            f"switch to Qwen3.5 27b for reliable results. "
            f"Error: {exc}"
        )

    return AgentResponse(
        agent_name      = agent_name,
        agent_color     = _AGENT_COLORS.get(agent_name, "#6b7280"),
        suggested_value = val,
        justification   = justification,
        sources         = [f"📖 {book_file}"],
    )
