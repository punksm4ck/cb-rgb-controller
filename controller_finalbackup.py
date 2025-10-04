#!/usr/bin/env python3
"""
Enhanced Chromebook RGB Keyboard Controller - v6.1.0
Ultra-robust error handling with comprehensive fallback mechanisms.
Supports both ectool and direct EC control methods.
Features settings persistence, comprehensive logging, and bulletproof error recovery.
"""

import tkinter as tk
from tkinter import ttk, colorchooser, messagebox, scrolledtext, filedialog
import subprocess
import os
import sys
import datetime
import re
import json
import threading
import time
import colorsys
import logging
import logging.handlers
import platform
import random
import traceback
import math
import shlex
import signal
import shutil
import tempfile
from functools import partial, wraps
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass, asdict, field
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import queue
from enum import Enum

# Try to import psutil for enhanced system information
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Application Constants
VERSION = "6.1.0"
APP_NAME = "Enhanced Chromebook RGB Control"
NUM_ZONES = 4
LEDS_PER_ZONE = 3
TOTAL_LEDS = NUM_ZONES * LEDS_PER_ZONE

# Error Handling Constants
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_BASE = 0.5  # Base delay in seconds
MAX_ERROR_COUNT = 10
CIRCUIT_BREAKER_THRESHOLD = 5
CIRCUIT_BREAKER_TIMEOUT = 30  # seconds

# Desktop file configuration
DESKTOP_FILE_NAME = "chromebook-rgb-gui.desktop"


class ErrorSeverity(Enum):
    """Error severity levels for handling decisions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComponentState(Enum):
    """Component operational states."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    FAILED = "failed"


@dataclass
class ErrorContext:
    """Context information for error handling."""
    component: str
    operation: str
    attempt: int = 1
    max_attempts: int = MAX_RETRY_ATTEMPTS
    last_error: Optional[Exception] = None
    error_count: int = 0
    severity: ErrorSeverity = ErrorSeverity.MEDIUM

    def should_retry(self) -> bool:
        """Determine if operation should be retried."""
        return (
            self.attempt < self.max_attempts and
            self.error_count < MAX_ERROR_COUNT and
            self.severity != ErrorSeverity.CRITICAL
        )

    def get_retry_delay(self) -> float:
        """Calculate exponential backoff delay."""
        return min(RETRY_DELAY_BASE * (2 ** (self.attempt - 1)), 10.0)


def safe_execute(max_attempts: int = MAX_RETRY_ATTEMPTS,
                severity: ErrorSeverity = ErrorSeverity.MEDIUM):
    """Decorator for safe execution with retry logic."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            context = ErrorContext(
                component=func.__module__ or "unknown",
                operation=func.__name__,
                max_attempts=max_attempts,
                severity=severity
            )

            logger = logging.getLogger(f"{context.component}.{context.operation}")

            while context.should_retry():
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    context.last_error = e
                    context.error_count += 1
                    context.attempt += 1

                    if context.should_retry():
                        delay = context.get_retry_delay()
                        logger.warning(
                            f"Attempt {context.attempt-1}/{context.max_attempts} failed: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"Operation failed after {context.attempt-1} attempts: {e}",
                            exc_info=True
                        )
                        if severity == ErrorSeverity.CRITICAL:
                            raise
                        return None

            return None
        return wrapper
    return decorator


class CircuitBreaker:
    """Circuit breaker pattern for preventing cascade failures."""

    def __init__(self, failure_threshold: int = CIRCUIT_BREAKER_THRESHOLD,
                 timeout: float = CIRCUIT_BREAKER_TIMEOUT):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = ComponentState.HEALTHY
        self._lock = threading.RLock()

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self._lock:
                if self.state == ComponentState.FAILED:
                    if (time.time() - self.last_failure_time) > self.timeout:
                        self.state = ComponentState.DEGRADED
                        self.failure_count = 0
                    else:
                        raise Exception(f"Circuit breaker open for {func.__name__}")

                try:
                    result = func(*args, **kwargs)
                    if self.state == ComponentState.DEGRADED:
                        self.state = ComponentState.HEALTHY
                        self.failure_count = 0
                    return result
                except Exception as e:
                    self.failure_count += 1
                    self.last_failure_time = time.time()

                    if self.failure_count >= self.failure_threshold:
                        self.state = ComponentState.FAILED
                    elif self.failure_count >= self.failure_threshold // 2:
                        self.state = ComponentState.DEGRADED

                    raise
        return wrapper


@contextmanager
def safe_file_operation(filepath: Path, operation: str = "operation"):
    """Context manager for safe file operations with cleanup."""
    temp_file = None
    backup_file = None
    logger = logging.getLogger('SafeFileOp')

    try:
        # Create backup if file exists and we're writing
        if filepath.exists() and operation in ["write", "update"]:
            backup_file = filepath.with_suffix(f"{filepath.suffix}.backup")
            try:
                shutil.copy2(filepath, backup_file)
                logger.debug(f"Created backup: {backup_file}")
            except Exception as e:
                logger.warning(f"Could not create backup: {e}")

        # Create temp file for atomic operations
        if operation in ["write", "update"]:
            temp_file = filepath.with_suffix(f"{filepath.suffix}.tmp")

        yield temp_file or filepath

        # Atomic move if temp file was used
        if temp_file and temp_file.exists():
            temp_file.replace(filepath)
            logger.debug(f"Atomic {operation} completed: {filepath}")

        # Clean up backup on success
        if backup_file and backup_file.exists():
            backup_file.unlink()

    except Exception as e:
        logger.error(f"File {operation} failed for {filepath}: {e}")

        # Restore from backup if available
        if backup_file and backup_file.exists() and operation in ["write", "update"]:
            try:
                backup_file.replace(filepath)
                logger.info(f"Restored from backup: {filepath}")
            except Exception as restore_error:
                logger.error(f"Could not restore from backup: {restore_error}")

        # Clean up temp file
        if temp_file and temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass

        raise
    finally:
        # Final cleanup
        if temp_file and temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass


class SafeInput:
    """Comprehensive input validation and sanitization."""

    @staticmethod
    def validate_integer(value: Any, min_val: int = None, max_val: int = None,
                        default: int = 0) -> int:
        """Safely validate and convert to integer."""
        try:
            if isinstance(value, bool):
                return int(value)

            if isinstance(value, str):
                value = value.strip()
                if not value:
                    return default

                # Handle hex strings
                if value.startswith(('0x', '0X')):
                    result = int(value, 16)
                else:
                    result = int(float(value))  # Handle float strings
            else:
                result = int(value)

            # Apply bounds
            if min_val is not None:
                result = max(min_val, result)
            if max_val is not None:
                result = min(max_val, result)

            return result

        except (ValueError, TypeError, OverflowError) as e:
            logging.getLogger('SafeInput').warning(
                f"Invalid integer input '{value}': {e}. Using default: {default}"
            )
            return default

    @staticmethod
    def validate_float(value: Any, min_val: float = None, max_val: float = None,
                      default: float = 0.0) -> float:
        """Safely validate and convert to float."""
        try:
            if isinstance(value, bool):
                return float(value)

            if isinstance(value, str):
                value = value.strip()
                if not value:
                    return default

            result = float(value)

            # Check for NaN and infinity
            if not math.isfinite(result):
                return default

            # Apply bounds
            if min_val is not None:
                result = max(min_val, result)
            if max_val is not None:
                result = min(max_val, result)

            return result

        except (ValueError, TypeError, OverflowError) as e:
            logging.getLogger('SafeInput').warning(
                f"Invalid float input '{value}': {e}. Using default: {default}"
            )
            return default

    @staticmethod
    def validate_string(value: Any, max_length: int = 1000,
                       allowed_chars: str = None, default: str = "") -> str:
        """Safely validate and sanitize string input."""
        try:
            if value is None:
                return default

            result = str(value).strip()

            # Limit length
            if len(result) > max_length:
                result = result[:max_length]
                logging.getLogger('SafeInput').warning(
                    f"String truncated to {max_length} characters"
                )

            # Filter allowed characters
            if allowed_chars:
                result = ''.join(c for c in result if c in allowed_chars)

            return result

        except Exception as e:
            logging.getLogger('SafeInput').warning(
                f"Invalid string input: {e}. Using default: '{default}'"
            )
            return default

    @staticmethod
    def validate_color_hex(value: Any, default: str = "#000000") -> str:
        """Safely validate hex color string."""
        try:
            if value is None:
                return default

            color_str = str(value).strip().lower()

            # Add # if missing
            if not color_str.startswith('#'):
                color_str = '#' + color_str

            # --- FIX STARTS HERE ---
            # Correctly validate and convert 3-digit hex codes
            if re.match(r'^#[0-9a-f]{3}$', color_str):
                color_str = '#' + ''.join(c * 2 for c in color_str[1:])
            # Correctly validate 6-digit hex codes
            elif not re.match(r'^#[0-9a-f]{6}$', color_str):
                # If neither format matches, return the default.
                logging.getLogger('SafeInput').warning(
                    f"Invalid color format for '{value}'. Using default: {default}"
                )
                return default
            # --- FIX ENDS HERE ---

            return color_str

        except Exception as e:
            logging.getLogger('SafeInput').warning(
                f"Invalid color input '{value}': {e}. Using default: {default}"
            )
            return default

    @staticmethod
    def validate_path(value: Any, must_exist: bool = False,
                     must_be_dir: bool = False, default: Optional[Path] = None) -> Optional[Path]:
        """Safely validate file system path."""
        try:
            if value is None:
                return default

            path = Path(str(value)).resolve()

            # Security check - prevent path traversal
            try:
                path.relative_to(Path.cwd().root)  # Must be under root
            except ValueError:
                logging.getLogger('SafeInput').warning(
                    f"Path outside allowed area: {path}"
                )
                return default

            if must_exist and not path.exists():
                return default

            if must_be_dir and path.exists() and not path.is_dir():
                return default

            return path

        except Exception as e:
            logging.getLogger('SafeInput').warning(
                f"Invalid path input '{value}': {e}. Using default: {default}"
            )
            return default


@dataclass
class RGBColor:
    """Represents an RGB color with comprehensive validation and error handling."""
    r: int
    g: int
    b: int

    def __post_init__(self):
        """Validate and clamp RGB values with error handling."""
        try:
            self.r = SafeInput.validate_integer(self.r, 0, 255, 0)
            self.g = SafeInput.validate_integer(self.g, 0, 255, 0)
            self.b = SafeInput.validate_integer(self.b, 0, 255, 0)
        except Exception as e:
            logging.getLogger('RGBColor').error(f"Color validation error: {e}")
            self.r = self.g = self.b = 0

    def to_hex(self) -> str:
        """Convert to hex color string with error handling."""
        try:
            return f"#{self.r:02x}{self.g:02x}{self.b:02x}"
        except Exception as e:
            logging.getLogger('RGBColor').error(f"Hex conversion error: {e}")
            return "#000000"

    @classmethod
    def from_hex(cls, hex_str: str) -> 'RGBColor':
        """Create RGBColor from hex string with comprehensive error handling."""
        try:
            validated_hex = SafeInput.validate_color_hex(hex_str, "#000000")
            hex_clean = validated_hex.lstrip('#')

            if len(hex_clean) == 6:
                return cls(
                    int(hex_clean[0:2], 16),
                    int(hex_clean[2:4], 16),
                    int(hex_clean[4:6], 16)
                )
        except Exception as e:
            logging.getLogger('RGBColor').error(f"Hex parsing error for '{hex_str}': {e}")

        return cls(0, 0, 0)

    @classmethod
    def from_dict(cls, color_dict: Dict[str, Any]) -> 'RGBColor':
        """Create RGBColor from dictionary with error handling."""
        try:
            if not isinstance(color_dict, dict):
                raise ValueError("Input is not a dictionary")

            return cls(
                SafeInput.validate_integer(color_dict.get('r', 0), 0, 255, 0),
                SafeInput.validate_integer(color_dict.get('g', 0), 0, 255, 0),
                SafeInput.validate_integer(color_dict.get('b', 0), 0, 255, 0)
            )
        except Exception as e:
            logging.getLogger('RGBColor').error(f"Dict parsing error: {e}")
            return cls(0, 0, 0)

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary with error handling."""
        try:
            return {"r": int(self.r), "g": int(self.g), "b": int(self.b)}
        except Exception as e:
            logging.getLogger('RGBColor').error(f"Dict conversion error: {e}")
            return {"r": 0, "g": 0, "b": 0}

    def is_valid(self) -> bool:
        """Check if color values are valid."""
        return all(0 <= val <= 255 for val in [self.r, self.g, self.b])


