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
    "Automotive Safety Systems Agent": {
        "file": "Standard-Design And Process Fmea (Failure Mode, Effects And Criticality Analysis).pdf",
        "description": (
            "Automotive restraint systems expert: airbag cushion, inflator, squib, "
            "pyrotechnic deployment, folding process, SRS module, cover integration, "
            "FMVSS 208 compliance, ISO 26262 functional safety, deployment pressure "
            "and timing, fabric seam integrity, vent hole sizing."
        ),
        "keywords": [
            "airbag", "cushion", "inflator", "squib", "deployment", "pyrotechnic",
            "restraint", "srs", "fold", "folding", "cover", "bag", "module",
            "fmvss", "iso 26262", "functional safety", "vent hole", "seam",
            "curtain", "side airbag", "driver airbag", "passenger airbag",
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
    "Automotive Safety Systems Agent":    "#f43f5e",
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

def _route_by_keywords(function: str, failure_mode: str) -> str:
    """Keyword scoring fallback — uses whole-word matching to avoid substring false positives."""
    combined = f"{function} {failure_mode}".lower()
    best_agent = next(iter(SPECIALIST_MAP))
    best_score = 0
    for agent_name, spec in SPECIALIST_MAP.items():
        score = sum(
            1 for kw in spec["keywords"]
            if re.search(r"\b" + re.escape(kw) + r"\b", combined)
        )
        if score > best_score:
            best_score = score
            best_agent = agent_name
    return best_agent


def _build_router_prompt() -> str:
    """Build the system prompt for the LLM router listing all available specialists."""
    lines = [
        "You are an FMEA specialist routing agent. Your only task is to select",
        "the single most relevant specialist for the given component function",
        "and failure mode.",
        "",
        "Available specialists:",
    ]
    for name, spec in SPECIALIST_MAP.items():
        # Use first sentence of description as a short label
        short = spec["description"].split(":")[1].split(".")[0].strip() if ":" in spec["description"] else spec["description"]
        lines.append(f"- {name}: {short}")
    lines += [
        "",
        "Rules:",
        "- Reply with ONLY the exact specialist name from the list above",
        "- Do not add any explanation, punctuation, or extra text",
        "- If uncertain, choose the specialist whose domain is closest to the physical failure mechanism",
    ]
    return "\n".join(lines)


_ROUTER_SYSTEM_PROMPT: str = _build_router_prompt()


# ============================================================================
# LLM-AS-JUDGE
# ============================================================================

_JUDGE_SYSTEM_PROMPT = (
    "You are a senior automotive FMEA quality auditor. Your task is to evaluate "
    "whether an AI-generated FMEA field assessment is technically sound and "
    "coherent with the component described.\n\n"
    "Return JSON with exactly four keys:\n"
    '  "verdict":           "correct" | "partial" | "incorrect"\n'
    '  "correct_points":    ["list of technically valid statements"]\n'
    '  "incorrect_points":  ["list of technically invalid statements"]\n'
    '  "confidence":        float 0.0 to 1.0\n\n'
    "Verdict criteria:\n"
    '  "correct"   — all points valid, no inconsistencies\n'
    '  "partial"   — majority valid but at least one incoherent statement\n'
    '  "incorrect" — fundamentally incoherent with component or failure mode\n\n'
    "Reference always applicable: Renault Standard - Design And Process FMEA\n\n"
    "RULES:\n"
    "- Evaluate technical coherence, not writing style\n"
    "- Flag statements contradicting the physical nature of the component\n"
    "- Flag materials, processes or standards inconsistent with part type\n"
    "- Return ONLY raw JSON, no markdown fences"
)


async def _judge_response(
    *,
    context: str,
    function: str,
    failure_mode: str,
    field_label: str,
    agent_name: str,
    suggested_value: Optional[str | int],
    justification: str,
    api_key: str,
    model: str,
    base_url: str,
) -> dict:
    """
    Call the LLM judge to evaluate the agent's output.

    Returns a dict with keys: verdict, correct_points, incorrect_points, confidence.
    On any failure returns a safe 'partial' fallback so the response is never blocked
    due to a judge error.
    """
    user_prompt = (
        f"Component context: {context}\n"
        f"Item function: {function}\n"
        f"Failure mode: {failure_mode}\n"
        f"FMEA field assessed: {field_label}\n"
        f"Specialist selected: {agent_name}\n"
        f"AI-generated assessment: {suggested_value}\n"
        f"Justification provided: {justification}\n"
        "Reference standard: Renault Standard - Design And Process FMEA\n"
        "Evaluate technical coherence with the component and failure mode described."
    )

    _fallback: dict = {
        "verdict": "partial",
        "correct_points": [],
        "incorrect_points": ["Judge failed to evaluate — review manually"],
        "confidence": 0.0,
    }

    try:
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _JUDGE_SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0,
            max_tokens=400,
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        if raw.endswith("```"):
            raw = raw[: raw.rfind("```")].strip()
        if not raw.startswith("{"):
            m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
            if m:
                raw = m.group(0)
        result = json.loads(raw)
        if result.get("verdict") not in ("correct", "partial", "incorrect"):
            return _fallback
        result.setdefault("correct_points", [])
        result.setdefault("incorrect_points", [])
        result.setdefault("confidence", 0.0)
        return result
    except Exception:
        return _fallback


async def _route_by_llm(
    function: str,
    failure_mode: str,
    api_key: str,
) -> str | None:
    """
    Ask the LLM to select the most relevant specialist.

    Returns the agent name if valid, None if the LLM response is not in SPECIALIST_MAP.
    Falls back gracefully on any network or parse error.
    """
    base_url = os.getenv("LLM_BASE_URL", "https://ia.beta.utc.fr/api/v1")
    model    = os.getenv("LLM_DEFAULT_MODEL", "RedHatAI/Qwen3.6-35B-A3B-NVFP4")

    try:
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _ROUTER_SYSTEM_PROMPT},
                {"role": "user",   "content": f"Function: {function}\nFailure mode: {failure_mode}"},
            ],
            temperature=0,
            max_tokens=20,
        )
        raw = response.choices[0].message.content.strip()
        # Strip any <think>...</think> blocks from reasoning models
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        # Validate — only accept names that actually exist
        if raw in SPECIALIST_MAP:
            return raw
        # Try case-insensitive match as safety net
        for name in SPECIALIST_MAP:
            if name.lower() == raw.lower():
                return name
        return None
    except Exception:
        return None


