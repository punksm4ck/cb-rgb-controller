#!/usr/bin/env python3
"""Core constants for RGB Controller"""

import os
from pathlib import Path
from typing import Dict, Any, List 

# Application Constants
VERSION = "6.1.0" 
APP_NAME = "Enhanced Chromebook RGB Control"
NUM_ZONES = 4  # Number of logical zones the user interacts with
LEDS_PER_ZONE = 3 # Assumed LEDs per hardware controllable zone segment (e.g., for ectool)
TOTAL_LEDS = NUM_ZONES * LEDS_PER_ZONE # Total logical LEDs for effects like full keyboard preview

# Animation Constants
ANIMATION_FRAME_DELAY = 0.05  # Default 50ms (20 FPS) between animation frames
REACTIVE_DELAY = 0.5        # Default 500ms duration for a reactive effect pulse
MIN_ANIMATION_FRAME_DELAY = 0.01 # Minimum delay to prevent CPU overload in fast effects
BASE_ANIMATION_DELAY_SPEED_1 = 0.2 # Base delay for slowest speed (speed=1) in effects (e.g. 200ms per step)

# Hardware Interaction
ECTOOL_INTER_COMMAND_DELAY = 0.01  # Small delay (10ms) between consecutive ectool commands if needed

# Preview Configuration (if you implement a GUI preview)
PREVIEW_WIDTH = 400
PREVIEW_HEIGHT = 80
PREVIEW_KEYBOARD_COLOR = "#2c2c2c" 
PREVIEW_LED_SIZE = 12          
PREVIEW_LED_SPACING = 10       

# Error Handling Constants
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_BASE = 0.5  # seconds
MAX_ERROR_COUNT = 10    # General threshold for some operations
CIRCUIT_BREAKER_THRESHOLD = 5
CIRCUIT_BREAKER_TIMEOUT = 30 # seconds

# Hardware Detection Constants
HARDWARE_DETECTION_TIMEOUT = 10.0  # seconds to wait for hardware detection

# File paths (centralized for easier management)
def get_app_config_dir() -> Path:
    """Gets the application's configuration directory, preferring XDG standards."""
    # Create a filesystem-friendly name for the app's config directory
    app_name_fs = APP_NAME.lower().replace(" ", "_").replace("-", "_") 
    
    xdg_config_home_str = os.environ.get('XDG_CONFIG_HOME')
    if xdg_config_home_str and Path(xdg_config_home_str).is_dir(): # Check if XDG_CONFIG_HOME is valid
        base_path = Path(xdg_config_home_str)
    else:
        base_path = Path.home() / ".config" # Fallback for Linux/macOS
        if os.name == 'nt': # Windows fallback
            appdata = os.environ.get('APPDATA')
            if appdata:
                base_path = Path(appdata)
            else: # Absolute last resort for Windows if APPDATA isn't set
                base_path = Path.home() / "AppData" / "Roaming"
    
    return base_path / app_name_fs

APP_CONFIG_BASE_DIR = get_app_config_dir()
CONFIG_DIR = APP_CONFIG_BASE_DIR # Main directory for app data (legacy, can be removed if APP_CONFIG_BASE_DIR is used everywhere)
LOG_DIR = APP_CONFIG_BASE_DIR / "logs"
SETTINGS_FILE = APP_CONFIG_BASE_DIR / "settings.json" 
DESKTOP_FILE_NAME = f"{APP_NAME.lower().replace(' ', '-')}.desktop"


# Default Settings dictionary
# This serves as the schema and fallback for SettingsManager.
default_settings: Dict[str, Any] = {
    'brightness': 100,                                      
    'current_color': {"r": 255, "g": 0, "b": 0},             
    'zone_colors': [                                         
        {"r": 255, "g": 0, "b": 0},    # Zone 1 (Red)
        {"r": 0, "g": 255, "b": 0},    # Zone 2 (Green)
        {"r": 0, "g": 0, "b": 255},    # Zone 3 (Blue)
        {"r": 255, "g": 255, "b": 0}   # Zone 4 (Yellow)
    ], 
    'effect_name': "Static Color",                           
    'effect_speed': 5,                                       
    'effect_color': "#0064FF",                               
    'effect_rainbow_mode': False,                            
    'gradient_start_color': "#FF0000",                       
    'gradient_end_color': "#0000FF",                         
    'effect_background_color': "#101010",                    
    'last_control_method': "ectool",                         
    'restore_on_startup': True,                              
    'auto_apply_last_setting': True,                         
    'last_mode': "static",                                   
    'clean_shutdown': False,                                 
    'minimize_to_tray': True,                               
    'keep_effects_running': True                            
}

# Ensure zone_colors default has exactly NUM_ZONES items
_default_zone_color_palette = default_settings['zone_colors']
default_settings['zone_colors'] = [
    _default_zone_color_palette[i % len(_default_zone_color_palette)] 
    for i in range(NUM_ZONES)
]
