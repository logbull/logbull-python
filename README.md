# LogBull Python

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/logbull.svg)](https://pypi.org/project/logbull/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A Python library for sending logs to [LogBull](https://github.com/logbull/logbull) - a self-hosted log collection system.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Examples](#usage-examples)
  - [1. Standalone LogBullLogger](#1-standalone-logbulllogger)
  - [2. Python Logging Handler](#2-python-logging-handler)
  - [3. Loguru Integration](#3-loguru-integration)
  - [4. Structlog Integration](#4-structlog-integration)
- [Configuration Options](#configuration-options)
  - [LogBullLogger Parameters](#logbulllogger-parameters)
  - [Available Log Levels](#available-log-levels)
- [API Reference](#api-reference)
  - [LogBullLogger Methods](#logbulllogger-methods)
  - [Import Structure](#import-structure)
- [Requirements](#requirements)
- [License](#license)
- [Contributing](#contributing)
- [LogBull Server](#logbull-server)

## Features

- **Multiple integration options**: Standalone logger, Python logging handler, Loguru sink, and Structlog processor
- **Context support**: Attach persistent context to logs (session_id, user_id, etc.)
- **Type safety**: Full type annotations for better developer experience
- **Zero dependencies**: No third-party dependencies required

## Installation

```bash
pip install logbull
```

## Quick Start

The fastest way to start using LogBull - is to use itself as a logger.

```python
from logbull import LogBullLogger

# Initialize logger
logger = LogBullLogger(
    project_id="YOUR_PROJECT_ID",
    host="http://your-logbull-server:4005",
    api_key="YOUR_API_KEY"  # optional, if you need it
)

# Log messages (printed to console AND sent to LogBull)
logger.info("User logged in successfully", fields={
    "user_id": "12345",
    "username": "john_doe",
    "ip": "192.168.1.100"
})
```

## Usage Examples

### 1. Standalone LogBullLogger

```python
from logbull import LogBullLogger

# Basic configuration (INFO level by default)
logger = LogBullLogger(
    project_id="YOUR_PROJECT_ID",
    host="http://YOUR_LOGBULL_SERVER:4005",
    api_key="YOUR_API_KEY"  # optional, if you need it
)

# With DEBUG level
debug_logger = LogBullLogger(
    project_id="YOUR_PROJECT_ID",
    host="http://YOUR_LOGBULL_SERVER:4005",
    api_key="YOUR_API_KEY"  # optional, if you need it
    log_level="DEBUG"  # optional, defaults to INFO
)

# Basic logging
logger.info("User logged in successfully", fields={
    "user_id": "12345",
    "username": "john_doe",
    "ip": "192.168.1.100"
})

logger.error("Database connection failed", fields={
    "database": "users_db",
    "error_code": 500
})

# Debug logging (only shown if log_level="DEBUG")
debug_logger.debug("Processing user data", fields={
    "step": "validation",
    "user_id": "12345"
})
```

#### Context Management

```python
# Attach persistent context to all subsequent logs
session_logger = logger.with_context({
    "session_id": "sess_abc123",
    "user_id": "user_456",
    "request_id": "req_789"
})

# All logs from session_logger include the context automatically
session_logger.info("User started checkout process", fields={
    "cart_items": 3,
    "total_amount": 149.99
})
# Output includes: session_id, user_id, request_id + cart_items, total_amount

session_logger.error("Payment processing failed", fields={
    "payment_method": "credit_card",
    "error_code": "DECLINED"
})

# Context can be chained
transaction_logger = session_logger.with_context({
    "transaction_id": "txn_xyz789",
    "merchant_id": "merchant_123"
})

transaction_logger.info("Transaction completed", fields={
    "amount": 149.99,
    "currency": "USD"
})
# Includes all previous context + new transaction context
```

### 2. Python Logging Handler

```python
import logging
from logbull import LogBullHandler

# Setup standard Python logger with LogBull handler
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

logbull_handler = LogBullHandler(
    project_id="YOUR_PROJECT_ID",
    host="http://YOUR_LOGBULL_SERVER:4005",
    api_key="YOUR_API_KEY"  # optional, if you need it
)
logger.addHandler(logbull_handler)

# Use standard logging - logs automatically sent to LogBull
logger.info("Execution log: %s", execution_log.text, extra={"bot_id": bot_id})
logger.warning("Rate limit approaching", extra={
    "current_requests": 950,
    "limit": 1000
})
logger.error("Database error", extra={
    "query": "SELECT * FROM users",
    "error": "Connection timeout"
})
```

### 3. Loguru Integration

```python
from loguru import logger
from logbull import LoguruSink

# Add LogBull as a Loguru sink
logger.add(
    LoguruSink(
        project_id="YOUR_PROJECT_ID",
        host="http://YOUR_LOGBULL_SERVER:4005",
        api_key="YOUR_API_KEY"  # optional, if you need it
    ),
    level="INFO",
    format="{time} | {level} | {message}",
    serialize=True  # Captures structured data
)

# Use Loguru as usual - logs automatically sent to LogBull
logger.info("User action", user_id=12345, action="login", ip="192.168.1.100")
logger.error("Payment failed", order_id="ord_123", amount=99.99, currency="USD")

# Bind context for multiple logs
bound_logger = logger.bind(request_id="req_789", session_id="sess_456")
bound_logger.info("Request started")
bound_logger.info("Request completed", duration_ms=250)
```

### 4. Structlog Integration

```python
import structlog
from logbull import StructlogProcessor

# Configure structlog with LogBull processor
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        StructlogProcessor(
            project_id="YOUR_PROJECT_ID",
            host="http://YOUR_LOGBULL_SERVER:4005",
            api_key="YOUR_API_KEY"  # optional, if you need it
        ),
        structlog.processors.JSONRenderer(), # make sure it is the last processor
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
    logger_factory=structlog.WriteLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Use structlog - logs processed and sent to LogBull
logger.info("API request",
    method="POST",
    path="/api/users",
    status_code=201,
    response_time_ms=45
)

# With bound context
logger = logger.bind(correlation_id="corr_123", user_id="user_789")
logger.info("Processing payment", amount=150.00, currency="EUR")
logger.error("Payment gateway error",
    error_code="GATEWAY_TIMEOUT",
    retry_count=3
)
```

## Configuration Options

### LogBullLogger Parameters

- `project_id` (required): Your LogBull project ID (UUID format)
- `host` (required): LogBull server URL
- `api_key` (optional): API key for authentication
- `log_level` (optional): Minimum log level to process (default: "INFO")
- `context` (optional): Default context to attach to all logs

### Available Log Levels

- `DEBUG`: Detailed information for debugging
- `INFO`: General information messages
- `WARNING`/`WARN`: Warning messages
- `ERROR`: Error messages
- `CRITICAL`/`FATAL`: Critical error messages

## API Reference

### LogBullLogger Methods

- `debug(message, fields=None)`: Log debug message
- `info(message, fields=None)`: Log info message
- `warning(message, fields=None)`: Log warning message
- `error(message, fields=None)`: Log error message
- `critical(message, fields=None)`: Log critical message
- `with_context(context)`: Create new logger with additional context
- `flush()`: Immediately send all queued logs
- `shutdown()`: Stop background processing and send remaining logs

### Import Structure

```python
# Main imports
from logbull import LogBullLogger, LogBullHandler

# Integration-specific imports
from logbull.handlers import LoguruSink, StructlogProcessor

# Type imports (for type checking)
from logbull.core.types import LogLevel, LogFields
```

## Requirements

- Python 3.8+
- No external dependencies required
- Optional: `loguru` for Loguru integration
- Optional: `structlog` for Structlog integration

## License

Apache 2.0 License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## LogBull Server

This library requires a LogBull server instance. Visit [LogBull on GitHub](https://github.com/logbull/logbull) for server setup instructions.
