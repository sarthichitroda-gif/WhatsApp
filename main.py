import json
from fastapi import FastAPI, Request, BackgroundTasks
import requests
from google.auth import default
from google.auth.transport.requests import Request as GoogleAuthRequest
import logging

logging.basicConfig(level=logging.INFO)

# Vertex AI endpoint
PROJECT_ID = "magiq-ai"
LOCATION = "us-central1"
MODEL = "gemini-2.5-pro"
ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{MODEL}:generateContent"

# Your custom people-intel-service API key
API_BASE_URL = "https://people-intel-service-test-3lu6lw5c5q-as.a.run.app/api/v1"
API_KEY = "YOUR_API_KEY"  # Replace with your actual API key here
headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}

app = FastAPI()

# Simple in-memory caches; replace with Redis or DB for production
person_results_cache = {}
personality_results_cache = {}

def get_gcloud_access_token():
    credentials, project = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    credentials.refresh(GoogleAuthRequest())
    return credentials.token

def call_gemini_summarize(text: str) -> str:
    token = get_gcloud_access_token()
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": f"Summarize the following LinkedIn posts into a concise paragraph as if you are explaining it to another person:\n{text}"}]
            }
        ]
    }
    response = requests.post(
        ENDPOINT,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        data=json.dumps(payload),
    )
    if response.status_code == 200:
        res_json = response.json()
        return res_json["candidates"][0]["content"]["parts"][0]["text"]
    else:
        return f"Error summarizing posts: {response.text}"

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
    person_id = data.get("personId", "N/A")
    analysis_date = data.get("analysisDate", "N/A")

    disc = data.get("discProfile", {})
    disc_summary = data.get("discProfileShortSummary", "")

    detailed = data.get("detailedAnalysis", {})
    recommendations = data.get("recommendations", {})
    interests = data.get("interestsDetected", [])

    def format_list(items):
        return "\n".join(f"- {item}" for item in items)

    formatted = f"""Personality Analysis Summary

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
- Best Engaged Via: {', '.join(recommendations.get('suggestedOutreachApproach', {}).get('bestEngagedVia', []))}
- Messaging Tip: {recommendations.get('suggestedOutreachApproach', {}).get('messagingTip', 'N/A')}
- Preferred Call to Action: {recommendations.get('suggestedOutreachApproach', {}).get('preferredCTA', 'N/A')}

Tone to Use:
{recommendations.get('toneToUse', 'N/A')}

Interests Detected:
{', '.join(interests) if interests else 'N/A'}
"""
    return formatted

def process_personality_analysis(linkedin_url: str, session_id: str):
    person_id, error = get_person_id_from_linkedin(linkedin_url)
    if error:
        personality_results_cache[session_id] = f"Error getting person ID: {error}"
        return

    response = requests.get(
        f"{API_BASE_URL}/person-personality-analysis",
        headers=headers,
        params={"personId": person_id}
    )

    if response.status_code == 200:
        data = response.json()
        formatted_result = format_personality_analysis(data)
        personality_results_cache[session_id] = formatted_result
    else:
        personality_results_cache[session_id] = f"Error fetching personality analysis: {response.status_code} - {response.text}"

