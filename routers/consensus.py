"""
62-Specialist Consensus Engine.
Uses DeepSeek API (OpenAI-compatible) — cheap, fast, no Anthropic key needed.
"""
import asyncio
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from openai import AsyncOpenAI

router = APIRouter()

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

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
    {"name": "Allergist/Immunologist", "focus": "allergies, immune dysregulation", "bias": "trigger identification"},
    {"name": "Pain Management Specialist", "focus": "chronic pain, interventional pain", "bias": "multimodal, avoid opioids"},
    {"name": "Palliative Care Specialist", "focus": "symptom burden, quality of life", "bias": "comfort and dignity"},
    {"name": "Sports Medicine Physician", "focus": "athletic injuries, performance", "bias": "return to function"},
    {"name": "Sleep Medicine Specialist", "focus": "sleep disorders, circadian, fatigue", "bias": "sleep architecture"},
    {"name": "Clinical Pharmacologist", "focus": "drug interactions, pharmacokinetics", "bias": "medication safety"},
    {"name": "Medical Geneticist", "focus": "hereditary conditions, genetic testing", "bias": "family history, risk genes"},
    {"name": "Clinical Epidemiologist", "focus": "population-level evidence, study design", "bias": "statistical rigor"},
    {"name": "Preventive Medicine Specialist", "focus": "disease prevention, screening", "bias": "upstream factors"},
    {"name": "Addiction Medicine Specialist", "focus": "substance use, dependency", "bias": "harm reduction"},
    {"name": "Hospitalist", "focus": "acute inpatient management", "bias": "safe discharge planning"},
    {"name": "Critical Care/ICU Specialist", "focus": "life-threatening conditions, organ support", "bias": "immediate stabilization"},
    {"name": "Pathologist", "focus": "tissue diagnosis, lab findings", "bias": "ground truth — what IS it"},
    {"name": "Microbiologist", "focus": "infectious organisms, resistance patterns", "bias": "antimicrobial stewardship"},
    {"name": "Clinical Nutritionist", "focus": "diet, nutritional deficiencies", "bias": "food-first approach"},
    {"name": "Clinical Psychologist", "focus": "behavioral patterns, cognitive factors", "bias": "non-pharmacological"},
    {"name": "Pharmacist", "focus": "medication safety, interactions, adherence", "bias": "deprescribing, safety"},
    {"name": "Integrative Medicine Physician", "focus": "complementary approaches, lifestyle", "bias": "whole-person"},
    {"name": "Radiation Oncologist", "focus": "radiation therapy criteria", "bias": "benefit vs toxicity"},
    {"name": "Medical Oncologist", "focus": "chemotherapy, targeted therapy, immunotherapy", "bias": "treatment response"},
    {"name": "Hepatologist", "focus": "liver disease, hepatitis, cirrhosis", "bias": "liver protection first"},
    {"name": "Diabetologist", "focus": "diabetes management, glycemic control", "bias": "long-term complications"},
    {"name": "Lipidologist", "focus": "cholesterol, cardiovascular metabolic risk", "bias": "lifetime risk reduction"},
    {"name": "Thyroid Specialist", "focus": "thyroid function, autoimmune thyroid", "bias": "TSH optimization"},
    {"name": "Reproductive Endocrinologist", "focus": "fertility, hormonal cycles", "bias": "reproductive outcomes"},
    {"name": "Neonatologist", "focus": "newborn care, premature infants", "bias": "extreme caution"},
    {"name": "Adolescent Medicine Specialist", "focus": "teen health, development", "bias": "developmental stage"},
    {"name": "Vascular Surgeon", "focus": "blood vessel disease, circulation", "bias": "intervention threshold"},
    {"name": "Interventional Radiologist", "focus": "image-guided procedures", "bias": "minimally invasive options"},
    {"name": "Nuclear Medicine Specialist", "focus": "imaging, radioactive diagnostics", "bias": "diagnostic precision"},
    {"name": "Physical Medicine & Rehab", "focus": "rehabilitation, functional recovery", "bias": "function restoration"},
    {"name": "Occupational Medicine Physician", "focus": "work-related illness, exposure", "bias": "functional capacity"},
    {"name": "Transplant Surgeon", "focus": "organ transplant criteria", "bias": "patient selection, long-term"},
    {"name": "Colorectal Surgeon", "focus": "colon, rectum, bowel disease", "bias": "surgical timing"},
    {"name": "Thoracic Surgeon", "focus": "lung and chest surgery", "bias": "resectability, surgical risk"},
    {"name": "Cardiac Surgeon", "focus": "heart surgery criteria, valve disease", "bias": "high-risk intervention decisions"},
    {"name": "Neurosurgeon", "focus": "surgical brain/spine conditions", "bias": "surgical vs conservative"},
    {"name": "Plastic Surgeon", "focus": "wound healing, reconstruction", "bias": "cosmetic and functional outcomes"},
    {"name": "Hematology-Oncology Specialist", "focus": "blood cancers, bone marrow", "bias": "aggressive when needed"},
    {"name": "Social Worker", "focus": "social determinants, support systems", "bias": "equity and access"},
    {"name": "Nurse Practitioner", "focus": "practical management, patient education", "bias": "holistic, preventive"},
]


