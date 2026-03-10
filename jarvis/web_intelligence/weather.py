from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib import parse as urllib_parse
from urllib import request as urllib_request


class WeatherService:
    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key

    async def get_weather(self, location: str) -> dict[str, Any]:
        if not self.api_key:
            try:
                payload = await asyncio.to_thread(self._fetch_wttr_payload, location)
                current = payload["current_condition"][0]
                return {
                    "location": location,
                    "temperature_c": current.get("temp_C"),
                    "description": current.get("weatherDesc", [{}])[0].get("value"),
                }
            except Exception as exc:
                return {"location": location, "temperature_c": None, "description": f"Weather lookup failed: {exc}"}
        try:
            payload = await asyncio.to_thread(self._fetch_openweather_payload, location)
            return {
                "location": payload.get("name", location),
                "temperature_c": payload.get("main", {}).get("temp"),
                "description": payload.get("weather", [{}])[0].get("description"),
            }
        except Exception as exc:
            return {"location": location, "temperature_c": None, "description": f"Weather lookup failed: {exc}"}

    def _fetch_wttr_payload(self, location: str) -> dict[str, Any]:
        encoded_location = urllib_parse.quote(location)
        with urllib_request.urlopen(f"https://wttr.in/{encoded_location}?format=j1", timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    def _fetch_openweather_payload(self, location: str) -> dict[str, Any]:
        encoded = urllib_parse.urlencode({"q": location, "appid": self.api_key, "units": "metric"})
        with urllib_request.urlopen(f"https://api.openweathermap.org/data/2.5/weather?{encoded}", timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