async def route_agent(function: str, failure_mode: str, api_key: str) -> str:
    """
    LLM-first router with keyword fallback.

    1. Ask the LLM to classify (temperature=0, max 20 tokens).
    2. Validate the response against SPECIALIST_MAP.
    3. If invalid or error, fall back to whole-word keyword scoring.

    Returns the agent name (always a valid key in SPECIALIST_MAP).
    """
    agent = await _route_by_llm(function, failure_mode, api_key)
    if agent is not None:
        return agent
    return _route_by_keywords(function, failure_mode)


# ============================================================================
# ASYNC AGENT CALL
# ============================================================================

async def _call_specialist_agent(
    agent_name: str,
    request: AgentRequest,
    api_key: str,
    base_url: str,
    model: str,
) -> tuple[Optional[str | int], str]:
    """
    Call the specialist LLM and return (suggested_value, justification).
    Extracted so route_and_call can retry without duplicating the call logic.
    """
    spec        = SPECIALIST_MAP[agent_name]
    book_file   = spec["file"]
    book_domain = spec["description"]
    field_label = _FIELD_LABEL.get(request.field, request.field.replace("_", " ").title())
    is_numeric  = request.field in _FIELD_IS_NUMERIC

    system_prompt = (
        f"You are a senior FMEA engineer. Your domain of expertise: {book_domain}\n"
        f"Reference document: {book_file}\n\n"
        'Return a valid JSON object with exactly these two keys:\n'
        '  "suggested_value": '
        + (
            '"an integer between 1 and 10 — no quotes, no explanation inline"'
            if is_numeric
            else '"a concise technical string, maximum 150 characters"'
          )
        + '\n  "justification":   "3 to 5 sentences of dense engineering reasoning"\n\n'
        "STRICT RULES:\n"
        '- Do NOT write "Based on the book", "According to", "The agent suggests", "As per..."\n'
        "- Write as a direct engineering technical verdict in first person\n"
        "- Cite quantitative data where applicable (failure rates, stress limits, detection thresholds)\n"
        "- Every sentence must carry technical content — no padding\n"
        "- Return ONLY the raw JSON object — no markdown fences, no commentary"
    )

    user_prompt = (
        f"Part / component context: {request.context}\n"
        f"Item function: {request.function}\n"
        f"Failure mode: {request.failure_mode}\n"
        f"\nProvide your expert assessment for the FMEA field: {field_label}"
    )

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

        # Strip <think>...</think> blocks (reasoning models)
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

        # Strip markdown code fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        if raw.endswith("```"):
            raw = raw[: raw.rfind("```")].strip()

        # Regex fallback: extract first {...} block in case the model added preamble text
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

    return val, justification


async def route_and_call(request: AgentRequest, api_key: str) -> AgentResponse:
    """
    Select the best-matching specialist, call it, then run the LLM-as-Judge.

    Judge verdict actions:
      correct   — deliver to engineer as-is
      partial   — deliver with warning; incorrect_points surface to the user for review
      incorrect — retry once with the same specialist, then deliver as partial

    Args:
        request:  Validated AgentRequest from the HTTP body.
        api_key:  UTC platform API key (sk-... format).

    Returns:
        AgentResponse with suggested value, justification, sources and judge fields.
    """
    agent_name  = await route_agent(request.function, request.failure_mode, api_key)
    spec        = SPECIALIST_MAP[agent_name]
    book_file   = spec["file"]
    field_label = _FIELD_LABEL.get(request.field, request.field.replace("_", " ").title())

    base_url = os.getenv("LLM_BASE_URL", "https://ia.beta.utc.fr/api/v1")
    model    = request.model_name or os.getenv("LLM_DEFAULT_MODEL", "RedHatAI/Qwen3.6-35B-A3B-NVFP4")

    val, justification = await _call_specialist_agent(
        agent_name, request, api_key, base_url, model
    )

    judge = await _judge_response(
        context         = request.context,
        function        = request.function,
        failure_mode    = request.failure_mode,
        field_label     = field_label,
        agent_name      = agent_name,
        suggested_value = val,
        justification   = justification,
        api_key         = api_key,
        model           = model,
        base_url        = base_url,
    )

    if judge["verdict"] == "incorrect":
        # Retry once — reclassify as partial so the response is never silently blocked
        val, justification = await _call_specialist_agent(
            agent_name, request, api_key, base_url, model
        )
        judge["verdict"] = "partial"
        if not judge["incorrect_points"]:
            judge["incorrect_points"] = [
                "Initial response was flagged as incorrect by the judge — this is a retry"
            ]

    return AgentResponse(
        agent_name             = agent_name,
        agent_color            = _AGENT_COLORS.get(agent_name, "#6b7280"),
        suggested_value        = val,
        justification          = justification,
        sources                = [book_file, "Renault Standard - Design And Process FMEA"],
        judge_verdict          = judge["verdict"],
        judge_correct_points   = judge.get("correct_points", []),
        judge_incorrect_points = judge.get("incorrect_points", []),
        judge_confidence       = judge.get("confidence"),
    )
