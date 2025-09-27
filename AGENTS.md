### Code run

For running commands, always use `uv`

### Code check

After each large update run:

- uv run ruff check . --fix

### Code style

- Always put private methods and fields lower than public methods (\_method below public method)

  For example:

  ```python
  class MyClass:
      public_field = 1
      _private_field = 2

      def __init__(self):
          self.public_method()
          self._private_method()

      def public_method(self):
          pass

      def _private_method(self):
          pass
  ```

- After code changes, always think how to refactor it and whether it is possible to reuse something, make it simpler and more readable.

### Code comments

Do not use obvious comments (even for docstrings). Give meaningful names to funcs, variables. Provide meaningful typings. Use comment for complex logic and not obvious points.

Wrong:

```python
def get_health_status(self) -> Optional[HealthCheckResponse]:
    """Get detailed health status from LogBull server.

    Returns:
        Health status response or None if unavailable
    """
    try:
        return self._make_health_request()
    except Exception as e:
        logger.debug(f"Failed to get health status: {e}")
        return None
```

Right (because func name is self-explanatory and typing is clear):

```python
def get_health_status(self) -> Optional[HealthCheckResponse]:
    try:
        return self._make_health_request()
    except Exception as e:
        logger.debug(f"Failed to get health status: {e}")
        return None
```