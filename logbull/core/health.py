import json
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .types import HealthCheckResponse


class HealthChecker:
    def __init__(self, host: str):
        self.host = host.rstrip("/")

    def check_availability(self) -> bool:
        try:
            response = self._make_health_request()
            return response is not None
        except Exception as e:
            print(f"LogBull: Health check failed: {e}")
            return False

    def get_health_status(self) -> Optional[HealthCheckResponse]:
        try:
            return self._make_health_request()
        except Exception as e:
            print(f"LogBull: Failed to get health status: {e}")
            return None

    def _make_health_request(self) -> Optional[HealthCheckResponse]:
        health_url = f"{self.host}/api/v1/downdetect/is-available"

        try:
            request = Request(health_url)
            request.add_header("Content-Type", "application/json")
            request.add_header("User-Agent", "LogBull-Python-Client/1.0")

            with urlopen(request, timeout=30) as response:
                if response.status == 200:
                    content = response.read().decode("utf-8")
                    if content.strip():
                        try:
                            parsed_response: HealthCheckResponse = json.loads(content)
                            return parsed_response
                        except json.JSONDecodeError:
                            return {"status": "ok"}
                    else:
                        return {"status": "ok"}
                else:
                    print(f"LogBull: Health check returned status {response.status}")
                    return None

        except HTTPError as e:
            print(f"LogBull: Health check HTTP error: {e.code} - {e.reason}")
            return None

        except URLError as e:
            print(f"LogBull: Health check URL error: {e.reason}")
            return None

        except Exception as e:
            print(f"LogBull: Health check unexpected error: {e}")
            return None
