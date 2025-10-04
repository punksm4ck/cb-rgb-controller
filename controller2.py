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
from .utils.system_info import log_system_info, log_error_with_context


class RGBControllerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.logger = self.setup_logging()
        self.pystray_icon_image: Optional[Image.Image] = None
        self.tk_icon_photoimage: Optional[tk.PhotoImage] = None

        try:
            self._initialize_core_components()
        except (IOError, PermissionError) as e:
            self._handle_critical_initialization_error(e)
        except tk.TclError as e:
            self.logger.debug(f"A tkinter widget-related error occurred (likely during shutdown): {e}")
    # ... often safe to ignore during shutdown ...


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

    def log_missing_keyboard_library(self):
        self.logger.warning("Keyboard library not available. Hotkeys disabled.")

    def _stop_all_visuals_and_clear_hardware(self):
        """Stops software effects and attempts to clear hardware patterns."""
        self.logger.debug("Stopping all software effects and GUI previews.")
        self.effect_manager.stop_current_effect()
        self.stop_preview_animation()
        self.hardware.clear_all_leds()
        self.update_preview_keyboard(colors=[RGBColor(0,0,0)] * NUM_ZONES)
        self.logger.debug("All visuals stopped and hardware cleared.")

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

    def _initialize_core_components(self):
        """Initializes core application components like settings and hardware."""
        self.settings = SettingsManager()
        self.hardware = HardwareController(self.settings.get("last_control_method"))
        self.effect_manager = EffectManager(self.hardware, self.settings)
        self.logger.info("Core components initialized.")

    def create_desktop_launcher(self):
        if platform.system() != "Linux":
            messagebox.showinfo("Not Supported", "Desktop launcher creation is currently only supported on Linux.", parent=self.root)
            return

        try:
            python_exe = sys.executable
            project_root_dir = Path(__file__).resolve().parent.parent
            module_to_run = project_root_dir.name
            working_dir_for_launcher = project_root_dir.parent
            exec_cmd = f'{shlex.quote(str(python_exe))} -m {shlex.quote(module_to_run)}'

            # Find icon
            icon_path = project_root_dir / "assets" / "icon.png"
            icon_name_or_path = str(icon_path.resolve()) if icon_path.exists() else "input-keyboard"

            content = (f"[Desktop Entry]\nVersion=1.0\nName={APP_NAME}\nComment=Control RGB Keyboard Lighting\n"
                       f"Exec={exec_cmd}\nIcon={icon_name_or_path}\nTerminal=false\nType=Application\n"
                       f"Categories=Utility;Settings;HardwareSettings;\nPath={str(working_dir_for_launcher)}\n")

            # --- Write to multiple locations ---
            locations_to_try = [
                Path.home() / ".local/share/applications",
                Path.home() / "Desktop"
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
                messagebox.showerror("Launcher Error", "Could not create launcher in any location.\nPlease check permissions.", parent=self.root)

        except (IOError, PermissionError) as e:
            self.logger.error(f"Could not determine paths for launcher: {e}", exc_info=True)
            messagebox.showerror("Launcher Error", f"Could not determine script paths: {e}", parent=self.root)

    def log_missing_keyboard_library(self):
        """Provide detailed instructions for installing keyboard library"""

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

        # Initialize all zones to off (black)
        for i in range(NUM_ZONES):
            self.zone_colors[i] = RGBColor(0, 0, 0)

        # Simulate realistic key press patterns for preview
        if hasattr(self, 'key_grid') and self.key_grid:
            self._simulate_realistic_key_presses_for_reactive_preview(frame_count, base_color_rgb, is_rainbow)
        else:
            self._simulate_zone_based_reactive_preview(frame_count, base_color_rgb, is_rainbow, speed_multiplier)

        self.update_preview_keyboard()

    def _simulate_realistic_key_presses_for_reactive_preview(self, frame_count, base_color, is_rainbow):
        """Simulate realistic typing patterns for reactive preview"""
        if not hasattr(self, 'key_grid') or not self.key_grid:
            return

        # Clear all keys first
        for row in self.key_grid:
            for key_info in row:
                try:
                    canvas = self.preview_canvas
                    canvas.itemconfig(key_info['element'], fill='#404040', outline='#606060', width=1)
                except:
                    pass

        # Simulate typing patterns
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

        # Light up active keys
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
                    self.zone_colors[i] = RGBColor(0, 0, 0)

    def preview_anti_reactive(self, frame_count: int):
        """Preview anti-reactive effect - all on except when keys are pressed"""
        try:
            base_color_rgb = RGBColor.from_hex(self.effect_color_var.get())
        except ValueError:
            base_color_rgb = RGBColor(255, 255, 255)

        is_rainbow = self.effect_rainbow_mode_var.get()
        speed_multiplier = self.get_hardware_synchronized_speed()

        # Initialize all zones to on
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

        # Start with all keys lit up
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

        # Same patterns but turn OFF the pressed keys
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
                self.zone_colors[i] = RGBColor(0, 0, 0)  # Off when pressed

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

Note: Global hotkeys require elevated privileges to capture system-wide key events.
This is a security feature of operating systems.
        """
        self.logger.warning("Keyboard library not available. ALT+Brightness hotkeys disabled.")
        self.log_to_gui_diag_area(missing_msg.strip(), "warning")
        print(missing_msg, file=sys.stderr)

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

        self.preview_led_states = [RGBColor(0,0,0)] * TOTAL_LEDS
        self.update_preview_leds()
        self.logger.debug("All visuals stopped and hardware clear attempted.")

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

        # Enhanced icon setup with better error handling
        self.setup_application_icons()

        self.style = ttk.Style(self.root)
        try:
            themes = self.style.theme_names()
            desired_themes = ['clam', 'alt', 'default'] # Some common good-looking themes
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
                # Create a more appealing RGB icon
                draw.rectangle((0, 0, icon_size//2, icon_size//2), fill="#FF4444")      # Red
                draw.rectangle((icon_size//2, 0, icon_size, icon_size//2), fill="#44FF44")  # Green
                draw.rectangle((0, icon_size//2, icon_size//2, icon_size), fill="#4444FF")  # Blue
                draw.rectangle((icon_size//2, icon_size//2, icon_size, icon_size), fill="#FF44FF")  # Magenta

                # Add a border
                draw.rectangle((0, 0, icon_size, icon_size), outline="#FFFFFF", width=2)

                self.pystray_icon_image = temp_pil_image
                self.logger.debug("Created default PIL image for pystray icon.")

                try:
                    # For Tkinter, use a smaller size
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

        # Add hotkey status indicator
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
                delta = event.delta // 120 # Windows
            elif sys.platform == "darwin":
                delta = event.delta # macOS
            else: # Linux
                if event.num == 4:
                    delta = -1 # Scroll up
                elif event.num == 5:
                    delta = 1 # Scroll down
            if delta != 0:
                c.yview_scroll(delta, "units")

        for widget in [canvas, scrollable_frame]: # Bind to both canvas and inner frame
            widget.bind_all("<MouseWheel>", _on_mousewheel) # Use bind_all for wider capture if needed, or stick to bind
            widget.bind("<Button-4>", _on_mousewheel) # For Linux scroll up
            widget.bind("<Button-5>", _on_mousewheel) # For Linux scroll down
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
        effects_to_remove = {"Rainbow Wave", "Rainbow Breathing"} # Example: if these are handled by rainbow mode toggle now
        filtered_effects = [effect for effect in all_effects if effect not in effects_to_remove]
        available_effects = ["None"] + filtered_effects + ["Reactive", "Anti-Reactive"] # Ensure "None" is an option

        effect_combo = ttk.Combobox(effect_frame, textvariable=self.effect_var, values=available_effects, state="readonly", width=25)
        effect_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        effect_combo.bind("<<ComboboxSelected>>", self.on_effect_change)
        ttk.Button(effect_frame, text="Start Effect", command=self.start_current_effect, style="Accent.TButton").pack(side=tk.LEFT, padx=5)

        color_frame = ttk.LabelFrame(parent, text="Effect Color Options", padding=10)
        color_frame.pack(fill=tk.X, padx=5, pady=5, expand=True)
        self.effect_color_rainbow_frame = ttk.Frame(color_frame) # Container for both check and color picker

        self.rainbow_mode_check = ttk.Checkbutton(self.effect_color_rainbow_frame, text="Use Rainbow Mode for Effect", variable=self.effect_rainbow_mode_var, command=self.on_rainbow_mode_change)
        # self.rainbow_mode_check.pack(side=tk.LEFT, padx=(0,10)) # Packing handled by update_effect_controls_visibility

        self.effect_color_frame = ttk.Frame(self.effect_color_rainbow_frame) # Specific frame for color picker parts
        self.effect_color_display = tk.Label(self.effect_color_frame, width=10, height=2, bg=self.effect_color_var.get(), relief=tk.SUNKEN, borderwidth=2)
        self.effect_color_display.pack(side=tk.LEFT, padx=10, pady=5)
        ttk.Button(self.effect_color_frame, text="Choose Effect Color", command=self.choose_effect_color).pack(side=tk.LEFT, padx=5, pady=5)
        # self.effect_color_frame.pack(side=tk.LEFT, fill=tk.X, expand=True) # Packing handled by update_effect_controls_visibility

        self.update_effect_controls_visibility() # Initial setup of visibility
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
        ttk.Radiobutton(method_lf, text="EC Direct (Advanced)", variable=self.control_method_var, value="ec_direct", command=self.save_control_method, state=tk.NORMAL).pack(anchor=tk.W, padx=5) # Enabled

        display_lf = ttk.LabelFrame(frame, text="Display Options", padding="10")
        display_lf.pack(fill=tk.X, pady=(0, 10), anchor="n")
        self.fullscreen_button = ttk.Button(display_lf, text="Enter Fullscreen (F11)", command=self.toggle_fullscreen)
        self.fullscreen_button.pack(anchor=tk.W, pady=2, padx=5)
        ttk.Label(display_lf, text="Press ESC to exit fullscreen.", font=('Helvetica', 9, 'italic')).pack(anchor=tk.W, padx=5)

        # Enhanced tray settings with dependency info
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

            # Status indicator
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
            # Detailed instructions for missing dependencies
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
        if KEYBOARD_LIB_AVAILABLE: # Add button to test hotkey names
            ttk.Button(log_actions_frame, text="Test Keyboard Hotkey Names", command=self.test_hotkey_names_util).pack(side=tk.LEFT, padx=5)

        test_frame = ttk.LabelFrame(diag_pane, text="Hardware Tests (Use with Caution)", padding=10)
        diag_pane.add(test_frame, weight=0) # test_frame has less weight
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

        # Compact rectangular keyboard dimensions - much narrower background
        canvas_width = 480  # Reduced from 900 to ~half width
        canvas_height = 140  # Slightly reduced height for perfect fit
        current_canvas = tk.Canvas(canvas_container, width=canvas_width, height=canvas_height, bg='#1a1a1a', relief=tk.GROOVE, borderwidth=2)
        current_canvas.pack()

        if title == "Effect Preview": # This is the primary canvas for dynamic effect previews
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

        # Get the elements list to store in
        if elements_list == 'static_keyboard_elements':
            elements = self.static_keyboard_elements = []
        elif elements_list == 'zone_keyboard_elements':
            elements = self.zone_keyboard_elements = []
        else:
            elements = self.preview_keyboard_elements = []

        # Clear existing elements
        canvas.delete("all")
        elements.clear()

        # Enhanced dimensions for realistic keyboard
        canvas_width = 480
        canvas_height = 140

        margin_x = 20
        margin_y = 12
        keyboard_width = canvas_width - (margin_x * 2)
        keyboard_height = 90

        # Create a grid-based system for realistic zone mapping
        rows = 6
        cols_per_row = [15, 15, 15, 15, 15, 15]  # Keys per row
        key_width = keyboard_width / 15  # Standardized key width
        key_height = 14
        key_gap = 1

        start_x = margin_x
        start_y = margin_y

        # Create realistic key mapping that supports both horizontal and vertical effects
        self.key_grid = []  # Store key positions for advanced effects

        for row_idx in range(rows):
            row_keys = []
            current_y = start_y + row_idx * (key_height + key_gap)

            for col_idx in range(cols_per_row[row_idx]):
                current_x = start_x + col_idx * (key_width + key_gap)

                # Create key rectangle
                key_rect = canvas.create_rectangle(
                    current_x, current_y,
                    current_x + key_width, current_y + key_height,
                    fill='#404040', outline='#707070', width=1
                )

                # Assign zones based on both horizontal and vertical position
                # This enables more realistic effects
                horizontal_zone = min(3, int((col_idx / cols_per_row[row_idx]) * 4))
                vertical_zone = min(3, int((row_idx / rows) * 4))

                # For most effects, use horizontal zones
                primary_zone = horizontal_zone

                # Store detailed position info for advanced effects
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

        # Add zone divider lines
        for zone_idx in range(1, 4):
            divider_x = start_x + (zone_idx * keyboard_width / 4)
            divider_line = canvas.create_line(
                divider_x, start_y, divider_x, start_y + keyboard_height,
                fill='#555555', width=1, dash=(2, 2)
            )
            elements.append({'element': divider_line, 'zone': -1, 'type': 'divider'})

        # Add zone labels
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
            # Update each keyboard element based on its zone
            for elem_info in elements:
                # --- PATCH: Add type check to prevent TypeError on malformed data ---
                if isinstance(elem_info, dict) and elem_info.get('type') == 'key':
                    zone = elem_info['zone']
                    if 0 <= zone < len(self.zone_colors):
                        color = self.zone_colors[zone].to_hex()

                        # Add subtle brightness effect for better visual feedback
                        zone_color_obj = self.zone_colors[zone]
                        if zone_color_obj.r + zone_color_obj.g + zone_color_obj.b > 50:
                            # Key is lit - add subtle glow effect with brighter outline
                            canvas.itemconfig(elem_info['element'], fill=color, outline='#ffffff', width=2)
                        else:
                            # Key is off - darker appearance
                            canvas.itemconfig(elem_info['element'], fill=color, outline='#606060', width=1)
                    else:
                        # Default inactive key appearance
                        canvas.itemconfig(elem_info['element'], fill='#303030', outline='#505050', width=1)
                elif isinstance(elem_info, dict) and elem_info.get('type') == 'divider':
                    # Update zone dividers based on activity
                    canvas.itemconfig(elem_info['element'], fill='#666666')
        except tk.TclError:
            # Canvas might be destroyed during shutdown
            pass

    def update_preview_leds(self):
        """Legacy method for compatibility - now redirects to keyboard preview"""
        self.update_preview_keyboard()

    # ... All other methods from the backup file are required here ...
    # (setup_gui_logging, all event handlers, all preview functions, etc.)

def main():
    """Main function to initialize and run the GUI application."""
    root = tk.Tk()
    app = RGBControllerGUI(root)
    # The Tkinter event loop listens for events and keeps the GUI running.
    root.mainloop()

if __name__ == "__main__":
    """
    This block is the standard entry point for Python scripts.
    It ensures that the `main()` function is called only when the script is executed directly
    and not when it is imported as a module into another script.
    This practice makes the code more modular and reusable.
    """
    try:
        main()
    except Exception as e:
        # A final, general exception handler for unhandled errors
        print(f"An unhandled critical error occurred: {e}", file=sys.stderr)
        log_error_with_context(e, sys.exc_info(), f"{APP_NAME}.Main")
        sys.exit(1)