@dataclass
class AppSettings:
    """Application settings with comprehensive validation and error recovery."""
    brightness: int = 100
    current_color: RGBColor = field(default_factory=lambda: RGBColor(0, 100, 255))
    zone_colors: List[RGBColor] = field(default_factory=list)
    effect_name: str = "Static (All Zones)"
    effect_speed: int = 5
    rainbow_speed: int = 5
    effect_color: str = "#0064ff"
    gradient_start_color: str = "#ff0000"
    gradient_end_color: str = "#0000ff"
    last_control_method: str = "ectool"
    restore_on_startup: bool = True
    auto_apply_last_setting: bool = True

    def __post_init__(self):
        """Initialize and validate all settings with error handling."""
        try:
            # Validate basic types with fallbacks
            self.brightness = SafeInput.validate_integer(self.brightness, 0, 100, 100)
            self.effect_speed = SafeInput.validate_integer(self.effect_speed, 1, 10, 5)
            self.rainbow_speed = SafeInput.validate_integer(self.rainbow_speed, 1, 10, 5)

            # Validate strings
            self.effect_name = SafeInput.validate_string(self.effect_name, 100, default="Static (All Zones)")
            self.last_control_method = SafeInput.validate_string(self.last_control_method, 50, default="ectool")

            # Validate colors
            self.effect_color = SafeInput.validate_color_hex(self.effect_color, "#0064ff")
            self.gradient_start_color = SafeInput.validate_color_hex(self.gradient_start_color, "#ff0000")
            self.gradient_end_color = SafeInput.validate_color_hex(self.gradient_end_color, "#0000ff")

            # Validate boolean values
            self.restore_on_startup = bool(self.restore_on_startup)
            self.auto_apply_last_setting = bool(self.auto_apply_last_setting)

            # Ensure current_color is valid
            if not isinstance(self.current_color, RGBColor):
                self.current_color = RGBColor(0, 100, 255)

            # Initialize default zone colors if empty or invalid
            if not self.zone_colors or len(self.zone_colors) < NUM_ZONES:
                self.zone_colors = [
                    RGBColor(255, 0, 0),   # Red
                    RGBColor(255, 255, 0), # Yellow
                    RGBColor(0, 255, 0),   # Green
                    RGBColor(0, 0, 255)    # Blue
                ]

            # Ensure we have exactly NUM_ZONES colors
            while len(self.zone_colors) < NUM_ZONES:
                self.zone_colors.append(RGBColor(0, 0, 0))

            self.zone_colors = self.zone_colors[:NUM_ZONES]

        except Exception as e:
            logging.getLogger('AppSettings').error(f"Settings validation error: {e}")
            # If validation fails completely, use factory defaults
            self._reset_to_defaults()

    def _reset_to_defaults(self):
        """Reset all settings to safe defaults."""
        self.brightness = 100
        self.current_color = RGBColor(0, 100, 255)
        self.zone_colors = [RGBColor(255, 0, 0), RGBColor(255, 255, 0),
                           RGBColor(0, 255, 0), RGBColor(0, 0, 255)]
        self.effect_name = "Static (All Zones)"
        self.effect_speed = 5
        self.rainbow_speed = 5
        self.effect_color = "#0064ff"
        self.gradient_start_color = "#ff0000"
        self.gradient_end_color = "#0000ff"
        self.last_control_method = "ectool"
        self.restore_on_startup = True
        self.auto_apply_last_setting = True

    def validate_and_fix(self) -> bool:
        """Validate all settings and fix any issues found."""
        try:
            original_data = self.__dict__.copy()
            self.__post_init__()
            return self.__dict__ == original_data
        except Exception as e:
            logging.getLogger('AppSettings').error(f"Validation/fix error: {e}")
            self._reset_to_defaults()
            return False


class SecurityError(Exception):
    """Raised when a security violation is detected."""
    pass


class HardwareError(Exception):
    """Raised when hardware operations fail."""
    pass


class ConfigurationError(Exception):
    """Raised when configuration is invalid or corrupted."""
    pass


@safe_execute(max_attempts=3, severity=ErrorSeverity.HIGH)
def get_user_config_directory() -> Path:
    """Get the user's configuration directory safely with multiple fallbacks."""
    logger = logging.getLogger('ConfigDir')

    # Strategy 1: Try to get actual user's home via SUDO_USER
    try:
        sudo_user = os.getenv("SUDO_USER")
        if sudo_user:
            try:
                result = subprocess.run(
                    ["getent", "passwd", sudo_user],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=True
                )
                home_dir = result.stdout.strip().split(':')[5]
                if home_dir and Path(home_dir).is_dir():
                    config_dir = Path(home_dir) / ".config" / "rgb_controller"
                    logger.info(f"Using SUDO_USER config directory: {config_dir}")
                    return config_dir
            except (subprocess.SubprocessError, IndexError, OSError) as e:
                logger.debug(f"SUDO_USER method failed: {e}")
    except Exception as e:
        logger.debug(f"SUDO_USER environment check failed: {e}")

    # Strategy 2: Use current user's home
    try:
        home_dir = Path.home()
        if home_dir.is_dir() and home_dir.name != "root":
            config_dir = home_dir / ".config" / "rgb_controller"
            logger.info(f"Using current user config directory: {config_dir}")
            return config_dir
    except Exception as e:
        logger.debug(f"Current user home failed: {e}")

    # Strategy 3: Use XDG_CONFIG_HOME if set
    try:
        xdg_config = os.getenv("XDG_CONFIG_HOME")
        if xdg_config:
            config_dir = Path(xdg_config) / "rgb_controller"
            logger.info(f"Using XDG_CONFIG_HOME directory: {config_dir}")
            return config_dir
    except Exception as e:
        logger.debug(f"XDG_CONFIG_HOME failed: {e}")

    # Strategy 4: Check common user directories
    try:
        for user_dir in Path("/home").iterdir():
            if user_dir.is_dir() and user_dir.owner() != "root":
                config_dir = user_dir / ".config" / "rgb_controller"
                logger.warning(f"Guessing user config directory: {config_dir}")
                return config_dir
    except Exception as e:
        logger.debug(f"User directory search failed: {e}")

    # Strategy 5: Use system-wide fallback
    try:
        fallback_dir = Path("/tmp/rgb_controller_config")
        logger.warning(f"Using fallback config directory: {fallback_dir}")
        return fallback_dir
    except Exception as e:
        logger.error(f"Even fallback directory creation failed: {e}")
        raise ConfigurationError("Could not determine any suitable config directory")


