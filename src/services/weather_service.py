"""
Weather Service
Provides weather information using OpenWeatherMap API.
"""

import requests
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum

from ..utils.logger import EventLogger, MetricsLogger


class WeatherCondition(str, Enum):
    """Weather condition types"""
    CLEAR = "Clear"
    CLOUDS = "Clouds"
    RAIN = "Rain"
    DRIZZLE = "Drizzle"
    THUNDERSTORM = "Thunderstorm"
    SNOW = "Snow"
    MIST = "Mist"
    SMOKE = "Smoke"
    HAZE = "Haze"
    DUST = "Dust"
    FOG = "Fog"
    SAND = "Sand"
    ASH = "Ash"
    SQUALL = "Squall"
    TORNADO = "Tornado"


@dataclass
class WeatherData:
    """Current weather data"""
    temperature_c: float
    temperature_f: float
    feels_like_c: float
    feels_like_f: float
    humidity: int
    pressure: int
    wind_speed_mps: float
    wind_speed_mph: float
    wind_direction: int
    cloudiness: int
    condition: WeatherCondition
    description: str
    location: str
    country: str
    timestamp: datetime
    sunrise: datetime
    sunset: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "temperature_c": self.temperature_c,
            "temperature_f": self.temperature_f,
            "feels_like_c": self.feels_like_c,
            "feels_like_f": self.feels_like_f,
            "humidity": self.humidity,
            "pressure": self.pressure,
            "wind_speed_mps": self.wind_speed_mps,
            "wind_speed_mph": self.wind_speed_mph,
            "wind_direction": self.wind_direction,
            "cloudiness": self.cloudiness,
            "condition": self.condition.value,
            "description": self.description,
            "location": self.location,
            "country": self.country,
            "timestamp": self.timestamp.isoformat(),
            "sunrise": self.sunrise.isoformat(),
            "sunset": self.sunset.isoformat()
        }


@dataclass
class ForecastData:
    """Forecast data for a specific time"""
    datetime: datetime
    temperature_c: float
    temperature_f: float
    condition: WeatherCondition
    description: str
    precipitation_probability: float
    humidity: int
    wind_speed_mps: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "datetime": self.datetime.isoformat(),
            "temperature_c": self.temperature_c,
            "temperature_f": self.temperature_f,
            "condition": self.condition.value,
            "description": self.description,
            "precipitation_probability": self.precipitation_probability,
            "humidity": self.humidity,
            "wind_speed_mps": self.wind_speed_mps
        }


