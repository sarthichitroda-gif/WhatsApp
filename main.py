from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests
import os

app = FastAPI()

OPENWEATHER_API_KEY = "52b258a0392ab12e1128b67868b54787"

@app.get("/")
def read_root():
    return {"message": "API is working"}

@app.get("/test")
def test():
    return {"message": "Test endpoint working"}

@app.get("/")
async def root():
    return {"message": "API is working"}

@app.post("/webhook")
async def webhook(request: Request):
    req = await request.json()
    intent_name = req.get("queryResult", {}).get("intent", {}).get("displayName")
    city = req.get("queryResult", {}).get("parameters", {}).get("geo-city")

    if intent_name == "LinkedIn Profile Summarizer":
        if city:
            api_url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
            response = requests.get(api_url)

            if response.status_code == 200:
                data = response.json()
                temp = data["main"]["temp"]
                condition = data["weather"][0]["description"]
                fulfillment_text = f"The current temperature in {city} is {temp}°C with {condition}."
            else:
                fulfillment_text = f"Sorry, I couldn't fetch the weather for {city}."
        else:
            fulfillment_text = "Please tell me the city you want the weather for."
    else:
        fulfillment_text = "Intent not handled."

    return JSONResponse(content={"fulfillmentText": fulfillment_text})