from fastapi import FastAPI, Request
import requests
import time

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
        return None, f"Please make sure the input is in proper format https://www.linkedin.com/in/userid"

    person_data = person_response.json()

    # Adjusted to get nested 'personId' inside 'data'
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
- Best Engaged Via: {", ".join(recommendations.get("suggestedOutreachApproach", {}).get("bestEngagedVia", []))}
- Messaging Tip: {recommendations.get("suggestedOutreachApproach", {}).get("messagingTip", "N/A")}
- Preferred Call to Action: {recommendations.get("suggestedOutreachApproach", {}).get("preferredCTA", "N/A")}

Tone to Use:
{recommendations.get("toneToUse", "N/A")}

Interests Detected:
{", ".join(interests) if interests else "N/A"}
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
                person_id = data.get("personId", "N/A")

                # Example: top 3 skills
                skills = data.get("skills", [])
                top_skills = ", ".join(skill.get("name") for skill in skills[:3]) if skills else "N/A"

                # Education: Just list school names (top 2)
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
            else:
                fulfillment_text = (
                    f"Please make sure the input is in proper format https://www.linkedin.com/in/userid"
                )

        elif intent == "GetPersonalityAnalysis":
            linkedin_url = params.get("linkedinUrl")
            
            # Step 1: Get personId from linkedinUrl
            person_id, error = get_person_id_from_linkedin(linkedin_url)
            if error:
                return {"fulfillmentText": error}

            # Step 2: Call personality analysis API with personId
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
                    f"Please make sure the input is in proper format https://www.linkedin.com/in/userid"
                )

        else:
            fulfillment_text = "Sorry, I don't recognize this request."

    except Exception as e:
        fulfillment_text = f"An error occurred: {str(e)}"

    return {"fulfillmentText": fulfillment_text}