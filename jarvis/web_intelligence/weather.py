from __future__ import annotations

from typing import Any

import httpx


class WeatherService:
    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key

    async def get_weather(self, location: str) -> dict[str, Any]:
        if not self.api_key:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(f"https://wttr.in/{location}", params={"format": "j1"})
                    response.raise_for_status()
                    payload = response.json()
                current = payload["current_condition"][0]
                return {
                    "location": location,
                    "temperature_c": current.get("temp_C"),
                    "description": current.get("weatherDesc", [{}])[0].get("value"),
                }
            except Exception as exc:
                return {"location": location, "temperature_c": None, "description": f"Weather lookup failed: {exc}"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={"q": location, "appid": self.api_key, "units": "metric"},
                )
                response.raise_for_status()
                payload = response.json()
            return {
                "location": payload.get("name", location),
                "temperature_c": payload.get("main", {}).get("temp"),
                "description": payload.get("weather", [{}])[0].get("description"),
            }
        except Exception as exc:
            return {"location": location, "temperature_c": None, "description": f"Weather lookup failed: {exc}"}
