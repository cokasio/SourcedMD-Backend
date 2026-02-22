"""
PubMed research endpoint with GRADE evidence grading.
Uses NCBI E-utilities API (free, no key required for basic use).
"""
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import xml.etree.ElementTree as ET

router = APIRouter()

PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
PUBMED_SUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"


class ResearchRequest(BaseModel):
    query: str
    max_results: int = 10
    filter_study_type: Optional[str] = None  # RCT, systematic_review, meta_analysis


def grade_evidence(pub_type: str, study_design: str) -> dict:
    """
    Apply GRADE evidence grading framework.
    Returns: quality level (HIGH/MODERATE/LOW/VERY_LOW), confidence, reasoning
    """
    pub_type_lower = pub_type.lower()
    study_lower = study_design.lower()

    if any(t in pub_type_lower for t in ["systematic review", "meta-analysis"]):
        return {
            "grade": "HIGH",
            "confidence": 0.95,
            "label": "High Quality Evidence",
            "reasoning": "Systematic review or meta-analysis of RCTs — highest level of evidence"
        }
    elif any(t in pub_type_lower for t in ["randomized controlled", "clinical trial"]):
        return {
            "grade": "MODERATE",
            "confidence": 0.75,
            "label": "Moderate Quality Evidence",
            "reasoning": "Randomized controlled trial — strong design, potential limitations"
        }
    elif any(t in study_lower for t in ["cohort", "case-control", "observational"]):
        return {
            "grade": "LOW",
            "confidence": 0.50,
            "label": "Low Quality Evidence",
            "reasoning": "Observational study — confounding factors possible"
        }
    else:
        return {
            "grade": "VERY_LOW",
            "confidence": 0.25,
            "label": "Very Low Quality Evidence",
            "reasoning": "Case report, expert opinion, or unclear study design"
        }


@router.post("/research/medical")
async def search_medical_research(request: ResearchRequest):
    """
    Search PubMed and apply GRADE evidence grading to results.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Search PubMed for IDs
            search_params = {
                "db": "pubmed",
                "term": request.query,
                "retmax": request.max_results,
                "retmode": "json",
                "sort": "relevance",
            }
            if request.filter_study_type:
                type_filters = {
                    "RCT": "Clinical Trial[pt]",
                    "systematic_review": "Systematic Review[pt]",
                    "meta_analysis": "Meta-Analysis[pt]",
                }
                if request.filter_study_type in type_filters:
                    search_params["term"] += f" AND {type_filters[request.filter_study_type]}"

            search_resp = await client.get(PUBMED_SEARCH_URL, params=search_params)
            search_data = search_resp.json()
            ids = search_data.get("esearchresult", {}).get("idlist", [])

            if not ids:
                return {"query": request.query, "results": [], "total": 0}

            # Step 2: Fetch summaries
            summary_params = {
                "db": "pubmed",
                "id": ",".join(ids),
                "retmode": "json",
            }
            summary_resp = await client.get(PUBMED_SUMMARY_URL, params=summary_params)
            summary_data = summary_resp.json()
            articles = summary_data.get("result", {})

            results = []
            for pmid in ids:
                if pmid not in articles:
                    continue
                article = articles[pmid]
                pub_types = article.get("pubtype", [])
                pub_type_str = ", ".join(pub_types) if pub_types else "Unknown"
                grade = grade_evidence(pub_type_str, pub_type_str)

                authors = article.get("authors", [])
                author_names = [a.get("name", "") for a in authors[:3]]
                if len(authors) > 3:
                    author_names.append("et al.")

                results.append({
                    "pmid": pmid,
                    "title": article.get("title", ""),
                    "authors": author_names,
                    "journal": article.get("source", ""),
                    "year": article.get("pubdate", "")[:4],
                    "pub_type": pub_type_str,
                    "doi": article.get("elocationid", ""),
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "grade": grade,
                })

            # Sort by GRADE quality
            grade_order = {"HIGH": 0, "MODERATE": 1, "LOW": 2, "VERY_LOW": 3}
            results.sort(key=lambda x: grade_order.get(x["grade"]["grade"], 4))

            return {
                "query": request.query,
                "total": len(results),
                "results": results,
                "grade_summary": {
                    "high": sum(1 for r in results if r["grade"]["grade"] == "HIGH"),
                    "moderate": sum(1 for r in results if r["grade"]["grade"] == "MODERATE"),
                    "low": sum(1 for r in results if r["grade"]["grade"] == "LOW"),
                    "very_low": sum(1 for r in results if r["grade"]["grade"] == "VERY_LOW"),
                }
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PubMed search failed: {str(e)}")
