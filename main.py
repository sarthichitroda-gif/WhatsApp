from fastapi import FastAPI, Request
import requests
import json

# Your Gemini API key for Google Vertex AI (Gemini/PaLM)
GEMINI_API_KEY = "AIzaSyAnKoMBJc-M8PYmmhZFS7FFbha47eDgh84"
ENDPOINT = "https://us-central1-aiplatform.googleapis.com/v1/projects/google/locations/us-central1/publishers/google/models/text-bison@001:generateText"
"

# Your custom people-intel-service API key
API_BASE_URL = "https://people-intel-service-test-3lu6lw5c5q-as.a.run.app/api/v1"
API_KEY = "YOUR_API_KEY"  # Replace with your actual API key here

headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}

app = FastAPI()

def call_gemini_summarize(text: str) -> str:
    payload = {
        "prompt": {
            "text": f"Summarize the following LinkedIn posts into a concise paragraph:\n\n{text}"
        },
        "temperature": 0.5,
        "maxOutputTokens": 256,
    }
    response = requests.post(
        f"{ENDPOINT}?key={GEMINI_API_KEY}",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload),
    )
    if response.status_code == 200:
        res_json = response.json()
        return res_json["candidates"][0]["output"]
    else:
        return f"Error summarizing posts: {response.text}"

def get_person_id_from_linkedin(linkedin_url: str):
    person_response = requests.get(
        f"{API_BASE_URL}/get-person",
        headers=headers,
        params={"linkedinUrl": linkedin_url}
    )

    if person_response.status_code != 200:
        return None, f"Please make sure the input is in proper format https://www.linkedin.com/in/userid"

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

@app.post("/webhook")
async def webhook(request: Request):
    req = await request.json()
    intent = req.get("queryResult", {}).get("intent", {}).get("displayName")
    params = req.get("queryResult", {}).get("parameters", {})

    fulfillment_text = "Sorry, I couldn't process your request."

    try:
        if intent == "GetPerson":
            linkedin_url = params.get("linkedinUrl")

            response = requests.get(
                f"{API_BASE_URL}/get-person",
                headers=headers,
                params={"linkedinUrl": linkedin_url}
            )

            if response.status_code == 200:
                resp_json = response.json()
                data = resp_json.get("data", {})

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

                fulfillment_text = (
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
            else:
                fulfillment_text = (
                    "Please make sure the input is in proper format https://www.linkedin.com/in/userid"
                )

        elif intent == "GetPersonalityAnalysis":
            linkedin_url = params.get("linkedinUrl")
            person_id, error = get_person_id_from_linkedin(linkedin_url)
            if error:
                return {"fulfillmentText": error}

            response = requests.get(
                f"{API_BASE_URL}/person-personality-analysis",
                headers=headers,
                params={"personId": person_id}
            )

            if response.status_code == 200:
                data = response.json()
                fulfillment_text = format_personality_analysis(data)
            else:
                fulfillment_text = (
                    "Please make sure the input is in proper format https://www.linkedin.com/in/userid"
                )

        else:
            fulfillment_text = "Sorry, I don't recognize this request."

    except Exception as e:
        fulfillment_text = f"An error occurred: {str(e)}"

    return {"fulfillmentText": fulfillment_text}