@safe_execute(max_attempts=2, severity=ErrorSeverity.CRITICAL)
def setup_logging(config_dir: Path) -> logging.Logger:
    """Set up comprehensive logging system with error recovery."""
    # Ensure config directory exists with multiple attempts
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            config_dir.mkdir(parents=True, exist_ok=True)
            break
        except OSError as e:
            if attempt == max_attempts - 1:
                print(f"FATAL: Could not create config directory at {config_dir}: {e}", file=sys.stderr)
                print("Trying fallback location...", file=sys.stderr)

                # Try fallback directory
                try:
                    fallback_dir = Path(tempfile.gettempdir()) / "rgb_controller_logs"
                    fallback_dir.mkdir(parents=True, exist_ok=True)
                    config_dir = fallback_dir
                    print(f"Using fallback log directory: {config_dir}", file=sys.stderr)
                    break
                except Exception as fallback_error:
                    print(f"FATAL: Could not create fallback directory: {fallback_error}", file=sys.stderr)
                    sys.exit(1)
            else:
                time.sleep(0.5)  # Brief delay before retry

    # Clear existing handlers safely
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    for handler in root_logger.handlers[:]:
        try:
            handler.flush()
            handler.close()
            root_logger.removeHandler(handler)
        except Exception as e:
            print(f"Warning: Could not properly close log handler: {e}", file=sys.stderr)

    # Setup formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )

    # File handlers with comprehensive error handling
    log_files = [
        ("rgb_control.log", logging.INFO, 5),
        ("rgb_errors.log", logging.ERROR, 10),
        ("rgb_debug.log", logging.DEBUG, 20)
    ]

    successful_handlers = 0
    for filename, level, max_mb in log_files:
        try:
            # Check available disk space
            try:
                stat = shutil.disk_usage(config_dir)
                available_mb = stat.free / (1024 * 1024)
                if available_mb < max_mb * 2:  # Ensure 2x the log size is available
                    print(f"Warning: Low disk space for {filename}. Available: {available_mb:.1f}MB", file=sys.stderr)
            except Exception:
                pass  # Continue anyway

            handler = logging.handlers.RotatingFileHandler(
                config_dir / filename,
                maxBytes=max_mb * 1024 * 1024,
                backupCount=3,
                encoding='utf-8'
            )
            handler.setLevel(level)
            handler.setFormatter(detailed_formatter)

            # Test write to ensure handler works
            test_record = logging.LogRecord(
                name="test", level=level, pathname="", lineno=0,
                msg="Log handler test", args=(), exc_info=None
            )
            handler.emit(test_record)
            handler.flush()

            root_logger.addHandler(handler)
            successful_handlers += 1

        except Exception as e:
            print(f"Error setting up log file {filename}: {e}", file=sys.stderr)

    # Ensure at least console logging works
    try:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        successful_handlers += 1
    except Exception as e:
        print(f"Error setting up console logging: {e}", file=sys.stderr)

    if successful_handlers == 0:
        print("FATAL: Could not set up any logging handlers", file=sys.stderr)
        sys.exit(1)

    logger = logging.getLogger('RGBController')

    # Log setup completion
    try:
        log_system_info(logger)
        logger.info(f"Logging initialized with {successful_handlers} handlers")
    except Exception as e:
        print(f"Error in initial logging: {e}", file=sys.stderr)

    return logger


class SafeSubprocess:
    """Safe subprocess execution with comprehensive error handling and security."""

    @staticmethod
    @safe_execute(max_attempts=2, severity=ErrorSeverity.MEDIUM)
    def run_command(
        cmd: List[str],
        timeout: float = 5.0,
        check: bool = False,
        input_data: Optional[bytes] = None
    ) -> subprocess.CompletedProcess:
        """Run a command safely with comprehensive validation and error handling."""
        logger = logging.getLogger('SafeSubprocess')

        # Input validation with detailed error reporting
        try:
            if not cmd or not isinstance(cmd, (list, tuple)):
                raise SecurityError("Command must be a non-empty list or tuple")

            if not all(isinstance(arg, (str, bytes)) for arg in cmd):
                raise SecurityError("All command arguments must be strings or bytes")

            # Convert bytes to strings if necessary
            cmd = [str(arg) if isinstance(arg, bytes) else arg for arg in cmd]

            if not all(arg.strip() for arg in cmd):
                raise SecurityError("Command arguments cannot be empty or whitespace-only")

            # Security validation
            dangerous_patterns = [
                ';', '&&', '||', '|', '>', '<', '`', '$',
                '$(', '${', '`', '\n', '\r', '\0'
            ]

            for i, arg in enumerate(cmd):
                if any(pattern in arg for pattern in dangerous_patterns):
                    raise SecurityError(f"Potentially dangerous pattern in argument {i}: {arg}")

                # Check for suspicious character sequences
                if '..' in arg and ('/' in arg or '\\' in arg):
                    raise SecurityError(f"Potential path traversal in argument {i}: {arg}")

            # Validate timeout
            timeout = SafeInput.validate_float(timeout, 0.1, 300.0, 5.0)

            logger.debug(f"Executing command: {' '.join(cmd[:3])}{'...' if len(cmd) > 3 else ''}")

            # Execute with comprehensive error handling
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=check,
                    input=input_data.decode('utf-8') if isinstance(input_data, bytes) else input_data
                )

                # Log execution results
                if result.returncode != 0:
                    logger.warning(f"Command failed with return code {result.returncode}")
                    if result.stderr:
                        logger.debug(f"Error output: {result.stderr[:500]}")

                return result

            except subprocess.TimeoutExpired as e:
                logger.error(f"Command timeout after {timeout}s: {' '.join(cmd)}")
                raise HardwareError(f"Command timeout: {' '.join(cmd)}") from e

            except subprocess.CalledProcessError as e:
                logger.error(f"Command failed: {' '.join(cmd)} (return code: {e.returncode})")
                raise HardwareError(f"Command failed: {' '.join(cmd)}") from e

            except OSError as e:
                logger.error(f"OS error executing command: {e}")
                raise HardwareError(f"OS error: {e}") from e

        except SecurityError:
            raise  # Re-raise security errors
        except Exception as e:
            logger.error(f"Unexpected error in command execution: {e}", exc_info=True)
            raise HardwareError(f"Unexpected error: {e}") from e


