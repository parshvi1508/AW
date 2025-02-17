import asyncio
import httpx
import json
from datetime import datetime

# Test cases with synthetic patient data
test_patients = [
    {
        "patient_id": "MH-001",
        "age": 25,
        "medications": ["ibuprofen"],
        "allergies": [],
        "vitals": {"SpO2": 99, "heart_rate": 70}
    },
    {
        "patient_id": "MH-002",
        "age": 68,
        "medications": ["warfarin", "aspirin", "lisinopril", "metformin"],
        "allergies": ["penicillin"],
        "vitals": {"SpO2": 94, "heart_rate": 105}
    },
    {
        "patient_id": "MH-003",
        "age": 45,
        "medications": ["metoprolol", "simvastatin"],
        "allergies": ["sulfa"],
        "vitals": {"SpO2": 97, "heart_rate": 68}
    }
]

async def test_medguardian_api():
    async with httpx.AsyncClient() as client:
        for patient in test_patients:
            try:
                response = await client.post(
                    "http://localhost:8000/medguardian/process/",
                    json=patient
                )
                print(f"\nTesting Patient {patient['patient_id']}:")
                print("Request:", json.dumps(patient, indent=2))
                print("Response:", json.dumps(response.json(), indent=2))
            except Exception as e:
                print(f"Error testing patient {patient['patient_id']}: {str(e)}")

if __name__ == "__main__":
    print("Starting MedGuardian API tests...")
    asyncio.run(test_medguardian_api())