from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import os
import datetime
from dotenv import load_dotenv
import httpx
import asyncio
from typing import List, Dict, Optional

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Check if API keys are available
if not GROQ_API_KEY or not TAVILY_API_KEY:
    print("Warning: API keys not found in .env file")
    print("Using mock responses for testing")
    MOCK_MODE = True
else:
    MOCK_MODE = False

# Initialize FastAPI with explicit parameters
app = FastAPI(
    title="MedGuardian API",
    description="Medical risk assessment and drug interaction API",
    version="1.0.0"
)

class PatientData(BaseModel):
    patient_id: str
    age: int
    medications: List[str]
    allergies: List[str] = []
    vitals: Optional[Dict[str, float]] = None

    class Config:
        json_schema_extra = {  # Updated from schema_extra
            "example": {
                "patient_id": "MH-123456",
                "age": 45,
                "medications": ["aspirin", "lisinopril"],
                "allergies": ["penicillin"],
                "vitals": {"SpO2": 98, "heart_rate": 72}
            }
        }

async def mock_drug_info(drug_name: str) -> List[Dict]:
    """Mock drug information for testing"""
    return [{
        "title": f"Information about {drug_name}",
        "content": f"Common interactions for {drug_name} include drowsiness and dizziness.",
        "url": "https://example.com/drugs"
    }]

async def mock_risk_analysis(patient_data: PatientData) -> str:
    """Mock risk analysis for testing"""
    risks = []
    if patient_data.age > 65:
        risks.append("Elderly patient - increased risk")
    if len(patient_data.medications) > 2:
        risks.append("Multiple medications - potential interactions")
    if patient_data.allergies:
        risks.append(f"Known allergies: {', '.join(patient_data.allergies)}")
    
    if risks:
        return "HIGH RISK: " + "; ".join(risks)
    return "LOW RISK: No significant risk factors identified"

async def search_drug_info(drug_name: str) -> List[Dict]:
    """Search for drug information using Tavily API"""
    if MOCK_MODE:
        return await mock_drug_info(drug_name)
        
    search_url = "https://api.tavily.com/search"
    params = {
        "api_key": TAVILY_API_KEY,
        "query": f"{drug_name} drug interactions medical",
        "search_depth": "advanced",
        "include_domains": ["drugs.com", "medlineplus.gov", "mayoclinic.org"]
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(search_url, params=params, timeout=10.0)
            response.raise_for_status()
            return response.json().get("results", [])[:2]
    except Exception as e:
        print(f"Error in drug info search: {str(e)}")
        return []

async def analyze_risks_with_groq(patient_data: PatientData, drug_info: List[Dict]) -> str:
    """Analyze patient risks using Groq API"""
    if MOCK_MODE:
        return await mock_risk_analysis(patient_data)
        
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
    Analyze potential risks for patient {patient_data.patient_id}:
    - Age: {patient_data.age}
    - Current Medications: {', '.join(patient_data.medications)}
    - Known Allergies: {', '.join(patient_data.allergies) if patient_data.allergies else 'None'}
    - Current Vitals: {patient_data.vitals}
    
    Drug Information:
    {drug_info}
    
    Provide a concise risk assessment focusing on:
    1. Potential drug interactions
    2. Age-related risks
    3. Allergy concerns
    4. Vital sign implications
    """
    
    payload = {
        "model": "mixtral-8x7b-32768",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 500
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error in risk analysis: {str(e)}")
        return "Unable to perform risk analysis"

def get_risk_level(analysis: str) -> str:
    """Determine risk level based on analysis content"""
    high_risk_terms = ['high risk', 'severe', 'dangerous', 'critical', 'emergency']
    return "HIGH RISK" if any(term in analysis.lower() for term in high_risk_terms) else "LOW RISK"

@app.post("/medguardian/process/")
async def process_patient_data(patient_data: PatientData):
    """Process patient data and return risk assessment"""
    try:
        #vitals exist
        if patient_data.vitals is None:
            patient_data.vitals = {"SpO2": 98, "heart_rate": 72}
        
        # Gather drug information
        drug_info = []
        for medication in patient_data.medications:
            info = await search_drug_info(medication)
            if info:
                drug_info.extend(info)
        
        # Perform risk analysis
        risk_analysis = await analyze_risks_with_groq(patient_data, drug_info)
        risk_level = get_risk_level(risk_analysis)
        
        return {
            "patient_id": patient_data.patient_id,
            "risk_level": risk_level,
            "risk_analysis": risk_analysis,
            "analyzed_medications": len(patient_data.medications),
            "timestamp": datetime.datetime.now().isoformat(),
            "mode": "MOCK" if MOCK_MODE else "LIVE"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)