class SettingsManager:
    """Manages application settings with bulletproof error handling and recovery."""

    def __init__(self, config_file: Path):
        self.config_file = SafeInput.validate_path(config_file, default=Path("settings.json"))
        self.logger = logging.getLogger('SettingsManager')
        self._lock = threading.RLock()
        self.settings = AppSettings()
        self._corruption_count = 0
        self._max_corruption_retries = 3

        # Initialize settings with comprehensive error handling
        self._initialize_settings()

    @safe_execute(max_attempts=3, severity=ErrorSeverity.HIGH)
    def _initialize_settings(self) -> None:
        """Initialize settings with multiple fallback strategies."""
        try:
            with self._lock:
                self.load_settings()
        except Exception as e:
            self.logger.error(f"Settings initialization failed: {e}")
            self._handle_settings_corruption()

    def _handle_settings_corruption(self) -> None:
        """Handle corrupted settings with recovery strategies."""
        self._corruption_count += 1
        self.logger.warning(f"Settings corruption detected (attempt {self._corruption_count})")

        if self._corruption_count <= self._max_corruption_retries:
            # Try backup recovery
            if self._restore_from_backup():
                return

            # Reset to defaults and save
            self.logger.info("Resetting settings to defaults due to corruption")
            self.settings = AppSettings()
            self.save_settings()
        else:
            self.logger.error("Maximum corruption recovery attempts exceeded")
            raise ConfigurationError("Settings permanently corrupted")

    def _restore_from_backup(self) -> bool:
        """Attempt to restore settings from backup file."""
        backup_file = self.config_file.with_suffix('.backup')
        try:
            if backup_file.exists():
                self.logger.info(f"Attempting to restore from backup: {backup_file}")
                backup_file.replace(self.config_file)
                self.load_settings()
                return True
        except Exception as e:
            self.logger.error(f"Backup restoration failed: {e}")
        return False

    @safe_execute(max_attempts=3, severity=ErrorSeverity.MEDIUM)
    def load_settings(self) -> None:
        """Load settings from file with comprehensive error handling."""
        with self._lock:
            try:
                if not self.config_file.exists():
                    self.logger.info("No settings file found, using defaults")
                    self.settings = AppSettings()
                    self.save_settings()
                    return

                # Validate file before loading
                if not self._validate_settings_file():
                    raise ConfigurationError("Settings file validation failed")

                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if not isinstance(data, dict):
                    raise ValueError("Settings file does not contain a valid dictionary")

                # Parse and validate loaded data
                settings_dict = self._parse_settings_data(data)
                self.settings = AppSettings(**settings_dict)

                # Validate the loaded settings
                if not self.settings.validate_and_fix():
                    self.logger.warning("Settings required fixes during loading")

                self.logger.info(f"Settings loaded successfully from {self.config_file}")

            except json.JSONDecodeError as e:
                self.logger.error(f"JSON decode error in settings file: {e}")
                raise ConfigurationError(f"Invalid JSON in settings file: {e}")
            except Exception as e:
                self.logger.error(f"Error loading settings: {e}")
                raise ConfigurationError(f"Settings loading failed: {e}")

    def _validate_settings_file(self) -> bool:
        """Validate settings file before attempting to load."""
        try:
            # Check file size (should be reasonable for JSON settings)
            file_size = self.config_file.stat().st_size
            if file_size > 1024 * 1024:  # 1MB limit
                self.logger.error(f"Settings file too large: {file_size} bytes")
                return False

            if file_size == 0:
                self.logger.warning("Settings file is empty")
                return False

            # Basic JSON syntax check
            with open(self.config_file, 'r', encoding='utf-8') as f:
                json.load(f)

            return True

        except Exception as e:
            self.logger.error(f"Settings file validation failed: {e}")
            return False

    def _parse_settings_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate settings data with comprehensive error handling."""
        settings_dict = {}

        try:
            # Parse integer fields with validation
            for field, default in [('brightness', 100), ('effect_speed', 5), ('rainbow_speed', 5)]:
                if field in data:
                    settings_dict[field] = SafeInput.validate_integer(
                        data[field],
                        0 if field == 'brightness' else 1,
                        100 if field == 'brightness' else 10,
                        default
                    )

            # Parse string fields with validation
            string_fields = {
                'effect_name': 'Static (All Zones)',
                'last_control_method': 'ectool',
                'effect_color': '#0064ff',
                'gradient_start_color': '#ff0000',
                'gradient_end_color': '#0000ff'
            }

            for field, default in string_fields.items():
                if field in data:
                    if field.endswith('_color'):
                        settings_dict[field] = SafeInput.validate_color_hex(data[field], default)
                    else:
                        settings_dict[field] = SafeInput.validate_string(data[field], 100, default=default)

            # Parse boolean fields
            for field, default in [('restore_on_startup', True), ('auto_apply_last_setting', True)]:
                if field in data:
                    settings_dict[field] = bool(data[field])

            # Parse color objects
            if 'current_color' in data:
                try:
                    settings_dict['current_color'] = RGBColor.from_dict(data['current_color'])
                except Exception as e:
                    self.logger.warning(f"Invalid current_color in settings: {e}")

            # Parse zone colors array
            if 'zone_colors' in data and isinstance(data['zone_colors'], list):
                zone_colors = []
                for i, color_data in enumerate(data['zone_colors'][:NUM_ZONES]):
                    try:
                        zone_colors.append(RGBColor.from_dict(color_data))
                    except Exception as e:
                        self.logger.warning(f"Invalid zone color {i}: {e}")
                        zone_colors.append(RGBColor(0, 0, 0))

                if zone_colors:
                    settings_dict['zone_colors'] = zone_colors

            return settings_dict

        except Exception as e:
            self.logger.error(f"Error parsing settings data: {e}")
            return {}

    @safe_execute(max_attempts=3, severity=ErrorSeverity.HIGH)
    def save_settings(self) -> None:
        """Save settings to file with atomic write and comprehensive error handling."""
        with self._lock:
            try:
                # Ensure parent directory exists
                self.config_file.parent.mkdir(parents=True, exist_ok=True)

                # Check available disk space
                try:
                    stat = shutil.disk_usage(self.config_file.parent)
                    available_mb = stat.free / (1024 * 1024)
                    if available_mb < 1:  # Require at least 1MB free
                        raise OSError(f"Insufficient disk space: {available_mb:.1f}MB available")
                except Exception as space_error:
                    self.logger.warning(f"Could not check disk space: {space_error}")

                # Prepare data for serialization
                data = self._prepare_settings_for_serialization()

                # Validate data before writing
                json_str = json.dumps(data, indent=2)
                if len(json_str) > 100 * 1024:  # 100KB limit
                    raise ValueError("Settings data too large to save")

                # Atomic write with backup
                with safe_file_operation(self.config_file, "write") as temp_file:
                    with open(temp_file, 'w', encoding='utf-8') as f:
                        f.write(json_str)
                        f.flush()
                        os.fsync(f.fileno())  # Force write to disk

                self.logger.info(f"Settings saved successfully to {self.config_file}")
                self._corruption_count = 0  # Reset corruption counter on successful save

            except OSError as e:
                self.logger.error(f"OS error saving settings: {e}")
                raise ConfigurationError(f"File system error: {e}")
            except Exception as e:
                self.logger.error(f"Error saving settings: {e}")
                raise ConfigurationError(f"Settings save failed: {e}")

    def _prepare_settings_for_serialization(self) -> Dict[str, Any]:
        """Prepare settings data for JSON serialization with validation."""
        try:
            data = {
                'brightness': int(self.settings.brightness),
                'current_color': self.settings.current_color.to_dict(),
                'zone_colors': [color.to_dict() for color in self.settings.zone_colors],
                'effect_name': str(self.settings.effect_name),
                'effect_speed': int(self.settings.effect_speed),
                'rainbow_speed': int(self.settings.rainbow_speed),
                'effect_color': str(self.settings.effect_color),
                'gradient_start_color': str(self.settings.gradient_start_color),
                'gradient_end_color': str(self.settings.gradient_end_color),
                'last_control_method': str(self.settings.last_control_method),
                'restore_on_startup': bool(self.settings.restore_on_startup),
                'auto_apply_last_setting': bool(self.settings.auto_apply_last_setting)
            }

            # Validate serialized data
            for key, value in data.items():
                if value is None:
                    self.logger.warning(f"Null value found for setting: {key}")
                    # Set appropriate defaults
                    if key == 'brightness':
                        data[key] = 100
                    elif key in ['effect_speed', 'rainbow_speed']:
                        data[key] = 5
                    elif key.endswith('_color'):
                        data[key] = '#000000'
                    elif key in ['restore_on_startup', 'auto_apply_last_setting']:
                        data[key] = True
                    else:
                        data[key] = ''

            return data

        except Exception as e:
            self.logger.error(f"Error preparing settings for serialization: {e}")
            raise ConfigurationError(f"Settings serialization failed: {e}")

    @safe_execute(max_attempts=1, severity=ErrorSeverity.LOW)
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value safely with error handling."""
        try:
            with self._lock:
                if hasattr(self.settings, key):
                    value = getattr(self.settings, key)
                    return value if value is not None else default
                else:
                    self.logger.warning(f"Unknown setting key requested: {key}")
                    return default
        except Exception as e:
            self.logger.error(f"Error getting setting '{key}': {e}")
            return default

    @safe_execute(max_attempts=2, severity=ErrorSeverity.MEDIUM)
    def set(self, key: str, value: Any) -> None:
        """Set a setting value safely with validation and error handling."""
        try:
            with self._lock:
                if hasattr(self.settings, key):
                    # Validate value based on key type
                    validated_value = self._validate_setting_value(key, value)
                    setattr(self.settings, key, validated_value)
                    self.save_settings()
                else:
                    self.logger.warning(f"Attempted to set unknown setting: {key}")
        except Exception as e:
            self.logger.error(f"Error setting '{key}' to '{value}': {e}")
            raise ConfigurationError(f"Setting update failed: {e}")

    def _validate_setting_value(self, key: str, value: Any) -> Any:
        """Validate a setting value based on its key."""
        try:
            if key == 'brightness':
                return SafeInput.validate_integer(value, 0, 100, 100)
            elif key in ['effect_speed', 'rainbow_speed']:
                return SafeInput.validate_integer(value, 1, 10, 5)
            elif key.endswith('_color') and isinstance(value, str):
                return SafeInput.validate_color_hex(value, '#000000')
            elif key in ['effect_name', 'last_control_method']:
                return SafeInput.validate_string(value, 100, default='')
            elif key in ['restore_on_startup', 'auto_apply_last_setting']:
                return bool(value)
            elif key == 'current_color' and not isinstance(value, RGBColor):
                if isinstance(value, dict):
                    return RGBColor.from_dict(value)
                else:
                    return RGBColor(0, 0, 0)
            elif key == 'zone_colors' and isinstance(value, list):
                validated_colors = []
                for color in value[:NUM_ZONES]:
                    if isinstance(color, RGBColor):
                        validated_colors.append(color)
                    elif isinstance(color, dict):
                        validated_colors.append(RGBColor.from_dict(color))
                    else:
                        validated_colors.append(RGBColor(0, 0, 0))
                return validated_colors
            else:
                return value
        except Exception as e:
            self.logger.error(f"Value validation failed for {key}: {e}")
            # Return safe default based on key
            if key == 'brightness':
                return 100
            elif key in ['effect_speed', 'rainbow_speed']:
                return 5
            elif key.endswith('_color'):
                return '#000000'
            elif key == 'current_color':
                return RGBColor(0, 0, 0)
            elif key == 'zone_colors':
                return [RGBColor(0, 0, 0)] * NUM_ZONES
            else:
                return None

    @safe_execute(max_attempts=2, severity=ErrorSeverity.MEDIUM)
    def update(self, updates: Dict[str, Any]) -> None:
        """Update multiple settings atomically with error handling."""
        if not isinstance(updates, dict):
            self.logger.error("Updates must be provided as a dictionary")
            return

        try:
            with self._lock:
                # Validate all updates first
                validated_updates = {}
                for key, value in updates.items():
                    if hasattr(self.settings, key):
                        validated_updates[key] = self._validate_setting_value(key, value)
                    else:
                        self.logger.warning(f"Ignoring unknown setting in batch update: {key}")

                # Apply all validated updates
                for key, value in validated_updates.items():
                    setattr(self.settings, key, value)

                # Save once for all updates
                self.save_settings()

                self.logger.info(f"Successfully updated {len(validated_updates)} settings")

        except Exception as e:
            self.logger.error(f"Error in batch settings update: {e}")
            raise ConfigurationError(f"Batch update failed: {e}")


