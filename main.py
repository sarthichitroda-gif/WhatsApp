from fastapi import FastAPI, Request
import requests

app = FastAPI()

API_BASE_URL = "https://people-intel-service-test-3lu6lw5c5q-as.a.run.app/api/v1"
API_KEY = "YOUR_API_KEY"  # If authentication is required

@app.post("/webhook")
async def webhook(request: Request):
    req = await request.json()
    intent = req.get("queryResult", {}).get("intent", {}).get("displayName")
    params = req.get("queryResult", {}).get("parameters", {})

    headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}

    # Match intent to API endpoint
    if intent == "GetPerson":
        linkedin_url = params.get("linkedinUrl")
        response = requests.get(f"{API_BASE_URL}/get-person",
                                headers=headers,
                                params={"linkedinUrl": linkedin_url})

    elif intent == "GetSearchHistory":
        user_id = params.get("userId")
        response = requests.get(f"{API_BASE_URL}/person-search-history",
                                headers=headers,
                                params={"userId": user_id})

    elif intent == "GetServiceStatus":
        person_id = params.get("personId")
        response = requests.get(f"{API_BASE_URL}/person-service-status",
                                headers=headers,
                                params={"personId": person_id})

    elif intent == "GetPersonalityAnalysis":
        linkedin_url = params.get("linkedinUrl")
        response = requests.get(f"{API_BASE_URL}/person-personality-analysis",
                                headers=headers,
                                params={"linkedinUrl": linkedin_url})

    else:
        return {"fulfillmentText": "Sorry, I don't recognize this request."}

    # Format response for Dialogflow
    if response.status_code == 200:
        data = response.json()
        return {"fulfillmentText": f"Here’s the result: {data}"}
    else:
        return {"fulfillmentText": f"Error fetching data: {response.status_code} - {response.text}"}
