"""
Agent Platform Skills Module

This module provides skill implementations for the A2A protocol.
"""

from .weather import WeatherSkill, get_weather_skill

__all__ = [
    "WeatherSkill",
    "get_weather_skill"
]