class HardwareController:
    """Controls RGB hardware with comprehensive error handling and fault tolerance."""

    def __init__(self):
        self.logger = logging.getLogger('HardwareController')
        self._lock = threading.RLock()

        # Hardware availability flags
        self.ectool_available = False
        self.ec_direct_available = False

        # Circuit breakers for different operations
        self._ectool_breaker = CircuitBreaker(failure_threshold=5, timeout=30)
        self._ec_direct_breaker = CircuitBreaker(failure_threshold=3, timeout=60)

        # Capability flags with error tracking
        self.capabilities = {
            "ectool_demo": None,
            "ectool_clear": None,
            "ectool_zone": None,
            "ec_direct": None
        }
        self._capability_errors = {cap: 0 for cap in self.capabilities}

        # EC Direct configuration
        self.ec_io_path = "/sys/kernel/debug/ec/ec0/io"

        # Detection state
        self.hardware_ready = False
        self.detection_complete = threading.Event()
        self._detection_errors = 0
        self._max_detection_errors = 5

        # Command history for debugging
        self._command_history = []
        self._max_history = 100

        # Start hardware detection with error handling
        self._start_detection()

    @safe_execute(max_attempts=1, severity=ErrorSeverity.LOW)
    def _start_detection(self) -> None:
        """Start hardware detection in a separate thread with error handling."""
        try:
            detection_thread = threading.Thread(
                target=self._detect_hardware_with_recovery,
                daemon=True,
                name="HardwareDetection"
            )
            detection_thread.start()
        except Exception as e:
            self.logger.error(f"Failed to start hardware detection thread: {e}")
            # Fallback: run detection in current thread
            self._detect_hardware_with_recovery()

    def _detect_hardware_with_recovery(self) -> None:
        """Detect hardware with comprehensive error recovery."""
        while self._detection_errors < self._max_detection_errors:
            try:
                self._detect_hardware()
                break  # Success
            except Exception as e:
                self._detection_errors += 1
                self.logger.error(
                    f"Hardware detection attempt {self._detection_errors} failed: {e}"
                )

                if self._detection_errors < self._max_detection_errors:
                    # Exponential backoff
                    delay = min(2 ** (self._detection_errors - 1), 30)
                    self.logger.info(f"Retrying hardware detection in {delay}s...")
                    time.sleep(delay)
                else:
                    self.logger.critical("Hardware detection failed permanently")

        # Always mark as complete, even if failed
        self.hardware_ready = True
        self.detection_complete.set()

    @safe_execute(max_attempts=3, severity=ErrorSeverity.HIGH)
    def _detect_hardware(self) -> None:
        """Detect available hardware control methods with error handling."""
        self.logger.info("Starting hardware detection...")

        # Detect ectool with comprehensive error handling
        try:
            self._detect_ectool()
        except Exception as e:
            self.logger.error(f"ectool detection failed: {e}")

        # Detect EC direct access with error handling
        try:
            self._detect_ec_direct()
        except Exception as e:
            self.logger.error(f"EC direct detection failed: {e}")

        # Log detection results
        self.logger.info(
            f"Hardware detection complete - "
            f"ectool: {self.ectool_available}, EC direct: {self.ec_direct_available}"
        )

        # Warn if no methods available
        if not self.ectool_available and not self.ec_direct_available:
            self.logger.warning("No hardware control methods available!")

    @safe_execute(max_attempts=2, severity=ErrorSeverity.MEDIUM)
    def _detect_ectool(self) -> None:
        """Detect ectool availability with comprehensive error handling."""
        try:
            # Check if ectool exists in PATH
            which_result = SafeSubprocess.run_command(["which", "ectool"], timeout=3)
            if which_result.returncode != 0 or not which_result.stdout.strip():
                self.logger.info("ectool not found in PATH")
                return

            ectool_path = which_result.stdout.strip()
            self.logger.debug(f"Found ectool at: {ectool_path}")

            # Test ectool version to ensure it's responsive
            version_result = SafeSubprocess.run_command(["ectool", "version"], timeout=5)
            if version_result.returncode != 0:
                self.logger.warning(f"ectool version command failed: {version_result.stderr}")
                return

            self.ectool_available = True
            version_line = version_result.stdout.splitlines()[0] if version_result.stdout else "Unknown"
            self.logger.info(f"ectool available: {version_line}")

            # Test capabilities with error recovery
            self._test_ectool_capabilities()

        except (subprocess.SubprocessError, OSError) as e:
            self.logger.warning(f"ectool detection system error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error in ectool detection: {e}")

    @safe_execute(max_attempts=1, severity=ErrorSeverity.LOW)
    def _test_ectool_capabilities(self) -> None:
        """Test ectool RGB capabilities with individual error handling."""
        if not self.ectool_available:
            return

        self.logger.info("Testing ectool RGB capabilities...")

        capability_tests = [
            (["rgbkbd", "demo", "0"], "ectool_demo"),
            (["rgbkbd", "clear", "0"], "ectool_clear"),
            (["rgbkbd", "0", "0", "0", "0"], "ectool_zone")
        ]

        for cmd, capability in capability_tests:
            try:
                result = SafeSubprocess.run_command(["ectool"] + cmd, timeout=3)
                success = result.returncode == 0
                self.capabilities[capability] = success
                self.logger.info(f"  {capability}: {'Available' if success else 'Not available'}")

                if not success:
                    self._capability_errors[capability] += 1
                    self.logger.debug(f"  Error: {result.stderr[:100]}")

            except Exception as e:
                self.capabilities[capability] = False
                self._capability_errors[capability] += 1
                self.logger.warning(f"  {capability}: Test failed - {e}")

    @safe_execute(max_attempts=2, severity=ErrorSeverity.MEDIUM)
    def _detect_ec_direct(self) -> None:
        """Detect EC direct access with comprehensive error handling."""
        try:
            # Check if EC interface exists
            if not os.path.exists(self.ec_io_path):
                self.logger.debug(f"EC interface not found: {self.ec_io_path}")
                return

            # Check permissions
            if not os.access(self.ec_io_path, os.R_OK | os.W_OK):
                self.logger.info("EC interface exists but not accessible, attempting setup...")
                if not self._setup_ec_access():
                    return

            # Test EC access with a safe read operation
            try:
                with open(self.ec_io_path, 'rb') as f:
                    f.read(1)  # Read one byte to test access
            except Exception as e:
                self.logger.warning(f"EC interface test read failed: {e}")
                return

            self.ec_direct_available = True
            self.capabilities["ec_direct"] = True
            self.logger.info(f"EC direct access available via {self.ec_io_path}")

        except OSError as e:
            self.logger.warning(f"OS error in EC direct detection: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error in EC direct detection: {e}")

    @safe_execute(max_attempts=2, severity=ErrorSeverity.MEDIUM)
    def _setup_ec_access(self) -> bool:
        """Set up EC direct access with comprehensive error handling."""
        try:
            # Check if ec_sys module is loaded
            try:
                lsmod_result = SafeSubprocess.run_command(["lsmod"], timeout=5)
                if "ec_sys" not in lsmod_result.stdout:
                    self.logger.info("Loading ec_sys module...")

                    # Load module with error handling
                    modprobe_result = SafeSubprocess.run_command(
                        ["sudo", "modprobe", "ec_sys", "write_support=1"],
                        timeout=15
                    )

                    if modprobe_result.returncode != 0:
                        self.logger.error(f"Failed to load ec_sys module: {modprobe_result.stderr}")
                        return False

                    self.logger.info("ec_sys module loaded successfully")

                    # Brief delay for module initialization
                    time.sleep(1)

            except Exception as e:
                self.logger.error(f"Error checking/loading ec_sys module: {e}")
                return False

            # Check if debugfs is mounted
            try:
                if not os.path.ismount("/sys/kernel/debug"):
                    self.logger.info("Mounting debugfs...")

                    mount_result = SafeSubprocess.run_command(
                        ["sudo", "mount", "-t", "debugfs", "none", "/sys/kernel/debug"],
                        timeout=15
                    )

                    if mount_result.returncode != 0:
                        self.logger.error(f"Failed to mount debugfs: {mount_result.stderr}")
                        return False

                    self.logger.info("debugfs mounted successfully")

                    # Brief delay for mount to complete
                    time.sleep(1)

            except Exception as e:
                self.logger.error(f"Error checking/mounting debugfs: {e}")
                return False

            # Verify EC interface is now accessible
            try:
                if os.path.exists(self.ec_io_path) and os.access(self.ec_io_path, os.R_OK | os.W_OK):
                    return True
                else:
                    self.logger.error("EC interface still not accessible after setup")
                    return False
            except Exception as e:
                self.logger.error(f"Error verifying EC access after setup: {e}")
                return False

        except Exception as e:
            self.logger.error(f"Unexpected error in EC access setup: {e}")
            return False

    @safe_execute(max_attempts=1, severity=ErrorSeverity.LOW)
    def wait_for_detection(self, timeout: float = 10.0) -> bool:
        """Wait for hardware detection to complete with error handling."""
        try:
            timeout = SafeInput.validate_float(timeout, 0.1, 300.0, 10.0)
            return self.detection_complete.wait(timeout)
        except Exception as e:
            self.logger.error(f"Error waiting for hardware detection: {e}")
            return False

    @CircuitBreaker(failure_threshold=3, timeout=30)
    @safe_execute(max_attempts=2, severity=ErrorSeverity.MEDIUM)
    def write_ec_register(self, register: int, value: int) -> bool:
        """Write to EC register with comprehensive error handling and validation."""
        if not self.ec_direct_available:
            self.logger.debug("EC direct not available for register write")
            return False

        with self._lock:
            try:
                # Validate inputs with strict bounds
                register = SafeInput.validate_integer(register, 0, 255, 0)
                value = SafeInput.validate_integer(value, 0, 255, 0)

                # Check if EC interface is still accessible
                if not os.access(self.ec_io_path, os.W_OK):
                    self.logger.error("EC interface no longer writable")
                    return False

                # Use dd for atomic single-byte write
                dd_cmd = [
                    "sudo", "dd",
                    f"of={self.ec_io_path}",
                    "bs=1",
                    f"seek={register}",
                    "count=1",
                    "conv=notrunc",
                    "status=none"
                ]

                # Prepare input data
                input_data = bytes([value])

                # Execute write command
                result = subprocess.run(
                    dd_cmd,
                    input=input_data,
                    timeout=3,
                    check=True,
                    capture_output=True
                )

                # Brief delay for EC processing
                time.sleep(0.02)

                # Log successful write for debugging
                self._add_to_command_history(f"EC_WRITE reg={register} val={value}")

                return True

            except subprocess.CalledProcessError as e:
                self.logger.error(f"EC register write command failed: {e}")
                return False
            except subprocess.TimeoutExpired:
                self.logger.error("EC register write timeout")
                return False
            except OSError as e:
                self.logger.error(f"OS error during EC register write: {e}")
                return False
            except Exception as e:
                self.logger.error(f"Unexpected error in EC register write: {e}")
                return False

    def _add_to_command_history(self, command: str) -> None:
        """Add command to history for debugging purposes."""
        try:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self._command_history.append(f"{timestamp}: {command}")

            # Limit history size
            if len(self._command_history) > self._max_history:
                self._command_history = self._command_history[-self._max_history//2:]
        except Exception as e:
            self.logger.debug(f"Error adding to command history: {e}")

    @CircuitBreaker(failure_threshold=5, timeout=30)
    @safe_execute(max_attempts=2, severity=ErrorSeverity.MEDIUM)
    def run_ectool_command(self, args: List[str], timeout: float = 5.0) -> Tuple[bool, str, str]:
        """Run ectool command with comprehensive error handling."""
        if not self.ectool_available:
            return False, "", "ectool not available"

        with self._lock:
            try:
                # Validate arguments
                if not args or not all(isinstance(arg, str) for arg in args):
                    raise ValueError("Invalid ectool command arguments")

                # Prepare command
                cmd = ["ectool"] + args
                timeout = SafeInput.validate_float(timeout, 0.5, 60.0, 5.0)

                # Execute command
                result = SafeSubprocess.run_command(cmd, timeout=timeout)

                success = result.returncode == 0

                # Log command for debugging (but not for frequent RGB commands)
                is_rgb_command = "rgbkbd" in args and any(arg.isdigit() for arg in args[1:])
                if not is_rgb_command or not success:
                    command_str = " ".join(cmd[:4]) + ("..." if len(cmd) > 4 else "")
                    if success:
                        self.logger.debug(f"ectool command succeeded: {command_str}")
                    else:
                        self.logger.warning(
                            f"ectool command failed: {command_str} "
                            f"(RC: {result.returncode})"
                        )
                        if result.stderr:
                            self.logger.debug(f"Error output: {result.stderr[:200]}")

                # Add to command history
                self._add_to_command_history(f"ECTOOL: {' '.join(cmd)}")

                return success, result.stdout, result.stderr

            except Exception as e:
                self.logger.error(f"ectool command error: {e}")
                return False, "", str(e)

    @safe_execute(max_attempts=3, severity=ErrorSeverity.MEDIUM)
    def set_brightness(self, brightness_percent: int) -> bool:
        """Set keyboard brightness with comprehensive error handling and fallbacks."""
        brightness_percent = SafeInput.validate_integer(brightness_percent, 0, 100, 50)

        if not self.hardware_ready:
            if not self.wait_for_detection(5):
                self.logger.warning("Hardware detection not complete for brightness setting")

        # Strategy 1: Try ectool method
        if self.ectool_available:
            try:
                success, output, error = self.run_ectool_command(
                    ["pwmsetkblight", str(brightness_percent)],
                    timeout=5
                )
                if success:
                    self.logger.info(f"Brightness set to {brightness_percent}% via ectool")
                    return True
                else:
                    self.logger.warning(f"ectool brightness failed: {error}")
            except Exception as e:
                self.logger.error(f"ectool brightness method error: {e}")

        # Strategy 2: Try EC direct method
        if self.ec_direct_available:
            try:
                ec_value = int((brightness_percent / 100.0) * 255)
                if self.write_ec_register(163, ec_value):
                    self.logger.info(f"Brightness set to {brightness_percent}% via EC direct")
                    return True
                else:
                    self.logger.warning("EC direct brightness method failed")
            except Exception as e:
                self.logger.error(f"EC direct brightness method error: {e}")

        # Strategy 3: Try system backlight interface (fallback)
        try:
            backlight_paths = [
                "/sys/class/backlight/intel_backlight/brightness",
                "/sys/class/leds/chromeos::kbd_backlight/brightness"
            ]

            for path in backlight_paths:
                try:
                    if os.path.exists(path) and os.access(path, os.W_OK):
                        # Read max brightness first
                        max_path = os.path.dirname(path) + "/max_brightness"
                        if os.path.exists(max_path):
                            with open(max_path, 'r') as f:
                                max_brightness = int(f.read().strip())

                            target_value = int((brightness_percent / 100.0) * max_brightness)
                            with open(path, 'w') as f:
                                f.write(str(target_value))

                            self.logger.info(f"Brightness set to {brightness_percent}% via {path}")
                            return True
                except Exception as e:
                    self.logger.debug(f"Backlight interface {path} failed: {e}")

        except Exception as e:
            self.logger.debug(f"System backlight fallback error: {e}")

        self.logger.error(f"All brightness control methods failed for {brightness_percent}%")
        return False

    @safe_execute(max_attempts=2, severity=ErrorSeverity.LOW)
    def get_brightness(self) -> int:
        """Get current keyboard brightness with error handling and fallbacks."""
        if not self.hardware_ready:
            if not self.wait_for_detection(3):
                self.logger.warning("Hardware detection not complete for brightness reading")

        # Strategy 1: Try ectool method
        if self.ectool_available:
            try:
                success, output, error = self.run_ectool_command(["pwmgetkblight"], timeout=5)
                if success and output:
                    # Parse brightness from various possible output formats
                    brightness_patterns = [
                        r'Current keyboard backlight:\s*(\d+)',
                        r'(\d+)\s*%',
                        r'brightness:\s*(\d+)',
                        r'(\d+)'
                    ]

                    for pattern in brightness_patterns:
                        match = re.search(pattern, output)
                        if match:
                            try:
                                brightness = SafeInput.validate_integer(match.group(1), 0, 100, 50)
                                self.logger.debug(f"Got brightness {brightness}% via ectool")
                                return brightness
                            except Exception as e:
                                self.logger.debug(f"Brightness parsing error: {e}")
                                continue
                else:
                    self.logger.debug(f"ectool get brightness failed: {error}")
            except Exception as e:
                self.logger.debug(f"ectool get brightness error: {e}")

        # Strategy 2: Try system backlight interfaces
        try:
            backlight_paths = [
                "/sys/class/backlight/intel_backlight",
                "/sys/class/leds/chromeos::kbd_backlight"
            ]

            for base_path in backlight_paths:
                try:
                    brightness_path = f"{base_path}/brightness"
                    max_brightness_path = f"{base_path}/max_brightness"

                    if os.path.exists(brightness_path) and os.path.exists(max_brightness_path):
                        with open(brightness_path, 'r') as f:
                            current = int(f.read().strip())
                        with open(max_brightness_path, 'r') as f:
                            maximum = int(f.read().strip())

                        if maximum > 0:
                            percentage = int((current / maximum) * 100)
                            percentage = SafeInput.validate_integer(percentage, 0, 100, 50)
                            self.logger.debug(f"Got brightness {percentage}% via {base_path}")
                            return percentage
                except Exception as e:
                    self.logger.debug(f"Backlight interface {base_path} error: {e}")
        except Exception as e:
            self.logger.debug(f"System backlight reading error: {e}")

        # Default fallback
        self.logger.info("Could not read brightness, returning default 50%")
        return 50

    @safe_execute(max_attempts=2, severity=ErrorSeverity.MEDIUM)
    def set_all_leds_color(self, color: RGBColor) -> bool:
        """Set all LEDs to a single color with comprehensive error handling."""
        if not isinstance(color, RGBColor) or not color.is_valid():
            self.logger.error(f"Invalid color provided: {color}")
            return False

        if not self.hardware_ready:
            if not self.wait_for_detection(3):
                self.logger.warning("Hardware detection not complete for LED control")

        # Strategy 1: Try ectool method
        if self.ectool_available and self.capabilities.get("ectool_zone"):
            try:
                packed_color = (color.r << 16) | (color.g << 8) | color.b
                success = True

                for zone in range(NUM_ZONES):
                    zone_start = zone * LEDS_PER_ZONE
                    cmd_success, _, error = self.run_ectool_command([
                        "rgbkbd", str(zone_start),
                        str(packed_color), str(packed_color), str(packed_color)
                    ], timeout=3)

                    if not cmd_success:
                        success = False
                        self.logger.debug(f"ectool zone {zone} failed: {error}")

                if success:
                    self.logger.debug(f"All LEDs set to {color.to_hex()} via ectool")
                    return True
                else:
                    self.logger.warning("ectool method had partial failures")
            except Exception as e:
                self.logger.error(f"ectool LED control error: {e}")

        # Strategy 2: Try EC direct method
        if self.ec_direct_available:
            try:
                # Initialize EC RGB mode
                if not self.write_ec_register(160, 0):
                    raise HardwareError("Failed to initialize EC RGB mode")
                time.sleep(0.05)

                if not self.write_ec_register(161, 0):
                    raise HardwareError("Failed to set EC RGB sub-mode")

                # Set colors for all zones
                for zone in range(NUM_ZONES):
                    base_reg = 165 + zone * 3
                    if not (self.write_ec_register(base_reg, color.r) and
                           self.write_ec_register(base_reg + 1, color.g) and
                           self.write_ec_register(base_reg + 2, color.b)):
                        raise HardwareError(f"Failed to set color for zone {zone}")

                # Activate changes
                if self.write_ec_register(160, 1):
                    self.logger.debug(f"All LEDs set to {color.to_hex()} via EC direct")
                    return True
                else:
                    raise HardwareError("Failed to activate EC RGB changes")

            except Exception as e:
                self.logger.error(f"EC direct LED control error: {e}")

        self.logger.error(f"All LED control methods failed for color {color.to_hex()}")
        return False

    @safe_execute(max_attempts=2, severity=ErrorSeverity.MEDIUM)
    def set_zone_colors(self, zone_colors: List[RGBColor]) -> bool:
        """Set individual zone colors with comprehensive error handling."""
        if not isinstance(zone_colors, list):
            self.logger.error("Zone colors must be provided as a list")
            return False

        # Validate and pad zone colors
        validated_colors = []
        for i in range(NUM_ZONES):
            if i < len(zone_colors) and isinstance(zone_colors[i], RGBColor):
                if zone_colors[i].is_valid():
                    validated_colors.append(zone_colors[i])
                else:
                    self.logger.warning(f"Invalid color for zone {i}, using black")
                    validated_colors.append(RGBColor(0, 0, 0))
            else:
                validated_colors.append(RGBColor(0, 0, 0))

        if not self.hardware_ready:
            if not self.wait_for_detection(3):
                self.logger.warning("Hardware detection not complete for zone control")

        # Try ectool method
        if self.ectool_available and self.capabilities.get("ectool_zone"):
            try:
                success = True
                for i, color in enumerate(validated_colors):
                    packed_color = (color.r << 16) | (color.g << 8) | color.b
                    zone_start = i * LEDS_PER_ZONE

                    cmd_success, _, error = self.run_ectool_command([
                        "rgbkbd", str(zone_start),
                        str(packed_color), str(packed_color), str(packed_color)
                    ], timeout=3)

                    if not cmd_success:
                        success = False
                        self.logger.debug(f"ectool zone {i} color set failed: {error}")

                if success:
                    self.logger.debug("Zone colors set successfully via ectool")
                    return True
                else:
                    self.logger.warning("ectool zone colors had partial failures")
            except Exception as e:
                self.logger.error(f"ectool zone color control error: {e}")

        # EC direct method not typically used for individual zones
        # as it's more complex and less reliable

        self.logger.error("Zone color control failed")
        return False

    @safe_execute(max_attempts=2, severity=ErrorSeverity.LOW)
    def clear_all_leds(self) -> bool:
        """Clear all LEDs (turn off) with error handling."""
        # Strategy 1: Try ectool clear command
        if self.ectool_available and self.capabilities.get("ectool_clear"):
            try:
                success, _, error = self.run_ectool_command(["rgbkbd", "clear", "0"], timeout=3)
                if success:
                    self.logger.debug("LEDs cleared via ectool clear command")
                    return True
                else:
                    self.logger.debug(f"ectool clear failed: {error}")
            except Exception as e:
                self.logger.debug(f"ectool clear error: {e}")

        # Strategy 2: Set all LEDs to black
        try:
            if self.set_all_leds_color(RGBColor(0, 0, 0)):
                self.logger.debug("LEDs cleared by setting to black")
                return True
        except Exception as e:
            self.logger.error(f"Clear LEDs by color setting failed: {e}")

        self.logger.warning("All LED clearing methods failed")
        return False

    @safe_execute(max_attempts=2, severity=ErrorSeverity.LOW)
    def set_demo_mode(self, mode_id: int) -> bool:
        """Set hardware demo mode with error handling."""
        mode_id = SafeInput.validate_integer(mode_id, 0, 10, 0)

        if self.ectool_available and self.capabilities.get("ectool_demo"):
            try:
                success, output, error = self.run_ectool_command(
                    ["rgbkbd", "demo", str(mode_id)],
                    timeout=5
                )

                if success:
                    self.logger.info(f"Demo mode {mode_id} activated")
                    return True
                else:
                    self.logger.error(f"Demo mode {mode_id} failed: {error}")
            except Exception as e:
                self.logger.error(f"Demo mode error: {e}")
        else:
            self.logger.warning("Demo mode not available (ectool demo capability missing)")

        return False

    @safe_execute(max_attempts=1, severity=ErrorSeverity.LOW)
    def get_command_history(self) -> List[str]:
        """Get recent command history for debugging."""
        try:
            return self._command_history.copy()
        except Exception as e:
            self.logger.error(f"Error getting command history: {e}")
            return []

    @safe_execute(max_attempts=1, severity=ErrorSeverity.LOW)
    def get_status_summary(self) -> Dict[str, Any]:
        """Get comprehensive hardware status summary."""
        try:
            return {
                'ectool_available': self.ectool_available,
                'ec_direct_available': self.ec_direct_available,
                'hardware_ready': self.hardware_ready,
                'capabilities': self.capabilities.copy(),
                'capability_errors': self._capability_errors.copy(),
                'detection_errors': self._detection_errors,
                'ec_io_path': self.ec_io_path,
                'command_history_count': len(self._command_history)
            }
        except Exception as e:
            self.logger.error(f"Error getting status summary: {e}")
            return {'error': str(e)}


class AnimationManager:
    """Manages lighting animations with bulletproof error handling and recovery."""

    def __init__(self, hardware: HardwareController):
        self.hardware = hardware
        self.logger = logging.getLogger('AnimationManager')

        # Thread management with error handling
        try:
            self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="Animation")
        except Exception as e:
            self.logger.error(f"Failed to create thread pool: {e}")
            self._executor = None

        self._current_animation = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        self._animation_errors = 0
        self._max_animation_errors = 10

        # Error recovery state
        self._last_error_time = 0
        self._error_cooldown = 5.0  # seconds

    @safe_execute(max_attempts=2, severity=ErrorSeverity.MEDIUM)
    def stop_current_animation(self) -> None:
        """Stop the currently running animation with comprehensive error handling."""
        with self._lock:
            try:
                if self._current_animation and not self._current_animation.done():
                    self.logger.info("Stopping current animation")
                    self._stop_event.set()

                    try:
                        # Wait for animation to complete with timeout
                        self._current_animation.result(timeout=2.0)
                        self.logger.debug("Animation stopped successfully")
                    except FutureTimeoutError:
                        self.logger.warning("Animation stop timeout, forcing termination")
                        self._current_animation.cancel()
                    except Exception as e:
                        self.logger.warning(f"Animation stop error (non-critical): {e}")

                    self._current_animation = None

                self._stop_event.clear()

            except Exception as e:
                self.logger.error(f"Error stopping animation: {e}")
                # Force reset state even if stopping failed
                self._current_animation = None
                self._stop_event.clear()

    @safe_execute(max_attempts=1, severity=ErrorSeverity.MEDIUM)
    def start_animation(self, animation_func: Callable, *args, **kwargs) -> None:
        """Start a new animation with comprehensive error handling."""
        if not callable(animation_func):
            self.logger.error("Animation function is not callable")
            return

        # Check error cooldown
        current_time = time.time()
        if current_time - self._last_error_time < self._error_cooldown:
            self.logger.warning(f"Animation start blocked due to recent errors (cooldown: {self._error_cooldown}s)")
            return

        if self._animation_errors >= self._max_animation_errors:
            self.logger.error(f"Too many animation errors ({self._animation_errors}), blocking new animations")
            return

        with self._lock:
            try:
                # Stop any current animation
                self.stop_current_animation()

                # Check if executor is available
                if not self._executor:
                    self.logger.error("Thread executor not available for animations")
                    return

                self.logger.info(f"Starting animation: {animation_func.__name__}")

                # Submit new animation with error wrapper
                self._current_animation = self._executor.submit(
                    self._run_animation_safely,
                    animation_func,
                    *args,
                    **kwargs
                )

            except Exception as e:
                self.logger.error(f"Error starting animation: {e}")
                self._animation_errors += 1
                self._last_error_time = current_time

    def _run_animation_safely(self, animation_func: Callable, *args, **kwargs) -> None:
        """Run animation function with comprehensive error handling and recovery."""
        function_name = getattr(animation_func, '__name__', 'unknown')

        try:
            # Validate hardware is ready
            if not self.hardware.hardware_ready:
                if not self.hardware.wait_for_detection(5):
                    raise HardwareError("Hardware not ready for animation")

            # Run the animation function
            animation_func(self._stop_event, self.hardware, *args, **kwargs)

            self.logger.debug(f"Animation {function_name} completed successfully")

            # Reset error count on successful completion
            self._animation_errors = max(0, self._animation_errors - 1)

        except Exception as e:
            self._animation_errors += 1
            self._last_error_time = time.time()

            # Log different error types appropriately
            if isinstance(e, HardwareError):
                self.logger.warning(f"Hardware error in animation {function_name}: {e}")
            elif "stop" in str(e).lower() or "interrupt" in str(e).lower():
                self.logger.debug(f"Animation {function_name} stopped: {e}")
            else:
                self.logger.error(f"Unexpected error in animation {function_name}: {e}", exc_info=True)

            # Attempt hardware recovery for hardware errors
            if isinstance(e, HardwareError) and self._animation_errors < 3:
                self.logger.info("Attempting hardware recovery after animation error")
                try:
                    # Simple recovery: clear LEDs and brief delay
                    self.hardware.clear_all_leds()
                    time.sleep(1)
                except Exception as recovery_error:
                    self.logger.error(f"Hardware recovery failed: {recovery_error}")

        finally:
            # Ensure stop event is set
            self._stop_event.set()

    @safe_execute(max_attempts=1, severity=ErrorSeverity.LOW)
    def is_running(self) -> bool:
        """Check if an animation is currently running with error handling."""
        try:
            with self._lock:
                return (self._current_animation is not None and
                       not self._current_animation.done())
        except Exception as e:
            self.logger.error(f"Error checking animation status: {e}")
            return False

    @safe_execute(max_attempts=1, severity=ErrorSeverity.MEDIUM)
    def shutdown(self) -> None:
        """Shutdown the animation manager with comprehensive cleanup."""
        try:
            self.logger.info("Shutting down animation manager")

            # Stop current animation
            self.stop_current_animation()

            # Shutdown executor with timeout
            if self._executor:
                try:
                    self._executor.shutdown(wait=True, timeout=5.0)
                    self.logger.debug("Animation executor shutdown completed")
                except Exception as e:
                    self.logger.warning(f"Executor shutdown error: {e}")
                    # Force shutdown
                    self._executor = None

            self.logger.info("Animation manager shutdown complete")

        except Exception as e:
            self.logger.error(f"Error during animation manager shutdown: {e}")


