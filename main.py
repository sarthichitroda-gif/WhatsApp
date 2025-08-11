from fastapi import FastAPI, Request
import requests

app = FastAPI()

API_BASE_URL = "https://people-intel-service-test-3lu6lw5c5q-as.a.run.app/api/v1"
API_KEY = "YOUR_API_KEY"  # Replace with your real API key
headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}


def get_person_id_from_linkedin(linkedin_url: str):
    person_response = requests.get(
        f"{API_BASE_URL}/get-person",
        headers=headers,
        params={"linkedinUrl": linkedin_url}
    )
    if person_response.status_code != 200:
        return None, f"Error fetching person: {person_response.status_code} - {person_response.text}"

    person_data = person_response.json()
    person_id = person_data.get("data", {}).get("personId")
    if not person_id:
        return None, "Person ID not found in API response."
    return person_id, None


def format_personality_analysis(data: dict) -> str:
    data = data.get("data", {})
    linkedin_url = data.get("linkedinUrl", "N/A")
    disc = data.get("discProfile", {})
    disc_summary = data.get("discProfileShortSummary", "")
    detailed = data.get("detailedAnalysis", {})
    recommendations = data.get("recommendations", {})
    interests = data.get("interestsDetected", [])

    def format_list(items):
        return "\n".join(f"- {item}" for item in items)

    return f"""Personality Analysis Summary

LinkedIn URL: {linkedin_url}

DISC Profile
- Dominance: {disc.get("dominance", "N/A")}
- Influence: {disc.get("influence", "N/A")}
- Steadiness: {disc.get("steadiness", "N/A")}
- Conscientiousness: {disc.get("conscientiousness", "N/A")}

Summary:
{disc_summary}

Detailed Analysis
Strengths:
{format_list(detailed.get("strengths", []))}

Weaknesses:
{format_list(detailed.get("weaknesses", []))}

Communication Style:
{detailed.get("communicationStyle", "N/A")}

Work Style:
{detailed.get("workStyle", "N/A")}

Leadership Style:
{detailed.get("leadershipStyle", "N/A")}

Team Collaboration:
{detailed.get("teamCollaboration", "N/A")}

Recommendations
Suggested Outreach Approach:
- Best Engaged Via: {", ".join(recommendations.get("suggestedOutreachApproach", {}).get("bestEngagedVia", []))}
- Messaging Tip: {recommendations.get("suggestedOutreachApproach", {}).get("messagingTip", "N/A")}
- Preferred Call to Action: {recommendations.get("suggestedOutreachApproach", {}).get("preferredCTA", "N/A")}

Tone to Use:
{recommendations.get("toneToUse", "N/A")}

Interests Detected:
{", ".join(interests) if interests else "N/A"}
"""


def get_from_context(req, key):
    """Retrieve a value from Dialogflow contexts."""
    for ctx in req.get("queryResult", {}).get("outputContexts", []):
        if ctx["name"].endswith("/contexts/linkedin_context"):
            return ctx["parameters"].get(key)
    return None


def save_to_context(req, linkedin_url=None, person_id=None):
    """Create output context JSON for Dialogflow."""
    params = {}
    if linkedin_url:
        params["linkedinUrl"] = linkedin_url
    if person_id:
        params["personId"] = person_id

    return [{
        "name": f"{req['session']}/contexts/linkedin_context",
        "lifespanCount": 5,
        "parameters": params
    }]


