"""
Weather Skill Implementation

Provides weather query functionality as an A2A skill.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

logger = logging.getLogger(__name__)


class WeatherCondition(str, Enum):
    """Weather conditions"""
    SUNNY = "sunny"
    CLOUDY = "cloudy"
    PARTLY_CLOUDY = "partly_cloudy"
    RAINY = "rainy"
    SNOWY = "snowy"
    STORMY = "stormy"
    FOGGY = "foggy"
    WINDY = "windy"


@dataclass
class WeatherData:
    """Weather data structure"""
    city: str
    country: str = ""
    temperature_celsius: float = 0.0
    temperature_fahrenheit: float = 32.0
    humidity: int = 0
    condition: WeatherCondition = WeatherCondition.SUNNY
    description: str = ""
    wind_speed_kmh: float = 0.0
    wind_direction: str = ""
    visibility_km: float = 10.0
    pressure_hpa: int = 1013
    uv_index: int = 0
    sunrise: str = ""
    sunset: str = ""
    forecast: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "simulated"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "city": self.city,
            "country": self.country,
            "temperature": {
                "celsius": self.temperature_celsius,
                "fahrenheit": self.temperature_fahrenheit
            },
            "humidity": self.humidity,
            "condition": self.condition.value,
            "description": self.description,
            "wind": {
                "speed_kmh": self.wind_speed_kmh,
                "direction": self.wind_direction
            },
            "visibility_km": self.visibility_km,
            "pressure_hpa": self.pressure_hpa,
            "uv_index": self.uv_index,
            "sunrise": self.sunrise,
            "sunset": self.sunset,
            "forecast": self.forecast,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source
        }

    def to_natural_language(self) -> str:
        """Generate natural language description"""
        temp_f = self.temperature_fahrenheit
        temp_c = self.temperature_celsius

        text = f"Current weather in {self.city}"
        if self.country:
            text += f", {self.country}"
        text += f":\n\n"

        text += f"Temperature: {temp_c:.1f}C ({temp_f:.1f}F)\n"
        text += f"Condition: {self.description or self.condition.value.replace('_', ' ').title()}\n"
        text += f"Humidity: {self.humidity}%\n"

        if self.wind_speed_kmh > 0:
            text += f"Wind: {self.wind_speed_kmh:.1f} km/h {self.wind_direction}\n"

        if self.visibility_km < 10:
            text += f"Visibility: {self.visibility_km:.1f} km\n"

        if self.sunrise and self.sunset:
            text += f"\nSunrise: {self.sunrise}, Sunset: {self.sunset}\n"

        if self.forecast:
            text += "\nForecast:\n"
            for day in self.forecast[:3]:
                text += f"  - {day.get('date', 'N/A')}: {day.get('condition', 'N/A')}, "
                text += f"High {day.get('high_c', 'N/A')}C, Low {day.get('low_c', 'N/A')}C\n"

        return text


class WeatherSkill:
    """
    Weather Query Skill

    Provides weather information for A2A protocol.
    Supports multiple weather data sources.
    """

    SKILL_ID = "weather"
    SKILL_NAME = "Weather Query"
    SKILL_DESCRIPTION = "Get current weather and forecast for any city"
    SKILL_TAGS = ["weather", "forecast", "temperature"]
    SKILL_INPUT_MODES = ["text"]
    SKILL_OUTPUT_MODES = ["text"]
    SKILL_EXAMPLES = [
        "What's the weather in Shanghai?",
        "Will it rain tomorrow in Beijing?",
        "Current temperature in New York"
    ]

    # Pricing (in wei)
    BASE_PRICE_WEI = 500000000000000  # 0.0005 ETH

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize weather skill.

        Args:
            api_key: Optional API key for weather service
        """
        self.api_key = api_key or os.environ.get("WEATHER_API_KEY")
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client"""
        if not HAS_HTTPX:
            raise ImportError("httpx package required")
        if not self._http_client:
            self._http_client = httpx.AsyncClient(timeout=10.0)
        return self._http_client

    async def close(self):
        """Close resources"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    def get_skill_definition(self) -> Dict[str, Any]:
        """Get A2A skill definition"""
        return {
            "id": self.SKILL_ID,
            "name": self.SKILL_NAME,
            "description": self.SKILL_DESCRIPTION,
            "tags": self.SKILL_TAGS,
            "examples": self.SKILL_EXAMPLES,
            "inputModes": self.SKILL_INPUT_MODES,
            "outputModes": self.SKILL_OUTPUT_MODES,
            "pricing": {
                "base_price_wei": str(self.BASE_PRICE_WEI),
                "base_price_eth": "0.0005",
                "per_request": True
            }
        }

    async def execute(
        self,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute weather query.

        Args:
            message: User query (e.g., "Weather in Shanghai")
            metadata: Additional metadata

        Returns:
            Weather data and natural language response
        """
        # Extract city from message
        city = self._extract_city(message)

        if not city:
            return {
                "success": False,
                "error": "Could not determine city from query",
                "response": "Please specify a city for weather query. For example: 'Weather in Shanghai'"
            }

        # Get weather data
        try:
            weather = await self._fetch_weather(city)

            return {
                "success": True,
                "data": weather.to_dict(),
                "response": weather.to_natural_language(),
                "tokens_used": {
                    "input": len(message.split()),
                    "output": len(weather.to_natural_language().split())
                }
            }

        except Exception as e:
            logger.error(f"Weather query failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": f"Unable to get weather for {city}: {str(e)}"
            }

    def _extract_city(self, message: str) -> Optional[str]:
        """Extract city name from user message"""
        # Common patterns
        import re

        message_lower = message.lower()

        # Pattern: "weather in {city}"
        match = re.search(r'weather (?:in|for|at) ([a-zA-Z\s]+)', message_lower)
        if match:
            return match.group(1).strip().title()

        # Pattern: "{city} weather"
        match = re.search(r'([a-zA-Z\s]+) weather', message_lower)
        if match:
            return match.group(1).strip().title()

        # Pattern: "temperature in {city}"
        match = re.search(r'temperature (?:in|for|at) ([a-zA-Z\s]+)', message_lower)
        if match:
            return match.group(1).strip().title()

        # Known cities
        known_cities = [
            "Shanghai", "Beijing", "Shenzhen", "Guangzhou", "Hong Kong",
            "Tokyo", "Seoul", "Singapore", "Bangkok", "Jakarta",
            "New York", "Los Angeles", "Chicago", "San Francisco", "Seattle",
            "London", "Paris", "Berlin", "Rome", "Madrid",
            "Sydney", "Melbourne", "Auckland"
        ]

        for city in known_cities:
            if city.lower() in message_lower:
                return city

        return None

    async def _fetch_weather(self, city: str) -> WeatherData:
        """
        Fetch weather data for a city.

        Uses real API if available, otherwise returns simulated data.
        """
        # Try wttr.in (free, no API key required)
        try:
            if HAS_HTTPX:
                return await self._fetch_from_wttr(city)
        except Exception as e:
            logger.warning(f"wttr.in failed: {e}, using simulated data")

        # Fall back to simulated data
        return self._generate_simulated_weather(city)

    async def _fetch_from_wttr(self, city: str) -> WeatherData:
        """Fetch weather from wttr.in"""
        client = await self._get_client()

        url = f"https://wttr.in/{city}?format=j1"
        response = await client.get(url)
        response.raise_for_status()

        data = response.json()

        # Parse current condition
        current = data.get("current_condition", [{}])[0]
        weather_desc = current.get("weatherDesc", [{}])[0].get("value", "")

        # Map condition
        condition = WeatherCondition.SUNNY
        weather_lower = weather_desc.lower()
        if "rain" in weather_lower:
            condition = WeatherCondition.RAINY
        elif "cloud" in weather_lower or "overcast" in weather_lower:
            condition = WeatherCondition.CLOUDY
        elif "snow" in weather_lower:
            condition = WeatherCondition.SNOWY
        elif "storm" in weather_lower or "thunder" in weather_lower:
            condition = WeatherCondition.STORMY
        elif "fog" in weather_lower or "mist" in weather_lower:
            condition = WeatherCondition.FOGGY

        # Parse forecast
        forecast = []
        for day in data.get("weather", []):
            forecast.append({
                "date": day.get("date", ""),
                "condition": day.get("hourly", [{}])[4].get("weatherDesc", [{}])[0].get("value", ""),
                "high_c": int(day.get("maxtempC", 0)),
                "low_c": int(day.get("mintempC", 0)),
                "chance_of_rain": day.get("hourly", [{}])[4].get("chanceofrain", "0")
            })

        temp_c = float(current.get("temp_C", 20))
        temp_f = float(current.get("temp_F", 68))

        # Get location info
        area = data.get("nearest_area", [{}])[0]
        country = area.get("country", [{}])[0].get("value", "")

        # Get astronomy
        astronomy = data.get("weather", [{}])[0].get("astronomy", [{}])[0]

        return WeatherData(
            city=city,
            country=country,
            temperature_celsius=temp_c,
            temperature_fahrenheit=temp_f,
            humidity=int(current.get("humidity", 50)),
            condition=condition,
            description=weather_desc,
            wind_speed_kmh=float(current.get("windspeedKmph", 0)),
            wind_direction=current.get("winddir16Point", ""),
            visibility_km=float(current.get("visibility", 10)),
            pressure_hpa=int(current.get("pressure", 1013)),
            uv_index=int(current.get("uvIndex", 3)),
            sunrise=astronomy.get("sunrise", ""),
            sunset=astronomy.get("sunset", ""),
            forecast=forecast,
            source="wttr.in"
        )

    def _generate_simulated_weather(self, city: str) -> WeatherData:
        """Generate simulated weather data"""
        import random

        # Simulated data based on city location
        city_data = {
            "Shanghai": {"temp_c": 15, "humid": 70, "cond": WeatherCondition.PARTLY_CLOUDY},
            "Beijing": {"temp_c": 8, "humid": 40, "cond": WeatherCondition.SUNNY},
            "Tokyo": {"temp_c": 12, "humid": 60, "cond": WeatherCondition.CLOUDY},
            "New York": {"temp_c": 5, "humid": 55, "cond": WeatherCondition.PARTLY_CLOUDY},
            "London": {"temp_c": 8, "humid": 80, "cond": WeatherCondition.RAINY},
            "Sydney": {"temp_c": 25, "humid": 65, "cond": WeatherCondition.SUNNY}
        }

        base = city_data.get(city, {"temp_c": 18, "humid": 50, "cond": WeatherCondition.SUNNY})

        # Add some randomness
        temp_c = base["temp_c"] + random.randint(-3, 3)
        temp_f = temp_c * 9/5 + 32

        # Generate forecast
        forecast = []
        for i in range(3):
            date = datetime.now() + timedelta(days=i+1)
            forecast.append({
                "date": date.strftime("%Y-%m-%d"),
                "condition": random.choice(list(WeatherCondition)).value,
                "high_c": temp_c + random.randint(0, 5),
                "low_c": temp_c - random.randint(2, 8),
                "chance_of_rain": random.randint(0, 50)
            })

        return WeatherData(
            city=city,
            temperature_celsius=temp_c,
            temperature_fahrenheit=temp_f,
            humidity=base["humid"] + random.randint(-10, 10),
            condition=base["cond"],
            description=base["cond"].value.replace("_", " ").title(),
            wind_speed_kmh=random.randint(5, 25),
            wind_direction=random.choice(["N", "NE", "E", "SE", "S", "SW", "W", "NW"]),
            visibility_km=10.0,
            pressure_hpa=1013 + random.randint(-10, 10),
            uv_index=random.randint(1, 8),
            sunrise="06:30",
            sunset="18:00",
            forecast=forecast,
            source="simulated"
        )


# Singleton instance
_weather_skill: Optional[WeatherSkill] = None


def get_weather_skill() -> WeatherSkill:
    """Get the weather skill instance"""
    global _weather_skill
    if _weather_skill is None:
        _weather_skill = WeatherSkill()
    return _weather_skill


async def main():
    """Test the weather skill"""
    skill = WeatherSkill()

    try:
        # Test queries
        queries = [
            "What's the weather in Shanghai?",
            "Temperature in Beijing",
            "Will it rain in Tokyo today?"
        ]

        for query in queries:
            print(f"\nQuery: {query}")
            print("-" * 50)
            result = await skill.execute(query)
            if result["success"]:
                print(result["response"])
            else:
                print(f"Error: {result['error']}")

    finally:
        await skill.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
