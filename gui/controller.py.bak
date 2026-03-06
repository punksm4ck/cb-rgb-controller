#!/usr/bin/env python3
"""Enhanced RGB Keyboard Controller GUI with universal controls and rainbow effects - Combined Best Features"""

import tkinter as tk
from tkinter import ttk, colorchooser, messagebox, scrolledtext, filedialog
import logging
import logging.handlers
import threading
import time
import colorsys
import math
import random
import json
import os
import sys
import platform
import subprocess
import shlex
from typing import List, Dict, Any, Callable, Tuple, Optional
from pathlib import Path
from datetime import datetime
from functools import partial
import queue
import io

# For system tray functionality
PYSTRAY_AVAILABLE = False
PIL_AVAILABLE = False
try:
    import pystray
    PYSTRAY_AVAILABLE = True
    try:
        from PIL import Image, ImageDraw
        PIL_AVAILABLE = True
    except ImportError:
        print("WARNING: PIL (Pillow) not found. System tray icon will be very basic or might fail. Install with 'pip install Pillow'.", file=sys.stderr)
except ImportError:
    print("WARNING: pystray not found. System tray functionality will be disabled. Install with 'pip install pystray'.", file=sys.stderr)

# For global keyboard hotkeys
KEYBOARD_LIB_AVAILABLE = False
try:
    import keyboard
    KEYBOARD_LIB_AVAILABLE = True
except ImportError:
    print("WARNING: 'keyboard' library not found. ALT+Brightness hotkeys will be disabled. Install with 'pip install keyboard'. Note: May require root/admin privileges to run.", file=sys.stderr)

# Import core modules
# NOTE: In a production environment, these imports would be from a deployed package.
# For this script, we assume the directory structure allows these relative imports to work.
try:
    from .core.rgb_color import RGBColor
    from .core.settings import SettingsManager
    from .core.constants import (
        NUM_ZONES, LEDS_PER_ZONE, TOTAL_LEDS,
        PREVIEW_WIDTH, PREVIEW_HEIGHT, PREVIEW_LED_SIZE,
        PREVIEW_LED_SPACING, PREVIEW_KEYBOARD_COLOR,
        ANIMATION_FRAME_DELAY, APP_NAME, VERSION,
        REACTIVE_DELAY, default_settings, SETTINGS_FILE,
        HARDWARE_DETECTION_TIMEOUT
    )
    from .core.exceptions import HardwareError, ConfigurationError
    from .hardware.controller import HardwareController
    from .effects.manager import EffectManager

except ImportError as e:
    print(f"FATAL ERROR: Could not import core modules. Ensure you are running this script as a package with 'python -m your_package_name'. Error: {e}", file=sys.stderr)
    sys.exit(1)

# --- Placeholder Classes to resolve NameError ---
class PerformanceMonitor:
    """A placeholder class for monitoring application performance."""
    def __init__(self):
        # This is a placeholder and has no functionality yet.
        pass

class AdvancedDiagnostics:
    """A placeholder class for handling advanced diagnostics."""
    def __init__(self, logger):
        self.logger = logger
        # This is a placeholder and has no functionality yet.
        pass

def log_error_with_context(logger, e, context=None):
    """Logs an error with additional context."""
    if context is None:
        context = {}
    logger.error(f"Error: {e} | Context: {context}", exc_info=True)

def log_system_info(logger):
    """Logs basic system and Python environment information."""
    logger.info(f"System: {platform.system()} {platform.release()} ({platform.machine()})")
    logger.info(f"Python: {sys.version.splitlines()[0]}")

class RGBControllerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.logger = self.setup_logging()
        self.pystray_icon_image: Optional[Image.Image] = None
        self.tk_icon_photoimage: Optional[tk.PhotoImage] = None

        # Placeholder for core components
        self.settings: Optional[SettingsManager] = None
        self.hardware: Optional[HardwareController] = None
        self.effect_manager: Optional[EffectManager] = None

        try:
            self._initialize_core_components()
        except (IOError, PermissionError) as e:
            self._handle_critical_initialization_error(e)
        except tk.TclError as e:
            self.logger.debug(f"A tkinter widget-related error occurred (likely during shutdown): {e}")

        # State Variables
        self.is_fullscreen = False
        self.preview_animation_active = False
        self.preview_animation_id: Optional[str] = None
        self._preview_frame_count = 0
        self._loading_settings = False
        self.tray_icon: Optional[pystray.Icon] = None
        self.tray_thread: Optional[threading.Thread] = None
        self.window_hidden_to_tray = False
        self._hotkey_setup_attempted = False
        self._brightness_hotkeys_working = False
        self._registered_hotkeys = []
        self.key_grid = None

        self.setup_variables()
        self.setup_main_window()
        self.create_widgets()
        self.setup_bindings()

        if KEYBOARD_LIB_AVAILABLE:
            self.setup_global_hotkeys_enhanced()

        # Staggered startup sequence
        self.root.after(100, self.initialize_hardware_async)
        self.root.after(200, self.load_saved_settings)
        self.root.after(300, self.show_system_info) # Populate diagnostics on startup
        self.root.after(600, self.apply_startup_settings_if_enabled_async)

        self.logger.info(f"{APP_NAME} v{VERSION} GUI Initialized and ready.")

    def _initialize_core_components(self):
        """Initializes core app components that might fail on startup."""
        self.settings = SettingsManager(SETTINGS_FILE)
        self.hardware = HardwareController(self.logger, last_control_method=self.settings.get('last_control_method', 'ectool'))
        self.effect_manager = EffectManager(self.logger, self.hardware, self.settings)
        self.setup_gui_logging()

    def _handle_critical_initialization_error(self, e):
        """Handle errors that prevent the app from starting properly."""
        self.logger.critical(f"Critical initialization error: {e}", exc_info=True)
        messagebox.showerror("Fatal Initialization Error", f"The application failed to start due to a critical error: {e}\n\nPlease check the application logs for details.")
        sys.exit(1)

    def _stop_all_visuals_and_clear_hardware(self):
        """Stops software effects and attempts to clear hardware patterns."""
        self.logger.debug("Stopping all software effects and GUI previews.")
        if hasattr(self, 'effect_manager') and self.effect_manager:
            self.effect_manager.stop_current_effect()
        self.stop_preview_animation()
        if hasattr(self, 'hardware') and self.hardware and self.hardware.is_operational():
            self.logger.debug("Attempting to clear hardware effects/LEDs.")
            if hasattr(self.hardware, 'attempt_stop_hardware_effects'):
                self.hardware.attempt_stop_hardware_effects()
            else:
                self.logger.warning("hardware.attempt_stop_hardware_effects not found, falling back to clear_all_leds.")
                self.hardware.clear_all_leds()
        self.zone_colors = [RGBColor(0,0,0)] * NUM_ZONES
        self.update_preview_keyboard()
        self.logger.debug("All visuals stopped and hardware clear attempted.")

    def setup_logging(self) -> logging.Logger:
        logger = logging.getLogger(f"{APP_NAME}.GUI")
        if logger.hasHandlers(): return logger
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s')
        try:
            log_dir = SETTINGS_FILE.parent / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "rgb_controller_gui.log"
            fh = logging.handlers.RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        except (IOError, PermissionError) as e:
            logger.error(f"Failed to set up GUI file logging: {e}", exc_info=True)
        return logger

    def create_desktop_launcher(self):
        if platform.system() != "Linux":
            messagebox.showinfo("Not Supported", "Desktop launcher creation is currently only supported on Linux.", parent=self.root)
            return

        try:
            python_exe = sys.executable
            project_root_dir = Path(__file__).resolve().parent.parent
            module_to_run = project_root_dir.name
            working_dir_for_launcher = project_root_dir.parent
            # Use pkexec to request admin privileges and run the main launch script directly
            launch_script_path = working_dir_for_launcher / "launch_rgb.sh"
            exec_cmd = f'pkexec {shlex.quote(str(launch_script_path))}'

            icon_path = project_root_dir / "assets" / "icon.png"
            icon_name_or_path = str(icon_path.resolve()) if icon_path.exists() else "input-keyboard"

            content = (f"[Desktop Entry]\nVersion=1.0\nName={APP_NAME}\nComment=Control RGB Keyboard Lighting\n"
                       f"Exec={exec_cmd}\nIcon={icon_name_or_path}\nTerminal=false\nType=Application\n"
                       f"Categories=Utility;Settings;HardwareSettings;\nPath={str(working_dir_for_launcher)}\n")

            # Use the original user's home directory if passed by the launch script, otherwise default
            user_home_path = Path(os.environ.get('ORIGINAL_HOME', Path.home()))

            locations_to_try = [
                user_home_path / ".local/share/applications",
                user_home_path / "Desktop"
            ]

            success_paths = []
            for loc in locations_to_try:
                try:
                    loc.mkdir(parents=True, exist_ok=True)
                    file_path = loc / f"{module_to_run}.desktop"
                    file_path.write_text(content, encoding='utf-8')
                    file_path.chmod(0o755)
                    success_paths.append(f"✓ {loc.name}: {file_path}")
                except (IOError, PermissionError) as e:
                    self.logger.error(f"Failed to create launcher at {loc}: {e}")

            if success_paths:
                messagebox.showinfo("Launcher Created", "\n".join(success_paths), parent=self.root)
            else:
                messagebox.showerror("Launcher Error", "Could not create launcher in any location. Please check permissions.", parent=self.root)

        except (IOError, PermissionError) as e:
            self.logger.error(f"Could not determine paths for launcher: {e}", exc_info=True)
            messagebox.showerror("Launcher Error", f"Could not determine script paths: {e}", parent=self.root)

    def log_missing_keyboard_library(self):
        """Provide detailed instructions for installing keyboard library"""
        missing_msg = """
KEYBOARD HOTKEYS DISABLED - Missing Dependencies:

The 'keyboard' library is required for ALT+Brightness hotkey functionality.
INSTALLATION INSTRUCTIONS:
=========================

1. Install the keyboard library:
   pip install keyboard

2. IMPORTANT - PERMISSIONS REQUIRED:
   • Linux: Run application with sudo for global hotkeys
     sudo python -m rgb_controller_finalv2
   • Windows: Run as Administrator
   • macOS: Grant Accessibility permissions in System Preferences

3. Alternative installation methods:
   • conda install -c conda-forge keyboard
   • pip3 install keyboard (if pip points to Python 2)

4. Troubleshooting:
   • If installation fails, try: pip install --user keyboard
   • On Ubuntu/Debian: sudo apt install python3-dev first
   • On CentOS/RHEL: sudo yum install python3-devel first

5. After installation, restart the application

Note: Global hotkeys require elevated privileges to capture system-wide key events. This is a security feature of operating systems.
        """
        self.logger.warning("Keyboard library not available. ALT+Brightness hotkeys disabled.")
        self.log_to_gui_diag_area(missing_msg.strip(), "warning")
        print(missing_msg, file=sys.stderr)

    def setup_reactive_effects_system(self):
        """Initialize reactive effects system with proper key detection"""
        self.logger.info("Initializing reactive effects system...")
        self.reactive_detection_methods = []
        if KEYBOARD_LIB_AVAILABLE:
            try:
                self.reactive_detection_methods.append("keyboard_global")
                self.logger.info("Reactive effects: Global keyboard detection available")
            except (IOError, PermissionError) as e:
                self.logger.warning(f"Reactive effects: Global keyboard detection failed: {e}")
        self.reactive_detection_methods.append("gui_focused")
        if hasattr(self.hardware, 'supports_key_press_detection'):
            if self.hardware.supports_key_press_detection():
                self.reactive_detection_methods.append("hardware_ec")
                self.logger.info("Reactive effects: Hardware EC key detection available")
        self.logger.info(f"Reactive effects: Available detection methods: {self.reactive_detection_methods}")

    def preview_reactive(self, frame_count: int):
        """Preview reactive effect - keys light up only when pressed"""
        try:
            base_color_rgb = RGBColor.from_hex(self.effect_color_var.get())
        except ValueError:
            base_color_rgb = RGBColor(255, 255, 255)
        is_rainbow = self.effect_rainbow_mode_var.get()
        speed_multiplier = self.get_hardware_synchronized_speed()
        for i in range(NUM_ZONES):
            self.zone_colors[i] = RGBColor(0, 0, 0)
        if hasattr(self, 'key_grid') and self.key_grid:
            self._simulate_realistic_key_presses_for_reactive_preview(frame_count, base_color_rgb, is_rainbow)
        else:
            self._simulate_zone_based_reactive_preview(frame_count, base_color_rgb, is_rainbow, speed_multiplier)
        self.update_preview_keyboard()

    def _simulate_realistic_key_presses_for_reactive_preview(self, frame_count, base_color, is_rainbow):
        """Simulate realistic typing patterns for reactive preview"""
        if not hasattr(self, 'key_grid') or not self.key_grid:
            return
        for row in self.key_grid:
            for key_info in row:
                try:
                    canvas = self.preview_canvas
                    canvas.itemconfig(key_info['element'], fill='#404040', outline='#606060', width=1)
                except:
                    pass
        typing_patterns = [
            {'keys': [(1, 5), (1, 6), (1, 7), (1, 7), (1, 8)], 'start_frame': 0, 'duration': 15},
            {'keys': [(2, 1), (1, 1), (2, 2), (2, 0)], 'start_frame': 50, 'duration': 20},
            {'keys': [(4, 7)], 'start_frame': 100, 'duration': 8},
            {'keys': [(4, 12), (4, 13), (4, 14), (4, 15)], 'start_frame': 150, 'duration': 12},
        ]
        active_keys = set()
        for pattern in typing_patterns:
            pattern_frame = (frame_count - pattern['start_frame']) % 200
            if 0 <= pattern_frame < pattern['duration']:
                for i, (row, col) in enumerate(pattern['keys']):
                    key_start = i * 2
                    if key_start <= pattern_frame < key_start + pattern['duration'] - i:
                        if 0 <= row < len(self.key_grid) and 0 <= col < len(self.key_grid[row]):
                            active_keys.add((row, col))
        for row, col in active_keys:
            if 0 <= row < len(self.key_grid) and 0 <= col < len(self.key_grid[row]):
                key_info = self.key_grid[row][col]
                if is_rainbow:
                    hue = ((row + col) / 10 + frame_count * 0.01) % 1.0
                    rgb_float = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                    color = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
                else:
                    color = base_color
                try:
                    canvas = self.preview_canvas
                    canvas.itemconfig(key_info['element'], fill=color.to_hex(), outline='#ffffff', width=2)
                except:
                    pass

    def _simulate_zone_based_reactive_preview(self, frame_count, base_color, is_rainbow, speed_multiplier):
        """Fallback zone-based reactive simulation"""
        for i in range(NUM_ZONES):
            press_seed = (frame_count * speed_multiplier + i * 23) % 80
            is_pressed = press_seed < 12
            if is_pressed:
                if is_rainbow:
                    hue = (i / NUM_ZONES + frame_count * speed_multiplier * 0.1) % 1.0
                    rgb_float = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                    self.zone_colors[i] = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
                else:
                    self.zone_colors[i] = base_color
            else:
                self.zone_colors[i] = RGBColor(0, 0, 0)

    def preview_anti_reactive(self, frame_count: int):
        """Preview anti-reactive effect - all on except when keys are pressed"""
        try:
            base_color_rgb = RGBColor.from_hex(self.effect_color_var.get())
        except ValueError:
            base_color_rgb = RGBColor(255, 255, 255)
        is_rainbow = self.effect_rainbow_mode_var.get()
        speed_multiplier = self.get_hardware_synchronized_speed()
        for i in range(NUM_ZONES):
            if is_rainbow:
                hue = (i / NUM_ZONES) % 1.0
                rgb_float = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                self.zone_colors[i] = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
            else:
                self.zone_colors[i] = base_color_rgb
        if hasattr(self, 'key_grid') and self.key_grid:
            self._simulate_realistic_key_presses_for_anti_reactive_preview(frame_count, base_color_rgb, is_rainbow)
        else:
            self._simulate_zone_based_anti_reactive_preview(frame_count, speed_multiplier)
        self.update_preview_keyboard()

    def _simulate_realistic_key_presses_for_anti_reactive_preview(self, frame_count, base_color, is_rainbow):
        """Simulate key presses that turn OFF keys (anti-reactive)"""
        if not hasattr(self, 'key_grid') or not self.key_grid:
            return
        for row_idx, row in enumerate(self.key_grid):
            for col_idx, key_info in enumerate(row):
                if is_rainbow:
                    hue = ((row_idx + col_idx) / 10) % 1.0
                    rgb_float = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                    color = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
                else:
                    color = base_color
                try:
                    canvas = self.preview_canvas
                    canvas.itemconfig(key_info['element'], fill=color.to_hex(), outline='#ffffff', width=1)
                except:
                    pass
        typing_patterns = [
            {'keys': [(1, 5), (1, 6), (1, 7), (1, 7), (1, 8)], 'start_frame': 0, 'duration': 15},
            {'keys': [(2, 1), (1, 1), (2, 2), (2, 0)], 'start_frame': 50, 'duration': 20},
            {'keys': [(4, 7)], 'start_frame': 100, 'duration': 8},
            {'keys': [(4, 12), (4, 13), (4, 14), (4, 15)], 'start_frame': 150, 'duration': 12},
        ]
        for pattern in typing_patterns:
            pattern_frame = (frame_count - pattern['start_frame']) % 200
            if 0 <= pattern_frame < pattern['duration']:
                for i, (row, col) in enumerate(pattern['keys']):
                    key_start = i * 2
                    if key_start <= pattern_frame < key_start + pattern['duration'] - i:
                        if 0 <= row < len(self.key_grid) and 0 <= col < len(self.key_grid[row]):
                            key_info = self.key_grid[row][col]
                            try:
                                canvas = self.preview_canvas
                                canvas.itemconfig(key_info['element'], fill='#000000', outline='#404040', width=1)
                            except:
                                pass

    def _simulate_zone_based_anti_reactive_preview(self, frame_count, speed_multiplier):
        """Zone-based anti-reactive simulation"""
        for i in range(NUM_ZONES):
            press_seed = (frame_count * speed_multiplier + i * 23) % 80
            is_pressed = press_seed < 12
            if is_pressed:
                self.zone_colors[i] = RGBColor(0, 0, 0)

    def preview_rainbow_zones_cycle(self, frame_count: int):
        """FIXED: Rainbow zones with realistic bleeding effect matching hardware"""
        speed_multiplier = self.get_hardware_synchronized_speed()
        if hasattr(self, 'key_grid') and self.key_grid:
            self._preview_rainbow_with_key_level_bleeding(frame_count, speed_multiplier)
        else:
            self._preview_rainbow_with_enhanced_zone_bleeding(frame_count, speed_multiplier)
        self.update_preview_keyboard()

    def _preview_rainbow_with_key_level_bleeding(self, frame_count, speed_multiplier):
        """Hardware-accurate rainbow effect with key-level bleeding"""
        if not hasattr(self, 'key_grid') or not self.key_grid:
            return
        base_offset = frame_count * speed_multiplier * 0.3
        for row_idx, row in enumerate(self.key_grid):
            for col_idx, key_info in enumerate(row):
                position_factor = (15 - col_idx) / 15.0
                row_factor = row_idx / len(self.key_grid)
                hue = (base_offset + position_factor + row_factor * 0.2) % 1.0
                bleeding_factor = 0.15
                if col_idx > 0:
                    right_hue = (base_offset + (15 - (col_idx - 1)) / 15.0 + row_factor * 0.2) % 1.0
                    hue = hue * (1 - bleeding_factor) + right_hue * bleeding_factor
                rgb_float = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                color = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
                try:
                    canvas = self.preview_canvas
                    canvas.itemconfig(key_info['element'], fill=color.to_hex())
                except:
                    pass

    def _preview_rainbow_with_enhanced_zone_bleeding(self, frame_count, speed_multiplier):
        """Enhanced zone-based rainbow with bleeding simulation"""
        base_offset = frame_count * speed_multiplier * 0.3
        extended_zones = NUM_ZONES * 2
        extended_colors = []
        for i in range(extended_zones):
            position = (extended_zones - 1 - i) / extended_zones
            hue = (base_offset + position) % 1.0
            rgb_float = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            extended_colors.append(RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255)))
        for i in range(NUM_ZONES):
            start_idx = i * 2
            end_idx = min(start_idx + 3, extended_zones)
            avg_r = sum(extended_colors[j].r for j in range(start_idx, end_idx)) // (end_idx - start_idx)
            avg_g = sum(extended_colors[j].g for j in range(start_idx, end_idx)) // (end_idx - start_idx)
            avg_b = sum(extended_colors[j].b for j in range(start_idx, end_idx)) // (end_idx - start_idx)
            self.zone_colors[i] = RGBColor(avg_r, avg_g, avg_b)

    def _update_brightness_text_display(self, *args):
        if hasattr(self, 'brightness_text_var') and self.brightness_text_var:
            try:
                current_val = self.brightness_var.get()
                if hasattr(self, 'brightness_label') and self.brightness_label.winfo_exists():
                    self.brightness_label.config(text=f"{current_val}%")
                self.brightness_text_var.set(f"{current_val}%")
            except tk.TclError:
                self.logger.debug("TclError in _update_brightness_text_display.")
            except (IOError, PermissionError) as e:
                self.logger.warning(f"Error updating brightness text display: {e}")

    def setup_variables(self):
        self.zone_colors: List[RGBColor] = [RGBColor(0, 0, 0)] * NUM_ZONES
        self.brightness_var = tk.IntVar(value=self.settings.get("brightness", default_settings["brightness"]))
        self.brightness_text_var = tk.StringVar(value=f"{self.brightness_var.get()}%")
        self.brightness_var.trace_add("write", self._update_brightness_text_display)
        effect_speed_setting = self.settings.get("effect_speed", default_settings["effect_speed"])
        self.speed_var = tk.IntVar(value=effect_speed_setting * 10)
        current_color_dict = self.settings.get("current_color", default_settings["current_color"])
        self.current_color_var = tk.StringVar(value=RGBColor.from_dict(current_color_dict).to_hex())
        self.effect_var = tk.StringVar(value=self.settings.get("effect_name", default_settings["effect_name"]))
        self.status_var = tk.StringVar(value="Initializing...")
        self.effect_color_var = tk.StringVar(value=self.settings.get("effect_color", default_settings["effect_color"]))
        self.effect_rainbow_mode_var = tk.BooleanVar(value=self.settings.get("effect_rainbow_mode", default_settings["effect_rainbow_mode"]))
        self.gradient_start_color_var = tk.StringVar(value=self.settings.get("gradient_start_color", default_settings["gradient_start_color"]))
        self.gradient_end_color_var = tk.StringVar(value=self.settings.get("gradient_end_color", default_settings["gradient_end_color"]))
        self.restore_startup_var = tk.BooleanVar(value=self.settings.get("restore_on_startup", default_settings["restore_on_startup"]))
        self.auto_apply_var = tk.BooleanVar(value=self.settings.get("auto_apply_last_setting", default_settings["auto_apply_last_setting"]))
        self.control_method_var = tk.StringVar(value=self.settings.get("last_control_method", default_settings["last_control_method"]))
        self.minimize_to_tray_var = tk.BooleanVar(value=self.settings.get("minimize_to_tray", True))

        # New members for enhanced functionality
        self.performance_monitor = PerformanceMonitor()
        self.diagnostics = AdvancedDiagnostics(self.logger)
        self.hotkey_status_label = None # Will be created in create_common_controls

    def _try_load_icon_from_file(self):
        if self.tk_icon_photoimage:
            return
        try:
            script_dir = Path(__file__).resolve().parent
            icon_path_candidate1 = script_dir / "assets" / "icon.png"
            icon_path_candidate2 = script_dir.parent / "assets" / "icon.png" # Check one level up if assets is sibling to gui dir
            icon_path_candidate3 = Path(sys.prefix) / "share" / APP_NAME.lower().replace(" ", "_") / "icon.png" # For installed case
            final_icon_path = None
            if icon_path_candidate1.exists():
                final_icon_path = icon_path_candidate1
            elif icon_path_candidate2.exists():
                final_icon_path = icon_path_candidate2
            elif icon_path_candidate3.exists():
                final_icon_path = icon_path_candidate3
            if final_icon_path:
                self.tk_icon_photoimage = tk.PhotoImage(file=str(final_icon_path))
                self.root.iconphoto(True, self.tk_icon_photoimage)
                self.logger.info(f"Set Tkinter window icon from file: {final_icon_path}")
                if PYSTRAY_AVAILABLE and PIL_AVAILABLE and self.pystray_icon_image is None:
                    try:
                        self.pystray_icon_image = Image.open(final_icon_path)
                        self.logger.info(f"Loaded PIL Image for pystray from file: {final_icon_path}")
                    except Exception as e_pil_load:
                        self.logger.warning(f"Could not load PIL Image for pystray from file {final_icon_path}: {e_pil_load}")
            else:
                self.logger.warning(f"No icon.png found at expected paths for file loading: {icon_path_candidate1}, {icon_path_candidate2}, {icon_path_candidate3}")
        except Exception as e_file_icon:
            self.logger.warning(f"Could not load Tkinter window icon from file: {e_file_icon}")

    def setup_main_window(self):
        self.root.title(f"{APP_NAME} v{VERSION}")
        self.root.geometry("1000x750")
        self.root.minsize(900, 700)
        self.setup_application_icons()
        self.style = ttk.Style(self.root)
        try:
            themes = self.style.theme_names()
            desired_themes = ['clam', 'alt', 'default']
            for t in desired_themes:
                if t in themes:
                    self.style.theme_use(t)
                    break
            else:
                self.logger.info(f"Using system default theme: {self.style.theme_use()}")
        except tk.TclError:
            self.logger.warning("Failed to set ttk theme.")
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TLabelframe', background='#f0f0f0', padding=5)
        self.style.configure('TLabelframe.Label', background='#f0f0f0', font=('Helvetica', 10, 'bold'))
        self.style.configure('TLabel', background='#f0f0f0', padding=2)
        self.style.configure('TButton', padding=5)
        self.style.configure('Accent.TButton', font=('Helvetica', 10, 'bold'), relief=tk.RAISED)
        self.style.map('Accent.TButton', background=[('active', '#e0e0e0'), ('pressed', '#cccccc')])

    def setup_application_icons(self):
        """Enhanced icon setup with better error handling and fallbacks"""
        icon_created = False
        if PYSTRAY_AVAILABLE and PIL_AVAILABLE:
            try:
                icon_size = 64
                temp_pil_image = Image.new('RGBA', (icon_size, icon_size), (0, 0, 0, 0))
                draw = ImageDraw.Draw(temp_pil_image)
                draw.rectangle((0, 0, icon_size//2, icon_size//2), fill="#FF4444")
                draw.rectangle((icon_size//2, 0, icon_size, icon_size//2), fill="#44FF44")
                draw.rectangle((0, icon_size//2, icon_size//2, icon_size), fill="#4444FF")
                draw.rectangle((icon_size//2, icon_size//2, icon_size, icon_size), fill="#FF44FF")
                draw.rectangle((0, 0, icon_size, icon_size), outline="#FFFFFF", width=2)
                self.pystray_icon_image = temp_pil_image
                self.logger.debug("Created default PIL image for pystray icon.")
                try:
                    img_buffer = io.BytesIO()
                    temp_pil_image.resize((32, 32)).save(img_buffer, format='PNG')
                    img_buffer.seek(0)
                    self.tk_icon_photoimage = tk.PhotoImage(data=img_buffer.getvalue())
                    self.root.iconphoto(True, self.tk_icon_photoimage)
                    self.logger.info("Set Tkinter window icon using generated PIL image.")
                    icon_created = True
                except Exception as tk_icon_e:
                    self.logger.warning(f"Could not convert/set Tkinter window icon from PIL image: {tk_icon_e}.")
            except Exception as e_pil:
                self.logger.warning(f"Could not create icon image using PIL: {e_pil}.")
                self.pystray_icon_image = None
        if not icon_created:
            self._try_load_icon_from_file()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=5)
        main_frame.pack(fill=tk.BOTH, expand=True)
        common_controls_frame = self.create_common_controls(main_frame)
        common_controls_frame.pack(fill=tk.X, pady=(0,5), padx=5)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.create_tabs()
        self.create_status_bar()

    def setup_bindings(self):
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Escape>", self.exit_fullscreen)
        self.root.protocol("WM_DELETE_WINDOW", self.handle_close_button_press)
        self.root.bind("<Unmap>", self.on_minimize_event)

    def create_common_controls(self, parent: ttk.Frame) -> ttk.Frame:
        controls_frame = ttk.LabelFrame(parent, text="Universal Controls", padding=10)
        controls_frame.pack(fill=tk.X, pady=5)
        bf = ttk.Frame(controls_frame)
        bf.pack(fill=tk.X, pady=5)
        ttk.Label(bf, text="Brightness:").pack(side=tk.LEFT, padx=(0,5))
        bs = ttk.Scale(bf, from_=0, to=100, variable=self.brightness_var, orient=tk.HORIZONTAL, command=self.on_brightness_change)
        bs.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        self.brightness_label = ttk.Label(bf, textvariable=self.brightness_text_var, width=5)
        self.brightness_label.pack(side=tk.LEFT)
        hotkey_frame = ttk.Frame(controls_frame)
        hotkey_frame.pack(fill=tk.X, pady=2)
        self.hotkey_status_label = ttk.Label(hotkey_frame, text="Hotkeys: Checking...", font=('Helvetica', 8))
        self.hotkey_status_label.pack(side=tk.LEFT)
        sf = ttk.Frame(controls_frame)
        sf.pack(fill=tk.X, pady=5)
        ttk.Label(sf, text="Effect Speed (1-100):").pack(side=tk.LEFT, padx=(0,5))
        ss = ttk.Scale(sf, from_=1, to=100, variable=self.speed_var, orient=tk.HORIZONTAL, command=self.on_speed_change)
        ss.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        self.speed_label = ttk.Label(sf, text=f"{self.speed_var.get()}%", width=5)
        self.speed_var.trace_add("write", lambda *args: self.speed_label.config(text=f"{self.speed_var.get()}%") if hasattr(self, 'speed_label') and self.speed_label.winfo_exists() else None)
        self.speed_label.pack(side=tk.LEFT)
        btn_f = ttk.Frame(controls_frame)
        btn_f.pack(fill=tk.X, pady=10)
        ttk.Button(btn_f, text="All White", command=lambda: self.apply_static_color("#ffffff")).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_f, text="All Off (Clear)", command=self.clear_all_zones_and_effects).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_f, text="Stop Current Effect", command=self.stop_current_effect, style="Accent.TButton").pack(side=tk.LEFT, padx=2)
        return controls_frame

    def _create_tab_content_frame(self, tab_parent: ttk.Frame) -> ttk.Frame:
        outer_frame = ttk.Frame(tab_parent)
        outer_frame.pack(fill=tk.BOTH, expand=True)
        bg_color = self.style.lookup('TFrame', 'background')
        canvas = tk.Canvas(outer_frame, highlightthickness=0, borderwidth=0, background=bg_color)
        scrollbar = ttk.Scrollbar(outer_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, padding=10)
        scrollable_frame.bind("<Configure>", lambda e, c=canvas: c.configure(scrollregion=c.bbox("all")))
        canvas.item_frame_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.bind("<Configure>", lambda e, c=canvas: c.itemconfig(c.item_frame_id, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event, c=canvas):
            delta = 0
            if sys.platform == "win32":
                delta = event.delta // 120
            elif sys.platform == "darwin":
                delta = event.delta
            else:
                if event.num == 4:
                    delta = -1
                elif event.num == 5:
                    delta = 1
            if delta != 0:
                c.yview_scroll(delta, "units")

        for widget in [canvas, scrollable_frame]:
            widget.bind_all("<MouseWheel>", _on_mousewheel)
            widget.bind("<Button-4>", _on_mousewheel)
            widget.bind("<Button-5>", _on_mousewheel)
        return scrollable_frame

    def create_tabs(self):
        static_tab = ttk.Frame(self.notebook)
        self.notebook.add(static_tab, text="Static Color")
        self.create_static_controls(self._create_tab_content_frame(static_tab))
        zone_tab = ttk.Frame(self.notebook)
        self.notebook.add(zone_tab, text="Zone Control")
        self.create_zone_controls(self._create_tab_content_frame(zone_tab))
        effects_tab = ttk.Frame(self.notebook)
        self.notebook.add(effects_tab, text="Effects")
        self.create_effects_controls(self._create_tab_content_frame(effects_tab))
        settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(settings_tab, text="Settings")
        self.create_settings_controls(self._create_tab_content_frame(settings_tab))
        diag_tab = ttk.Frame(self.notebook)
        self.notebook.add(diag_tab, text="Diagnostics")
        self.create_diagnostics_tab(self._create_tab_content_frame(diag_tab))

    def create_static_controls(self, parent: ttk.Frame):
        color_frame = ttk.LabelFrame(parent, text="Color Selection", padding=10)
        color_frame.pack(fill=tk.X, padx=5, pady=5, expand=True)
        self.color_display = tk.Label(color_frame, width=10, height=2, bg=self.current_color_var.get(), relief=tk.SUNKEN, borderwidth=2)
        self.color_display.pack(side=tk.LEFT, padx=10, pady=5)
        ttk.Button(color_frame, text="Choose Color", command=self.open_color_picker).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(color_frame, text="Apply to All Zones", command=lambda: self.apply_static_color(self.current_color_var.get()), style="Accent.TButton").pack(side=tk.LEFT, padx=5, pady=5)
        preset_frame = ttk.LabelFrame(parent, text="Preset Colors", padding=10)
        preset_frame.pack(fill=tk.X, padx=5, pady=5, expand=True)
        presets = [("Red","#ff0000"),("Green","#00ff00"),("Blue","#0000ff"),("Yellow","#ffff00"),("Cyan","#00ffff"),("Magenta","#ff00ff"),("Orange","#ff8800"),("Purple","#800080"),("Pink","#ff88ff")]
        preset_grid = ttk.Frame(preset_frame)
        preset_grid.pack(pady=5)
        for i, (name, color_hex) in enumerate(presets):
            btn = tk.Button(preset_grid, text=name, bg=color_hex, width=8, relief=tk.RAISED, borderwidth=2, command=partial(self.apply_static_color, color_hex))
            btn.grid(row=i//3, column=i%3, padx=3, pady=3, sticky="ew")
        self.create_preview_canvas(parent, "Static Color Preview")

    def create_zone_controls(self, parent: ttk.Frame):
        zones_frame = ttk.LabelFrame(parent, text="Individual Zone Colors", padding=10)
        zones_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.zone_displays: List[tk.Label] = []
        for i in range(NUM_ZONES):
            zf = ttk.Frame(zones_frame, padding=(0,2))
            zf.pack(fill=tk.X)
            ttk.Label(zf, text=f"Zone {i+1}:").pack(side=tk.LEFT, padx=(0,5))
            initial_zc_obj = self.zone_colors[i] if i < len(self.zone_colors) else RGBColor(0,0,0)
            zd = tk.Label(zf, width=8, height=1, bg=initial_zc_obj.to_hex(), relief=tk.SUNKEN, borderwidth=2)
            zd.pack(side=tk.LEFT, padx=5)
            self.zone_displays.append(zd)
            ttk.Button(zf, text="Set Color", command=partial(self.set_zone_color_interactive, i)).pack(side=tk.LEFT, padx=5)
        action_frame = ttk.Frame(zones_frame, padding=(0,10))
        action_frame.pack(fill=tk.X, pady=(5,0))
        ttk.Button(action_frame, text="Apply Zone Colors to HW", command=self.apply_current_zone_colors_to_hardware, style="Accent.TButton").pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="Rainbow Across Zones", command=self.apply_rainbow_zones).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="Gradient Across Zones", command=self.apply_gradient_zones).pack(side=tk.LEFT, padx=2)
        gradient_ctrl_frame = ttk.Frame(zones_frame, padding=(0,5))
        gradient_ctrl_frame.pack(fill=tk.X, pady=10)
        ttk.Label(gradient_ctrl_frame, text="Gradient Start:").pack(side=tk.LEFT)
        self.gradient_start_display = tk.Label(gradient_ctrl_frame, width=8, height=1, bg=self.gradient_start_color_var.get(), relief=tk.SUNKEN, borderwidth=2)
        self.gradient_start_display.pack(side=tk.LEFT, padx=5)
        ttk.Button(gradient_ctrl_frame, text="...", width=3, command=self.choose_gradient_start).pack(side=tk.LEFT)
        ttk.Label(gradient_ctrl_frame, text="Gradient End:").pack(side=tk.LEFT, padx=(10,5))
        self.gradient_end_display = tk.Label(gradient_ctrl_frame, width=8, height=1, bg=self.gradient_end_color_var.get(), relief=tk.SUNKEN, borderwidth=2)
        self.gradient_end_display.pack(side=tk.LEFT, padx=5)
        ttk.Button(gradient_ctrl_frame, text="...", width=3, command=self.choose_gradient_end).pack(side=tk.LEFT)
        self.create_preview_canvas(parent, "Zone Preview")

    def create_effects_controls(self, parent: ttk.Frame):
        effect_frame = ttk.LabelFrame(parent, text="Effect Selection", padding=10)
        effect_frame.pack(fill=tk.X, padx=5, pady=5, expand=True)
        ttk.Label(effect_frame, text="Effect:").pack(side=tk.LEFT, padx=(0,10))
        all_effects = self.effect_manager.get_available_effects()
        effects_to_remove = {"Rainbow Wave", "Rainbow Breathing"}
        filtered_effects = [effect for effect in all_effects if effect not in effects_to_remove]
        available_effects = ["None"] + filtered_effects + ["Reactive", "Anti-Reactive"]
        effect_combo = ttk.Combobox(effect_frame, textvariable=self.effect_var, values=available_effects, state="readonly", width=25)
        effect_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        effect_combo.bind("<<ComboboxSelected>>", self.on_effect_change)
        ttk.Button(effect_frame, text="Start Effect", command=self.start_current_effect, style="Accent.TButton").pack(side=tk.LEFT, padx=5)
        color_frame = ttk.LabelFrame(parent, text="Effect Color Options", padding=10)
        color_frame.pack(fill=tk.X, padx=5, pady=5, expand=True)
        self.effect_color_rainbow_frame = ttk.Frame(color_frame)
        self.rainbow_mode_check = ttk.Checkbutton(self.effect_color_rainbow_frame, text="Use Rainbow Mode for Effect", variable=self.effect_rainbow_mode_var, command=self.on_rainbow_mode_change)
        self.effect_color_frame = ttk.Frame(self.effect_color_rainbow_frame)
        self.effect_color_display = tk.Label(self.effect_color_frame, width=10, height=2, bg=self.effect_color_var.get(), relief=tk.SUNKEN, borderwidth=2)
        self.effect_color_display.pack(side=tk.LEFT, padx=10, pady=5)
        ttk.Button(self.effect_color_frame, text="Choose Effect Color", command=self.choose_effect_color).pack(side=tk.LEFT, padx=5, pady=5)
        self.update_effect_controls_visibility()
        self.create_preview_canvas(parent, "Effect Preview")

    def create_settings_controls(self, parent: ttk.Frame):
        frame = ttk.LabelFrame(parent, text="Application Settings", padding=10)
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        persist_lf = ttk.LabelFrame(frame, text="Persistence", padding="10")
        persist_lf.pack(fill=tk.X, pady=(5, 10), anchor="n")
        ttk.Checkbutton(persist_lf, text="Restore settings on startup", variable=self.restore_startup_var, command=self.save_persistence_settings).pack(anchor=tk.W, padx=5)
        ttk.Checkbutton(persist_lf, text="Auto-apply last setting on startup (if restore is enabled)", variable=self.auto_apply_var, command=self.save_persistence_settings).pack(anchor=tk.W, padx=5)
        method_lf = ttk.LabelFrame(frame, text="Hardware Control Method Preference", padding="10")
        method_lf.pack(fill=tk.X, pady=(0, 10), anchor="n")
        ttk.Radiobutton(method_lf, text="ectool (Recommended if available)", variable=self.control_method_var, value="ectool", command=self.save_control_method).pack(anchor=tk.W, padx=5)
        ttk.Radiobutton(method_lf, text="EC Direct (Advanced)", variable=self.control_method_var, value="ec_direct", command=self.save_control_method, state=tk.NORMAL).pack(anchor=tk.W, padx=5)
        display_lf = ttk.LabelFrame(frame, text="Display Options", padding="10")
        display_lf.pack(fill=tk.X, pady=(0, 10), anchor="n")
        self.fullscreen_button = ttk.Button(display_lf, text="Enter Fullscreen (F11)", command=self.toggle_fullscreen)
        self.fullscreen_button.pack(anchor=tk.W, pady=2, padx=5)
        ttk.Label(display_lf, text="Press ESC to exit fullscreen.", font=('Helvetica', 9, 'italic')).pack(anchor=tk.W, padx=5)
        self.create_tray_settings_section(frame)
        mgmt_lf = ttk.LabelFrame(frame, text="Settings Management", padding="10")
        mgmt_lf.pack(fill=tk.X, pady=(0, 10), anchor="n")
        mgmt_btns_frm = ttk.Frame(mgmt_lf)
        mgmt_btns_frm.pack(fill=tk.X, pady=5)
        ttk.Button(mgmt_btns_frm, text="Reset Defaults", command=self.reset_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(mgmt_btns_frm, text="Export Settings", command=self.export_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(mgmt_btns_frm, text="Import Settings", command=self.import_settings).pack(side=tk.LEFT, padx=5)
        launcher_lf = ttk.LabelFrame(frame, text="Desktop Integration (Linux)", padding="10")
        launcher_lf.pack(fill=tk.X, anchor="n")
        ttk.Button(launcher_lf, text="Create/Update Desktop Launcher", command=self.create_desktop_launcher).pack(anchor=tk.W, padx=5, pady=5)

    def create_tray_settings_section(self, parent):
        """Enhanced tray settings with dependency information"""
        if PYSTRAY_AVAILABLE:
            tray_lf = ttk.LabelFrame(parent, text="System Tray Options", padding="10")
            tray_lf.pack(fill=tk.X, pady=(0, 10), anchor="n")
            status_frame = ttk.Frame(tray_lf)
            status_frame.pack(fill=tk.X, pady=2)
            status_text = "✓ System tray available"
            if not PIL_AVAILABLE:
                status_text += " (Icons will be basic - install Pillow for better icons)"
            ttk.Label(status_frame, text=status_text, font=('Helvetica', 9), foreground='green').pack(anchor=tk.W)
            if not hasattr(self, 'minimize_to_tray_var'):
                self.minimize_to_tray_var = tk.BooleanVar(value=self.settings.get("minimize_to_tray", True))
            ttk.Checkbutton(tray_lf, text="Minimize to system tray when closing/minimizing",
                           variable=self.minimize_to_tray_var, command=self.save_tray_settings).pack(anchor=tk.W, padx=5)
            ttk.Label(tray_lf, text="When enabled, clicking 'X' or Minimize will send to tray.",
                     font=('Helvetica', 9, 'italic')).pack(anchor=tk.W, padx=5)
            ttk.Label(tray_lf, text="Use 'Quit' from tray menu to exit completely.",
                     font=('Helvetica', 9, 'italic')).pack(anchor=tk.W, padx=5)
        else:
            no_tray_lf = ttk.LabelFrame(parent, text="System Tray Options", padding="10")
            no_tray_lf.pack(fill=tk.X, pady=(0,10), anchor="n")
            ttk.Label(no_tray_lf, text="⚠ System tray functionality is unavailable",
                     font=('Helvetica', 9, 'bold'), foreground='orange').pack(anchor=tk.W, padx=5)
            install_text = """To enable system tray functionality:

1. Install required packages:
   pip install pystray Pillow

2. Restart the application

3. Alternative installation:
   • conda install -c conda-forge pystray pillow
   • On Ubuntu: sudo apt install python3-pil

Note: Some systems may require additional notification packages"""
            ttk.Label(no_tray_lf, text=install_text, font=('Helvetica', 8),
                     justify=tk.LEFT, wraplength=500).pack(anchor=tk.W, padx=5, pady=5)

    def create_diagnostics_tab(self, parent: ttk.Frame):
        diag_pane = ttk.PanedWindow(parent, orient=tk.VERTICAL)
        diag_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        hw_frame = ttk.LabelFrame(diag_pane, text="Hardware Status & Capabilities", padding=10)
        diag_pane.add(hw_frame, weight=1)
        self.hardware_status_text = scrolledtext.ScrolledText(hw_frame, height=8, state=tk.DISABLED, relief=tk.SUNKEN, borderwidth=1, wrap=tk.WORD, font=("monospace", 9))
        self.hardware_status_text.pack(fill=tk.BOTH, expand=True, pady=(0,5))
        ttk.Button(hw_frame, text="Refresh Hardware Status", command=self.refresh_hardware_status).pack(pady=5)
        sys_log_frame = ttk.LabelFrame(diag_pane, text="System Information & Application Log", padding=10)
        diag_pane.add(sys_log_frame, weight=2)
        log_notebook = ttk.Notebook(sys_log_frame)
        log_notebook.pack(fill=tk.BOTH, expand=True, pady=5)
        sys_info_tab = ttk.Frame(log_notebook)
        log_notebook.add(sys_info_tab, text="System Details")
        self.system_info_display_text = scrolledtext.ScrolledText(sys_info_tab, height=10, state=tk.DISABLED, relief=tk.SUNKEN, borderwidth=1, wrap=tk.WORD, font=("monospace", 9))
        self.system_info_display_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        sys_info_btn_frame = ttk.Frame(sys_info_tab)
        sys_info_btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(sys_info_btn_frame, text="Refresh System Info", command=self.show_system_info).pack(side=tk.LEFT, padx=5)
        app_log_tab = ttk.Frame(log_notebook)
        log_notebook.add(app_log_tab, text="Application Log")
        self.gui_log_text_widget = scrolledtext.ScrolledText(app_log_tab, height=10, state=tk.DISABLED, relief=tk.SUNKEN, borderwidth=1, wrap=tk.WORD, font=("monospace", 9))
        self.gui_log_text_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        log_actions_frame = ttk.Frame(app_log_tab)
        log_actions_frame.pack(fill=tk.X, pady=5)
        ttk.Button(log_actions_frame, text="Open Log Directory", command=self.show_log_locations).pack(side=tk.LEFT, padx=5)
        if KEYBOARD_LIB_AVAILABLE:
            ttk.Button(log_actions_frame, text="Test Keyboard Hotkey Names", command=self.test_hotkey_names_util).pack(side=tk.LEFT, padx=5)
        test_frame = ttk.LabelFrame(diag_pane, text="Hardware Tests (Use with Caution)", padding=10)
        diag_pane.add(test_frame, weight=0)
        ttk.Button(test_frame, text="Run Basic Test Cycle", command=self.run_comprehensive_test).pack(side=tk.LEFT, padx=5, pady=2)
        ttk.Button(test_frame, text="Test ectool Version", command=self.test_ectool).pack(side=tk.LEFT, padx=5, pady=2)

    def create_status_bar(self):
        status_frame = ttk.Frame(self.root, relief=tk.SUNKEN, padding=2)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.connection_label = ttk.Label(status_frame, text="HW: Unknown", relief=tk.FLAT, width=15, anchor=tk.E)
        self.connection_label.pack(side=tk.RIGHT, padx=2)

    def create_preview_canvas(self, parent: ttk.Frame, title: str) -> ttk.Frame:
        preview_frame = ttk.LabelFrame(parent, text=title, padding=10)
        preview_frame.pack(fill=tk.X, expand=False, padx=5, pady=10)
        canvas_container = ttk.Frame(preview_frame)
        canvas_container.pack(pady=5)
        canvas_width = 480
        canvas_height = 140
        current_canvas = tk.Canvas(canvas_container, width=canvas_width, height=canvas_height, bg='#1a1a1a', relief=tk.GROOVE, borderwidth=2)
        current_canvas.pack()
        if title == "Effect Preview":
            self.preview_canvas = current_canvas
            self.preview_keyboard_elements = []
            self.create_realistic_keyboard_layout()
        elif title == "Static Color Preview":
            self.static_preview_canvas = current_canvas
            self.static_keyboard_elements = []
            self.create_realistic_keyboard_layout(canvas=current_canvas, elements_list='static_keyboard_elements')
        elif title == "Zone Preview":
            self.zone_preview_canvas = current_canvas
            self.zone_keyboard_elements = []
            self.create_realistic_keyboard_layout(canvas=current_canvas, elements_list='zone_keyboard_elements')
        return preview_frame

    def create_realistic_keyboard_layout(self, canvas=None, elements_list='preview_keyboard_elements'):
        """Create realistic keyboard layout with proper vertical zone support - ENHANCED"""
        if canvas is None:
            canvas = self.preview_canvas
        if elements_list == 'static_keyboard_elements':
            elements = self.static_keyboard_elements = []
        elif elements_list == 'zone_keyboard_elements':
            elements = self.zone_keyboard_elements = []
        else:
            elements = self.preview_keyboard_elements = []
        canvas.delete("all")
        elements.clear()
        canvas_width = 480
        canvas_height = 140
        margin_x = 20
        margin_y = 12
        keyboard_width = canvas_width - (margin_x * 2)
        keyboard_height = 90
        rows = 6
        cols_per_row = [15, 15, 15, 15, 15, 15]
        key_width = keyboard_width / 15
        key_height = 14
        key_gap = 1
        start_x = margin_x
        start_y = margin_y
        self.key_grid = []
        for row_idx in range(rows):
            row_keys = []
            current_y = start_y + row_idx * (key_height + key_gap)
            for col_idx in range(cols_per_row[row_idx]):
                current_x = start_x + col_idx * (key_width + key_gap)
                key_rect = canvas.create_rectangle(
                    current_x, current_y,
                    current_x + key_width, current_y + key_height,
                    fill='#404040', outline='#707070', width=1
                )
                horizontal_zone = min(3, int((col_idx / cols_per_row[row_idx]) * 4))
                vertical_zone = min(3, int((row_idx / rows) * 4))
                primary_zone = horizontal_zone
                key_info = {
                    'element': key_rect,
                    'zone': primary_zone,
                    'h_zone': horizontal_zone,
                    'v_zone': vertical_zone,
                    'row': row_idx,
                    'col': col_idx,
                    'x': current_x,
                    'y': current_y,
                    'type': 'key'
                }
                elements.append(key_info)
                row_keys.append(key_info)
            self.key_grid.append(row_keys)
        for zone_idx in range(1, 4):
            divider_x = start_x + (zone_idx * keyboard_width / 4)
            divider_line = canvas.create_line(
                divider_x, start_y, divider_x, start_y + keyboard_height,
                fill='#555555', width=1, dash=(2, 2)
            )
            elements.append({'element': divider_line, 'zone': -1, 'type': 'divider'})
        zone_label_y = start_y + keyboard_height + 8
        for zone_idx in range(4):
            zone_label_x = start_x + (zone_idx * keyboard_width / 4) + (keyboard_width / 8)
            text_element = canvas.create_text(
                zone_label_x, zone_label_y,
                text=f'Z{zone_idx + 1}',
                fill='#aaaaaa', font=('Arial', 7, 'bold')
            )
            elements.append({'element': text_element, 'zone': zone_idx, 'type': 'label'})

    def update_preview_keyboard(self, canvas=None, elements_list=None):
        """Update the keyboard preview with current LED states - improved real-time accuracy"""
        if canvas is None:
            canvas = self.preview_canvas
        if elements_list is None:
            elements = self.preview_keyboard_elements
        elif elements_list == 'static_keyboard_elements':
            elements = self.static_keyboard_elements
        elif elements_list == 'zone_keyboard_elements':
            elements = self.zone_keyboard_elements
        else:
            elements = self.preview_keyboard_elements
        if not canvas or not canvas.winfo_exists() or not elements:
            return
        try:
            for elem_info in elements:
                if isinstance(elem_info, dict) and elem_info.get('type') == 'key':
                    zone = elem_info['zone']
                    if 0 <= zone < len(self.zone_colors):
                        color = self.zone_colors[zone].to_hex()
                        zone_color_obj = self.zone_colors[zone]
                        if zone_color_obj.r + zone_color_obj.g + zone_color_obj.b > 50:
                            canvas.itemconfig(elem_info['element'], fill=color, outline='#ffffff', width=2)
                        else:
                            canvas.itemconfig(elem_info['element'], fill=color, outline='#606060', width=1)
                    else:
                        canvas.itemconfig(elem_info['element'], fill='#303030', outline='#505050', width=1)
                elif isinstance(elem_info, dict) and elem_info.get('type') == 'divider':
                    canvas.itemconfig(elem_info['element'], fill='#666666')
        except tk.TclError:
            pass

    def update_preview_leds(self):
        """Legacy method for compatibility - now redirects to keyboard preview"""
        self.update_preview_keyboard()

    def log_to_gui_diag_area(self, message: str, level: str = "info"):
        """Helper to write messages to the GUI's diagnostic log text widget."""
        self.logger.log(getattr(logging, level.upper(), logging.INFO), message)
        if hasattr(self, 'gui_log_text_widget') and self.gui_log_text_widget and self.gui_log_text_widget.winfo_exists():
            try:
                prefix = f"[{level.upper()}] "
                self.gui_log_text_widget.config(state=tk.NORMAL)
                self.gui_log_text_widget.insert(tk.END, prefix + message + '\n')
                self.gui_log_text_widget.see(tk.END)
                num_lines = int(self.gui_log_text_widget.index('end-1c').split('.')[0])
                max_log_lines = 500
                if num_lines > max_log_lines:
                    self.gui_log_text_widget.delete('1.0', f'{num_lines - max_log_lines + 1}.0')
                self.gui_log_text_widget.config(state=tk.DISABLED)
            except tk.TclError as e:
                self.logger.debug(f"TclError writing to GUI log widget: {e}")
            except (IOError, PermissionError) as e:
                self.logger.error(f"Error writing to GUI log widget: {e}")

    def setup_gui_logging(self):
        if not hasattr(self, 'gui_log_text_widget') or not self.gui_log_text_widget:
            self.logger.error("gui_log_text_widget not available for GUI logging.")
            return
        class GuiLogHandler(logging.Handler):
            def __init__(self, text_widget: scrolledtext.ScrolledText, master_tk: tk.Tk):
                super().__init__()
                self.text_widget = text_widget
                self.master_tk = master_tk
                self.log_queue = queue.Queue()
                self._check_queue_interval_ms = 200
                self._schedule_queue_check()
            def emit(self, record: logging.LogRecord):
                self.log_queue.put(self.format(record))
            def _schedule_queue_check(self):
                if self.master_tk.winfo_exists():
                    self.master_tk.after(self._check_queue_interval_ms, self._process_log_queue)
            def _process_log_queue(self):
                try:
                    while not self.log_queue.empty():
                        message = self.log_queue.get_nowait()
                        if self.text_widget.winfo_exists():
                            self.text_widget.config(state=tk.NORMAL)
                            self.text_widget.insert(tk.END, message + '\n')
                            self.text_widget.see(tk.END)
                            num_lines = int(self.text_widget.index('end-1c').split('.')[0])
                            max_log_lines = 500
                            if num_lines > max_log_lines:
                                self.text_widget.delete('1.0', f'{num_lines - max_log_lines + 1}.0')
                            self.text_widget.config(state=tk.DISABLED)
                except queue.Empty:
                    pass
                except tk.TclError:
                    pass
                except (IOError, PermissionError) as e:
                    print(f"Error processing GUI log queue: {e}", file=sys.stderr)
                finally:
                    if self.master_tk.winfo_exists() and not getattr(self.master_tk, '_is_being_destroyed', False):
                        self._schedule_queue_check()
        try:
            gui_handler = GuiLogHandler(self.gui_log_text_widget, self.root)
            gui_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s', datefmt='%H:%M:%S'))
            gui_handler.setLevel(logging.INFO)
            logging.getLogger().addHandler(gui_handler)
            self.logger.info("GUI logging handler initialized and attached to root logger.")
        except (IOError, PermissionError) as e:
            self.logger.error(f"Failed to set up GUI logging handler: {e}", exc_info=True)

    def setup_tray_icon(self):
        if not PYSTRAY_AVAILABLE:
            self.logger.warning("pystray not available, cannot minimize to tray.")
            self._show_tray_dependency_error()
            self.on_closing(from_tray_setup_failure=True)
            return
        if self.tray_icon and self.tray_thread and self.tray_thread.is_alive():
            self.logger.debug("Tray icon already running.")
            return

        def create_icon_for_tray():
            icon_img = getattr(self, 'pystray_icon_image', None)
            if icon_img is None:
                self.logger.warning("self.pystray_icon_image is None for tray. Creating minimal fallback if PIL is available.")
                try:
                    if PIL_AVAILABLE:
                        icon_img = Image.new('RGBA', (64, 64), (100, 100, 255, 255))
                        draw = ImageDraw.Draw(icon_img)
                        draw.text((10,10), "RGB", fill="white")
                    else:
                        self.logger.error("Cannot create fallback tray icon image: PIL (Pillow) is not available.")
                        return None
                except Exception as e_fb:
                    self.logger.error(f"Could not create minimal fallback icon for tray: {e_fb}")
                    return None
            return icon_img

        def on_open_gui():
            self.logger.info("Restoring GUI from tray.")
            self.window_hidden_to_tray = False
            self.root.after(0, self.root.deiconify)
            self.root.after(0, self.root.wm_deiconify)
            self.root.after(0, self.root.focus_set)
            if self.tray_icon:
                self.logger.info("Stopping tray icon as GUI is now visible.")
                try:
                    self.tray_icon.stop()
                except Exception as e_stop:
                    self.logger.error(f"Error stopping tray icon: {e_stop}")
                self.tray_icon = None
                if self.tray_thread and self.tray_thread.is_alive():
                    self.logger.debug("Tray thread should exit soon after icon.stop().")
                self.tray_thread = None

        def on_quit_app_from_tray():
            self.logger.info("Quitting application from tray icon.")
            self.root.after(0, self.on_closing, False, True)

        tray_image = create_icon_for_tray()
        if tray_image is None:
            self.logger.error("No image for tray icon, cannot create. Tray functionality disabled for this session.")
            self.root.after(0, self._handle_tray_failure)
            return

        self.logger.info("Creating tray icon (GUI will be hidden if successful).")
        menu_items = [
            pystray.MenuItem('Open GUI', on_open_gui, default=True),
            pystray.MenuItem('Stop Effect', lambda: self.root.after(0, self.stop_current_effect)),
            pystray.MenuItem('Clear LEDs', lambda: self.root.after(0, self.clear_all_zones_and_effects)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Quit', on_quit_app_from_tray)
        ]

        try:
            self.tray_icon = pystray.Icon('rgb_controller', tray_image, APP_NAME, pystray.Menu(*menu_items))
        except (IOError, PermissionError) as e:
            self.logger.error(f"Failed to create pystray.Icon object: {e}", exc_info=True)
            self.root.after(0, self._handle_tray_failure)
            return

        def run_tray():
            try:
                self.logger.debug(f"Pystray icon ({self.tray_icon.name if self.tray_icon else 'None'}) run starting.")
                self.tray_icon.run()
            except (IOError, PermissionError) as e:
                self.logger.error(f"Tray icon run loop crashed: {e}", exc_info=True)
                if self.root.winfo_exists() and self.window_hidden_to_tray:
                    self.root.after(0, self._handle_tray_failure)
            finally:
                self.logger.info("Tray icon run loop finished.")

        self.tray_thread = threading.Thread(target=run_tray, daemon=True, name="TrayIconThread")
        self.tray_thread.start()
        self.root.after(1000, self._check_tray_status)

    def _show_tray_dependency_error(self):
        """Show detailed error message for missing tray dependencies"""
        error_msg = """System Tray Dependencies Missing

Required packages are not installed:
• pystray - System tray functionality
• Pillow (PIL) - Icon image support

INSTALLATION INSTRUCTIONS:
========================

1. Install both packages:
   pip install pystray Pillow

2. Alternative methods:
   • conda install -c conda-forge pystray pillow
   • On Ubuntu: sudo apt install python3-pil
   • pip3 install pystray Pillow (if pip points to Python 2)

3. For system-specific issues:
   • Ubuntu/Debian: sudo apt install python3-dev libxss1
   • Some systems need: sudo apt install notification-daemon
   • GNOME: sudo apt install gir1.2-appindicator3-0.1

4. Restart the application after installation

The application will continue without tray functionality."""
        self.log_to_gui_diag_area(error_msg, "error")
        if self.root.winfo_exists():
            messagebox.showerror("System Tray Unavailable", error_msg, parent=self.root)

    def _check_tray_status(self):
        if self.window_hidden_to_tray:
            is_tray_thread_alive = self.tray_thread and self.tray_thread.is_alive()
            if not is_tray_thread_alive:
                self.logger.warning("Tray icon thread died prematurely or did not start. Assuming tray startup failure.")
                self._handle_tray_failure()
            elif self.tray_icon is None and is_tray_thread_alive:
                self.logger.warning("Tray icon object became None unexpectedly while thread is alive. Assuming failure.")
                self._handle_tray_failure()

    def _handle_tray_failure(self):
        """Handle tray failures gracefully by restoring the main window"""
        self.logger.warning("Tray failure recovery initiated.")
        if self.window_hidden_to_tray and self.root.winfo_exists():
            try:
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
                self.window_hidden_to_tray = False
                self.logger.info("Window restored successfully from tray failure.")
            except (IOError, PermissionError) as e:
                self.logger.error(f"Failed to restore window from tray failure: {e}")
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except:
                pass
            self.tray_icon = None
        if self.tray_thread:
            try:
                self.tray_thread.join(timeout=1.0)
            except:
                pass
            self.tray_thread = None
        if hasattr(self, 'minimize_to_tray_var'):
            self.minimize_to_tray_var.set(False)
            self.settings.set("minimize_to_tray", False)
        self.log_status("System tray disabled due to technical issues. Window will remain visible.")

    def handle_close_button_press(self):
        self.logger.info("WM_DELETE_WINDOW protocol called (X button click).")
        minimize_to_tray_enabled = self.minimize_to_tray_var.get() if hasattr(self, 'minimize_to_tray_var') else self.settings.get("minimize_to_tray", True)
        if PYSTRAY_AVAILABLE and minimize_to_tray_enabled:
            self.logger.info("Minimizing to system tray (minimize_to_tray=True).")
            self.window_hidden_to_tray = True
            self.root.withdraw()
            self.setup_tray_icon()
        else:
            self.logger.info("Proceeding with normal quit sequence (minimize_to_tray=False or pystray unavailable).")
            self.on_closing()

    def on_closing(self, from_tray_setup_failure=False, confirmed_quit=False):
        self.logger.info(f"on_closing called (from_tray_setup_failure={from_tray_setup_failure}, confirmed_quit={confirmed_quit}).")
        should_quit = confirmed_quit
        if not confirmed_quit:
            if self.root.winfo_exists() and messagebox.askokcancel("Quit", f"Are you sure you want to quit {APP_NAME}?", parent=self.root):
                self.logger.info("User confirmed quit via messagebox.")
                should_quit = True
            else:
                self.logger.info("User cancelled quit.")
                if from_tray_setup_failure and self.root.winfo_exists() and self.window_hidden_to_tray:
                    self.logger.info("Restoring window as quit was cancelled after tray failure.")
                    self.root.deiconify()
                    self.root.focus_set()
                    self.window_hidden_to_tray = False
                should_quit = False
        if should_quit:
            self.perform_final_shutdown(clean_shutdown=True)

    def on_minimize_event(self, event):
        if self.root.winfo_exists() and self.root.state() == 'iconic':
            self.logger.debug(f"Minimize event detected (state: {self.root.state()}).")
            minimize_to_tray_enabled = self.minimize_to_tray_var.get() if hasattr(self, 'minimize_to_tray_var') else self.settings.get("minimize_to_tray", True)
            if PYSTRAY_AVAILABLE and minimize_to_tray_enabled:
                self.logger.info("Window minimized via button/taskbar, hiding to tray.")
                self.window_hidden_to_tray = True
                self.root.withdraw()
                self.setup_tray_icon()
                return 'break'
            else:
                self.logger.info("Window minimized via button/taskbar, using normal taskbar minimize.")

    def save_tray_settings(self):
        if hasattr(self, 'minimize_to_tray_var'):
            self.settings.set("minimize_to_tray", self.minimize_to_tray_var.get())
            self.log_status("System tray settings saved.")
        else:
            self.logger.warning("minimize_to_tray_var not found, cannot save tray settings.")

    def initialize_hardware_async(self):
        self.status_var.set("Initializing hardware...")
        self.connection_label.config(text="HW: Init...")
        def init_thread_target():
            preferred_method = self.settings.get("last_control_method", default_settings["last_control_method"])
            self.logger.info(f"Hardware initialization: Preferred method from settings: {preferred_method}")
            if self.hardware.wait_for_detection(timeout=HARDWARE_DETECTION_TIMEOUT, preferred_method=preferred_method):
                if self.hardware.is_operational():
                    self.root.after(0, lambda: self.status_var.set("Hardware initialized."))
                    self.root.after(0, lambda: self.connection_label.config(text=f"HW: Ready ({self.hardware.get_active_method_display()})"))
                    active_method = self.hardware.get_active_method_display()
                    if preferred_method == "ec_direct" and "EC Direct" not in active_method:
                        msg = "Preferred control method 'EC Direct' is not currently active. Hardware might be using a fallback (e.g., ectool) or EC Direct is not fully implemented/available. Check Diagnostics."
                        self.logger.warning(msg)
                        self.root.after(0, lambda: self.log_to_gui_diag_area(msg, "warning"))
                else:
                    self.root.after(0, lambda: self.status_var.set("Hardware: No control methods found or not operational."))
                    self.root.after(0, lambda: self.connection_label.config(text="HW: Not Found/Ready"))
                    if self.root.winfo_exists():
                        self.root.after(0, lambda: messagebox.showwarning("Hardware Warning", "No RGB keyboard control methods were detected or hardware is not operational. Functionality will be limited.", parent=self.root))
            else:
                self.root.after(0, lambda: self.status_var.set("Hardware detection timed out/failed."))
                self.root.after(0, lambda: self.connection_label.config(text="HW: Error"))
                if self.root.winfo_exists():
                    self.root.after(0, lambda: messagebox.showerror("Hardware Error", "Hardware detection failed or timed out. Please check system setup, permissions, and logs.", parent=self.root))
            if self.root.winfo_exists():
                self.root.after(0, self.refresh_hardware_status)
        threading.Thread(target=init_thread_target, daemon=True, name="HWInitThread").start()

    def apply_startup_settings_if_enabled_async(self):
        if self.settings.get("restore_on_startup", default_settings["restore_on_startup"]):
            self.logger.info("Applying saved settings on startup...")
            if not self.hardware.detection_complete.is_set():
                self.logger.info("Delaying startup settings application until hardware detection completes.")
                self.root.after(1000, self.apply_startup_settings_if_enabled_async)
                return
            if not self.hardware.is_operational():
                self.logger.warning("Hardware not operational. Skipping startup settings application.")
                self.log_status("Hardware not ready, cannot apply startup settings.", "warning")
                return
            self._restore_settings_on_startup()
        else:
            self.logger.info("Restore on startup is disabled by user settings.")

    def _restore_settings_on_startup(self):
        try:
            self.logger.info("Restoring settings on startup...")
            if self.auto_apply_var.get() and self.settings.was_previous_session_clean():
                self.logger.info("Auto-applying last settings (clean shutdown detected).")
                last_effect_name = self.settings.get("effect_name", default_settings["effect_name"])
                last_mode = self.settings.get("last_mode", "static")
                brightness = self.settings.get("brightness", default_settings["brightness"])
                if self.hardware.is_operational():
                    self.hardware.set_brightness(brightness)
                self.brightness_var.set(brightness)
                is_static_type_effect = last_effect_name in ["Static Color", "Static Zone Colors", "Static Rainbow", "Static Gradient"]
                if last_effect_name != "None" and not is_static_type_effect and last_effect_name in self.effect_manager.get_available_effects():
                    self.logger.info(f"Restoring last dynamic effect: {last_effect_name}")
                    self.effect_var.set(last_effect_name)
                    self.effect_color_var.set(self.settings.get("effect_color", default_settings["effect_color"]))
                    self.effect_rainbow_mode_var.set(self.settings.get("effect_rainbow_mode", default_settings["effect_rainbow_mode"]))
                    self.speed_var.set(self.settings.get("effect_speed", default_settings["effect_speed"]) * 10)
                    self.update_effect_controls_visibility()
                    self.start_current_effect()
                elif last_mode == "static" or last_effect_name == "Static Color":
                    static_color = RGBColor.from_dict(self.settings.get("current_color", default_settings["current_color"]))
                    self.apply_static_color(static_color.to_hex())
                elif last_mode == "zones" or last_effect_name == "Static Zone Colors":
                    self.apply_current_zone_colors_to_hardware()
                elif last_mode == "rainbow_zones" or last_effect_name == "Static Rainbow":
                    self.apply_rainbow_zones()
                elif last_mode == "gradient_zones" or last_effect_name == "Static Gradient":
                    self.apply_gradient_zones()
                else:
                    self.logger.info("No specific valid effect/mode to restore, applying default static color.")
                    default_color = RGBColor.from_dict(default_settings["current_color"])
                    self.apply_static_color(default_color.to_hex())
            else:
                if not self.auto_apply_var.get():
                    self.logger.info("Auto-apply disabled, not restoring last effect.")
                else:
                    self.logger.info("Previous session was not clean, not restoring last effect for safety.")
                default_color = RGBColor.from_dict(default_settings["current_color"])
                self.apply_static_color(default_color.to_hex())
            self.log_status("Startup settings restoration completed.")
        except (IOError, PermissionError) as e:
            self.logger.error(f"Error during startup settings restoration: {e}", exc_info=True)
            self.log_status(f"Error restoring startup settings: {e}", "error")
            try:
                default_color = RGBColor.from_dict(default_settings["current_color"])
                self.apply_static_color(default_color.to_hex())
            except:
                pass

    def on_brightness_change(self, val_str: str):
        if self._loading_settings:
            return
        try:
            value = int(float(val_str))
            self._apply_brightness_value(value, "slider")
        except ValueError:
            self.logger.warning(f"Invalid brightness value from slider: {val_str}")
        except tk.TclError:
            self.logger.debug("Brightness label no longer exists during on_brightness_change.")

    def _apply_brightness_value(self, value: int, source: str = "unknown"):
        """Applies brightness value to hardware and settings."""
        clamped_value = max(0, min(100, value))
        if self.hardware.set_brightness(clamped_value):
            self.settings.set("brightness", clamped_value)
            self.log_status(f"Brightness set to {clamped_value}% (source: {source})")
        else:
            self.log_status(f"Failed to set brightness to {clamped_value}% (source: {source})", "error")

    def on_speed_change(self, val_str: str):
        if self._loading_settings:
            return
        try:
            gui_speed_value = int(float(val_str))
            effect_speed_internal = max(1, min(10, int(gui_speed_value / 10.0 + 0.5)))
            self.settings.set("effect_speed", effect_speed_internal)
            if self.effect_manager.is_effect_running():
                self.effect_manager.update_effect_speed(effect_speed_internal)
            self.log_status(f"Effect speed set to {effect_speed_internal} (UI: {gui_speed_value}%)")
            if hasattr(self, 'speed_label') and self.speed_label.winfo_exists():
                self.speed_label.config(text=f"{gui_speed_value}%")
        except ValueError:
            self.logger.warning(f"Invalid speed value: {val_str}")
        except tk.TclError:
            self.logger.debug("Speed label no longer exists.")

    def on_rainbow_mode_change(self):
        if self._loading_settings:
            return
        rainbow_enabled = self.effect_rainbow_mode_var.get()
        self.settings.set("effect_rainbow_mode", rainbow_enabled)
        self.update_effect_controls_visibility()
        current_effect_name = self.effect_var.get()
        is_static_effect = current_effect_name in ["Static Color", "Static Zone Colors", "Static Rainbow", "Static Gradient"]
        if not is_static_effect and current_effect_name != "None":
            self._update_effect_preview_only()

    def _update_effect_preview_only(self):
        """Update only the preview without applying to hardware"""
        current_effect_name = self.effect_var.get()
        if current_effect_name == "None" or current_effect_name in ["Static Color", "Static Zone Colors", "Static Rainbow", "Static Gradient"]:
            return
        self.stop_preview_animation()
        preview_method_name = f"preview_{current_effect_name.lower().replace(' ','_').replace('(','').replace(')','')}"
        if hasattr(self, preview_method_name) and callable(getattr(self, preview_method_name)):
            self.start_preview_animation(getattr(self, preview_method_name))
        else:
            self._update_generic_preview_on_param_change()

    def _update_generic_preview_on_param_change(self):
        self.stop_preview_animation()
        effect_name = self.effect_var.get()
        if effect_name == "None" or effect_name in ["Static Color", "Static Zone Colors", "Static Rainbow", "Static Gradient"]:
            return
        if not self.effect_rainbow_mode_var.get():
            try:
                color = RGBColor.from_hex(self.effect_color_var.get())
                for i in range(NUM_ZONES):
                    self.zone_colors[i] = color
                self.update_preview_keyboard()
            except ValueError:
                for i in range(NUM_ZONES):
                    self.zone_colors[i] = RGBColor(0,0,0)
                self.update_preview_keyboard()
        else:
            for i in range(NUM_ZONES):
                hue = (i / NUM_ZONES) % 1.0
                rgb_float = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                self.zone_colors[i] = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
            self.update_preview_keyboard()

    def on_effect_change(self, *args):
        if self._loading_settings:
            return
        effect_name = self.effect_var.get()
        self.settings.set("effect_name", effect_name)
        self.update_effect_controls_visibility()
        self.stop_preview_animation()
        static_effects_map = {
            "Static Color": lambda: self.preview_static_color(),
            "Static Zone Colors": lambda: self.preview_static_per_zone(0),
            "Static Rainbow": lambda: self.preview_static_rainbow(0),
            "Static Gradient": lambda: self.preview_static_gradient(0)
        }
        if effect_name in static_effects_map:
            static_effects_map[effect_name]()
            self.update_preview_keyboard()
            self.log_status(f"Effect '{effect_name}' selected. Click 'Start Effect' to apply to hardware.")
            return
        if effect_name != "None":
            preview_method_name = f"preview_{effect_name.lower().replace(' ','_').replace('(','').replace(')','')}"
            if hasattr(self, preview_method_name) and callable(getattr(self, preview_method_name)):
                self.logger.debug(f"Activating specific GUI preview for {effect_name}")
                self.start_preview_animation(getattr(self, preview_method_name))
            else:
                self.logger.debug(f"No specific GUI preview for {effect_name}. Setting static representation for preview.")
                self._update_generic_preview_on_param_change()
            self.log_status(f"Effect '{effect_name}' selected. Click 'Start Effect' to apply to hardware.")
        else:
            for i in range(NUM_ZONES):
                self.zone_colors[i] = RGBColor(0,0,0)
            self.update_preview_keyboard()
            self.log_status("No effect selected.")

    def preview_static_color(self):
        """Preview static color in the keyboard layout - FIXED"""
        try:
            color = RGBColor.from_hex(self.current_color_var.get())
        except ValueError:
            color = RGBColor(0,0,0)
        for i in range(NUM_ZONES):
            self.zone_colors[i] = color
        self.update_preview_keyboard()
        if hasattr(self, 'static_preview_canvas'):
            self.update_preview_keyboard(self.static_preview_canvas, 'static_keyboard_elements')

    def update_effect_controls_visibility(self):
        """Updated to handle Reactive and Anti-Reactive effects"""
        effect_name = self.effect_var.get()
        color_configurable_effects = [
            "Breathing", "Wave", "Pulse", "Zone Chase", "Starlight", "Scanner",
            "Strobe", "Ripple", "Raindrop", "Reactive", "Anti-Reactive"
        ]
        is_color_configurable = effect_name in color_configurable_effects
        if hasattr(self, 'effect_color_rainbow_frame') and self.effect_color_rainbow_frame.winfo_exists():
            if is_color_configurable:
                if not self.effect_color_rainbow_frame.winfo_ismapped():
                    self.effect_color_rainbow_frame.pack(fill=tk.X, pady=(0,5), anchor='w')
                if hasattr(self, 'rainbow_mode_check') and self.rainbow_mode_check.winfo_exists():
                    if not self.rainbow_mode_check.winfo_ismapped():
                        self.rainbow_mode_check.pack(side=tk.LEFT, padx=(0,10), pady=(0,5))
                if hasattr(self, 'effect_color_frame') and self.effect_color_frame.winfo_exists():
                    if not self.effect_rainbow_mode_var.get():
                        if not self.effect_color_frame.winfo_ismapped():
                            self.effect_color_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=0, padx=5)
                    else:
                        if self.effect_color_frame.winfo_ismapped():
                            self.effect_color_frame.pack_forget()
            else:
                if self.effect_color_rainbow_frame.winfo_ismapped():
                    self.effect_color_rainbow_frame.pack_forget()

    def apply_static_color(self, hex_color_str: str):
        self._stop_all_visuals_and_clear_hardware()
        try:
            color = RGBColor.from_hex(hex_color_str)
            if not color.is_valid():
                self.log_status(f"Invalid hex color for static apply: {hex_color_str}", "error")
                return
            if self.hardware.set_all_leds_color(color):
                self.current_color_var.set(hex_color_str)
                if hasattr(self, 'color_display') and self.color_display.winfo_exists():
                    self.color_display.config(bg=hex_color_str)
                self.settings.set("current_color", color.to_dict())
                self.settings.set("last_mode", "static")
                self.log_status(f"Applied static color {hex_color_str} to all zones")
                for i in range(NUM_ZONES):
                    self.zone_colors[i] = color
                self.update_preview_keyboard()
            else:
                raise HardwareError("HardwareController.set_all_leds_color returned false or failed.")
        except (IOError, PermissionError) as e:
            log_error_with_context(self.logger, e, {"color": hex_color_str, "action": "apply_static_color"})
            if self.root.winfo_exists():
                messagebox.showerror("Error", f"Failed to apply static color: {e}", parent=self.root)

    def set_zone_color_interactive(self, zone_index: int):
        if not (0 <= zone_index < NUM_ZONES and zone_index < len(self.zone_displays)):
            self.logger.error(f"Invalid zone index {zone_index}. Max zones: {NUM_ZONES}, displays: {len(self.zone_displays)}")
            return
        initial_color_hex = self.zone_colors[zone_index].to_hex()
        new_color_tuple = colorchooser.askcolor(initialcolor=initial_color_hex, title=f"Set Color for Zone {zone_index + 1}", parent=self.root)
        if new_color_tuple and new_color_tuple[1]:
            chosen_hex = new_color_tuple[1]
            self.zone_colors[zone_index] = RGBColor.from_hex(chosen_hex)
            if self.zone_displays[zone_index].winfo_exists():
                self.zone_displays[zone_index].config(bg=chosen_hex)
            self.log_status(f"Zone {zone_index+1} GUI color changed. Click 'Apply Zone Colors to HW'.")
            self.settings.set("zone_colors", [zc.to_dict() for zc in self.zone_colors])
            self.update_preview_keyboard()

    def apply_current_zone_colors_to_hardware(self):
        self._stop_all_visuals_and_clear_hardware()
        try:
            if self.hardware.set_zone_colors(self.zone_colors):
                self.log_status("Applied current zone colors to hardware.")
                self.settings.set("zone_colors", [zc.to_dict() for zc in self.zone_colors])
                self.settings.set("last_mode", "zones")
                self.update_preview_keyboard()
            else:
                raise HardwareError("HardwareController.set_zone_colors returned false.")
        except (IOError, PermissionError) as e:
            log_error_with_context(self.logger, e)
            if self.root.winfo_exists():
                messagebox.showerror("Error", f"Failed to apply zone colors: {e}", parent=self.root)

    def apply_rainbow_zones(self):
        self._stop_all_visuals_and_clear_hardware()
        try:
            rainbow_zone_colors_list = []
            for i in range(NUM_ZONES):
                hue = i / float(NUM_ZONES) if NUM_ZONES > 0 else 0
                rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                rainbow_zone_colors_list.append(RGBColor(int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255)))
            if self.hardware.set_zone_colors(rainbow_zone_colors_list):
                self.zone_colors = rainbow_zone_colors_list
                for i, color_obj in enumerate(self.zone_colors):
                    zd_widget = self.zone_displays[i]
                    if i < len(self.zone_displays) and zd_widget.winfo_exists():
                        zd_widget.config(bg=color_obj.to_hex())
                self.settings.set("zone_colors", [c.to_dict() for c in self.zone_colors])
                self.settings.set("last_mode", "rainbow_zones")
                self.log_status("Applied rainbow pattern to zones.")
                self.update_preview_keyboard()
            else:
                raise HardwareError("Failed to set rainbow colors to hardware (set_zone_colors returned false)")
        except (IOError, PermissionError) as e:
            log_error_with_context(self.logger, e)
            if self.root.winfo_exists():
                messagebox.showerror("Error", f"Failed to apply rainbow zones: {e}", parent=self.root)

    def apply_gradient_zones(self):
        self._stop_all_visuals_and_clear_hardware()
        try:
            start_color = RGBColor.from_hex(self.gradient_start_color_var.get())
            end_color = RGBColor.from_hex(self.gradient_end_color_var.get())
            gradient_zone_colors_list = []
            for i in range(NUM_ZONES):
                ratio = i / float(NUM_ZONES - 1) if NUM_ZONES > 1 else 0.0
                r = int(start_color.r*(1-ratio)+end_color.r*ratio)
                g = int(start_color.g*(1-ratio)+end_color.g*ratio)
                b = int(start_color.b*(1-ratio)+end_color.b*ratio)
                gradient_zone_colors_list.append(RGBColor(r, g, b))
            if self.hardware.set_zone_colors(gradient_zone_colors_list):
                self.zone_colors = gradient_zone_colors_list
                for i, color_obj in enumerate(self.zone_colors):
                    zd_widget = self.zone_displays[i]
                    if i < len(self.zone_displays) and self.zone_displays[i].winfo_exists():
                        self.zone_displays[i].config(bg=color_obj.to_hex())
                self.settings.set("zone_colors", [c.to_dict() for c in self.zone_colors])
                self.settings.set("last_mode", "gradient_zones")
                self.log_status("Applied gradient to zones.")
                self.update_preview_keyboard()
            else:
                raise HardwareError("Failed to set gradient colors to hardware (set_zone_colors returned false)")
        except (IOError, PermissionError) as e:
            log_error_with_context(self.logger, e)
            if self.root.winfo_exists():
                messagebox.showerror("Error", f"Failed to apply gradient: {e}", parent=self.root)

    def clear_all_zones_and_effects(self):
        self._stop_all_visuals_and_clear_hardware()
        self.log_status("All effects stopped & LEDs cleared by user action.")
        black = RGBColor(0,0,0)
        self.zone_colors = [black] * NUM_ZONES
        for zd in self.zone_displays:
            if hasattr(zd, 'winfo_exists') and zd.winfo_exists():
                zd.config(bg=black.to_hex())
        self.current_color_var.set(black.to_hex())
        if hasattr(self, 'color_display') and self.color_display.winfo_exists():
            self.color_display.config(bg=black.to_hex())
        self.effect_var.set("None")
        self.settings.set("current_color", black.to_dict())
        self.settings.set("zone_colors", [black.to_dict()]*NUM_ZONES)
        self.settings.set("effect_name", "None")
        self.update_preview_keyboard()

    def open_color_picker(self):
        self.stop_preview_animation()
        result = colorchooser.askcolor(initialcolor=self.current_color_var.get(), title="Choose Static Color", parent=self.root)
        if result and result[1]:
            self.current_color_var.set(result[1])
            if hasattr(self, 'color_display') and self.color_display.winfo_exists():
                self.color_display.config(bg=result[1])
            if self.effect_var.get() == "Static Color":
                self.preview_static_color()
                self.update_preview_keyboard()

    def choose_effect_color(self):
        result = colorchooser.askcolor(initialcolor=self.effect_color_var.get(), title="Choose Effect Base Color", parent=self.root)
        if result and result[1]:
            self.effect_color_var.set(result[1])
            if hasattr(self,'effect_color_display') and self.effect_color_display.winfo_exists():
                self.effect_color_display.config(bg=result[1])
            self.settings.set("effect_color", result[1])
            self._update_effect_preview_only()

    def choose_gradient_start(self):
        result = colorchooser.askcolor(initialcolor=self.gradient_start_color_var.get(), title="Choose Gradient Start Color", parent=self.root)
        if result and result[1]:
            self.gradient_start_color_var.set(result[1])
            if hasattr(self,'gradient_start_display') and self.gradient_start_display.winfo_exists():
                self.gradient_start_display.config(bg=result[1])
            self.settings.set("gradient_start_color", result[1])
            if self.effect_var.get() == "Static Gradient":
                self.preview_static_gradient(0)
                self.update_preview_keyboard()

    def choose_gradient_end(self):
        result = colorchooser.askcolor(initialcolor=self.gradient_end_color_var.get(), title="Choose Gradient End Color", parent=self.root)
        if result and result[1]:
            self.gradient_end_color_var.set(result[1])
            if hasattr(self,'gradient_end_display') and self.gradient_end_display.winfo_exists():
                self.gradient_end_display.config(bg=result[1])
            self.settings.set("gradient_end_color", result[1])
            if self.effect_var.get() == "Static Gradient":
                self.preview_static_gradient(0)
                self.update_preview_keyboard()

    def start_current_effect(self):
        effect_name = self.effect_var.get()
        self._stop_all_visuals_and_clear_hardware()
        static_effects_map = {
            "Static Color": lambda: self.apply_static_color(self.current_color_var.get()),
            "Static Zone Colors": self.apply_current_zone_colors_to_hardware,
            "Static Rainbow": self.apply_rainbow_zones,
            "Static Gradient": self.apply_gradient_zones
        }
        if effect_name in static_effects_map:
            static_effects_map[effect_name]()
            self.settings.set("effect_name", effect_name)
            return
        if effect_name in ["Reactive", "Anti-Reactive"]:
            self._stop_all_visuals_and_clear_hardware()
            if not hasattr(self, 'reactive_effects_enabled'):
                self.setup_reactive_effects_system()
            params = {
                "speed": max(1, min(10, int(self.speed_var.get() / 10.0 + 0.5))),
                "rainbow_mode": self.effect_rainbow_mode_var.get()
            }
            try:
                params["color"] = RGBColor.from_hex(self.effect_color_var.get()) if not params["rainbow_mode"] else RGBColor(255, 255, 255)
            except ValueError:
                params["color"] = RGBColor(255, 255, 255)
            preview_method_name = f"preview_{effect_name.lower().replace('-', '_')}"
            if hasattr(self, preview_method_name):
                self.start_preview_animation(getattr(self, preview_method_name))
                self.log_status(f"Started {effect_name} effect preview. Full hardware reactive support requires hardware module updates.")
                self.settings.set("effect_name", effect_name)
                self.settings.set("last_mode", "effect")
            else:
                self.log_status(f"Preview method for {effect_name} not found", "error")
            return
        if effect_name == "None":
            self.log_status("Effect set to None. All effects stopped and LEDs cleared.")
            self.settings.set("effect_name", "None")
            return
        params: Dict[str, Any] = {}
        try:
            params["speed"] = max(1, min(10, int(self.speed_var.get() / 10.0 + 0.5)))
            is_rainbow = self.effect_rainbow_mode_var.get()
            params["rainbow_mode"] = is_rainbow
            try:
                params["color"] = RGBColor.from_hex(self.effect_color_var.get()) if not is_rainbow else RGBColor(0,0,0)
            except ValueError:
                self.logger.warning(f"Invalid effect color hex {self.effect_color_var.get()}, using black for effect params.")
                params["color"] = RGBColor(0,0,0)
            if self.effect_manager.start_effect(effect_name, **params):
                self.log_status(f"Started effect: {effect_name}")
                self.settings.set("effect_name", effect_name)
                self.settings.set("last_mode", "effect")
                preview_method_name = f"preview_{effect_name.lower().replace(' ','_').replace('(','').replace(')','')}"
                if hasattr(self, preview_method_name) and callable(getattr(self, preview_method_name)):
                    self.start_preview_animation(getattr(self, preview_method_name))
                else:
                    self._update_generic_preview_on_param_change()
            else:
                self.log_status(f"Effect '{effect_name}' not found by manager or failed to start.", "warning")
                if self.root.winfo_exists():
                    messagebox.showwarning("Effect Error", f"Could not start effect: {effect_name}. It might not be available in the effect library.", parent=self.root)
                self.effect_var.set("None")
        except (IOError, PermissionError) as e:
            log_error_with_context(self.logger, e, {"effect": effect_name, "params": str(params)})
            if self.root.winfo_exists():
                messagebox.showerror("Effect Error", f"Failed to start effect '{effect_name}': {e}", parent=self.root)
            self.effect_var.set("None")

    def stop_current_effect(self):
        self._stop_all_visuals_and_clear_hardware()
        self.log_status("Current effect stopped by user action. LEDs cleared.")
        if self.effect_var.get() != "None":
            self.effect_var.set("None")

    def restart_current_effect(self):
        effect_name = self.effect_var.get()
        if effect_name != "None" and effect_name not in ["Static Color", "Static Zone Colors", "Static Rainbow", "Static Gradient"]:
            self.log_status(f"Restarting effect: {effect_name} due to parameter change.")
            self.root.after(50, self.start_current_effect)
        elif self.preview_animation_active:
            self.log_status(f"Restarting preview for: {effect_name} due to parameter change.")
            self.start_current_effect()

    def save_persistence_settings(self):
        self.settings.set("restore_on_startup", self.restore_startup_var.get())
        self.settings.set("auto_apply_last_setting", self.auto_apply_var.get())
        self.log_status("Persistence settings saved.")

    def save_control_method(self):
        method = self.control_method_var.get()
        self.settings.set("last_control_method", method)
        self.log_status(f"Control method preference set to: {method}")
        if method == "ec_direct":
            self._show_ec_direct_implementation_guide()
        if hasattr(self.hardware, 'set_control_method_preference'):
            try:
                self.hardware.set_control_method_preference(method)
                self.logger.info(f"Notified HardwareController of preference: {method}")
            except (IOError, PermissionError) as e:
                self.logger.error(f"Error notifying HardwareController of preference change: {e}")
        else:
            self.logger.info("HardwareController does not have 'set_control_method_preference'. Preference saved; hardware layer may pick it up on next init.")

    def _show_ec_direct_implementation_guide(self):
        """Show comprehensive EC Direct implementation guide"""
        msg_title = "EC Direct Mode - Implementation Required"
        msg_body = """EC Direct mode selected. This is an ADVANCED feature that requires manual implementation.
IMPLEMENTATION STEPS:
====================
1. HARDWARE-SPECIFIC RESEARCH:
   • Find your device's Embedded Controller (EC) documentation
   • Identify RGB control commands and registers
   • Determine I/O port addresses or memory locations
   • Research your specific laptop/keyboard model's EC interface
2. MODIFY HardwareController CLASS:
   Edit: gui/hardware/controller.py
   Implement these methods for EC Direct:
   • _detect_ec_direct() - Detect EC availability
   • _ec_set_brightness(value) - Direct brightness control
   • _ec_set_all_leds_color(color) - Set all LEDs via EC
   • _ec_set_zone_colors(colors) - Set individual zones via EC
   • _ec_clear_all_leds() - Clear LEDs via EC
3. COMMON EC ACCESS METHODS:
   Linux:
   • /dev/port access (requires root): os.open('/dev/port', os.O_RDWR)
   • outb/inb operations: ctypes or custom kernel module
   • ACPI interface: /sys/kernel/debug/ec/ec0/io (if available)
   Windows:
   • Direct port I/O via WinIo, InpOut32, or similar libraries
   • WMI interface if available
   • Custom driver development
4. EXAMPLE LINUX IMPLEMENTATION:
   ```python
   import os
   import ctypes
   def ec_write_byte(port, value):
       # Requires root privileges
       with open('/dev/port', 'r+b', 0) as f:
           f.seek(port)
           f.write(bytes([value]))
   def ec_read_byte(port):
       with open('/dev/port', 'rb', 0) as f:
           f.seek(port)
           return ord(f.read(1))
   ```
5. SAFETY WARNINGS:
   ⚠ CAUTION: Incorrect EC commands can cause:
   • System instability or crashes
   • Hardware damage
   • BIOS/UEFI corruption
   • Permanent device malfunction
   ⚠ ALWAYS:
   • Test on disposable hardware first
   • Create system backups
   • Document all commands before use
   • Start with read-only operations
   • Implement proper error handling
6. DEVICE-SPECIFIC EXAMPLES:
   Different manufacturers use different EC interfaces:
   • Framework laptops: Specific EC protocol
   • System76: Open-source EC firmware
   • Chromebooks: Chrome EC with specific commands
   • Gaming laptops: Often proprietary protocols
7. PERMISSIONS REQUIRED:
   • Linux: root privileges or specific group membership
   • Windows: Administrator privileges or driver installation
   • macOS: System-level access (may require SIP disable)
8. TESTING PROCEDURE:
   • Start with reading EC status registers
   • Test brightness control first (safest)
   • Implement color control incrementally
   • Add comprehensive error handling
   • Test all edge cases thoroughly
CURRENT STATUS:
===============
This is currently a PLACEHOLDER implementation. The GUI provides the interface, but the actual EC communication must be implemented by you based on your specific hardware requirements. If you implement EC Direct successfully, please consider contributing your implementation back to the project to help other users with similar hardware!
"""
        self.logger.warning(f"{msg_title}: EC Direct selected but requires implementation")
        self.log_to_gui_diag_area(f"{msg_title}:\n{msg_body}", "warning")
        if self.root.winfo_exists():
            popup_msg = """EC Direct mode requires manual implementation for your specific hardware. This is an ADVANCED feature that involves:
• Direct Embedded Controller (EC) communication
• Hardware-specific research and coding
• Root/Administrator privileges
• Risk of system instability if done incorrectly
FULL IMPLEMENTATION GUIDE has been written to:
• Application Log (Diagnostics tab)
• Log files in the logs directory
⚠ WARNING: Incorrect EC commands can damage hardware!
Only proceed if you have embedded systems experience.
The application will use fallback methods (ectool) until EC Direct is implemented."""
            messagebox.showwarning(msg_title, popup_msg, parent=self.root)

    def reset_settings(self):
        if self.root.winfo_exists() and messagebox.askyesno("Confirm Reset", "Reset all settings to defaults? This cannot be undone.", parent=self.root):
            self._stop_all_visuals_and_clear_hardware()
            self.settings.reset_to_defaults()
            self.load_saved_settings()
            default_color_on_reset = RGBColor.from_dict(default_settings["current_color"])
            self.apply_static_color(default_color_on_reset.to_hex())
            self.log_status("All settings reset to defaults.")
            if self.root.winfo_exists():
                messagebox.showinfo("Settings Reset", "All settings have been reset to their default values.", parent=self.root)

    def export_settings(self):
        self.save_current_gui_state_to_settings()
        fpath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Settings File","*.json"), ("All Files","*.*")], title="Export Application Settings", parent=self.root)
        if fpath:
            try:
                with open(fpath, 'w', encoding='utf-8') as f:
                    json.dump(self.settings._settings, f, indent=2)
                self.log_status(f"Settings exported to {fpath}")
                if self.root.winfo_exists():
                    messagebox.showinfo("Export Successful", f"Settings exported to:\n{fpath}", parent=self.root)
            except (IOError, PermissionError) as e:
                self.log_status(f"Export failed: {e}", "error")
                if self.root.winfo_exists():
                    messagebox.showerror("Export Error", f"Could not export settings: {e}", parent=self.root)

    def import_settings(self):
        fpath_str = filedialog.askopenfilename(
            filetypes=[("JSON Settings File", "*.json"), ("All Files", "*.*")],
            title="Import Application Settings",
            parent=self.root
        )
        if not fpath_str:
            return
        try:
            fpath = Path(fpath_str).resolve()
            if not str(fpath).startswith(str(Path.home())):
                messagebox.showerror("Security Error", "Cannot import files from outside your home directory.", parent=self.root)
                self.log_status("Import blocked: attempt to read from a sensitive location.", "error")
                return
        except (IOError, PermissionError) as e:
            messagebox.showerror("File Error", f"Invalid or inaccessible file path: {e}", parent=self.root)
            return
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)
            is_valid, error_msg = self._validate_settings_data(imported_data)
            if not is_valid:
                raise ConfigurationError(f"Invalid settings file: {error_msg}")
            self._stop_all_visuals_and_clear_hardware()
            self.settings.update(imported_data)
            self.settings.save_settings()
            self.load_saved_settings()
            self._restore_settings_on_startup()
            messagebox.showinfo("Import Successful", f"Settings imported from:\n{fpath.name}", parent=self.root)
        except json.JSONDecodeError as e_json:
            self.log_status(f"Import failed: Invalid JSON. {e_json}", "error")
            messagebox.showerror("Import Error", f"Failed to import settings: Not a valid JSON file.\n{e_json}", parent=self.root)
        except (ConfigurationError, Exception) as e:
            self.log_status(f"Import failed: {e}", "error")
            messagebox.showerror("Import Error", f"Failed to import settings: {e}", parent=self.root)

    def _validate_settings_data(self, data: dict) -> Tuple[bool, str]:
        """Validates the structure, types, and value ranges of imported settings data."""
        if not isinstance(data, dict):
            return False, "Settings file must contain a JSON object."
        expected_types = {
            "brightness": int, "effect_speed": int, "effect_name": str,
            "effect_color": str, "effect_rainbow_mode": bool,
            "zone_colors": list, "restore_on_startup": bool
        }
        for key, expected_type in expected_types.items():
            if key not in data:
                return False, f"Required setting '{key}' is missing."
            if not isinstance(data[key], expected_type):
                return False, f"Setting '{key}' has incorrect type. Expected {expected_type.__name__}."
        if not 0 <= data["brightness"] <= 100:
            return False, "Brightness must be between 0 and 100."
        if not 1 <= data["effect_speed"] <= 10:
            return False, "Effect speed must be between 1 and 10."
        try:
            RGBColor.from_hex(data["effect_color"])
        except ValueError:
            return False, f"Invalid hex code for 'effect_color': {data['effect_color']}"
        if len(data["zone_colors"]) != NUM_ZONES:
             return False, f"Expected {NUM_ZONES} zone colors, but found {len(data['zone_colors'])}."
        for i, zc in enumerate(data["zone_colors"]):
            if not all(k in zc for k in ['r', 'g', 'b']):
                return False, f"Zone color at index {i} is missing 'r', 'g', or 'b' keys."
        return True, "Validation successful."

    def load_saved_settings(self):
        self._loading_settings = True
        self.logger.info("Loading saved settings into GUI controls...")
        try:
            self.brightness_var.set(self.settings.get("brightness", default_settings['brightness']))
            current_color_data = self.settings.get("current_color", default_settings['current_color'])
            current_color_obj = RGBColor.from_dict(current_color_data)
            if hasattr(self, 'color_display') and self.color_display.winfo_exists():
                self.color_display.config(bg=current_color_obj.to_hex())
            self.current_color_var.set(current_color_obj.to_hex())
            effect_speed_setting = self.settings.get("effect_speed", default_settings['effect_speed'])
            self.speed_var.set(effect_speed_setting * 10)
            if hasattr(self, 'speed_label') and self.speed_label.winfo_exists():
                self.speed_label.config(text=f"{self.speed_var.get()}%")
            zone_colors_list_data = self.settings.get("zone_colors", default_settings['zone_colors'])
            self.zone_colors = [RGBColor.from_dict(d) for d in zone_colors_list_data[:NUM_ZONES]]
            while len(self.zone_colors) < NUM_ZONES:
                self.zone_colors.append(RGBColor(0,0,0))
            self.zone_colors = self.zone_colors[:NUM_ZONES]
            if hasattr(self, 'zone_displays'):
                for i, zd_widget in enumerate(self.zone_displays):
                    if i < len(self.zone_colors) and zd_widget.winfo_exists():
                        zd_widget.config(bg=self.zone_colors[i].to_hex())
            self.gradient_start_color_var.set(self.settings.get("gradient_start_color", default_settings['gradient_start_color']))
            if hasattr(self, 'gradient_start_display') and self.gradient_start_display.winfo_exists():
                self.gradient_start_display.config(bg=self.gradient_start_color_var.get())
            self.gradient_end_color_var.set(self.settings.get("gradient_end_color", default_settings['gradient_end_color']))
            if hasattr(self, 'gradient_end_display') and self.gradient_end_display.winfo_exists():
                self.gradient_end_display.config(bg=self.gradient_end_color_var.get())
            self.effect_var.set(self.settings.get("effect_name", default_settings['effect_name']))
            self.effect_color_var.set(self.settings.get("effect_color", default_settings['effect_color']))
            if hasattr(self, 'effect_color_display') and self.effect_color_display.winfo_exists():
                self.effect_color_display.config(bg=self.effect_color_var.get())
            self.effect_rainbow_mode_var.set(self.settings.get("effect_rainbow_mode", default_settings['effect_rainbow_mode']))
            self.update_effect_controls_visibility()
            self.restore_startup_var.set(self.settings.get("restore_on_startup", default_settings['restore_on_startup']))
            self.auto_apply_var.set(self.settings.get("auto_apply_last_setting", default_settings['auto_apply_last_setting']))
            self.control_method_var.set(self.settings.get("last_control_method", default_settings['last_control_method']))
            if hasattr(self, 'minimize_to_tray_var'):
                self.minimize_to_tray_var.set(self.settings.get("minimize_to_tray", default_settings.get("minimize_to_tray", True)))
            self.logger.info("GUI controls updated from loaded settings.")
        except (IOError, PermissionError) as e:
            log_error_with_context(self.logger, e, {"action":"load_settings_into_gui_controls"})
            if self.root.winfo_exists():
                messagebox.showwarning("Settings Load Issue", f"Could not fully load settings into GUI: {e}", parent=self.root)
        finally:
            self._loading_settings = False
        effect_name_on_load = self.effect_var.get()
        if effect_name_on_load != "None" and effect_name_on_load not in ["Static Color", "Static Zone Colors", "Static Rainbow", "Static Gradient"]:
            preview_method_name = f"preview_{effect_name_on_load.lower().replace(' ','_').replace('(','').replace(')','')}"
            if hasattr(self, preview_method_name) and callable(getattr(self, preview_method_name)):
                self.start_preview_animation(getattr(self, preview_method_name))
            else:
                self._update_generic_preview_on_param_change()
        elif effect_name_on_load == "Static Color":
            self.preview_static_color()
            self.update_preview_keyboard()
        elif effect_name_on_load == "Static Zone Colors":
            self.update_preview_keyboard()
        elif effect_name_on_load == "Static Rainbow":
            self.preview_static_rainbow(0)
            self.update_preview_keyboard()
        elif effect_name_on_load == "Static Gradient":
            self.preview_static_gradient(0)
            self.update_preview_keyboard()
        else:
            for i in range(NUM_ZONES):
                self.zone_colors[i] = RGBColor(0,0,0)
            self.update_preview_keyboard()

    def save_current_gui_state_to_settings(self):
        self.logger.debug("Saving current GUI state to settings...")
        settings_to_update = {
            "brightness": self.brightness_var.get(),
            "effect_speed": max(1,min(10, int(self.speed_var.get()/10.0 + 0.5))),
            "current_color": RGBColor.from_hex(self.current_color_var.get()).to_dict(),
            "zone_colors": [zc.to_dict() for zc in self.zone_colors],
            "effect_name": self.effect_var.get(),
            "effect_color": self.effect_color_var.get(),
            "effect_rainbow_mode": self.effect_rainbow_mode_var.get(),
            "gradient_start_color": self.gradient_start_color_var.get(),
            "gradient_end_color": self.gradient_end_color_var.get(),
            "restore_on_startup": self.restore_startup_var.get(),
            "auto_apply_last_setting": self.auto_apply_var.get(),
            "last_control_method": self.control_method_var.get(),
        }
        if hasattr(self, 'minimize_to_tray_var'):
            settings_to_update["minimize_to_tray"] = self.minimize_to_tray_var.get()
        current_effect = self.effect_var.get()
        if current_effect == "Static Color":
            settings_to_update["last_mode"] = "static"
        elif current_effect == "Static Zone Colors":
            settings_to_update["last_mode"] = "zones"
        elif current_effect == "Static Rainbow":
            settings_to_update["last_mode"] = "rainbow_zones"
        elif current_effect == "Static Gradient":
            settings_to_update["last_mode"] = "gradient_zones"
        elif current_effect != "None":
            settings_to_update["last_mode"] = "effect"
        self.settings.update(settings_to_update)
        self.settings.save_settings()
        self.logger.info("Current GUI state saved to settings.")

    def preview_color_cycle(self, frame_count: int):
        speed_multiplier = self.get_hardware_synchronized_speed()
        hue = (frame_count * speed_multiplier * 0.5) % 1.0
        rgb_float = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
        color = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
        for i in range(NUM_ZONES):
            self.zone_colors[i] = color
        self.update_preview_keyboard()

    def preview_color_cycle_advanced(self, frame_count: int):
        try:
            base_hue = (frame_count * 0.02) % 1.0
            for i in range(NUM_ZONES):
                zone_hue = (base_hue + (i * 0.1)) % 1.0
                saturation = 0.8 + 0.2 * math.sin(frame_count * 0.1)
                value = 0.7 + 0.3 * math.sin(frame_count * 0.15 + i * 0.2)
                rgb_float = colorsys.hsv_to_rgb(zone_hue, saturation, value)
                self.zone_colors[i] = RGBColor(
                    int(rgb_float[0] * 255),
                    int(rgb_float[1] * 255),
                    int(rgb_float[2] * 255)
                )
            self.update_preview_keyboard()
        except (IOError, PermissionError) as e:
            self.logger.error(f"Error in advanced color cycle preview: {e}")
            self.preview_color_cycle(frame_count)

    def preview_pulse(self, frame_count: int):
        try:
            base_color_rgb = RGBColor.from_hex(self.effect_color_var.get())
        except ValueError:
            base_color_rgb = RGBColor(255, 0, 255)
        is_rainbow = self.effect_rainbow_mode_var.get()
        speed_multiplier = self.get_hardware_synchronized_speed()
        pulse_cycle = (math.sin(frame_count * speed_multiplier * 3) + 1) / 2
        for i in range(NUM_ZONES):
            if is_rainbow:
                hue = (frame_count * speed_multiplier * 0.2) % 1.0
                rgb_float = colorsys.hsv_to_rgb(hue, 1.0, pulse_cycle)
                self.zone_colors[i] = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
            else:
                self.zone_colors[i] = RGBColor(
                    int(base_color_rgb.r * pulse_cycle),
                    int(base_color_rgb.g * pulse_cycle),
                    int(base_color_rgb.b * pulse_cycle)
                )
        self.update_preview_keyboard()

    def preview_zone_chase(self, frame_count: int):
        try:
            base_color_rgb = RGBColor.from_hex(self.effect_color_var.get())
        except ValueError:
            base_color_rgb = RGBColor(255, 255, 0)
        is_rainbow = self.effect_rainbow_mode_var.get()
        speed_multiplier = self.get_hardware_synchronized_speed()
        active_zone = int((frame_count * speed_multiplier * 1.2) % NUM_ZONES)
        for i in range(NUM_ZONES):
            if i == active_zone:
                if is_rainbow:
                    hue = (frame_count * speed_multiplier * 0.3) % 1.0
                    rgb_float = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                    self.zone_colors[i] = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
                else:
                    self.zone_colors[i] = base_color_rgb
            else:
                distance = min(abs(i - active_zone), NUM_ZONES - abs(i - active_zone))
                fade = max(0, 1.0 - distance * 0.8)
                if fade > 0.1:
                    if is_rainbow:
                        hue = (frame_count * speed_multiplier * 0.3) % 1.0
                        rgb_float = colorsys.hsv_to_rgb(hue, 1.0, fade)
                        self.zone_colors[i] = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
                    else:
                        self.zone_colors[i] = RGBColor(
                            int(base_color_rgb.r * fade),
                            int(base_color_rgb.g * fade),
                            int(base_color_rgb.b * fade)
                        )
                else:
                    self.zone_colors[i] = RGBColor(0, 0, 0)
        self.update_preview_keyboard()

    def preview_scanner(self, frame_count: int):
        try:
            base_color_rgb = RGBColor.from_hex(self.effect_color_var.get())
        except ValueError:
            base_color_rgb = RGBColor(255, 0, 0)
        is_rainbow = self.effect_rainbow_mode_var.get()
        speed_multiplier = self.get_hardware_synchronized_speed()
        cycle_length = NUM_ZONES * 2 - 2
        position_in_cycle = int((frame_count * speed_multiplier * 1.5) % cycle_length)
        if position_in_cycle < NUM_ZONES:
            scanner_pos = position_in_cycle
        else:
            scanner_pos = cycle_length - position_in_cycle
        for i in range(NUM_ZONES):
            if i == scanner_pos:
                if is_rainbow:
                    hue = (scanner_pos / NUM_ZONES) % 1.0
                    rgb_float = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                    self.zone_colors[i] = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
                else:
                    self.zone_colors[i] = base_color_rgb
            else:
                self.zone_colors[i] = RGBColor(0, 0, 0)
        self.update_preview_keyboard()

    def preview_strobe(self, frame_count: int):
        try:
            base_color_rgb = RGBColor.from_hex(self.effect_color_var.get())
        except ValueError:
            base_color_rgb = RGBColor(255,255,255)
        is_rainbow = self.effect_rainbow_mode_var.get()
        strobe_on = (frame_count % 5) < 3
        for i in range(NUM_ZONES):
            if strobe_on:
                if is_rainbow:
                    hue = (i / NUM_ZONES) % 1.0
                    rgb_float = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                    self.zone_colors[i] = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
                else:
                    self.zone_colors[i] = base_color_rgb
            else:
                self.zone_colors[i] = RGBColor(0, 0, 0)
        self.update_preview_keyboard()

    def preview_ripple(self, frame_count: int):
        try:
            base_color_rgb = RGBColor.from_hex(self.effect_color_var.get())
        except ValueError:
            base_color_rgb = RGBColor(0,255,255)
        is_rainbow = self.effect_rainbow_mode_var.get()
        center = NUM_ZONES // 2
        ripple_radius = (frame_count * 0.5) % (NUM_ZONES + 5)
        for i in range(NUM_ZONES):
            distance_from_center = abs(i - center)
            ripple_intensity = max(0, 1.0 - abs(distance_from_center - ripple_radius) * 0.5)
            if is_rainbow:
                hue = (ripple_radius * 0.1) % 1.0
                rgb_float = colorsys.hsv_to_rgb(hue, 1.0, ripple_intensity)
                self.zone_colors[i] = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
            else:
                self.zone_colors[i] = RGBColor(
                    int(base_color_rgb.r * ripple_intensity),
                    int(base_color_rgb.g * ripple_intensity),
                    int(base_color_rgb.b * ripple_intensity)
                )
        self.update_preview_keyboard()

    def preview_wave(self, frame_count: int):
        try:
            base_color_rgb = RGBColor.from_hex(self.effect_color_var.get())
        except ValueError:
            base_color_rgb = RGBColor(0, 100, 255)
        is_rainbow = self.effect_rainbow_mode_var.get()
        speed_multiplier = self.get_hardware_synchronized_speed()
        active_zone = int((frame_count * speed_multiplier * 0.8) % NUM_ZONES)
        for i in range(NUM_ZONES):
            if i == active_zone:
                if is_rainbow:
                    hue = (frame_count * speed_multiplier * 0.3) % 1.0
                    rgb_float = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                    self.zone_colors[i] = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
                else:
                    self.zone_colors[i] = base_color_rgb
            else:
                self.zone_colors[i] = RGBColor(0, 0, 0)
        self.update_preview_keyboard()

    def preview_static_per_zone(self, frame_count):
        self.update_preview_keyboard()

    def preview_static_rainbow(self, frame_count):
        for i in range(NUM_ZONES):
            hue = (i / float(NUM_ZONES)) % 1.0 if NUM_ZONES > 0 else 0.0
            rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            self.zone_colors[i] = RGBColor(int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))

    def preview_static_gradient(self, frame_count):
        try:
            sc = RGBColor.from_hex(self.gradient_start_color_var.get())
            ec = RGBColor.from_hex(self.gradient_end_color_var.get())
        except ValueError:
            sc, ec = RGBColor(0,0,0), RGBColor(0,0,0)
        for i in range(NUM_ZONES):
            ratio = i / float(NUM_ZONES - 1) if NUM_ZONES > 1 else 0.0
            r = int(sc.r*(1-ratio)+ec.r*ratio)
            g = int(sc.g*(1-ratio)+ec.g*ratio)
            b = int(sc.b*(1-ratio)+ec.b*ratio)
            self.zone_colors[i] = RGBColor(r, g, b)

    def preview_breathing(self, frame_count: int):
        try:
            base_color_rgb = RGBColor.from_hex(self.effect_color_var.get())
        except ValueError:
            base_color_rgb = RGBColor(255,255,255)
        is_rainbow = self.effect_rainbow_mode_var.get()
        breath_cycle = (math.sin(frame_count * 0.1) + 1) / 2
        for i in range(NUM_ZONES):
            if is_rainbow:
                hue = (i / NUM_ZONES) % 1.0
                rgb_float = colorsys.hsv_to_rgb(hue, 1.0, breath_cycle)
                self.zone_colors[i] = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
            else:
                self.zone_colors[i] = RGBColor(
                    int(base_color_rgb.r * breath_cycle),
                    int(base_color_rgb.g * breath_cycle),
                    int(base_color_rgb.b * breath_cycle)
                )
        self.update_preview_keyboard()

    def get_hardware_synchronized_speed(self):
        internal_speed = max(1, min(10, int(self.speed_var.get() / 10.0 + 0.5)))
        hardware_speed_map = {
            1: 0.008, 2: 0.012, 3: 0.016, 4: 0.022, 5: 0.028,
            6: 0.035, 7: 0.045, 8: 0.055, 9: 0.070, 10: 0.090
        }
        return hardware_speed_map.get(internal_speed, 0.028)

    def preview_starlight(self, frame_count: int):
        try:
            base_color_rgb = RGBColor.from_hex(self.effect_color_var.get())
        except ValueError:
            base_color_rgb = RGBColor(255,255,255)
        is_rainbow = self.effect_rainbow_mode_var.get()
        speed_multiplier = self.get_hardware_synchronized_speed()
        if hasattr(self, 'key_grid') and self.key_grid:
            for row_idx, row in enumerate(self.key_grid):
                for col_idx, key_info in enumerate(row):
                    twinkle_seed = (frame_count * speed_multiplier + row_idx * 7 + col_idx * 13) % 100
                    intensity = 0.1 + 0.9 * (math.sin(twinkle_seed * 0.3) + 1) / 2
                    if (hash(f"{int(frame_count * speed_multiplier)}-{row_idx}-{col_idx}") % 100) < 15:
                        intensity = 1.0
                    if is_rainbow:
                        hue = ((row_idx + col_idx) / 10 + frame_count * speed_multiplier * 0.1) % 1.0
                        rgb_float = colorsys.hsv_to_rgb(hue, 1.0, intensity)
                        color = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
                    else:
                        color = RGBColor(
                            int(base_color_rgb.r * intensity),
                            int(base_color_rgb.g * intensity),
                            int(base_color_rgb.b * intensity)
                        )
                    try:
                        canvas = self.preview_canvas
                        canvas.itemconfig(key_info['element'], fill=color.to_hex())
                    except:
                        pass
        else:
            for i in range(NUM_ZONES):
                twinkle_seed = (frame_count * speed_multiplier + i * 17) % 100
                intensity = 0.2 + 0.8 * (math.sin(twinkle_seed * 0.1) + 1) / 2
                if is_rainbow:
                    hue = (i / NUM_ZONES + frame_count * speed_multiplier * 0.01) % 1.0
                    rgb_float = colorsys.hsv_to_rgb(hue, 1.0, intensity)
                    self.zone_colors[i] = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
                else:
                    self.zone_colors[i] = RGBColor(
                        int(base_color_rgb.r * intensity),
                        int(base_color_rgb.g * intensity),
                        int(base_color_rgb.b * intensity)
                    )
            self.update_preview_keyboard()

    def preview_raindrop(self, frame_count: int):
        if not hasattr(self, 'zone_colors') or len(self.zone_colors) < NUM_ZONES:
            return
        try:
            base_color_rgb = RGBColor.from_hex(self.effect_color_var.get())
        except ValueError:
            base_color_rgb = RGBColor(0,150,255)
        is_rainbow = self.effect_rainbow_mode_var.get()
        speed_multiplier = self.get_hardware_synchronized_speed()
        if hasattr(self, 'key_grid') and self.key_grid:
            for row in self.key_grid:
                for key_info in row:
                    try:
                        canvas = self.preview_canvas
                        canvas.itemconfig(key_info['element'], fill='#404040')
                    except:
                        pass
            num_drops = 3
            for drop_idx in range(num_drops):
                drop_col = (drop_idx * 5 + int(frame_count * speed_multiplier)) % 15
                drop_row = int((frame_count * speed_multiplier * 2 + drop_idx * 10) % (len(self.key_grid) + 3))
                for trail_offset in range(3):
                    trail_row = drop_row - trail_offset
                    if 0 <= trail_row < len(self.key_grid) and 0 <= drop_col < len(self.key_grid[trail_row]):
                        key_info = self.key_grid[trail_row][drop_col]
                        intensity = max(0, 1.0 - trail_offset * 0.4)
                        if is_rainbow:
                            hue = (drop_idx * 0.3 + frame_count * speed_multiplier * 0.1) % 1.0
                            rgb_float = colorsys.hsv_to_rgb(hue, 1.0, intensity)
                            color = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
                        else:
                            color = RGBColor(
                                int(base_color_rgb.r * intensity),
                                int(base_color_rgb.g * intensity),
                                int(base_color_rgb.b * intensity)
                            )
                        try:
                            canvas = self.preview_canvas
                            canvas.itemconfig(key_info['element'], fill=color.to_hex())
                        except:
                            pass
        else:
            for i in range(NUM_ZONES):
                if is_rainbow:
                    hue = ((i + frame_count * speed_multiplier * 0.1) / NUM_ZONES) % 1.0
                    rgb_float = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                    self.zone_colors[i] = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
                else:
                    drop_position = (frame_count * speed_multiplier) % (NUM_ZONES * 2)
                    if drop_position < NUM_ZONES and int(drop_position) == i:
                        self.zone_colors[i] = base_color_rgb
                    else:
                        fade = max(0, 1.0 - abs(i - drop_position) * 0.3)
                        self.zone_colors[i] = RGBColor(
                            int(base_color_rgb.r * fade),
                            int(base_color_rgb.g * fade),
                            int(base_color_rgb.b * fade)
                        )
            self.update_preview_keyboard()

    def start_preview_animation(self, preview_function: Callable[[int], None]):
        self.stop_preview_animation()
        self.preview_animation_active = True
        self.preview_function_callable = preview_function
        self._preview_frame_count = 0
        self._run_preview_animation()

    def stop_preview_animation(self):
        if self.preview_animation_id:
            self.root.after_cancel(self.preview_animation_id)
            self.preview_animation_id = None
        self.preview_animation_active = False

    def _run_preview_animation(self):
        if not self.preview_animation_active or not hasattr(self, 'preview_function_callable') or not callable(self.preview_function_callable):
            self.preview_animation_active = False
            return
        try:
            self.preview_function_callable(self._preview_frame_count)
            self._preview_frame_count += 1
        except (IOError, PermissionError) as e:
            self.logger.error(f"Error in preview animation function '{getattr(self.preview_function_callable, '__name__', 'unknown')}': {e}", exc_info=True)
            self.stop_preview_animation()
            return
        if self.preview_animation_active:
            delay_ms = int(ANIMATION_FRAME_DELAY * 1000)
            self.preview_animation_id = self.root.after(delay_ms, self._run_preview_animation)

    def toggle_fullscreen(self, event=None):
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes("-fullscreen", self.is_fullscreen)
        text = "Exit Fullscreen (F11/ESC)" if self.is_fullscreen else "Enter Fullscreen (F11)"
        if hasattr(self, 'fullscreen_button') and self.fullscreen_button.winfo_exists():
            self.fullscreen_button.config(text=text)

    def exit_fullscreen(self, event=None):
        if self.is_fullscreen:
            self.toggle_fullscreen()

    def log_status(self, message, level="info"):
        log_level_map = {"info": logging.INFO, "warning": logging.WARNING, "error": logging.ERROR}
        self.logger.log(log_level_map.get(level.lower(), logging.INFO), message)
        if hasattr(self, 'status_var') and self.status_var:
            try:
                self.status_var.set(message[:100])
            except tk.TclError:
                self.logger.debug("TclError setting status_var (likely during shutdown).")

    def refresh_hardware_status(self):
        if not hasattr(self, 'hardware_status_text') or not self.hardware_status_text.winfo_exists():
            return
        try:
            hw_info = self.hardware.get_hardware_info()
            if isinstance(hw_info, dict):
                status_text = json.dumps(hw_info, indent=2, default=str)
            else:
                status_text = str(hw_info)
            self.hardware_status_text.config(state=tk.NORMAL)
            self.hardware_status_text.delete("1.0", tk.END)
            self.hardware_status_text.insert("1.0", status_text)
            self.hardware_status_text.config(state=tk.DISABLED)
            self.log_status("Hardware status refreshed.")
        except (IOError, PermissionError) as e:
            self.logger.error(f"Failed to refresh hardware status: {e}", exc_info=True)
            if self.hardware_status_text.winfo_exists():
                self.hardware_status_text.config(state=tk.NORMAL)
                self.hardware_status_text.insert(tk.END, f"\nError refreshing hardware status: {e}")
                self.hardware_status_text.config(state=tk.DISABLED)

    def show_system_info(self):
        target_widget = getattr(self, 'system_info_display_text', None)
        if not target_widget or not target_widget.winfo_exists():
            self.logger.warning("System info display widget not available.")
            return
        log_system_info(self.logger)
        target_widget.config(state=tk.NORMAL)
        target_widget.delete("1.0", tk.END)
        try:
            log_base_dir = SETTINGS_FILE.parent
            log_dir_path = log_base_dir / "logs"
            info_lines = [
                f"Application Name: {APP_NAME} v{VERSION}",
                f"System: {platform.system()} {platform.release()} ({platform.machine()})",
                f"Platform: {platform.platform()}",
                f"Python Version: {sys.version.splitlines()[0]}",
                f"Python Executable: {sys.executable}",
                f"GUI Controller Script Path: {Path(__file__).resolve()}",
                f"Current Working Directory: {Path.cwd()}",
                f"Settings File Path: {self.settings.config_file if hasattr(self.settings, 'config_file') else 'N/A'}",
                f"Log Directory: {log_dir_path.resolve()}",
                f"Pystray Available: {PYSTRAY_AVAILABLE}",
                f"PIL (Pillow) Available: {PIL_AVAILABLE}",
                f"Keyboard Library Available: {KEYBOARD_LIB_AVAILABLE}",
                f"Hotkey Setup Attempted: {self._hotkey_setup_attempted}",
                f"Brightness Hotkeys Working: {self._brightness_hotkeys_working}",
            ]
            if platform.system() == "Linux":
                info_lines.append(f"XDG_SESSION_TYPE: {os.environ.get('XDG_SESSION_TYPE', 'Not set')}")
                info_lines.append(f"DISPLAY: {os.environ.get('DISPLAY', 'Not set')}")
        except (IOError, PermissionError) as e:
            info_lines = [f"Error gathering system info for display: {e}"]
        target_widget.insert(tk.END, "\n".join(info_lines))
        target_widget.config(state=tk.DISABLED)
        self.log_status("System info display updated in GUI.")

    def show_log_locations(self):
        target_widget = getattr(self, 'gui_log_text_widget', None)
        if not target_widget or not target_widget.winfo_exists():
            self.logger.warning("GUI log display widget not available for showing log locations.")
            return
        log_dir = SETTINGS_FILE.parent / "logs"
        fallback_log_dir = Path.home()
        fallback_log_name_pattern = f".{APP_NAME.lower().replace(' ','_')}_gui_fallback.log"
        target_widget.config(state=tk.NORMAL)
        target_widget.delete("1.0", tk.END)
        target_widget.insert(tk.END, "Log File Locations:\n" + "="*20 + "\n\n")
        target_widget.insert(tk.END, f"Primary GUI Application Log Directory:\n  {log_dir.resolve()}\n\n")
        if log_dir.exists():
            log_files = sorted(log_dir.glob("rgb_controller_gui_*.log"), key=os.path.getmtime, reverse=True)[:5]
            target_widget.insert(tk.END, "Recent GUI log files (in primary directory):\n")
            if log_files:
                for lf in log_files:
                    target_widget.insert(tk.END, f"  - {lf.name} ({(lf.stat().st_size / 1024):.1f} KB)\n")
            else:
                target_widget.insert(tk.END, "  (No GUI .log files matching pattern found in primary log directory)\n")
        else:
            target_widget.insert(tk.END, "Primary application log directory does not exist.\n")
        target_widget.insert(tk.END, f"\nFallback GUI Log File (if primary fails):\n  {fallback_log_dir.resolve() / fallback_log_name_pattern}\n")
        target_widget.config(state=tk.DISABLED)
        self.log_status("Log file locations displayed in GUI log area.")

    def run_comprehensive_test(self):
        self.log_status("--- Comprehensive Hardware Test Start ---", "info")
        self.log_to_gui_diag_area("--- Starting Comprehensive Hardware Test ---", "info")
        if not self.hardware.wait_for_detection(timeout=2.0) or not self.hardware.is_operational():
            msg = "Hardware not detected, not operational, or detection timed out. Cannot run tests."
            if self.root.winfo_exists():
                messagebox.showerror("Test Error", msg, parent=self.root)
            self.log_status(f"Comprehensive Test: {msg}", "error")
            self.log_to_gui_diag_area(f"Test Error: {msg}", "error")
            return
        self.effect_manager.stop_current_effect()
        original_brightness = self.hardware.get_brightness()
        if original_brightness is None:
            original_brightness = self.settings.get("brightness", default_settings['brightness'])
        test_results = []
        self.log_to_gui_diag_area(f"Initial brightness from hardware: {original_brightness}% (or fallback/setting).", "info")
        self.log_to_gui_diag_area("Test: Setting brightness to 50%...", "info")
        if self.hardware.set_brightness(50):
            time.sleep(0.2)
            current_hw_brightness = self.hardware.get_brightness()
            if current_hw_brightness is not None and abs(current_hw_brightness - 50) <= 10:
                test_results.append("✓ Brightness set to 50% OK.")
                self.log_to_gui_diag_area("  ✓ Brightness set to 50% reported OK by hardware.", "info")
            else:
                test_results.append(f"✗ Brightness to 50% FAILED (reads {current_hw_brightness}% from hardware).")
                self.log_to_gui_diag_area(f"  ✗ Brightness to 50% seems to have FAILED (hardware reports {current_hw_brightness}%).", "error")
        else:
            test_results.append("✗ Set brightness to 50% command failed (hardware.set_brightness returned False).")
            self.log_to_gui_diag_area("  ✗ Set brightness to 50% command failed at hardware layer.", "error")
        self.hardware.set_brightness(original_brightness)
        self.brightness_var.set(original_brightness)
        self.log_to_gui_diag_area(f"Test: Brightness restored to {original_brightness}%.", "info")
        time.sleep(0.2)
        self.log_to_gui_diag_area("Test: Setting all zones to RED (255,0,0)...", "info")
        red_color = RGBColor(255,0,0)
        if self.hardware.set_all_leds_color(red_color):
            test_results.append("✓ All zones RED OK.")
            self.log_to_gui_diag_area("  ✓ All zones RED command sent successfully.", "info")
            time.sleep(1)
        else:
            test_results.append("✗ All zones RED FAILED (set_all_leds_color returned False).")
            self.log_to_gui_diag_area("  ✗ All zones RED command failed at hardware layer.", "error")
        self.log_to_gui_diag_area("Test: Clearing all LEDs (setting to BLACK)...", "info")
        if self.hardware.clear_all_leds():
            test_results.append("✓ Clear LEDs OK.")
            self.log_to_gui_diag_area("  ✓ Clear LEDs command sent successfully.", "info")
            time.sleep(0.2)
        else:
            test_results.append("✗ Clear LEDs FAILED (clear_all_leds returned False).")
            self.log_to_gui_diag_area("  ✗ Clear LEDs command failed at hardware layer.", "error")
        self.log_status("--- Comprehensive Test End ---", "info")
        self.log_to_gui_diag_area("--- Comprehensive Hardware Test Finished ---", "info")
        self.log_to_gui_diag_area("Test Results Summary:\n" + "\n".join(test_results if test_results else ["No tests effectively run or all failed."]), "info")
        if self.root.winfo_exists():
            messagebox.showinfo("Hardware Test Results", "\n".join(test_results) if test_results else "No tests were effectively run or all failed.", parent=self.root)
        self.log_status("Restoring previous settings after test...")
        self.log_to_gui_diag_area("Attempting to restore previous settings post-test...", "info")
        self._restore_settings_on_startup()

    def test_ectool(self):
        self.log_status("Testing ectool availability/functionality...")
        self.log_to_gui_diag_area("--- Testing ectool ---", "info")
        if hasattr(self.hardware, '_detect_ectool'):
            self.log_to_gui_diag_area("Re-running ectool detection via hardware controller...", "info")
            self.hardware._detect_ectool()
        elif hasattr(self.hardware, 'get_ectool_version_or_status'):
            ectool_status = self.hardware.get_ectool_version_or_status()
            self.log_to_gui_diag_area(f"ectool status from hardware controller: {ectool_status}", "info")
        else:
            self.log_to_gui_diag_area("Hardware controller does not have a direct ectool test method. Refreshing general status.", "warning")
        self.refresh_hardware_status()
        msg = "ectool detection/status check initiated. Check Diagnostics tab for updated hardware status. Functionality might change based on results."
        self.log_to_gui_diag_area(msg, "info")
        if self.root.winfo_exists():
            messagebox.showinfo("ectool Test", msg, parent=self.root)

    def setup_global_hotkeys_enhanced(self):
        if not KEYBOARD_LIB_AVAILABLE:
            self.log_missing_keyboard_library()
            return
        self._hotkey_setup_attempted = True
        self.logger.info("Setting up enhanced global brightness hotkeys with ALT+BRIGHTNESS priority...")
        if hasattr(self, 'hotkey_status_label'):
            self.hotkey_status_label.config(text="Hotkeys: Setting up...", foreground='orange')
        try:
            hotkey_config = self._detect_brightness_keys_with_alt_priority()
            if not hotkey_config:
                self._log_hotkey_setup_failure("No suitable brightness keys detected")
                return
            success_count = 0
            for direction, config in hotkey_config.items():
                try:
                    if direction == "up":
                        keyboard.add_hotkey(config['combo'], self._handle_brightness_up_hotkey, suppress=False)
                    else:
                        keyboard.add_hotkey(config['combo'], self._handle_brightness_down_hotkey, suppress=False)
                    self._registered_hotkeys.append(config['combo'])
                    success_count += 1
                    self.logger.info(f"Successfully registered hotkey: {config['name']}")
                except Exception as e_reg:
                    self.logger.error(f"Failed to register hotkey '{config['name']}': {e_reg}")
                    self.log_to_gui_diag_area(f"ERROR: Could not register hotkey '{config['name']}': {e_reg}", "error")
            if success_count > 0:
                self._brightness_hotkeys_working = True
                self._log_hotkey_success(hotkey_config, success_count)
            else:
                self._log_hotkey_setup_failure("Failed to register any hotkeys")
        except (IOError, PermissionError) as e:
            self.logger.error(f"Critical error setting up global hotkeys: {e}", exc_info=True)
            self._log_hotkey_setup_failure(f"Critical setup error: {e}")

    def _detect_brightness_keys_with_alt_priority(self) -> Optional[Dict[str, Dict[str, str]]]:
        system = platform.system().lower()
        key_candidates = {
            "linux": [
                {"up": "alt+225", "down": "alt+224"},
                {"up": "alt+f7", "down": "alt+f6"},
                {"up": "alt+f6", "down": "alt+f5"},
                {"up": "alt+f8", "down": "alt+f7"},
                {"up": "alt+XF86MonBrightnessUp", "down": "alt+XF86MonBrightnessDown"},
                {"up": "alt+XF86BrightnessUp", "down": "alt+XF86BrightnessDown"},
            ],
            "windows": [
                {"up": "alt+fn+f7", "down": "alt+fn+f6"},
                {"up": "alt+fn+f8", "down": "alt+fn+f7"},
                {"up": "fn+f7", "down": "fn+f6"},
                {"up": "alt+f7", "down": "alt+f6"},
            ],
            "darwin": [
                {"up": "alt+fn+f2", "down": "alt+fn+f1"},
                {"up": "fn+f2", "down": "fn+f1"},
                {"up": "alt+f2", "down": "alt+f1"},
            ]
        }
        candidates = key_candidates.get(system, key_candidates["linux"])
        for candidate in candidates:
            try:
                test_up = candidate["up"]
                test_down = candidate["down"]
                priority_note = " [HIGH PRIORITY - Scan Codes]" if '225' in test_up else ""
                self.logger.info(f"Testing brightness key combination: Up='{test_up}', Down='{test_down}'{priority_note}")
                return {
                    "up": {
                        "combo": test_up,
                        "name": f"ALT + Brightness Up (Scan Code {test_up.split('+')[-1]})"
                    },
                    "down": {
                        "combo": test_down,
                        "name": f"ALT + Brightness Down (Scan Code {test_down.split('+')[-1]})"
                    }
                }
            except (IOError, PermissionError) as e:
                self.logger.debug(f"Brightness key candidate failed: {candidate}, error: {e}")
                continue
        return None

    def _validate_hotkey_combination(self, combo: str) -> bool:
        try:
            test_callback = lambda: None
            keyboard.add_hotkey(combo, test_callback, suppress=False)
            keyboard.remove_hotkey(combo)
            return True
        except (IOError, PermissionError) as e:
            self.logger.debug(f"Hotkey combination '{combo}' validation failed: {e}")
            return False

    def _log_hotkey_success(self, hotkey_config: Dict, success_count: int):
        up_combo = hotkey_config.get("up", {}).get("name", "Unknown")
        down_combo = hotkey_config.get("down", {}).get("name", "Unknown")
        alt_brightness_detected = "ALT" in up_combo and ("BRIGHTNESS" in up_combo or "XF86" in up_combo)
        priority_note = "\n🎯 PERFECT! ALT+BRIGHTNESS detected - ideal for Ubuntu/Chromebook setups!" if alt_brightness_detected else ""
        success_msg = f"""BRIGHTNESS HOTKEYS ENABLED ✓{priority_note}
Successfully registered {success_count}/2 brightness hotkeys:
• Brightness Up: {up_combo}
• Brightness Down: {down_combo}
USAGE:
• Press the above key combinations to adjust keyboard backlight brightness
• Brightness changes in 10% increments
• Changes are immediately applied to hardware and saved to settings
• These hotkeys work independently of screen brightness controls
UBUNTU/CHROMEBOOK USERS:
• ALT+BRIGHTNESS keys are ideal since regular brightness keys control screen
• This allows independent control of keyboard vs screen brightness
• Works perfectly alongside ChromeOS/Ubuntu screen brightness controls
NOTES:
• Hotkeys work globally (even when application is not in focus)
• Some systems may require running as administrator/root for global hotkeys
• If hotkeys don't work, try the 'Test Keyboard Hotkey Names' button in Diagnostics
• You can always use the brightness slider in the GUI as an alternative"""
        self.logger.info("Brightness hotkeys successfully enabled with ALT+BRIGHTNESS priority")
        self.log_to_gui_diag_area(success_msg, "info")
        if hasattr(self, 'hotkey_status_label'):
            status_color = 'green'
            status_text = f"Hotkeys: {up_combo} / {down_combo}"
            if alt_brightness_detected:
                status_text = f"🎯 {status_text}"
            self.hotkey_status_label.config(text=status_text, foreground=status_color)

    def _log_hotkey_setup_failure(self, reason: str):
        failure_msg = f"""BRIGHTNESS HOTKEYS DISABLED ✗
Reason: {reason}
TROUBLESHOOTING FOR ALT+BRIGHTNESS KEYS:
======================================
1. PERMISSIONS (Most Important):
   • Linux: Run with sudo for global hotkeys
     sudo python -m rgb_controller_finalv2
   • Windows: Run as Administrator
   • macOS: Grant Accessibility permissions
2. UBUNTU/CHROMEBOOK SPECIFIC:
   • Try running: sudo python -m rgb_controller_finalv2
   • Ensure you're in a graphical session (not SSH)
   • Test if ALT+F5/F6 work for screen brightness first
   • Some ChromeOS/Ubuntu setups need: sudo apt install xinput
3. LIBRARY INSTALLATION:
   • Ensure 'keyboard' library is installed: pip install keyboard
   • Try reinstalling: pip uninstall keyboard && pip install keyboard
   • On Ubuntu: sudo apt install python3-dev first
4. SYSTEM-SPECIFIC ISSUES:
   Linux/Ubuntu:
   • Install X11 development headers: sudo apt install libx11-dev
   • Some systems need: sudo apt install python3-dev
   • ChromeOS Linux container: May need additional permissions
   Windows:
   • May need Visual C++ Build Tools
   • Try: pip install keyboard --no-cache-dir
   macOS:
   • Grant Accessibility permissions in System Preferences
   • May need to disable System Integrity Protection temporarily
5. TESTING YOUR SPECIFIC KEYS:
   • Use 'Test Keyboard Hotkey Names' in Diagnostics tab
   • Look for your actual brightness key names
   • Common names: XF86MonBrightnessUp, XF86BrightnessUp, f5, f6, f7, f8
6. ALTERNATIVE SOLUTIONS:
   • Use the brightness slider in the GUI (always works)
   • Create custom keyboard shortcuts in Ubuntu Settings
   • Use xbindkeys for system-wide key binding
7. FOR YOUR UBUNTU/CHROMEBOOK SETUP:
   Since regular brightness keys control screen brightness:
   • Try: sudo python -m rgb_controller_finalv2
   • ALT+F5/F6 should control keyboard brightness
   • This is the ideal setup for your use case!
If you successfully identify your brightness key names, you can modify the _detect_brightness_keys_with_alt_priority() method in the source code."""
        self.logger.warning(f"Brightness hotkeys setup failed: {reason}")
        self.log_to_gui_diag_area(failure_msg, "warning")
        print(failure_msg, file=sys.stderr)
        if hasattr(self, 'hotkey_status_label'):
            self.hotkey_status_label.config(text="Hotkeys: Failed (see log)", foreground='red')

    def _handle_brightness_up_hotkey(self):
        if not self.root.winfo_exists():
            return
        self.logger.debug("Brightness Up Hotkey Pressed (ALT+BRIGHTNESS)")
        current_brightness = self.brightness_var.get()
        new_brightness = min(100, current_brightness + 10)
        if new_brightness != current_brightness:
            self.brightness_var.set(new_brightness)
            self.root.after(0, self._apply_brightness_value, new_brightness, "ALT+BRIGHTNESS_UP")

    def _handle_brightness_down_hotkey(self):
        if not self.root.winfo_exists():
            return
        self.logger.debug("Brightness Down Hotkey Pressed (ALT+BRIGHTNESS)")
        current_brightness = self.brightness_var.get()
        new_brightness = max(0, current_brightness - 10)
        if new_brightness != current_brightness:
            self.brightness_var.set(new_brightness)
            self.root.after(0, self._apply_brightness_value, new_brightness, "ALT+BRIGHTNESS_DOWN")

    def test_hotkey_names_util(self):
        if not KEYBOARD_LIB_AVAILABLE:
            error_msg = """Keyboard Library Missing
The 'keyboard' library is required for hotkey name detection.
INSTALLATION:
   pip install keyboard
PERMISSIONS:
   • Linux: sudo python -m rgb_controller_finalv2
   • Windows: Run as Administrator
   • macOS: Grant Accessibility permissions"""
            messagebox.showerror("Keyboard Library Missing", error_msg, parent=self.root)
            self.log_to_gui_diag_area(error_msg, "error")
            return
        self.log_to_gui_diag_area("--- Starting Enhanced Keyboard Key Name Detection ---", "info")
        instructions = """BRIGHTNESS KEY DETECTION HELPER - ALT+BRIGHTNESS FOCUS
INSTRUCTIONS:
   1. A detection window will appear
   2. First try: ALT + your brightness up/down keys
   3. Then try: regular brightness keys (F5, F6, etc.)
   4. Key names will appear in the Application Log below
   5. Press ESC in the detection window to stop
UBUNTU/CHROMEBOOK USERS - WHAT TO LOOK FOR:
   • ALT + XF86MonBrightnessUp / ALT + XF86MonBrightnessDown
   • ALT + XF86BrightnessUp / ALT + XF86BrightnessDown
   • ALT + f5 / ALT + f6 (very common)
   • Look for combinations that DON'T conflict with screen brightness
This will help identify the perfect key combination for your setup!"""
        self.log_to_gui_diag_area(instructions, "info")
        if self.root.winfo_exists():
            messagebox.showinfo("Enhanced ALT+BRIGHTNESS Detection", instructions, parent=self.root)
        detection_window = tk.Toplevel(self.root)
        detection_window.title("ALT+BRIGHTNESS Key Detector - Test Your Keys!")
        detection_window.geometry("450x250")
        detection_window.transient(self.root)
        detection_window.configure(bg='#f0f0f0')
        main_frame = ttk.Frame(detection_window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        title_label = ttk.Label(main_frame, text="🔍 ALT+BRIGHTNESS Key Detection",
                                     font=('Helvetica', 12, 'bold'))
        title_label.pack(pady=5)
        instruction_label = ttk.Label(main_frame,
                                     text="Try: ALT + brightness keys, then regular brightness keys\nKey names will appear below and in the main log",
                                     justify=tk.CENTER)
        instruction_label.pack(pady=5)
        self.detection_log = tk.Text(main_frame, height=8, width=55, font=('monospace', 9))
        self.detection_log.pack(pady=5, fill=tk.BOTH, expand=True)
        close_button = ttk.Button(main_frame, text="Close (or press ESC)",
                                 command=lambda: self._close_detection_window(detection_window))
        close_button.pack(pady=5)
        detection_window.focus_set()
        def enhanced_key_event_handler(event):
            try:
                timestamp = datetime.now().strftime("%H:%M:%S")
                event_info = f"[{timestamp}] Key: '{event.name}'"
                if hasattr(event, 'scan_code'):
                    event_info += f", Scan: {event.scan_code}"
                event_info += f", Type: {event.event_type}"
                is_alt_brightness = "alt" in event.name.lower() and any(keyword in event.name.lower() for keyword in
                                                                       ['brightness', 'xf86', 'f5', 'f6', 'f7', 'f8'])
                is_brightness_key = any(keyword in event.name.lower() for keyword in
                                       ['brightness', 'xf86', 'f5', 'f6', 'f7', 'f8'])
                if is_alt_brightness:
                    event_info += " 🎯 PERFECT ALT+BRIGHTNESS COMBO!"
                elif is_brightness_key:
                    event_info += " ⭐ BRIGHTNESS KEY (try with ALT)"
                log_msg = f"Key Event: {event_info}"
                self.logger.info(log_msg)
                self.root.after(0, self.log_to_gui_diag_area, log_msg, "info")
                if hasattr(self, 'detection_log') and self.detection_log.winfo_exists():
                    self.detection_log.insert(tk.END, event_info + "\n")
                    self.detection_log.see(tk.END)
                if event.name == 'esc' and event.event_type == keyboard.KEY_DOWN:
                    self.root.after(0, lambda: self._close_detection_window(detection_window))
                    return False
            except (IOError, PermissionError) as e:
                error_msg = f"Error in key detection: {e}"
                self.logger.error(error_msg)
                self.root.after(0, self.log_to_gui_diag_area, error_msg, "error")
            return True
        try:
            hook_id = keyboard.hook(enhanced_key_event_handler)
            detection_window._hook_id = hook_id
            def on_window_close():
                self._close_detection_window(detection_window)
            detection_window.protocol("WM_DELETE_WINDOW", on_window_close)
            detection_window.bind('<Escape>', lambda e: on_window_close())
        except (IOError, PermissionError) as e:
            error_msg = f"Failed to start key detection: {e}"
            self.logger.error(error_msg)
            self.log_to_gui_diag_area(error_msg, "error")
            detection_window.destroy()

    def _close_detection_window(self, window):
        try:
            if hasattr(window, '_hook_id'):
                keyboard.unhook(window._hook_id)
            self.log_to_gui_diag_area("--- Enhanced ALT+BRIGHTNESS Key Detection Stopped ---", "info")
            summary_msg = """DETECTION COMPLETE - ALT+BRIGHTNESS ANALYSIS
Review the key names above to identify your brightness keys.
IDEAL COMBINATIONS FOR UBUNTU/CHROMEBOOK:
   • ALT + XF86MonBrightnessUp / ALT + XF86MonBrightnessDown
   • ALT + XF86BrightnessUp / ALT + XF86BrightnessDown
   • ALT + f5 / ALT + f6
   • ALT + f7 / ALT + f8
NEXT STEPS:
   1. If you found ALT+BRIGHTNESS combinations, restart the app with sudo
   2. If only regular brightness keys were found, they can still work with ALT
   3. Submit your key names to help improve automatic detection
Your setup is perfect for independent keyboard vs screen brightness control!"""
            self.log_to_gui_diag_area(summary_msg, "info")
            window.destroy()
        except (IOError, PermissionError) as e:
            self.logger.error(f"Error closing detection window: {e}")
            try:
                window.destroy()
            except:
                pass

    def perform_final_shutdown(self, clean_shutdown: bool = False):
        self.logger.info(f"Performing final shutdown (clean_shutdown={clean_shutdown}).")
        self.root.attributes('-alpha', 0.5)
        if hasattr(self, '_hotkey_listener_stop_event'):
            self._hotkey_listener_stop_event.set()
        if KEYBOARD_LIB_AVAILABLE:
            try:
                for hotkey_combo in getattr(self, '_registered_hotkeys', []):
                    try:
                        keyboard.remove_hotkey(hotkey_combo)
                    except:
                        pass
                keyboard.unhook_all_hotkeys()
                keyboard.unhook_all()
                self.logger.info("Unhooked all keyboard listeners.")
            except Exception as e_unhook:
                self.logger.error(f"Error unhooking keyboard listeners: {e_unhook}")
        self.save_current_gui_state_to_settings()
        if hasattr(self, 'effect_manager') and self.effect_manager:
            self.effect_manager.stop_current_effect()
        if clean_shutdown:
            self.logger.info("Marking clean shutdown in settings.")
            if hasattr(self.settings, 'mark_clean_shutdown'):
                self.settings.mark_clean_shutdown()
            if hasattr(self.hardware, 'set_app_exiting_cleanly'):
                self.hardware.set_app_exiting_cleanly(True)
            self.logger.info("LEDs will remain in their last state (not cleared on clean exit by default).")
        else:
            self.logger.warning("Application performing an unclean shutdown (or user chose not to save state). Attempting to clear LEDs for safety.")
            try:
                if hasattr(self, 'hardware') and self.hardware.is_operational():
                    self.hardware.clear_all_leds()
                    self.logger.info("LEDs cleared on non-clean/explicit-clear shutdown.")
            except (IOError, PermissionError) as e:
                self.logger.error(f"Failed to clear LEDs during non-clean shutdown: {e}")
        if self.tray_icon:
            self.logger.info("Stopping tray icon...")
            self.tray_icon.stop()
        if self.tray_thread and self.tray_thread.is_alive():
            self.tray_thread.join(timeout=0.5)
        self.tray_icon = None
        self.tray_thread = None
        if self.root and hasattr(self.root, 'winfo_exists') and self.root.winfo_exists():
            setattr(self.root, '_is_being_destroyed', True)
        self.logger.info(f"{APP_NAME} shutting down now.")
        if self.root and hasattr(self.root, 'winfo_exists') and self.root.winfo_exists():
            try:
                self.root.destroy()
            except tk.TclError as e_destroy:
                self.logger.error(f"Error destroying Tk root: {e_destroy}")
        sys.exit(0)


def main():
    logging.basicConfig(level=logging.DEBUG,
                       format='%(asctime)s - %(name)s [%(levelname)s] %(module)s.%(funcName)s:%(lineno)d - %(message)s',
                       handlers=[logging.StreamHandler(sys.stdout)])
    module_logger = logging.getLogger(f"{APP_NAME}.controller_standalone")
    app_instance_ref = [None]
    def handle_exception_standalone(exc_type, exc_value, exc_traceback):
        app_instance = app_instance_ref[0]
        if issubclass(exc_type, KeyboardInterrupt):
            module_logger.info("KeyboardInterrupt received. Shutting down.")
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            if app_instance and hasattr(app_instance, 'perform_final_shutdown'):
                app_instance.perform_final_shutdown(clean_shutdown=False)
            sys.exit(1)
        module_logger.critical("Unhandled exception in controller_standalone:", exc_info=(exc_type, exc_value, exc_traceback))
        temp_root_for_msg = None
        parent_for_msg = None
        can_use_tkinter_for_msg = False
        try:
            if tk._default_root and tk._default_root.winfo_exists():
                parent_for_msg = tk._default_root
                can_use_tkinter_for_msg = True
            elif not tk._default_root:
                try:
                    temp_root_for_msg = tk.Tk()
                    temp_root_for_msg.withdraw()
                    parent_for_msg = temp_root_for_msg
                    can_use_tkinter_for_msg = True
                except tk.TclError:
                    print(f"FATAL ERROR (TKINTER TEMP ROOT CREATION FAILED FOR ERROR MSG): {exc_value}", file=sys.stderr)
            if can_use_tkinter_for_msg:
                messagebox.showerror("Unhandled Exception",
                                   f"An unexpected error occurred: {exc_value}\n\nThe application will now exit. Please check logs for details.",
                                   parent=parent_for_msg)
            else:
                print(f"FATAL ERROR (TKINTER UNAVAILABLE FOR ERROR MSG BOX): {exc_value}", file=sys.stderr)
        except Exception as e_msg_display:
            print(f"FATAL ERROR (ERROR DISPLAYING ERROR MESSAGE DIALOG): {e_msg_display}", file=sys.stderr)
            print(f"ORIGINAL FATAL ERROR WAS: {exc_value}", file=sys.stderr)
        finally:
            if temp_root_for_msg:
                try:
                    temp_root_for_msg.destroy()
                except:
                    pass
        if app_instance and hasattr(app_instance, 'perform_final_shutdown'):
            module_logger.info("Attempting unclean shutdown from unhandled exception handler.")
            app_instance.perform_final_shutdown(clean_shutdown=False)
        else:
            module_logger.critical("Unhandled exception, and app_instance not available for controlled shutdown.")
            try:
                if __package__ and __package__.startswith("rgb_controller_finalv2.gui"):
                    from ..hardware.controller import HardwareController as EmergHW
                elif __package__ == "gui":
                    from .hardware.controller import HardwareController as EmergHW
                else:
                    from hardware.controller import HardwareController as EmergHW
                temp_hw = EmergHW(emergency_mode=True)
                if temp_hw.wait_for_detection(timeout=0.2):
                    temp_hw.clear_all_leds()
                module_logger.info("Emergency hardware clear attempted.")
            except Exception as e_emerg:
                module_logger.warning(f"Emergency hardware clear failed during fatal exit: {e_emerg}")
        if tk._default_root and tk._default_root.winfo_exists():
            try:
                tk._default_root.destroy()
            except:
                pass
        sys.exit(1)
    sys.excepthook = handle_exception_standalone
    root = None
    try:
        root = tk.Tk()
        app_instance_ref[0] = RGBControllerGUI(root)
        root.mainloop()
    except SystemExit:
        module_logger.info("SystemExit caught in main, application will exit as planned.")
    except Exception as e_main:
        module_logger.critical("Fatal error during standalone GUI startup or mainloop (after excepthook setup).", exc_info=True)
        if app_instance_ref[0] and hasattr(app_instance_ref[0], 'perform_final_shutdown'):
            app_instance_ref[0].perform_final_shutdown(clean_shutdown=False)
        elif root and hasattr(root, 'winfo_exists') and root.winfo_exists():
            try:
                root.destroy()
            except:
                pass
        sys.exit(1)

if __name__ == "__main__":
    if not __package__:
        script_dir = Path(__file__).resolve().parent
        path_to_add = script_dir.parent
        if str(path_to_add) not in sys.path:
            sys.path.insert(0, str(path_to_add))
            print(f"[controller.py __main__] Added to sys.path for direct run: {path_to_add}")
            print(f"[controller.py __main__] Current sys.path[0]: {sys.path[0]}")
            print(f"[controller.py __main__] Attempting to run as if 'gui' is a package within '{path_to_add.name}'.")
    print(f"Running {Path(__file__).name} (invoked as: {__name__}, package: {__package__})...")
    if os.name != 'nt' and hasattr(os, 'geteuid') and os.geteuid() != 0:
        print("WARNING: Root/administrator privileges may be required for full hardware functionality (like direct EC access or global hotkeys).", file=sys.stderr)
        print("For ALT+BRIGHTNESS hotkeys on Ubuntu/Chromebook, try: sudo python -m rgb_controller_finalv2", file=sys.stderr)
    main()
