# gui/utils/decorators.py

import functools
import time
import logging
import threading # Added for CircuitBreaker's RLock
from typing import Callable, Any, Optional

# Note: The ErrorSeverity and ErrorContext classes below are local stubs.
# If your project has centralized, more feature-rich versions (e.g., ErrorSeverity as an Enum),
# consider importing and using those for better consistency and type safety across the application.
# For example, from ..core.exceptions or ..core.constants if defined there.

class ErrorSeverity: # Simplified stub, functional for this decorator's string comparisons
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorContext: # Simplified stub
    def __init__(self, component, operation, max_attempts, severity):
        self.component = component
        self.operation = operation
        self.attempt = 1
        self.max_attempts = max_attempts
        self.severity = severity # Should align with string values from ErrorSeverity class
        self.last_error = None
        self.error_count = 0
    def should_retry(self): return self.attempt < self.max_attempts # Simplified retry logic
    def get_retry_delay(self): return 0.5 * (2**(self.attempt - 1))


def safe_execute(max_attempts: int = 3, 
                 initial_delay: float = 0.5, 
                 max_delay: float = 10.0,
                 severity: str = ErrorSeverity.MEDIUM, 
                 exception_to_catch: type = Exception):
    """
    A robust decorator for safe execution with retry logic, exponential backoff,
    and detailed logging.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Optional[Any]:
            component_name = func.__module__ or "unknown_module"
            # Attempt to get class name if 'self' or 'cls' is the first argument
            if args:
                first_arg = args[0]
                if hasattr(first_arg, '__class__') and not isinstance(first_arg, type): # It's an instance
                    component_name = first_arg.__class__.__name__
                elif isinstance(first_arg, type): # It's a class itself (for classmethods)
                    component_name = first_arg.__name__
            
            logger = logging.getLogger(f"{component_name}.{func.__name__}")
            
            current_attempt = 0
            last_exception: Optional[Exception] = None

            while current_attempt < max_attempts:
                current_attempt += 1
                try:
                    return func(*args, **kwargs)
                except exception_to_catch as e:
                    last_exception = e
                    log_level = logging.WARNING if current_attempt < max_attempts else logging.ERROR
                    # Check against string values of the local ErrorSeverity class
                    if severity == ErrorSeverity.CRITICAL and current_attempt >= max_attempts :
                         log_level = logging.CRITICAL
                    
                    logger.log(log_level,
                               f"Attempt {current_attempt}/{max_attempts} for '{func.__name__}' failed: {type(e).__name__} - {e}",
                               exc_info=(log_level >= logging.ERROR))

                    if current_attempt < max_attempts:
                        delay = min(initial_delay * (2 ** (current_attempt - 1)), max_delay)
                        logger.info(f"Retrying '{func.__name__}' in {delay:.2f}s...")
                        time.sleep(delay)
                    else: 
                        if severity == ErrorSeverity.CRITICAL:
                            logger.critical(f"Critical operation '{func.__name__}' failed definitively after {max_attempts} attempts.")
                            raise 
                        logger.error(f"Operation '{func.__name__}' failed after {max_attempts} attempts.")
                        return None 
            return None 
        return wrapper
    return decorator

# Note: This CircuitBreaker is simpler than the one in the large combined script.
# The combined script's CircuitBreaker used a ComponentState Enum.
# If consistency with that more detailed version is needed, this should be updated.
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0.0 # Initialize to avoid issues with time.monotonic()
        self.is_open = False
        self._lock = threading.RLock() # RLock is good practice
        self._logger = logging.getLogger(f"CircuitBreaker.{func_name if (func_name:=getattr(self, '__name__', None)) else id(self)}")


    def __call__(self, func: Callable) -> Callable:
        func_name_for_logger = func.__name__ # Capture for logger before wrapper
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with self._lock:
                if self.is_open:
                    if time.monotonic() - self.last_failure_time > self.recovery_timeout:
                        self._logger.info(f"Circuit breaker for {func_name_for_logger} is half-open. Allowing one attempt.")
                        self.is_open = False # Half-open: allow one attempt
                        # Reset failure_count to allow some retries in half-open state before re-opening fully
                        # self.failure_count = self.failure_threshold // 2 
                    else:
                        self._logger.warning(f"Circuit breaker for {func_name_for_logger} is open. Call rejected.")
                        raise Exception(f"Circuit for {func_name_for_logger} is open.")
            try:
                result = func(*args, **kwargs)
                with self._lock: 
                    if self.failure_count > 0 or self.is_open : 
                         self._logger.info(f"Call to {func_name_for_logger} succeeded. Resetting circuit breaker.")
                    self.failure_count = 0
                    self.is_open = False
                return result
            except Exception as e:
                with self._lock:
                    self.failure_count += 1
                    self.last_failure_time = time.monotonic()
                    if self.failure_count >= self.failure_threshold:
                        if not self.is_open: # Log only when it transitions to open
                            self._logger.error(f"Circuit breaker for {func_name_for_logger} opened due to {self.failure_count} failures.")
                        self.is_open = True
                    else:
                        self._logger.warning(f"Call to {func_name_for_logger} failed ({self.failure_count}/{self.failure_threshold} failures).")
                raise e # Re-raise the original exception
        return wrapper

