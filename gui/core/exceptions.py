#!/usr/bin/env python3
"""Custom exceptions for RGB Controller"""

class RGBControllerBaseException(Exception):
    """Base exception for this application."""
    pass

class SecurityError(RGBControllerBaseException):
    """Raised when a security violation is detected (e.g., unsafe command)."""
    pass

class HardwareError(RGBControllerBaseException):
    """Raised when hardware operations fail or hardware is not detected/responsive."""
    pass

class ConfigurationError(RGBControllerBaseException):
    """Raised when configuration is invalid, corrupted, or cannot be accessed."""
    pass

class ValidationError(RGBControllerBaseException):
    """Raised when input validation fails for a specific value."""
    pass

class ResourceError(RGBControllerBaseException):
    """Raised when required system resources (e.g., files, commands) are unavailable."""
    pass

class KeyboardControlError(HardwareError):
    """Specific hardware error related to keyboard control operations."""
    pass

class EffectError(RGBControllerBaseException):
    """Raised when an effect encounters an issue or cannot be run."""
    pass


