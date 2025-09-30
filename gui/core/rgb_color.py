#!/usr/bin/env python3
"""RGB Color class implementation with validation and conversion utilities."""

import colorsys
import re
import sys # Added for sys.stderr
from typing import Dict, Tuple, Any, Union

# Assuming exceptions are in the same 'core' package or accessible
from .exceptions import ValidationError # This is good, using your custom exception

class RGBColor:
    """
    Represents an RGB color with validation and utility methods.
    Ensures R, G, B values are always integers between 0 and 255.
    """
    
    def __init__(self, r: Any, g: Any, b: Any):
        """
        Initialize RGB color. Values will be coerced to int and clamped to 0-255.
        """
        # No try-except here; _validate_component handles coercion and defaults.
        # If _validate_component were to raise an error, it would propagate.
        self.r = self._validate_component(r, 'R')
        self.g = self._validate_component(g, 'G')
        self.b = self._validate_component(b, 'B')

    @staticmethod
    def _validate_component(value: Any, component_name: str) -> int:
        """Validates and clamps a single color component. Defaults to 0 on error."""
        try:
            # Attempt to convert to float first to handle "128.0", then to int
            val = int(float(value)) 
        except (ValueError, TypeError):
            # Using print for a core class like this is okay for immediate feedback during dev,
            # but for library use, logging or raising ValidationError would be more conventional.
            # Since it defaults, it's a non-fatal issue.
            # print(f"Warning: Invalid value '{value}' for color component {component_name}. Defaulting to 0.", file=sys.stderr)
            return 0 
        return max(0, min(255, val))

    def __str__(self) -> str:
        return f"RGB({self.r}, {self.g}, {self.b})"
    
    def __repr__(self) -> str:
        # Using class name in repr is standard for unambiguous representation
        return f"RGBColor(r={self.r}, g={self.g}, b={self.b})"
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RGBColor):
            return NotImplemented # Important for correct comparison behavior
        return self.r == other.r and self.g == other.g and self.b == other.b
    
    def to_hex(self) -> str:
        """Convert to hex string format (e.g., '#FF0080')."""
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"
    
    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary format."""
        return {"r": self.r, "g": self.g, "b": self.b}
    
    def to_tuple(self) -> Tuple[int, int, int]:
        """Convert to tuple format (r, g, b)."""
        return (self.r, self.g, self.b)
    
    @classmethod
    def from_hex(cls, hex_str: str) -> 'RGBColor':
        """Create RGBColor from a hex string (e.g., '#FF0080', 'ff0080', '#F08')."""
        if not isinstance(hex_str, str):
            # Consider raising ValidationError or logging instead of print for library use
            # print(f"Warning: from_hex expects a string, got {type(hex_str)}. Defaulting to black.", file=sys.stderr)
            return cls(0, 0, 0) # Default to black
            
        clean_hex = hex_str.lstrip('#').lower()
        
        if len(clean_hex) == 3: 
            clean_hex = "".join(c*2 for c in clean_hex)
        
        if len(clean_hex) != 6 or not re.fullmatch(r'[0-9a-f]{6}', clean_hex):
            # print(f"Warning: Invalid hex color string '{hex_str}'. Defaulting to black.", file=sys.stderr)
            return cls(0, 0, 0) 
        try:
            r_val = int(clean_hex[0:2], 16)
            g_val = int(clean_hex[2:4], 16)
            b_val = int(clean_hex[4:6], 16)
            return cls(r_val, g_val, b_val)
        except ValueError: 
            # print(f"Warning: ValueError parsing hex components from '{clean_hex}'. Defaulting to black.", file=sys.stderr)
            return cls(0, 0, 0)
    
    @classmethod
    def from_dict(cls, color_dict: Dict[str, Any]) -> 'RGBColor':
        """Create RGBColor from a dictionary {'r': R, 'g': G, 'b': B}."""
        if not isinstance(color_dict, dict):
            # print(f"Warning: from_dict expects a dict, got {type(color_dict)}. Defaulting to black.", file=sys.stderr)
            return cls(0,0,0)
        # _validate_component will handle clamping and type coercion for r, g, b
        return cls(
            color_dict.get('r', 0), # Default to 0 if key is missing
            color_dict.get('g', 0),
            color_dict.get('b', 0)
        )
    
    @classmethod
    def from_hsv(cls, h: float, s: float, v: float) -> 'RGBColor':
        """Create RGBColor from HSV values (h, s, v expected in range 0-1)."""
        h_val = max(0.0, min(1.0, h)) # Clamping h,s,v to 0-1 range
        s_val = max(0.0, min(1.0, s))
        v_val = max(0.0, min(1.0, v))
        r_float, g_float, b_float = colorsys.hsv_to_rgb(h_val, s_val, v_val)
        return cls(int(r_float * 255), int(g_float * 255), int(b_float * 255))
    
    def to_hsv(self) -> Tuple[float, float, float]:
        """Convert RGB to HSV values (components in range 0-1)."""
        return colorsys.rgb_to_hsv(self.r / 255.0, self.g / 255.0, self.b / 255.0)
    
    def with_brightness(self, brightness_factor: float) -> 'RGBColor':
        """Return a new RGBColor with adjusted brightness. Factor is 0.0 to 1.0."""
        brightness_factor = max(0.0, min(1.0, brightness_factor))
        # _validate_component will handle clamping results of multiplication
        return RGBColor(
            self.r * brightness_factor,
            self.g * brightness_factor,
            self.b * brightness_factor
        )
    
    def interpolate(self, other_color: 'RGBColor', ratio: float) -> 'RGBColor':
        """Linearly interpolate between this color and another. Ratio is 0.0 to 1.0."""
        if not isinstance(other_color, RGBColor):
            # print(f"Warning: Cannot interpolate with non-RGBColor type {type(other_color)}. Returning self.", file=sys.stderr)
            return self 
        ratio = max(0.0, min(1.0, ratio))
        # _validate_component will handle clamping results of interpolation
        return RGBColor(
            self.r * (1 - ratio) + other_color.r * ratio,
            self.g * (1 - ratio) + other_color.g * ratio,
            self.b * (1 - ratio) + other_color.b * ratio
        )

    def is_dark(self, luminance_threshold: float = 0.4) -> bool:
        """Determine if the color is perceived as dark based on luminance (0-1 range)."""
        # Standard luminance calculation for sRGB:
        luminance = (0.2126 * self.r + 0.7152 * self.g + 0.0722 * self.b) / 255.0
        return luminance < luminance_threshold

    def get_contrast_color(self) -> 'RGBColor':
        """Returns black or white, whichever has better contrast with this color."""
        return RGBColor(0,0,0) if not self.is_dark(luminance_threshold=0.5) else RGBColor(255,255,255)

    def is_valid(self) -> bool:
        """
        Checks if the current R,G,B values are valid (0-255 integers).
        This should always be true due to the validation in __init__.
        """
        return (isinstance(self.r, int) and 0 <= self.r <= 255 and
                isinstance(self.g, int) and 0 <= self.g <= 255 and
                isinstance(self.b, int) and 0 <= self.b <= 255)


