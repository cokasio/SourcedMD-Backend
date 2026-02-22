"""
Master healthcare analysis endpoint.
Combines: PubMed research + ClinicalTrials + Specialist consensus.
"""
import asyncio
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class AnalyzeRequest(BaseModel):
    condition: str
    symptoms: Optional[str] = None
    history: Optional[str] = None
    medications: Optional[str] = None
    specialist_count: int = 5


@router.post("/healthcare/analyze")
async def analyze_condition(request: AnalyzeRequest):
    """
    Master analysis: PubMed + Trials + Consensus in parallel.
    """
    base_url = "http://localhost:8000"

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Run all three in parallel
        research_task = client.post(f"{base_url}/api/research/medical", json={
            "query": request.condition,
            "max_results": 5
        })
        trials_task = client.get(f"{base_url}/api/clinical-trials/search", params={
            "condition": request.condition,
            "max_results": 5
        })
        consensus_task = client.post(f"{base_url}/api/consensus/specialists", json={
            "condition": request.condition,
            "symptoms": request.symptoms,
            "context": request.history,
            "specialist_count": request.specialist_count
        })

        research_resp, trials_resp, consensus_resp = await asyncio.gather(
            research_task, trials_task, consensus_task,
            return_exceptions=True
        )

    research_data = research_resp.json() if not isinstance(research_resp, Exception) else {"error": str(research_resp), "results": []}
    trials_data = trials_resp.json() if not isinstance(trials_resp, Exception) else {"error": str(trials_resp), "results": []}
    consensus_data = consensus_resp.json() if not isinstance(consensus_resp, Exception) else {"error": str(consensus_resp), "specialist_opinions": []}

    return {
        "condition": request.condition,
        "disclaimer": "This is a research tool for information purposes only. Not medical advice. Consult a qualified healthcare professional.",
        "research": research_data,
        "clinical_trials": trials_data,
        "specialist_consensus": consensus_data,
        "summary": {
            "papers_found": len(research_data.get("results", [])),
            "trials_found": len(trials_data.get("results", [])),
            "specialists_consulted": consensus_data.get("specialists_consulted", 0),
            "consensus_score": consensus_data.get("consensus_score", 0),
        }
    }
