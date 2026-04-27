"""
skills/weather.py
─────────────────
Weather Skill — fetches live weather from OpenWeatherMap API.

INSTALL:
    pip install requests
    Get free API key: https://openweathermap.org/api

TRIGGERS:
    "weather", "temperature", "forecast", "rain", "hot", "cold"
"""

import requests
from core.config import CONFIG
from core.logger import log


class WeatherSkill:

    triggers = ["weather", "temperature", "forecast", "rain", "sunny",
                "hot outside", "cold outside", "humidity", "wind"]

    def handle(self, command: str) -> str:
        city    = CONFIG.get("city", "Coimbatore")
        api_key = CONFIG.get("openweather_api_key", "")

        if not api_key:
            return "[Weather] API key not set. Add openweather_api_key to config.json."

        try:
            url  = "https://api.openweathermap.org/data/2.5/weather"
            resp = requests.get(url, params={
                "q"     : city,
                "appid" : api_key,
                "units" : "metric"
            }, timeout=5)
            data = resp.json()

            if resp.status_code != 200:
                return f"[Weather] Error: {data.get('message', 'Unknown error')}"

            temp        = data["main"]["temp"]
            feels_like  = data["main"]["feels_like"]
            humidity    = data["main"]["humidity"]
            description = data["weather"][0]["description"].capitalize()
            wind        = data["wind"]["speed"]

            result = (
                f"Weather in {city}: {description}. "
                f"Temperature: {temp}°C, feels like {feels_like}°C. "
                f"Humidity: {humidity}%. Wind: {wind} m/s."
            )
            log.info(f"[WeatherSkill] {result}")
            return result

        except requests.Timeout:
            return "[Weather] Request timed out. Check your internet connection."
        except Exception as e:
            log.error(f"WeatherSkill error: {e}")
            return "[Weather] Unable to fetch weather data."