class EffectLibrary:
    """Collection of lighting effects with robust error handling."""

    @staticmethod
    def breathing_effect(stop_event: threading.Event, hardware: HardwareController,
                        color: RGBColor, speed: int) -> None:
        """Breathing effect implementation."""
        logger = logging.getLogger('EffectLibrary.breathing')
        frame = 0
        base_delay = 0.02
        error_count = 0
        max_errors = 10

        logger.info(f"Starting breathing effect - color: {color.to_hex()}, speed: {speed}")

        while not stop_event.is_set() and error_count < max_errors:
            try:
                # Calculate breathing intensity using sine wave
                phase = (frame % 100) / 100.0
                intensity = 0.1 + 0.9 * (0.5 + 0.5 * math.sin(phase * 2 * math.pi - math.pi / 2))

                # Apply intensity to color
                dimmed_color = RGBColor(
                    int(color.r * intensity),
                    int(color.g * intensity),
                    int(color.b * intensity)
                )

                if not hardware.set_all_leds_color(dimmed_color):
                    error_count += 1
                    logger.warning(f"Hardware command failed (error {error_count}/{max_errors})")
                else:
                    error_count = 0  # Reset error count on success

                # Speed-adjusted delay (faster speed = shorter delay)
                delay = base_delay * (1 + (10 - speed) * 0.1)
                if stop_event.wait(max(0.01, delay)):
                    break

                frame += 1

            except Exception as e:
                error_count += 1
                logger.error(f"Breathing effect error ({error_count}/{max_errors}): {e}")
                if stop_event.wait(0.1):  # Brief pause on error
                    break

        if error_count >= max_errors:
            logger.error("Breathing effect stopped due to too many errors")
        else:
            logger.info("Breathing effect completed normally")

    @staticmethod
    def color_cycle_effect(stop_event: threading.Event, hardware: HardwareController,
                          speed: int) -> None:
        """Color cycle effect implementation."""
        logger = logging.getLogger('EffectLibrary.color_cycle')
        hue = 0.0
        base_delay = 0.02
        error_count = 0
        max_errors = 10

        logger.info(f"Starting color cycle effect - speed: {speed}")

        while not stop_event.is_set() and error_count < max_errors:
            try:
                # Convert HSV to RGB
                r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                color = RGBColor(int(r * 255), int(g * 255), int(b * 255))

                if not hardware.set_all_leds_color(color):
                    error_count += 1
                    logger.warning(f"Hardware command failed (error {error_count}/{max_errors})")
                else:
                    error_count = 0

                # Update hue based on speed
                hue_increment = 0.002 * speed
                hue = (hue + hue_increment) % 1.0

                if stop_event.wait(base_delay):
                    break

            except Exception as e:
                error_count += 1
                logger.error(f"Color cycle error ({error_count}/{max_errors}): {e}")
                if stop_event.wait(0.1):
                    break

        if error_count >= max_errors:
            logger.error("Color cycle effect stopped due to too many errors")
        else:
            logger.info("Color cycle effect completed normally")

    @staticmethod
    def rainbow_wave_effect(stop_event: threading.Event, hardware: HardwareController,
                           speed: int) -> None:
        """Rainbow wave effect implementation."""
        logger = logging.getLogger('EffectLibrary.rainbow_wave')
        hue_offset = 0.0
        base_delay = 0.02
        error_count = 0
        max_errors = 10

        logger.info(f"Starting rainbow wave effect - speed: {speed}")

        while not stop_event.is_set() and error_count < max_errors:
            try:
                zone_colors = []
                for zone in range(NUM_ZONES):
                    hue = (hue_offset + (zone / NUM_ZONES) * 0.5) % 1.0
                    r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                    zone_colors.append(RGBColor(int(r * 255), int(g * 255), int(b * 255)))

                if not hardware.set_zone_colors(zone_colors):
                    error_count += 1
                    logger.warning(f"Hardware command failed (error {error_count}/{max_errors})")
                else:
                    error_count = 0

                # Update offset
                hue_increment = 0.002 * speed
                hue_offset = (hue_offset + hue_increment) % 1.0

                if stop_event.wait(base_delay):
                    break

            except Exception as e:
                error_count += 1
                logger.error(f"Rainbow wave error ({error_count}/{max_errors}): {e}")
                if stop_event.wait(0.1):
                    break

        if error_count >= max_errors:
            logger.error("Rainbow wave effect stopped due to too many errors")
        else:
            logger.info("Rainbow wave effect completed normally")

    @staticmethod
    def wave_effect(stop_event: threading.Event, hardware: HardwareController,
                   color: RGBColor, speed: int) -> None:
        """Wave effect that moves across zones."""
        logger = logging.getLogger('EffectLibrary.wave')
        wave_position = 0.0
        wave_width = 0.3
        base_delay = 0.05
        error_count = 0
        max_errors = 10

        logger.info(f"Starting wave effect - color: {color.to_hex()}, speed: {speed}")

        while not stop_event.is_set() and error_count < max_errors:
            try:
                zone_colors = []

                for zone in range(NUM_ZONES):
                    # Calculate zone position (0.0 to 1.0)
                    zone_pos = zone / float(NUM_ZONES - 1) if NUM_ZONES > 1 else 0.0

                    # Calculate distance from wave center
                    distance = abs(zone_pos - wave_position)

                    # Calculate intensity based on distance
                    if distance < wave_width:
                        intensity = (1.0 - (distance / wave_width)) ** 2
                    else:
                        intensity = 0.0

                    # Apply intensity to color
                    zone_color = RGBColor(
                        int(color.r * intensity),
                        int(color.g * intensity),
                        int(color.b * intensity)
                    )
                    zone_colors.append(zone_color)

                if not hardware.set_zone_colors(zone_colors):
                    error_count += 1
                    logger.warning(f"Hardware command failed (error {error_count}/{max_errors})")
                else:
                    error_count = 0

                # Move wave
                wave_increment = 0.01 * speed
                wave_position += wave_increment

                # Reset wave position when it moves off screen
                if wave_position > (1.0 + wave_width):
                    wave_position = -wave_width

                # Speed-adjusted delay
                delay = base_delay * (1 + (10 - speed) * 0.1)
                if stop_event.wait(max(0.02, delay)):
                    break

            except Exception as e:
                error_count += 1
                logger.error(f"Wave effect error ({error_count}/{max_errors}): {e}")
                if stop_event.wait(0.1):
                    break

        if error_count >= max_errors:
            logger.error("Wave effect stopped due to too many errors")
        else:
            logger.info("Wave effect completed normally")

    @staticmethod
    def strobe_effect(stop_event: threading.Event, hardware: HardwareController,
                     color: RGBColor, speed: int) -> None:
        """Strobe effect implementation."""
        logger = logging.getLogger('EffectLibrary.strobe')
        on_state = True
        error_count = 0
        max_errors = 10

        logger.info(f"Starting strobe effect - color: {color.to_hex()}, speed: {speed}")

        while not stop_event.is_set() and error_count < max_errors:
            try:
                # Choose color based on state
                current_color = color if on_state else RGBColor(0, 0, 0)

                if not hardware.set_all_leds_color(current_color):
                    error_count += 1
                    logger.warning(f"Hardware command failed (error {error_count}/{max_errors})")
                else:
                    error_count = 0

                # Toggle state
                on_state = not on_state

                # Speed-adjusted delay
                duration = 0.05 + ((10 - speed) * 0.05)
                if stop_event.wait(max(0.02, duration)):
                    break

            except Exception as e:
                error_count += 1
                logger.error(f"Strobe effect error ({error_count}/{max_errors}): {e}")
                if stop_event.wait(0.1):
                    break

        if error_count >= max_errors:
            logger.error("Strobe effect stopped due to too many errors")
        else:
            logger.info("Strobe effect completed normally")


