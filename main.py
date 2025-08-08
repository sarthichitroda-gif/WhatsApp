from fastapi import FastAPI, Request
import requests

app = FastAPI()

API_BASE_URL = "https://people-intel-service-test-3lu6lw5c5q-as.a.run.app/api/v1"
API_KEY = "YOUR_API_KEY"  # Replace with your real API key if needed


@app.post("/webhook")
async def webhook(request: Request):
    # Parse incoming JSON from Dialogflow
    req = await request.json()
    intent = req.get("queryResult", {}).get("intent", {}).get("displayName")
    params = req.get("queryResult", {}).get("parameters", {})

    headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}

    # Default fallback text
    fulfillment_text = "Sorry, I couldn't process your request."

    try:
        if intent == "GetPerson":
            linkedin_url = params.get("linkedinUrl")
            if not linkedin_url:
                return {"fulfillmentText": "Please provide a LinkedIn URL."}
            response = requests.get(
                f"{API_BASE_URL}/get-person",
                headers=headers,
                params={"linkedinUrl": linkedin_url}
            )

        elif intent == "GetSearchHistory":
            user_id = params.get("userId")
            if not user_id:
                return {"fulfillmentText": "Please provide a user ID."}
            response = requests.get(
                f"{API_BASE_URL}/person-search-history",
                headers=headers,
                params={"userId": user_id}
            )

        elif intent == "GetServiceStatus":
            person_id = params.get("personId")
            if not person_id:
                return {"fulfillmentText": "Please provide a person ID."}
            response = requests.get(
                f"{API_BASE_URL}/person-service-status",
                headers=headers,
                params={"personId": person_id}
            )

        elif intent == "GetPersonalityAnalysis":
            linkedin_url = params.get("linkedinUrl")
            if not linkedin_url:
                return {"fulfillmentText": "Please provide a LinkedIn URL."}
            response = requests.get(
                f"{API_BASE_URL}/person-personality-analysis",
                headers=headers,
                params={"linkedinUrl": linkedin_url}
            )

        else:
            return {"fulfillmentText": "Sorry, I don't recognize this request."}

        # Handle API response
        if response.status_code == 200:
            data = response.json()
            fulfillment_text = f"Here’s the result: {data}"
        else:
            fulfillment_text = (
                f"Error fetching data from service: {response.status_code} - {response.text}"
            )

    except Exception as e:
        fulfillment_text = f"An error occurred: {str(e)}"

    return {"fulfillmentText": fulfillment_text}