class ConsensusRequest(BaseModel):
    condition: str
    symptoms: Optional[str] = None
    context: Optional[str] = None
    specialist_count: int = 10


async def get_specialist_opinion(client: AsyncOpenAI, specialist: dict, condition: str, symptoms: str, context: str) -> dict:
    prompt = f"""You are a {specialist['name']}.
Focus: {specialist['focus']}
Clinical approach: {specialist['bias']}

Patient presents with: {condition}
{f'Symptoms: {symptoms}' if symptoms else ''}
{f'Context: {context}' if context else ''}

From YOUR specialist perspective only:
1. Primary concern (1-2 sentences)
2. What you investigate first (1-2 items)
3. Recommended approach (2 sentences)
4. Confidence: HIGH / MODERATE / LOW
5. Refer to another specialist? Who?

Be concise. Think like this specialist with their specific biases."""

    try:
        response = await client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250,
            temperature=0.7,
        )
        text = response.choices[0].message.content

        confidence = "MODERATE"
        text_upper = text.upper()
        if "CONFIDENCE: HIGH" in text_upper or "HIGH CONFIDENCE" in text_upper:
            confidence = "HIGH"
        elif "CONFIDENCE: LOW" in text_upper or "LOW CONFIDENCE" in text_upper:
            confidence = "LOW"

        return {
            "specialist": specialist["name"],
            "focus": specialist["focus"],
            "opinion": text,
            "confidence": confidence,
            "status": "success"
        }
    except Exception as e:
        return {
            "specialist": specialist["name"],
            "focus": specialist["focus"],
            "opinion": f"Unavailable: {str(e)}",
            "confidence": "LOW",
            "status": "error"
        }


@router.post("/consensus/specialists")
async def get_specialist_consensus(request: ConsensusRequest):
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="DEEPSEEK_API_KEY not configured")

    count = min(request.specialist_count, len(SPECIALISTS))
    selected = SPECIALISTS[:count]

    client = AsyncOpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)

    tasks = [
        get_specialist_opinion(client, spec, request.condition, request.symptoms or "", request.context or "")
        for spec in selected
    ]
    opinions = await asyncio.gather(*tasks)

    high = [o for o in opinions if o["confidence"] == "HIGH"]
    moderate = [o for o in opinions if o["confidence"] == "MODERATE"]
    low = [o for o in opinions if o["confidence"] == "LOW"]
    consensus_score = round(((len(high) * 1.0 + len(moderate) * 0.5) / len(opinions)) * 100, 1) if opinions else 0

    return {
        "condition": request.condition,
        "specialists_consulted": count,
        "consensus_score": consensus_score,
        "confidence_breakdown": {"high": len(high), "moderate": len(moderate), "low": len(low)},
        "specialist_opinions": opinions,
        "summary": f"{count} specialists consulted via DeepSeek. Consensus: {consensus_score}%. {len(high)} high confidence."
    }
