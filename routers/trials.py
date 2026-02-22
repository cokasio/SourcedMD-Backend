"""
ClinicalTrials.gov search endpoint.
Uses free public API — no key required.
"""
import httpx
from fastapi import APIRouter, HTTPException
from typing import Optional

router = APIRouter()

TRIALS_API_URL = "https://clinicaltrials.gov/api/v2/studies"


@router.get("/clinical-trials/search")
async def search_trials(
    condition: str,
    status: Optional[str] = "RECRUITING",
    phase: Optional[str] = None,
    max_results: int = 10,
):
    """
    Search ClinicalTrials.gov for relevant studies.
    """
    try:
        params = {
            "query.cond": condition,
            "filter.overallStatus": status,
            "pageSize": max_results,
            "format": "json",
            "fields": "NCTId,BriefTitle,OverallStatus,Phase,Condition,InterventionName,LocationFacility,LocationCity,LocationCountry,StartDate,PrimaryCompletionDate,EnrollmentCount,StudyType",
        }
        if phase:
            params["filter.phase"] = phase

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(TRIALS_API_URL, params=params)
            data = resp.json()

        studies = data.get("studies", [])
        results = []
        for study in studies:
            proto = study.get("protocolSection", {})
            id_module = proto.get("identificationModule", {})
            status_module = proto.get("statusModule", {})
            design_module = proto.get("designModule", {})
            conditions_module = proto.get("conditionsModule", {})
            interventions_module = proto.get("armsInterventionsModule", {})
            locations_module = proto.get("contactsLocationsModule", {})

            locations = locations_module.get("locations", [])
            loc_summaries = [
                f"{l.get('facility', '')} — {l.get('city', '')}, {l.get('country', '')}"
                for l in locations[:3]
            ]

            interventions = interventions_module.get("interventions", [])
            intervention_names = [i.get("name", "") for i in interventions[:3]]

            results.append({
                "nct_id": id_module.get("nctId", ""),
                "title": id_module.get("briefTitle", ""),
                "status": status_module.get("overallStatus", ""),
                "phase": design_module.get("phases", []),
                "study_type": design_module.get("studyType", ""),
                "conditions": conditions_module.get("conditions", []),
                "interventions": intervention_names,
                "locations": loc_summaries,
                "enrollment": design_module.get("enrollmentInfo", {}).get("count", None),
                "start_date": status_module.get("startDateStruct", {}).get("date", ""),
                "completion_date": status_module.get("primaryCompletionDateStruct", {}).get("date", ""),
                "url": f"https://clinicaltrials.gov/study/{id_module.get('nctId', '')}",
            })

        return {
            "condition": condition,
            "status_filter": status,
            "total": len(results),
            "results": results,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ClinicalTrials.gov search failed: {str(e)}")
