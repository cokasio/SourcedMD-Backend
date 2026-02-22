"""
62-Specialist Consensus Engine.
Runs a medical condition through multiple specialist perspectives in parallel.
Each specialist has distinct psychological profile, risk tolerance, and clinical lens.
"""
import asyncio
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import anthropic

router = APIRouter()

# 62 specialist types with psychological profiles
SPECIALISTS = [
    {"name": "Cardiologist", "focus": "cardiovascular risk, heart function, circulation", "bias": "risk-averse, evidence-focused"},
    {"name": "Neurologist", "focus": "brain function, nervous system, cognitive effects", "bias": "mechanistic thinking, precise"},
    {"name": "Endocrinologist", "focus": "hormones, metabolism, diabetes, thyroid", "bias": "systems-level, long-term"},
    {"name": "Oncologist", "focus": "cancer risk, tumor markers, malignancy", "bias": "worst-case scenario thinking"},
    {"name": "Pulmonologist", "focus": "lung function, breathing, respiratory", "bias": "functional outcomes"},
    {"name": "Gastroenterologist", "focus": "digestive system, liver, gut microbiome", "bias": "holistic gut-brain axis"},
    {"name": "Rheumatologist", "focus": "autoimmune, joints, inflammation", "bias": "chronic condition management"},
    {"name": "Nephrologist", "focus": "kidney function, fluid balance, electrolytes", "bias": "conservative, avoid harm"},
    {"name": "Infectious Disease Specialist", "focus": "pathogens, immunity, antimicrobials", "bias": "evidence-based, protocol-driven"},
    {"name": "Psychiatrist", "focus": "mental health, behavior, psychopharmacology", "bias": "biopsychosocial model"},
    {"name": "Hematologist", "focus": "blood disorders, coagulation, anemia", "bias": "laboratory-driven"},
    {"name": "Dermatologist", "focus": "skin manifestations, systemic skin disease", "bias": "visual pattern recognition"},
    {"name": "Ophthalmologist", "focus": "eye health, vision, retinal disease", "bias": "precision, preventive"},
    {"name": "Orthopedic Surgeon", "focus": "bones, joints, musculoskeletal", "bias": "structural, surgical when needed"},
    {"name": "General Surgeon", "focus": "surgical intervention criteria, post-op", "bias": "intervention threshold"},
    {"name": "Emergency Medicine Physician", "focus": "acute presentations, triage, immediate risk", "bias": "worst-first thinking"},
    {"name": "Family Medicine Physician", "focus": "whole-patient care, prevention, chronic mgmt", "bias": "patient-centered, holistic"},
    {"name": "Internal Medicine Specialist", "focus": "complex adult conditions, multimorbidity", "bias": "evidence-based, systematic"},
    {"name": "Pediatrician", "focus": "age-specific considerations, development", "bias": "conservative dosing"},
    {"name": "Geriatrician", "focus": "elderly patients, polypharmacy, frailty", "bias": "deprescribing, function over cure"},
    {"name": "Obstetrician/Gynecologist", "focus": "reproductive health, pregnancy considerations", "bias": "fetal safety first"},
    {"name": "Urologist", "focus": "urinary tract, prostate, kidney stones", "bias": "structural causes"},
    {"name": "Vascular Surgeon", "focus": "blood vessel disease, circulation", "bias": "intervention threshold"},
    {"name": "Plastic Surgeon", "focus": "wound healing, reconstruction", "bias": "cosmetic and functional outcomes"},
    {"name": "Neurosurgeon", "focus": "surgical brain/spine conditions", "bias": "surgical vs conservative"},
    {"name": "Cardiac Surgeon", "focus": "heart surgery criteria, valve disease", "bias": "high-risk intervention decisions"},
    {"name": "Thoracic Surgeon", "focus": "lung and chest surgery", "bias": "resectability, surgical risk"},
    {"name": "Colorectal Surgeon", "focus": "colon, rectum, bowel disease", "bias": "surgical timing"},
    {"name": "Transplant Surgeon", "focus": "organ transplant criteria", "bias": "patient selection, long-term"},
    {"name": "Allergist/Immunologist", "focus": "allergies, immune dysregulation", "bias": "trigger identification"},
    {"name": "Pain Management Specialist", "focus": "chronic pain, interventional pain", "bias": "multimodal, avoid opioids"},
    {"name": "Palliative Care Specialist", "focus": "symptom burden, quality of life", "bias": "comfort and dignity"},
    {"name": "Sports Medicine Physician", "focus": "athletic injuries, performance", "bias": "return to function"},
    {"name": "Occupational Medicine Physician", "focus": "work-related illness, exposure", "bias": "functional capacity"},
    {"name": "Physical Medicine & Rehab", "focus": "rehabilitation, functional recovery", "bias": "function restoration"},
    {"name": "Sleep Medicine Specialist", "focus": "sleep disorders, circadian, fatigue", "bias": "sleep architecture"},
    {"name": "Clinical Pharmacologist", "focus": "drug interactions, pharmacokinetics", "bias": "medication safety"},
    {"name": "Medical Geneticist", "focus": "hereditary conditions, genetic testing", "bias": "family history, risk genes"},
    {"name": "Clinical Epidemiologist", "focus": "population-level evidence, study design", "bias": "statistical rigor"},
    {"name": "Preventive Medicine Specialist", "focus": "disease prevention, screening", "bias": "upstream factors"},
    {"name": "Addiction Medicine Specialist", "focus": "substance use, dependency", "bias": "harm reduction"},
    {"name": "Hospitalist", "focus": "acute inpatient management", "bias": "safe discharge planning"},
    {"name": "Critical Care/ICU Specialist", "focus": "life-threatening conditions, organ support", "bias": "immediate stabilization"},
    {"name": "Interventional Radiologist", "focus": "image-guided procedures", "bias": "minimally invasive options"},
    {"name": "Nuclear Medicine Specialist", "focus": "imaging, radioactive diagnostics", "bias": "diagnostic precision"},
    {"name": "Pathologist", "focus": "tissue diagnosis, lab findings", "bias": "ground truth — what IS it"},
    {"name": "Microbiologist", "focus": "infectious organisms, resistance patterns", "bias": "antimicrobial stewardship"},
    {"name": "Clinical Nutritionist", "focus": "diet, nutritional deficiencies", "bias": "food-first approach"},
    {"name": "Clinical Psychologist", "focus": "behavioral patterns, cognitive factors", "bias": "non-pharmacological"},
    {"name": "Social Worker", "focus": "social determinants, support systems", "bias": "equity and access"},
    {"name": "Pharmacist", "focus": "medication safety, interactions, adherence", "bias": "deprescribing, safety"},
    {"name": "Nurse Practitioner", "focus": "practical management, patient education", "bias": "holistic, preventive"},
    {"name": "Integrative Medicine Physician", "focus": "complementary approaches, lifestyle", "bias": "whole-person"},
    {"name": "Radiation Oncologist", "focus": "radiation therapy criteria", "bias": "benefit vs toxicity"},
    {"name": "Medical Oncologist", "focus": "chemotherapy, targeted therapy, immunotherapy", "bias": "treatment response"},
    {"name": "Hematology-Oncology Specialist", "focus": "blood cancers, bone marrow", "bias": "aggressive when needed"},
    {"name": "Hepatologist", "focus": "liver disease, hepatitis, cirrhosis", "bias": "liver protection first"},
    {"name": "Diabetologist", "focus": "diabetes management, glycemic control", "bias": "long-term complications"},
    {"name": "Lipidologist", "focus": "cholesterol, cardiovascular metabolic risk", "bias": "lifetime risk reduction"},
    {"name": "Thyroid Specialist", "focus": "thyroid function, autoimmune thyroid", "bias": "TSH optimization"},
    {"name": "Reproductive Endocrinologist", "focus": "fertility, hormonal cycles", "bias": "reproductive outcomes"},
    {"name": "Neonatologist", "focus": "newborn care, premature infants", "bias": "extreme caution"},
    {"name": "Adolescent Medicine Specialist", "focus": "teen health, development", "bias": "developmental stage"},
]