class SystemMonitor:
    """Monitor system resources and performance."""

    def __init__(self):
        self.logger = logging.getLogger('SystemMonitor')
        self._monitoring = False
        self._monitor_thread = None
        self._stop_event = threading.Event()

    def start_monitoring(self) -> None:
        """Start system monitoring."""
        if not self._monitoring and PSUTIL_AVAILABLE:
            self._monitoring = True
            self._stop_event.clear()
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop,
                daemon=True,
                name="SystemMonitor"
            )
            self._monitor_thread.start()
            self.logger.info("System monitoring started")

    def stop_monitoring(self) -> None:
        """Stop system monitoring."""
        if self._monitoring:
            self._monitoring = False
            self._stop_event.set()
            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=2)
            self.logger.info("System monitoring stopped")

    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        check_interval = 30  # Check every 30 seconds

        while self._monitoring and not self._stop_event.is_set():
            try:
                # Check memory usage
                memory = psutil.virtual_memory()
                if memory.percent > 90:
                    self.logger.warning(f"High memory usage: {memory.percent:.1f}%")

                # Check CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                if cpu_percent > 90:
                    self.logger.warning(f"High CPU usage: {cpu_percent:.1f}%")

                # Check for our process
                try:
                    process = psutil.Process(os.getpid())
                    proc_memory = process.memory_info().rss / (1024 * 1024)  # MB

                    if proc_memory > 100:  # More than 100MB
                        self.logger.warning(f"High process memory usage: {proc_memory:.1f}MB")
                except psutil.NoSuchProcess:
                    pass

                # Wait for next check
                if self._stop_event.wait(check_interval):
                    break

            except Exception as e:
                self.logger.error(f"System monitoring error: {e}")
                if self._stop_event.wait(check_interval):
                    break

    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status."""
        status = {}

        if PSUTIL_AVAILABLE:
            try:
                # Memory info
                memory = psutil.virtual_memory()
                status['memory_percent'] = memory.percent
                status['memory_available_gb'] = memory.available / (1024**3)

                # CPU info
                status['cpu_percent'] = psutil.cpu_percent(interval=0.1)
                status['cpu_count'] = psutil.cpu_count()

                # Process info
                try:
                    process = psutil.Process(os.getpid())
                    status['process_memory_mb'] = process.memory_info().rss / (1024 * 1024)
                    status['process_cpu_percent'] = process.cpu_percent()
                except psutil.NoSuchProcess:
                    status['process_memory_mb'] = 0
                    status['process_cpu_percent'] = 0

            except Exception as e:
                logging.error(f"Error getting system status: {e}")

        return status


class EnhancedRGBController:
    """Main application controller with improved error handling and structure."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.logger = logging.getLogger('EnhancedRGBController')

        # Check root privileges
        if os.geteuid() != 0:
            logger.critical("Root privileges required")
            try:
                error_root = tk.Tk()
                error_root.withdraw()
                messagebox.showerror(
                    "Root Required",
                    f"Root privileges are required to control hardware.\n\n"
                    f"Please run with: sudo python3 {sys.argv[0]}"
                )
                error_root.destroy()
            except Exception:
                print(f"ERROR: Root privileges required. Run with: sudo python3 {sys.argv[0]}")
            sys.exit(1)

        # Create main window
        root = tk.Tk()
        logger.debug("Main window created")

        # Initialize application
        app = EnhancedRGBController(root)

        # Start GUI mainloop if initialization was successful
        if app._gui_initialized and root.winfo_exists():
            logger.info("Starting GUI mainloop...")
            root.mainloop()
            logger.info("GUI mainloop ended")
        else:
            logger.error("Application initialization failed")
            if root.winfo_exists():
                root.destroy()

    except KeyboardInterrupt:
        logger.info("Application interrupted by user (Ctrl+C)")
    except tk.TclError as e:
        logger.critical(f"Tkinter error: {e}", exc_info=True)
        print(f"FATAL TKINTER ERROR: {e}")
    except ImportError as e:
        logger.critical(f"Import error: {e}", exc_info=True)
        print(f"FATAL IMPORT ERROR: {e}")
    except Exception as e:
        logger.critical(f"Unexpected error: {e}", exc_info=True)
        print(f"UNEXPECTED ERROR: {e}")
    finally:
        logger.info(f"--- {APP_NAME} Shutdown ---")

        # Clean up logging handlers
        try:
            for handler in logging.getLogger().handlers[:]:
                try:
                    handler.flush()
                    handler.close()
                    logging.getLogger().removeHandler(handler)
                except Exception:
                    pass
        except Exception:
            pass


if __name__ == "__main__":
    main()