class WeatherService:
    """
    Weather service using OpenWeatherMap API.

    Features:
    - Current weather data
    - 5-day forecast
    - Location search
    - Unit conversion
    - Retry logic with exponential backoff
    """

    def __init__(
        self,
        api_key: str,
        logger: EventLogger,
        metrics_logger: MetricsLogger,
        units: str = "metric",
        max_retries: int = 3,
        timeout: int = 10
    ):
        """
        Initialize weather service.

        Args:
            api_key: OpenWeatherMap API key
            logger: Event logger
            metrics_logger: Metrics logger
            units: Units system ("metric" or "imperial")
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.logger = logger
        self.metrics_logger = metrics_logger
        self.units = units
        self.max_retries = max_retries
        self.timeout = timeout

        self.base_url = "https://api.openweathermap.org/data/2.5"

    def get_current_weather(
        self,
        location: str,
        country_code: Optional[str] = None
    ) -> Optional[WeatherData]:
        """
        Get current weather for a location.

        Args:
            location: City name
            country_code: Optional ISO 3166 country code

        Returns:
            WeatherData or None if failed
        """
        query = location
        if country_code:
            query = f"{location},{country_code}"

        params = {
            "q": query,
            "appid": self.api_key,
            "units": self.units
        }

        try:
            response = self._make_request_with_retry(
                f"{self.base_url}/weather",
                params
            )

            if response:
                return self._parse_weather_response(response)
            return None

        except Exception as e:
            self.logger.error(
                event='WEATHER_FETCH_ERROR',
                message=f'Failed to fetch weather for {location}: {str(e)}',
                location=location,
                error=str(e)
            )
            return None

    def get_forecast(
        self,
        location: str,
        days: int = 5,
        country_code: Optional[str] = None
    ) -> Optional[List[ForecastData]]:
        """
        Get weather forecast for a location.

        Args:
            location: City name
            days: Number of days (1-5)
            country_code: Optional ISO 3166 country code

        Returns:
            List of ForecastData or None if failed
        """
        query = location
        if country_code:
            query = f"{location},{country_code}"

        params = {
            "q": query,
            "appid": self.api_key,
            "units": self.units,
            "cnt": min(days * 8, 40)  # 8 forecasts per day, max 40
        }

        try:
            response = self._make_request_with_retry(
                f"{self.base_url}/forecast",
                params
            )

            if response:
                return self._parse_forecast_response(response)
            return None

        except Exception as e:
            self.logger.error(
                event='FORECAST_FETCH_ERROR',
                message=f'Failed to fetch forecast for {location}: {str(e)}',
                location=location,
                error=str(e)
            )
            return None

    def get_weather_by_coordinates(
        self,
        latitude: float,
        longitude: float
    ) -> Optional[WeatherData]:
        """
        Get current weather by geographic coordinates.

        Args:
            latitude: Latitude
            longitude: Longitude

        Returns:
            WeatherData or None if failed
        """
        params = {
            "lat": latitude,
            "lon": longitude,
            "appid": self.api_key,
            "units": self.units
        }

        try:
            response = self._make_request_with_retry(
                f"{self.base_url}/weather",
                params
            )

            if response:
                return self._parse_weather_response(response)
            return None

        except Exception as e:
            self.logger.error(
                event='WEATHER_FETCH_ERROR',
                message=f'Failed to fetch weather for ({latitude}, {longitude}): {str(e)}',
                error=str(e)
            )
            return None

    def _make_request_with_retry(
        self,
        url: str,
        params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Make HTTP request with exponential backoff retry logic.

        Args:
            url: API endpoint URL
            params: Query parameters

        Returns:
            JSON response dict or None if all retries failed
        """
        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    url,
                    params=params,
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    self.metrics_logger.record_metric(
                        'weather_api_success',
                        1,
                        {'attempt': attempt + 1}
                    )
                    return response.json()

                elif response.status_code == 429:
                    # Rate limit - wait and retry
                    wait_time = (2 ** attempt) * 1.0  # Exponential backoff
                    self.logger.warning(
                        event='WEATHER_API_RATE_LIMIT',
                        message=f'Rate limited, retrying in {wait_time}s',
                        attempt=attempt + 1
                    )
                    import time
                    time.sleep(wait_time)
                    continue

                elif response.status_code in [401, 403]:
                    # Auth error - don't retry
                    self.logger.error(
                        event='WEATHER_API_AUTH_ERROR',
                        message=f'Authentication failed: {response.status_code}',
                        status_code=response.status_code
                    )
                    return None

                elif response.status_code == 404:
                    # Not found - don't retry
                    self.logger.warning(
                        event='WEATHER_API_NOT_FOUND',
                        message='Location not found',
                        params=params
                    )
                    return None

                else:
                    # Other error - retry
                    self.logger.warning(
                        event='WEATHER_API_ERROR',
                        message=f'API error {response.status_code}, retrying...',
                        status_code=response.status_code,
                        attempt=attempt + 1
                    )
                    continue

            except requests.Timeout:
                self.logger.warning(
                    event='WEATHER_API_TIMEOUT',
                    message=f'Request timeout, attempt {attempt + 1}',
                    attempt=attempt + 1
                )
                continue

            except requests.ConnectionError:
                self.logger.warning(
                    event='WEATHER_API_CONNECTION_ERROR',
                    message=f'Connection error, attempt {attempt + 1}',
                    attempt=attempt + 1
                )
                continue

            except Exception as e:
                self.logger.error(
                    event='WEATHER_API_UNEXPECTED_ERROR',
                    message=f'Unexpected error: {str(e)}',
                    error=str(e),
                    attempt=attempt + 1
                )
                continue

        # All retries failed
        self.metrics_logger.record_metric('weather_api_failure', 1)
        return None

    def _parse_weather_response(self, data: Dict[str, Any]) -> WeatherData:
        """Parse weather API response into WeatherData"""
        main = data.get("main", {})
        weather = data.get("weather", [{}])[0]
        wind = data.get("wind", {})
        clouds = data.get("clouds", {})
        sys = data.get("sys", {})

        # Convert temperatures
        temp_c = main.get("temp", 0)
        feels_c = main.get("feels_like", 0)
        temp_f = temp_c * 9/5 + 32
        feels_f = feels_c * 9/5 + 32

        # Convert wind speed (m/s to mph)
        wind_mps = wind.get("speed", 0)
        wind_mph = wind_mps * 2.237

        # Parse condition
        try:
            condition = WeatherCondition(weather.get("main", "Clear"))
        except ValueError:
            condition = WeatherCondition.CLEAR

        return WeatherData(
            temperature_c=temp_c,
            temperature_f=temp_f,
            feels_like_c=feels_c,
            feels_like_f=feels_f,
            humidity=main.get("humidity", 0),
            pressure=main.get("pressure", 0),
            wind_speed_mps=wind_mps,
            wind_speed_mph=wind_mph,
            wind_direction=wind.get("deg", 0),
            cloudiness=clouds.get("all", 0),
            condition=condition,
            description=weather.get("description", ""),
            location=data.get("name", ""),
            country=sys.get("country", ""),
            timestamp=datetime.fromtimestamp(data.get("dt", 0)),
            sunrise=datetime.fromtimestamp(sys.get("sunrise", 0)),
            sunset=datetime.fromtimestamp(sys.get("sunset", 0))
        )

    def _parse_forecast_response(self, data: Dict[str, Any]) -> List[ForecastData]:
        """Parse forecast API response into list of ForecastData"""
        forecasts = []

        for item in data.get("list", []):
            main = item.get("main", {})
            weather = item.get("weather", [{}])[0]
            wind = item.get("wind", {})

            temp_c = main.get("temp", 0)
            temp_f = temp_c * 9/5 + 32
            wind_mps = wind.get("speed", 0)

            try:
                condition = WeatherCondition(weather.get("main", "Clear"))
            except ValueError:
                condition = WeatherCondition.CLEAR

            forecasts.append(ForecastData(
                datetime=datetime.fromtimestamp(item.get("dt", 0)),
                temperature_c=temp_c,
                temperature_f=temp_f,
                condition=condition,
                description=weather.get("description", ""),
                precipitation_probability=item.get("pop", 0) * 100,
                humidity=main.get("humidity", 0),
                wind_speed_mps=wind_mps
            ))

        return forecasts

    def format_weather_summary(self, weather: WeatherData) -> str:
        """Format weather data into human-readable summary"""
        return (
            f"Current weather in {weather.location}, {weather.country}:\n"
            f"Temperature: {weather.temperature_c:.1f}°C ({weather.temperature_f:.1f}°F)\n"
            f"Feels like: {weather.feels_like_c:.1f}°C ({weather.feels_like_f:.1f}°F)\n"
            f"Conditions: {weather.description.capitalize()}\n"
            f"Humidity: {weather.humidity}%\n"
            f"Wind: {weather.wind_speed_mps:.1f} m/s ({weather.wind_speed_mph:.1f} mph)\n"
            f"Sunrise: {weather.sunrise.strftime('%H:%M')}, "
            f"Sunset: {weather.sunset.strftime('%H:%M')}"
        )


def create_weather_service(
    api_key: str,
    logger: EventLogger,
    metrics_logger: MetricsLogger
) -> WeatherService:
    """Factory function to create WeatherService"""
    return WeatherService(
        api_key=api_key,
        logger=logger,
        metrics_logger=metrics_logger
    )