def process_get_person(linkedin_url: str, session_id: str):
    logging.info(f"Started process_get_person for session {session_id} with LinkedIn URL {linkedin_url}")
    response = requests.get(
        f"{API_BASE_URL}/get-person",
        headers=headers,
        params={"linkedinUrl": linkedin_url}
    )

    if response.status_code != 200:
        person_results_cache[session_id] = f"Error fetching person: {response.status_code} - {response.text}"
        return

    data = response.json().get("data", {})

    full_name = data.get("fullName", "N/A")
    headline = data.get("headline", "N/A")
    location = data.get("location", "N/A")
    linkedin_profile = data.get("linkedinUrl", "N/A")

    skills = data.get("skills", [])
    top_skills = ", ".join(skill.get("name") for skill in skills[:3]) if skills else "N/A"

    education = data.get("education", [])
    schools = ", ".join(edu.get("school") for edu in education[:2]) if education else "N/A"

    positions = data.get("positions", [])
    current_title = "N/A"
    current_company = "N/A"
    for pos in positions:
        if pos.get("endDate") is None:
            current_title = pos.get("title", "N/A")
            current_company = pos.get("company", "N/A")
            break

    posts = data.get("posts", [])[:5]
    combined_text = "\n".join(post.get("content", "") for post in posts)

    summary_text = call_gemini_summarize(combined_text)

    formatted_text = (
        f"Name: {full_name}\n"
        f"Headline: {headline}\n"
        f"Location: {location}\n"
        f"LinkedIn URL: {linkedin_profile}\n"
        f"Top Skills: {top_skills}\n"
        f"Education: {schools}\n"
        f"Current Job Role: {current_title}\n"
        f"Current Organization: {current_company}\n\n"
        f"Summary of Recent Posts:\n{summary_text}"
    )

    person_results_cache[session_id] = formatted_text
    logging.info(f"Completed process_get_person for session {session_id}")

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    req = await request.json()
    logging.info(f"Full request JSON: {req}")  # DEBUG: see complete request body
    session_id = req.get("session")
    logging.info(f"Session ID: {session_id}")
    intent = req.get("queryResult", {}).get("intent", {}).get("displayName")
    params = req.get("queryResult", {}).get("parameters", {})
    output_contexts = req.get("queryResult", {}).get("outputContexts", [])

    logging.info(f"Webhook called. Session: {session_id}, Intent: {intent}")

    fulfillment_text = "Sorry, I couldn't process your request."

    try:
        if intent == "GetPerson":
            linkedin_url = params.get("linkedinUrl")
            background_tasks.add_task(process_get_person, linkedin_url, session_id)
            fulfillment_text = "Thanks for your request! Fetching person info now. Please ask again shortly to get the results."

        elif intent == "GetPersonResult":
            # Extract linkedinUrl from getpersresult input context parameters
            linkedin_url = None
            context_name = None
            for ctx in output_contexts:
                if ctx.get("name", "").endswith("/contexts/getpersresult"):
                    linkedin_url = ctx.get("parameters", {}).get("linkedinUrl")
                    context_name = ctx.get("name")
                    break

            result = person_results_cache.get(session_id)
            if result:
                fulfillment_text = result
                del person_results_cache[session_id]
            else:
                fulfillment_text = "Person info is still being processed or not found. Please wait a moment and try again."

            # Return outputContexts with linkedinUrl to keep context alive
            if linkedin_url and context_name:
                return {
                    "fulfillmentText": fulfillment_text,
                    "outputContexts": [
                        {
                            "name": context_name,
                            "lifespanCount": 5,
                            "parameters": {
                                "linkedinUrl": linkedin_url,
                                "linkedinUrl.original": linkedin_url
                            }
                        }
                    ]
                }
            else:
                return {"fulfillmentText": fulfillment_text}

        elif intent == "GetPersonalityAnalysis":
            linkedin_url = params.get("linkedinUrl")
            background_tasks.add_task(process_personality_analysis, linkedin_url, session_id)
            fulfillment_text = "Thanks for your request! Personality analysis is being processed. Please ask again shortly to get the results."

        elif intent == "GetPersonalityAnalysisResult":
            result = personality_results_cache.get(session_id)
            if result:
                fulfillment_text = result
                del personality_results_cache[session_id]
            else:
                fulfillment_text = "Your personality analysis is still processing or not found. Please wait a moment and try again."

        else:
            fulfillment_text = "Sorry, I don't recognize this request."

    except Exception as e:
        fulfillment_text = f"An error occurred: {str(e)}"

    return {"fulfillmentText": fulfillment_text}