@app.post("/webhook")
async def webhook(request: Request):
    req = await request.json()
    intent = req.get("queryResult", {}).get("intent", {}).get("displayName")
    params = req.get("queryResult", {}).get("parameters", {})

    fulfillment_text = "Sorry, I couldn't process your request."
    output_contexts = []

    try:
        # Get stored values if available
        linkedin_url = params.get("linkedinUrl") or get_from_context(req, "linkedinUrl")
        person_id = get_from_context(req, "personId")

        # ----- INTENT: GetPerson -----
        if intent == "GetPerson":
            if not linkedin_url:
                return {"fulfillmentText": "Please provide a LinkedIn URL."}

            response = requests.get(
                f"{API_BASE_URL}/get-person",
                headers=headers,
                params={"linkedinUrl": linkedin_url}
            )

            if response.status_code == 200:
                data = response.json().get("data", {})
                full_name = data.get("fullName", "N/A")
                headline = data.get("headline", "N/A")
                location = data.get("location", "N/A")
                linkedin_profile = data.get("linkedinUrl", "N/A")
                person_id = data.get("personId", "N/A")
                skills = data.get("skills", [])
                top_skills = ", ".join(skill.get("name") for skill in skills[:3]) if skills else "N/A"
                education = data.get("education", [])
                schools = ", ".join(edu.get("school") for edu in education[:2]) if education else "N/A"

                fulfillment_text = (
                    f"Name: {full_name}\n"
                    f"Headline: {headline}\n"
                    f"Location: {location}\n"
                    f"LinkedIn URL: {linkedin_profile}\n"
                    f"Top Skills: {top_skills}\n"
                    f"Education: {schools}"
                )

                # Save for later intents
                output_contexts = save_to_context(req, linkedin_url=linkedin_url, person_id=person_id)

            else:
                fulfillment_text = f"Error fetching person data: {response.status_code} - {response.text}"

        # ----- INTENT: GetSearchHistory -----
        elif intent == "GetSearchHistory":
            if not linkedin_url and not person_id:
                return {"fulfillmentText": "Please provide a LinkedIn URL."}

            if not person_id:
                person_id, error = get_person_id_from_linkedin(linkedin_url)
                if error:
                    return {"fulfillmentText": error}

            response = requests.get(
                f"{API_BASE_URL}/person-search-history",
                headers=headers,
                params={"userId": person_id}
            )

            if response.status_code == 200:
                fulfillment_text = f"Here’s the result: {response.json()}"
                output_contexts = save_to_context(req, linkedin_url=linkedin_url, person_id=person_id)
            else:
                fulfillment_text = f"Error fetching data: {response.status_code} - {response.text}"

        # ----- INTENT: GetServiceStatus -----
        elif intent == "GetServiceStatus":
            if not linkedin_url and not person_id:
                return {"fulfillmentText": "Please provide a LinkedIn URL."}

            if not person_id:
                person_id, error = get_person_id_from_linkedin(linkedin_url)
                if error:
                    return {"fulfillmentText": error}

            response = requests.get(
                f"{API_BASE_URL}/person-service-status",
                headers=headers,
                params={"personId": person_id}
            )

            if response.status_code == 200:
                fulfillment_text = f"Here’s the result: {response.json()}"
                output_contexts = save_to_context(req, linkedin_url=linkedin_url, person_id=person_id)
            else:
                fulfillment_text = f"Error fetching data: {response.status_code} - {response.text}"

        # ----- INTENT: GetPersonalityAnalysis -----
        elif intent == "GetPersonalityAnalysis":
            if not linkedin_url and not person_id:
                return {"fulfillmentText": "Please provide a LinkedIn URL."}

            if not person_id:
                person_id, error = get_person_id_from_linkedin(linkedin_url)
                if error:
                    return {"fulfillmentText": error}

            response = requests.get(
                f"{API_BASE_URL}/person-personality-analysis",
                headers=headers,
                params={"personId": person_id}
            )

            if response.status_code == 200:
                fulfillment_text = format_personality_analysis(response.json())
                output_contexts = save_to_context(req, linkedin_url=linkedin_url, person_id=person_id)
            else:
                fulfillment_text = f"Error fetching personality analysis: {response.status_code} - {response.text}"

        else:
            fulfillment_text = "Sorry, I don't recognize this request."

    except Exception as e:
        fulfillment_text = f"An error occurred: {str(e)}"

    return {
        "fulfillmentText": fulfillment_text,
        "outputContexts": output_contexts
    }