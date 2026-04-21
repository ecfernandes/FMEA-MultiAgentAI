"""Test JSON mode and Pydantic extraction with UTC LLM platform."""
import json
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("UTCLLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL"),
)

MODEL = "mistral-small3.2:latest"

SYSTEM = (
    "You are an FMEA analyst. Return ONLY a valid JSON object with exactly "
    'these keys: "part_name" (string), "supplier" (string), '
    '"functions" (array of strings). No markdown, no extra text.'
)

USER = (
    "Extract FMEA header from this text:\n\n"
    "Part Name: Window Regulator Motor\n"
    "Supplier: Brose GmbH\n"
    "Functions:\n"
    "- To allow window lifting\n"
    "- To resist applied force\n"
    "- To ensure watertightness"
)

# Test 1: with response_format json_object
print("=" * 60)
print("Test 1: response_format={'type': 'json_object'}")
print("=" * 60)
try:
    r = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user",   "content": USER},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
        max_tokens=300,
    )
    txt = r.choices[0].message.content
    data = json.loads(txt)
    print("STATUS: OK")
    print("part_name:", data.get("part_name"))
    print("supplier:", data.get("supplier"))
    print("functions:", data.get("functions"))
except Exception as e:
    print("STATUS: FAILED ->", e)

# Test 2: without response_format (plain text JSON)
print()
print("=" * 60)
print("Test 2: sem response_format (texto livre)")
print("=" * 60)
try:
    r2 = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user",   "content": USER},
        ],
        temperature=0.0,
        max_tokens=300,
    )
    txt2 = r2.choices[0].message.content.strip()
    # Strip markdown fences if present
    if txt2.startswith("```"):
        txt2 = txt2.split("```")[1]
        if txt2.startswith("json"):
            txt2 = txt2[4:]
    data2 = json.loads(txt2)
    print("STATUS: OK")
    print("part_name:", data2.get("part_name"))
    print("supplier:", data2.get("supplier"))
    print("functions:", data2.get("functions"))
except Exception as e:
    print("STATUS: FAILED ->", e)
    print("Raw response:", txt2 if 'txt2' in dir() else "N/A")