class ConsensusRequest(BaseModel):
    condition: str
    symptoms: Optional[str] = None
    context: Optional[str] = None
    specialist_count: int = 10  # default 10, max 62


async def get_specialist_opinion(client: anthropic.AsyncAnthropic, specialist: dict, condition: str, symptoms: str, context: str) -> dict:
    """Get a single specialist's opinion asynchronously."""
    prompt = f"""You are a {specialist['name']} with the following clinical lens:
Focus area: {specialist['focus']}
Clinical bias/approach: {specialist['bias']}

A patient presents with: {condition}
{f'Symptoms: {symptoms}' if symptoms else ''}
{f'Additional context: {context}' if context else ''}

From YOUR specialist perspective only, provide:
1. Your primary concern/interpretation (2 sentences)
2. What you would investigate first (1-2 items)
3. Your recommended approach (2-3 sentences)
4. Confidence level: HIGH / MODERATE / LOW
5. Would you refer to another specialist? If so, who?

Be concise. Speak as this specialist would — with their specific biases and priorities."""

    try:
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = message.content[0].text

        # Extract confidence
        confidence = "MODERATE"
        if "HIGH" in response_text.upper():
            confidence = "HIGH"
        elif "LOW" in response_text.upper():
            confidence = "LOW"

        return {
            "specialist": specialist["name"],
            "focus": specialist["focus"],
            "opinion": response_text,
            "confidence": confidence,
            "status": "success"
        }
    except Exception as e:
        return {
            "specialist": specialist["name"],
            "focus": specialist["focus"],
            "opinion": f"Unable to get opinion: {str(e)}",
            "confidence": "LOW",
            "status": "error"
        }


@router.post("/consensus/specialists")
async def get_specialist_consensus(request: ConsensusRequest):
    """
    Run condition through N specialists in parallel.
    Returns individual opinions + consensus analysis.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    count = min(request.specialist_count, len(SPECIALISTS))
    selected = SPECIALISTS[:count]

    client = anthropic.AsyncAnthropic(api_key=api_key)

    # Run all specialists in parallel
    tasks = [
        get_specialist_opinion(
            client,
            spec,
            request.condition,
            request.symptoms or "",
            request.context or ""
        )
        for spec in selected
    ]

    opinions = await asyncio.gather(*tasks)

    # Consensus analysis
    high_confidence = [o for o in opinions if o["confidence"] == "HIGH"]
    moderate_confidence = [o for o in opinions if o["confidence"] == "MODERATE"]
    low_confidence = [o for o in opinions if o["confidence"] == "LOW"]

    consensus_score = (
        (len(high_confidence) * 1.0 + len(moderate_confidence) * 0.5) / len(opinions)
    ) if opinions else 0

    return {
        "condition": request.condition,
        "specialists_consulted": count,
        "consensus_score": round(consensus_score * 100, 1),
        "confidence_breakdown": {
            "high": len(high_confidence),
            "moderate": len(moderate_confidence),
            "low": len(low_confidence),
        },
        "specialist_opinions": opinions,
        "summary": f"{count} specialists consulted. Consensus score: {round(consensus_score * 100, 1)}%. {len(high_confidence)} specialists expressed high confidence."
    }
