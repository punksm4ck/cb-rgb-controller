# gui/core/__init__.py

"""
Core components for the RGB Controller application.
This file makes 'core' a Python package.
"""

from .rgb_color import RGBColor
from .settings import SettingsManager
from .constants import (
    NUM_ZONES, LEDS_PER_ZONE, TOTAL_LEDS,
    PREVIEW_WIDTH, PREVIEW_HEIGHT, PREVIEW_LED_SIZE,
    PREVIEW_LED_SPACING, PREVIEW_KEYBOARD_COLOR,
    ANIMATION_FRAME_DELAY, APP_NAME, VERSION,
    REACTIVE_DELAY, default_settings,
    CONFIG_DIR, LOG_DIR, SETTINGS_FILE # Export paths as well
)
from .exceptions import (
    SecurityError,
    HardwareError,
    ConfigurationError,
    ValidationError,
    ResourceError,
    KeyboardControlError
)


__all__ = [
    "RGBColor",
    "SettingsManager",
    "NUM_ZONES", "LEDS_PER_ZONE", "TOTAL_LEDS",
    "PREVIEW_WIDTH", "PREVIEW_HEIGHT", "PREVIEW_LED_SIZE",
    "PREVIEW_LED_SPACING", "PREVIEW_KEYBOARD_COLOR",
    "ANIMATION_FRAME_DELAY", "APP_NAME", "VERSION",
    "REACTIVE_DELAY", "default_settings",
    "CONFIG_DIR", "LOG_DIR", "SETTINGS_FILE",
    "SecurityError", "HardwareError", "ConfigurationError",
    "ValidationError", "ResourceError", "KeyboardControlError"
]

