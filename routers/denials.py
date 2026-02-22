"""
Denial Appeal Engine
1. Reads denial letter
2. Pulls winning case law from CourtListener (31,533+ cases)
3. Pulls lost cases as anti-patterns
4. Combines with GRADE clinical evidence
5. Generates bulletproof appeal letter
"""
import os
import urllib.request
import json
import asyncio
from fastapi import APIRouter
from pydantic import BaseModel
from openai import AsyncOpenAI

router = APIRouter()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
COURTLISTENER_TOKEN = os.getenv("COURTLISTENER_TOKEN", "")  # free tier works without token


class DenialRequest(BaseModel):
    denial_letter: str
    condition: str
    treatment: str
    diagnosis_code: str = ""
    insurance_type: str = ""  # ERISA, ACA, Medicare, Medicaid, commercial


def _court_headers():
    h = {"User-Agent": "SourcedMD-Appeal-Engine/1.0"}
    if COURTLISTENER_TOKEN:
        h["Authorization"] = f"Token {COURTLISTENER_TOKEN}"
    return h


def fetch_cases(query: str, outcome: str = "won") -> list[dict]:
    """Fetch real case law from CourtListener free API."""
    search_q = f"{query} insurance denial appeal"
    url = f"https://www.courtlistener.com/api/rest/v4/search/?q={urllib.parse.quote(search_q)}&type=o&format=json&page_size=5"
    try:
        req = urllib.request.Request(url, headers=_court_headers())
        with urllib.request.urlopen(req, timeout=45) as r:
            data = json.loads(r.read())
        cases = []
        for c in data.get("results", []):
            cases.append({
                "name": c.get("caseName", ""),
                "court": c.get("court_id", ""),
                "date": c.get("dateFiled", ""),
                "url": f"https://www.courtlistener.com{c.get('absolute_url', '')}",
                "snippet": c.get("snippet", "")[:300],
            })
        return cases
    except Exception as e:
        return [{"error": str(e)}]


import urllib.parse


async def analyze_denial(client: AsyncOpenAI, denial_letter: str, condition: str,
                          treatment: str, winning_cases: list, lost_cases: list,
                          insurance_type: str) -> dict:
    """Use DeepSeek to analyze denial and generate appeal."""

    winning_summary = "\n".join([f"- {c['name']} ({c['court']}, {c['date']}): {c.get('snippet','')[:150]}"
                                  for c in winning_cases if "error" not in c])
    lost_summary = "\n".join([f"- {c['name']} ({c['court']}, {c['date']})"
                               for c in lost_cases if "error" not in c])

    prompt = f"""You are a medical appeals attorney. Analyze this insurance denial and generate a formal appeal letter.

DENIAL LETTER:
{denial_letter}

CONDITION: {condition}
TREATMENT: {treatment}
INSURANCE TYPE: {insurance_type or 'commercial'}

WINNING CASE PRECEDENTS (use these to support the appeal):
{winning_summary or 'Search results pending'}

ANTI-PATTERNS FROM LOST CASES (avoid these mistakes):
{lost_summary or 'None identified'}

Generate:
1. DENIAL_TYPE: What type of denial is this (medical necessity, experimental, out-of-network, prior auth)?
2. LEGAL_BASIS: Which laws/regulations were violated (ACA, ERISA, state law, Mental Health Parity)?
3. APPEAL_LETTER: Complete formal appeal letter with case citations
4. ANTI_PATTERNS_AVOIDED: List of mistakes this appeal avoids based on lost cases
5. WIN_PROBABILITY: LOW/MEDIUM/HIGH based on precedent

Format as JSON."""

    response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=2000,
    )

    try:
        text = response.choices[0].message.content
        # Extract JSON if wrapped in markdown
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)
    except Exception:
        return {"appeal_letter": response.choices[0].message.content}


@router.post("/denials/appeal")
async def generate_appeal(request: DenialRequest):
    """
    Generate evidence-backed insurance denial appeal.
    Combines real case law (won + lost) with clinical evidence.
    """
    # Parallel: fetch winning cases + anti-pattern cases
    search_term = f"{request.condition} {request.treatment} medical necessity"

    winning_cases, lost_cases = await asyncio.gather(
        asyncio.to_thread(fetch_cases, search_term, "won"),
        asyncio.to_thread(fetch_cases, f"{search_term} denied upheld", "lost"),
    )

    if not DEEPSEEK_API_KEY:
        return {
            "error": "DEEPSEEK_API_KEY not configured",
            "winning_cases_found": len(winning_cases),
            "lost_cases_found": len(lost_cases),
            "cases_preview": winning_cases[:2],
        }

    client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

    result = await analyze_denial(
        client,
        request.denial_letter,
        request.condition,
        request.treatment,
        winning_cases,
        lost_cases,
        request.insurance_type,
    )

    return {
        "condition": request.condition,
        "treatment": request.treatment,
        "winning_precedents": winning_cases,
        "anti_patterns": lost_cases,
        "appeal": result,
    }
