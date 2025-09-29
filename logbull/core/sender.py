import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from queue import Empty, Queue
from typing import List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..utils import LogFormatter
from .registry import register_sender
from .types import LogBatch, LogBullConfig, LogBullResponse, LogEntry


class LogSender:
    def __init__(self, config: LogBullConfig):
        self.config = config
        self.formatter = LogFormatter()

        # Ensure batch size never exceeds 1000
        self.batch_size = min(config.get("batch_size", 1000), 1000)
        self.batch_interval = 1.0

        self._log_queue: Queue[LogEntry] = Queue()
        self._batch_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._thread_init_lock = threading.Lock()
        self._thread_started = False

        # Add shutdown flag to prevent new task submissions during shutdown
        self._shutdown_started = False
        self._shutdown_lock = threading.Lock()

        # ThreadPoolExecutor for concurrent HTTP requests
        self._executor: Optional[ThreadPoolExecutor] = None
        self._executor_lock = threading.Lock()
        self._active_requests = 0
        self._min_threads = 1
        self._max_threads = 10  # Start with reasonable max, can be adjusted

        # Register this sender for automatic cleanup on app shutdown
        register_sender(self)

    def add_log_to_queue(self, log_entry: LogEntry) -> None:
        if self._stop_event.is_set():
            return

        # Initialize thread lazily on first log
        if not self._thread_started:
            with self._thread_init_lock:
                if not self._thread_started:
                    self._start_batch_processor()
                    self._thread_started = True

        try:
            self._log_queue.put(log_entry, timeout=0.1)

            if self._log_queue.qsize() >= self.batch_size:
                self._send_queued_logs()

        except Exception as e:
            print(f"LogBull: Failed to add log to queue: {e}")

    def send_logs(self, logs: List[LogEntry]) -> LogBullResponse:
        if not logs:
            return {"accepted": 0, "rejected": 0, "message": "No logs to send"}

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
        self._send_queued_logs()

        # Wait for currently submitted tasks to complete
        if self._executor:
            # Wait for all currently running tasks to finish
            # This gives us better guarantees that logs are actually sent
            try:
                # We can't wait for individual futures since we don't store them,
                # but we can wait until active request count drops to 0
                timeout = 30  # Maximum wait time
                start_time = time.time()

                while (
                    self._active_requests > 0 and (time.time() - start_time) < timeout
                ):
                    time.sleep(0.1)  # Small sleep to avoid busy waiting

                if self._active_requests > 0:
                    print(
                        f"LogBull: Flush timeout - {self._active_requests} requests still pending"
                    )

            except Exception as e:
                print(f"LogBull: Error during flush wait: {e}")

    def shutdown(self) -> None:
        # Mark shutdown as started to prevent new task submissions
        with self._shutdown_lock:
            if self._shutdown_started:
                return  # Already shutting down
            self._shutdown_started = True

        self._stop_event.set()

        # Only flush if thread was started
        if self._thread_started:
            self.flush()

        # Shutdown the ThreadPoolExecutor and wait for completion
        if self._executor:
            try:
                # Give pending tasks a chance to complete
                self._executor.shutdown(wait=True)
            except Exception as e:
                print(f"LogBull: Error shutting down executor: {e}")
            finally:
                self._executor = None

        if self._batch_thread and self._batch_thread.is_alive():
            self._batch_thread.join(timeout=10)

    def _get_or_create_executor(self) -> Optional[ThreadPoolExecutor]:
        with self._executor_lock:
            # Don't create new executors during shutdown
            if self._shutdown_started:
                return None

            if self._executor is None:
                # Start with minimum threads, will grow as needed
                initial_threads = min(self._min_threads, self._max_threads)
                self._executor = ThreadPoolExecutor(
                    max_workers=initial_threads, thread_name_prefix="LogBull-Sender"
                )

            return self._executor

    def _resize_executor_if_needed(self) -> None:
        """Dynamically adjust thread pool size based on load"""
        if not self._executor or self._shutdown_started:
            return

        with self._executor_lock:
            if self._shutdown_started:  # Double-check after acquiring lock
                return

            current_threads = self._executor._max_workers

            # If we have many pending requests and can grow
            if (
                self._active_requests >= current_threads * 0.8
                and current_threads < self._max_threads
            ):
                # Grow the pool by creating a new executor
                new_size = min(current_threads + 2, self._max_threads)
                old_executor = self._executor
                self._executor = ThreadPoolExecutor(
                    max_workers=new_size, thread_name_prefix="LogBull-Sender"
                )

                # Let old executor finish its tasks in background
                threading.Thread(
                    target=lambda: old_executor.shutdown(wait=True), daemon=True
                ).start()

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

    def _send_queued_logs(self) -> None:
        # Check if shutdown has started before processing
        if self._shutdown_started:
            return

        logs_to_send: List[LogEntry] = []

        while len(logs_to_send) < self.batch_size and not self._log_queue.empty():
            try:
                log_entry = self._log_queue.get(timeout=0.1)
                logs_to_send.append(log_entry)
            except Empty:
                break

        if logs_to_send:
            try:
                executor = self._get_or_create_executor()
                if executor is None:
                    # Executor is shutdown, can't submit tasks
                    return

                self._active_requests += 1
                # Submit to thread pool without waiting for completion
                executor.submit(self._send_logs_async, logs_to_send)
                # Optionally check if we need to resize the executor
                self._resize_executor_if_needed()
            except Exception as e:
                print(f"LogBull: Failed to submit logs batch: {e}")
                self._active_requests -= 1

    def _send_logs_async(self, logs: List[LogEntry]) -> None:
        """Async wrapper for send_logs that handles completion"""
        try:
            response = self.send_logs(logs)
            self._handle_response(response, logs)
        except Exception as e:
            print(f"LogBull: Failed to send logs batch: {e}")
        finally:
            self._active_requests -= 1

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

                if response.status in [200, 202]:
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
        rejected = response.get("rejected", 0)

        if rejected > 0:
            print(f"LogBull: Rejected {rejected} log entries")

            errors = response.get("errors")
            if errors:
                print("LogBull: Rejected log details:")
                for error in errors:
                    index = error.get("index", -1)
                    message = error.get("message", "Unknown error")
                    if 0 <= index < len(sent_logs):
                        log_content = sent_logs[index]
                        print(f"  - Log #{index} rejected ({message}):")
                        print(f"    Level: {log_content.get('level', 'unknown')}")
                        print(f"    Message: {log_content.get('message', 'unknown')}")
                        print(
                            f"    Timestamp: {log_content.get('timestamp', 'unknown')}"
                        )
                        if log_content.get("fields"):
                            print(f"    Fields: {log_content['fields']}")
                        print()
