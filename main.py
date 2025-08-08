from fastapi import FastAPI, Request
import requests

app = FastAPI()

API_BASE_URL = "https://people-intel-service-test-3lu6lw5c5q-as.a.run.app/api/v1"
API_KEY = "YOUR_API_KEY"  # Replace with your real API key

headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}


def get_person_id_from_linkedin(linkedin_url: str):
    """Fetch the person ID from LinkedIn URL using the get-person API."""
    person_response = requests.get(
        f"{API_BASE_URL}/get-person",
        headers=headers,
        params={"linkedinUrl": linkedin_url}
    )

    if person_response.status_code != 200:
        return None, f"Error fetching person: {person_response.status_code} - {person_response.text}"

    person_data = person_response.json()

    # Adjust this based on your API's actual JSON structure
    person_id = person_data.get("id")  # or person_data["data"]["id"] if nested
    if not person_id:
        return None, "Person ID not found in API response."

    return person_id, None


@app.post("/webhook")
async def webhook(request: Request):
    req = await request.json()
    intent = req.get("queryResult", {}).get("intent", {}).get("displayName")
    params = req.get("queryResult", {}).get("parameters", {})

    fulfillment_text = "Sorry, I couldn't process your request."

    try:
        if intent in ["GetSearchHistory", "GetServiceStatus"]:
            linkedin_url = params.get("linkedinUrl")
            if not linkedin_url:
                return {"fulfillmentText": "Please provide a LinkedIn URL."}

            # Step 1: Get Person ID from LinkedIn
            person_id, error = get_person_id_from_linkedin(linkedin_url)
            if error:
                return {"fulfillmentText": error}

            # Step 2: Call the correct API based on intent
            if intent == "GetSearchHistory":
                endpoint = "person-search-history"
                param_key = "userId"
            else:
                endpoint = "person-service-status"
                param_key = "personId"

            response = requests.get(
                f"{API_BASE_URL}/{endpoint}",
                headers=headers,
                params={param_key: person_id}
            )

            if response.status_code == 200:
                data = response.json()
                fulfillment_text = f"Here’s the result: {data}"
            else:
                fulfillment_text = (
                    f"Error fetching data from {endpoint}: "
                    f"{response.status_code} - {response.text}"
                )

        elif intent == "GetPerson":
            linkedin_url = params.get("linkedinUrl")
            if not linkedin_url:
                return {"fulfillmentText": "Please provide a LinkedIn URL."}

            response = requests.get(
                f"{API_BASE_URL}/get-person",
                headers=headers,
                params={"linkedinUrl": linkedin_url}
            )

            if response.status_code == 200:
                data = response.json()
                fulfillment_text = f"Here’s the person data: {data}"
            else:
                fulfillment_text = (
                    f"Error fetching person data: {response.status_code} - {response.text}"
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

            if response.status_code == 200:
                data = response.json()
                fulfillment_text = f"Here’s the analysis: {data}"
            else:
                fulfillment_text = (
                    f"Error fetching personality analysis: {response.status_code} - {response.text}"
                )

        else:
            fulfillment_text = "Sorry, I don't recognize this request."

    except Exception as e:
        fulfillment_text = f"An error occurred: {str(e)}"

    return {"fulfillmentText": fulfillment_text}
