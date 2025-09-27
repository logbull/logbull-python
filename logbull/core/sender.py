import json
import threading
from queue import Empty, Queue
from typing import List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..utils import LogFormatter
from .health import HealthChecker
from .types import LogBatch, LogBullConfig, LogBullResponse, LogEntry


class LogSender:
    def __init__(self, config: LogBullConfig):
        self.config = config
        self.formatter = LogFormatter()
        self.health_checker = HealthChecker(config["host"])

        self.batch_size = config.get("batch_size", 1000)
        self.batch_interval = 1.0

        self._log_queue: Queue[LogEntry] = Queue()
        self._batch_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._health_checked = False

        self._start_batch_processor()

    def add_log_to_queue(self, log_entry: LogEntry) -> None:
        if self._stop_event.is_set():
            return

        try:
            self._log_queue.put(log_entry, timeout=0.1)

            if self._log_queue.qsize() >= self.batch_size:
                self._send_queued_logs(force=True)

        except Exception as e:
            print(f"LogBull: Failed to add log to queue: {e}")

    def send_logs(self, logs: List[LogEntry]) -> LogBullResponse:
        if not logs:
            return {"accepted": 0, "rejected": 0, "message": "No logs to send"}

        if not self._health_checked:
            if not self.health_checker.check_availability():
                print("LogBull: Server health check failed, attempting to send anyway")
            self._health_checked = True

        log_dicts: List[LogEntry] = []
        for entry in logs:
            log_dict: LogEntry = {
                "level": entry["level"],
                "message": entry["message"],
                "timestamp": entry["timestamp"],
                "fields": entry["fields"],
            }
            log_dicts.append(log_dict)
        batch: LogBatch = {"logs": log_dicts}
        return self._send_http_request(batch)

    def flush(self) -> None:
        self._send_queued_logs(force=True)

    def shutdown(self) -> None:
        self._stop_event.set()

        self.flush()

        if self._batch_thread and self._batch_thread.is_alive():
            self._batch_thread.join(timeout=5)

    def _start_batch_processor(self) -> None:
        self._batch_thread = threading.Thread(
            target=self._batch_processor_loop,
            name="LogBull-BatchProcessor",
            daemon=True,
        )
        self._batch_thread.start()

    def _batch_processor_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                if self._stop_event.wait(timeout=self.batch_interval):
                    break

                self._send_queued_logs()

            except Exception as e:
                print(f"LogBull: Error in batch processor: {e}")

    def _send_queued_logs(self, force: bool = False) -> None:
        logs_to_send: List[LogEntry] = []

        while len(logs_to_send) < self.batch_size and not self._log_queue.empty():
            try:
                log_entry = self._log_queue.get(timeout=0.1)
                logs_to_send.append(log_entry)
            except Empty:
                break

        if logs_to_send and (force or len(logs_to_send) >= self.batch_size):
            try:
                response = self.send_logs(logs_to_send)
                self._handle_response(response, logs_to_send)
            except Exception as e:
                print(f"LogBull: Failed to send logs batch: {e}")

    def _send_http_request(self, batch: LogBatch) -> LogBullResponse:
        url = f"{self.config['host']}/api/v1/logs/receiving/{self.config['project_id']}"

        try:
            data = json.dumps(batch).encode("utf-8")
            request = Request(url, data=data, method="POST")
            request.add_header("Content-Type", "application/json")
            request.add_header("User-Agent", "LogBull-Python-Client/1.0")

            api_key = self.config.get("api_key")
            if api_key:
                request.add_header("X-API-Key", api_key)

            with urlopen(request, timeout=30) as response:
                content = response.read().decode("utf-8")

                if response.status == 200:
                    try:
                        parsed_response: LogBullResponse = json.loads(content)
                        return parsed_response
                    except json.JSONDecodeError:
                        return {
                            "accepted": len(batch["logs"]),
                            "rejected": 0,
                            "message": "Response not JSON, assuming success",
                        }
                else:
                    print(
                        f"LogBull: Server returned status {response.status}: {content}"
                    )
                    return {
                        "accepted": 0,
                        "rejected": len(batch["logs"]),
                        "message": f"Server error: {response.status}",
                    }

        except HTTPError as e:
            error_message = f"HTTP error {e.code}: {e.reason}"
            print(f"LogBull: HTTP error: {error_message}")
            return {
                "accepted": 0,
                "rejected": len(batch["logs"]),
                "message": error_message,
            }

        except URLError as e:
            error_message = f"Connection error: {e.reason}"
            print(f"LogBull: Connection error: {error_message}")
            return {
                "accepted": 0,
                "rejected": len(batch["logs"]),
                "message": error_message,
            }

        except Exception as e:
            error_message = f"Unexpected error: {e}"
            print(f"LogBull: Unexpected error: {error_message}")
            return {
                "accepted": 0,
                "rejected": len(batch["logs"]),
                "message": error_message,
            }

    def _handle_response(
        self, response: LogBullResponse, sent_logs: List[LogEntry]
    ) -> None:
        accepted = response.get("accepted", 0)
        rejected = response.get("rejected", 0)

        if rejected > 0:
            print(f"LogBull: Rejected {rejected} log entries")

            errors = response.get("errors")
            if errors:
                for error in errors:
                    index = error.get("index", -1)
                    message = error.get("message", "Unknown error")
                    if index < len(sent_logs):
                        log_content = sent_logs[index]
                        print(f"LogBull: Rejected log #{index}: {message}")
                        print(f"LogBull: Log content: {log_content}")

        if accepted > 0:
            print(f"LogBull: Accepted {accepted} log entries")
