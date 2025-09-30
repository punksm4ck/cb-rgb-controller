#!/usr/bin/env python3
"""Hardware control implementation with full 4-zone RGB support - Fixed Version"""

import os
import time
import threading
import subprocess
import logging
import re
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path

from ..core.rgb_color import RGBColor
from ..core.exceptions import KeyboardControlError, HardwareError, ResourceError, ConfigurationError
from ..core.constants import NUM_ZONES, LEDS_PER_ZONE, ECTOOL_INTER_COMMAND_DELAY, APP_NAME, TOTAL_LEDS

from ..utils.decorators import safe_execute
from ..utils.input_validation import SafeInputValidation

# --- MODIFICATION: Use the system ectool ---
ECTOOL_EXECUTABLE = "/usr/local/bin/ectool"

# Based on constants.py LEDS_PER_ZONE = 3 and ectool help for `rgbkbd <key> <RGB> [<RGB> ...]`
# this implies a single command can set these 3 LEDs if three <RGB> values are provided.
HW_LEDS_PER_ZONE_COMMAND = 3

class HardwareController:
    def __init__(self, parent_logger, last_control_method: str):
        self.logger = parent_logger.getChild('HardwareController')
        self.detection_complete = threading.Event()
        self.ectool_available = False
        self.ec_direct_available = False # This will be True if EC Direct is implemented and verified
        self.hardware_ready = False
        self.preferred_control_method: Optional[str] = last_control_method
        self.active_control_method: str = "none"

        self.capabilities: Dict[str, bool] = {
            "ectool_present": False, "ectool_version_ok": False,
            "ectool_rgbkbd_functional": False,
            "ectool_rgbkbd_clear_functional": False,
            "ectool_rgbkbd_demo_off_functional": False,
            "ectool_pwmsetkblight_ok": False,
            "ectool_pwmgetkblight_ok": False,
            "ec_direct_access_ok": False,
        }

        self.current_brightness = 100
        self._lock = threading.RLock()
        self._zone_colors_cache: List[RGBColor] = [RGBColor(0,0,0) for _ in range(NUM_ZONES)]
        self._is_effect_running = False
        self._app_exiting_cleanly = False
        self._reactive_mode_enabled = False
        self._reactive_color = RGBColor(255, 255, 255)
        self._anti_reactive_mode = False

        self._detection_thread = threading.Thread(target=self._perform_hardware_detection, daemon=True, name="HardwareDetectionThread")
        self._detection_thread.start()

    def set_control_method_preference(self, method: str):
        self.logger.info(f"Control method preference received from GUI: {method}")
        if method in ["ectool", "ec_direct"]:
            with self._lock:
                self.preferred_control_method = method
                if self.detection_complete.is_set():
                    self.logger.info("Re-evaluating active control method due to preference change post-detection.")
                    self._update_active_method_based_on_preference()
        else:
            self.logger.warning(f"Invalid control method preference received: {method}")

    def _update_active_method_based_on_preference(self):
        new_active_method = "none"
        preferred = self.preferred_control_method

        self.logger.info(f"Updating active method. Preferred: '{preferred}', ectool_available: {self.ectool_available}, ec_direct_framework_ok: {self.capabilities.get('ec_direct_access_ok')}, ec_direct_actually_available: {self.ec_direct_available}")

        if preferred == "ec_direct":
            if self.ec_direct_available:
                new_active_method = "ec_direct"
                self.logger.info("EC Direct is available and preferred. Setting as active.")
            elif self.capabilities.get("ec_direct_access_ok"):
                new_active_method = "ec_direct"
                self.logger.info("EC Direct framework is selected (preferred). Actual implementation is PENDING. Functions will log warnings.")
            elif self.ectool_available:
                new_active_method = "ectool"
                self.logger.warning("EC Direct preferred but not available/selected. Falling back to ectool.")
            else:
                self.logger.error("EC Direct preferred, but neither EC Direct framework nor ectool are available.")
        elif preferred == "ectool":
            if self.ectool_available:
                new_active_method = "ectool"
                self.logger.info("ectool is available and preferred (or fallback). Setting as active.")
            elif self.ec_direct_available:
                new_active_method = "ec_direct"
                self.logger.warning("ectool preferred but not available. Oddly falling back to fully available EC Direct.")
            elif self.capabilities.get("ec_direct_access_ok"):
                new_active_method = "ec_direct"
                self.logger.warning("ectool preferred but not available. Falling back to EC Direct framework (IMPLEMENTATION PENDING).")
            else:
                self.logger.error("ectool preferred, but neither ectool nor EC Direct framework are available.")
        else:
            if self.ectool_available:
                new_active_method = "ectool"
            elif self.ec_direct_available:
                new_active_method = "ec_direct"
            elif self.capabilities.get("ec_direct_access_ok"):
                new_active_method = "ec_direct"
            self.logger.info(f"No strong preference or default logic applied. Resulting active method: '{new_active_method}'")

        if self.active_control_method != new_active_method:
            self.logger.info(f"Active control method changed from '{self.active_control_method}' to '{new_active_method}'.")
        self.active_control_method = new_active_method

        if self.active_control_method == "ectool":
            self.hardware_ready = self.ectool_available
        elif self.active_control_method == "ec_direct":
            self.hardware_ready = self.capabilities.get("ec_direct_access_ok", False)
        else:
            self.hardware_ready = False
        self.logger.info(f"Hardware_ready status: {self.hardware_ready} (Active method: {self.active_control_method})")


    @safe_execute(max_attempts=1, severity="critical")
    def _perform_hardware_detection(self) -> None:
        self.logger.info(f"Starting hardware detection process. Initial preferred method: {self.preferred_control_method}")
        time.sleep(0.1)
        self.logger.info(f"Proceeding with detection. Current preferred method (after potential GUI update): {self.preferred_control_method}")

        try:
            self._detect_ectool()
            self._detect_ec_direct()

            self._update_active_method_based_on_preference()

            if not self.hardware_ready:
                self.logger.warning("No primary RGB control methods detected, functional, or selected after all checks.")
            else:
                self.logger.info(f"Hardware detection checks completed. Active method: '{self.active_control_method}'.")
        except Exception as e:
            self.logger.error(f"Critical error during hardware detection: {e}", exc_info=True)
            self.hardware_ready = False
            self.active_control_method = "none"
        finally:
            self.detection_complete.set()
            self.logger.info(f"Hardware detection process finished. ectool_available={self.ectool_available}, ec_direct_framework_ok={self.capabilities.get('ec_direct_access_ok')}, ec_direct_actually_available={self.ec_direct_available}, hardware_ready={self.hardware_ready}, active_method='{self.active_control_method}'")
            self.log_capabilities()

    def _detect_ectool(self) -> None:
        self.logger.debug(f"Attempting to detect ectool using executable: '{ECTOOL_EXECUTABLE}'")
        self.ectool_available = False

        if not Path(ECTOOL_EXECUTABLE).is_file():
            self.logger.error(f"ectool executable not found at specified path: {ECTOOL_EXECUTABLE}")
            self.capabilities["ectool_present"] = False; return

        self.logger.info(f"Using ectool at: {ECTOOL_EXECUTABLE}")
        self.capabilities["ectool_present"] = True

        try:
            self.logger.debug("Testing 'ectool version'...")
            success_version, stdout_version, stderr_version = self._run_ectool_cmd_internal(['version'], timeout=3.0, silent=False)
            self.capabilities["ectool_version_ok"] = success_version
            if not success_version:
                self.logger.warning(f"ectool 'version' command failed. Stderr: {stderr_version}, Stdout: {stdout_version}"); return

            self.logger.debug("Testing 'ectool rgbkbd 0 0' (basic single LED to black)...")
            success_rgbkbd_single, _, stderr_rgbkbd_single = self._run_ectool_cmd_internal(['rgbkbd', '0', '0'], timeout=2.0, silent=False)
            self.capabilities["ectool_rgbkbd_functional"] = success_rgbkbd_single
            if not success_rgbkbd_single: self.logger.warning(f"ectool 'rgbkbd <key> <RGB>' basic test failed. Stderr: {stderr_rgbkbd_single}")

            self.logger.debug("Testing 'ectool rgbkbd clear 0' (clear to black)...")
            success_clear, _, stderr_clear = self._run_ectool_cmd_internal(['rgbkbd', 'clear', '0'], timeout=3.0, silent=False)
            self.capabilities["ectool_rgbkbd_clear_functional"] = success_clear
            if not success_clear: self.logger.warning(f"ectool 'rgbkbd clear <RGB>' test failed. Stderr: {stderr_clear}")

            self.logger.debug("Testing 'ectool rgbkbd demo 0' (demo off)...")
            success_demo_off, _, stderr_demo_off = self._run_ectool_cmd_internal(['rgbkbd', 'demo', '0'], timeout=2.0, silent=False)
            self.capabilities["ectool_rgbkbd_demo_off_functional"] = success_demo_off
            if not success_demo_off: self.logger.warning(f"ectool 'rgbkbd demo 0' test failed. Stderr: {stderr_demo_off}")

            self.logger.debug("Testing 'ectool pwmgetkblight'...")
            success_pwmget, stdout_pwmget, stderr_pwmget = self._run_ectool_cmd_internal(['pwmgetkblight'], timeout=2.0)
            if success_pwmget and stdout_pwmget is not None:
                match = re.search(r'(\d+)', stdout_pwmget)
                if match:
                    self.current_brightness = SafeInputValidation.validate_integer(match.group(1), 0, 100, 100)
                    self.capabilities["ectool_pwmgetkblight_ok"] = True
                    self.logger.info(f"ectool 'pwmgetkblight' available. Current brightness: {self.current_brightness}%")
                else: self.logger.warning(f"ectool 'pwmgetkblight' output not recognized: '{stdout_pwmget}'")
            else: self.logger.warning(f"ectool 'pwmgetkblight' failed. Stderr: {stderr_pwmget}, Stdout: '{stdout_pwmget}'")

            test_brightness = self.current_brightness if self.capabilities["ectool_pwmgetkblight_ok"] else 50
            self.logger.debug(f"Testing 'ectool pwmsetkblight {test_brightness}'...")
            success_pwmset, _, stderr_pwmset = self._run_ectool_cmd_internal(['pwmsetkblight', str(test_brightness)], timeout=2.0)
            self.capabilities["ectool_pwmsetkblight_ok"] = success_pwmset
            if not success_pwmset: self.logger.warning(f"ectool 'pwmsetkblight' command failed. Stderr: {stderr_pwmset}")

            self.ectool_available = (self.capabilities["ectool_present"] and
                                     self.capabilities["ectool_version_ok"] and
                                     (self.capabilities["ectool_rgbkbd_functional"] or self.capabilities["ectool_rgbkbd_clear_functional"]) and
                                     (self.capabilities["ectool_pwmgetkblight_ok"] and self.capabilities["ectool_pwmsetkblight_ok"]))
            if self.ectool_available: self.logger.info("Core ectool functionalities detected and working.")
            else: self.logger.warning("Not all core ectool functionalities detected or working. ectool may not be fully operational.")
        except Exception as e:
            self.logger.error(f"Unexpected error during ectool functional detection: {e}", exc_info=True)
            self.ectool_available = False

    def _detect_ec_direct(self) -> None:
        self.logger.info("Checking for EC Direct mode...")
        self.capabilities["ec_direct_access_ok"] = False
        self.ec_direct_available = False

        if self.ectool_available:
            self.capabilities["ec_direct_access_ok"] = True
            self.ec_direct_available = True
            self.logger.info("EC Direct access framework is now functional via ectool wrappers.")
        else:
            self.logger.info("EC Direct access framework is not functional as ectool is unavailable.")

        if self.ec_direct_available:
            self.logger.info("EC Direct mode is ready (using ectool wrappers).")
        else:
            self.logger.warning("EC Direct mode framework is present but non-functional. Requires ectool or manual implementation.")


    def log_capabilities(self):
        self.logger.info("--- Detected Hardware Capabilities Summary ---")
        for cap, status in self.capabilities.items(): self.logger.info(f"  {cap}: {'OK' if status else 'FAIL/Unavailable'}")
        self.logger.info(f"  Preferred Control Method: {self.preferred_control_method}")
        self.logger.info(f"  Active Control Method: {self.active_control_method}")
        self.logger.info(f"  Overall Hardware Ready: {self.hardware_ready}")
        self.logger.info("------------------------------------------")

    @safe_execute(max_attempts=2, severity="medium")
    def _run_ectool_cmd_internal(self, args: List[str], timeout: float = 1.5, silent: bool = True) -> Tuple[bool, str, str]:
        cmd_to_run = [ECTOOL_EXECUTABLE] + args
        if not self.capabilities.get("ectool_present", False):
            self.logger.error(f"ectool not present, cannot run command: {' '.join(cmd_to_run)}")
            return False, "", "ectool executable not found"

        self.logger.debug(f"Executing ectool command: {' '.join(cmd_to_run)}")
        try:
            result = subprocess.run(cmd_to_run, capture_output=True, timeout=timeout, check=False)
            success = result.returncode == 0
            stdout_str = result.stdout.decode('utf-8', errors='replace').strip() if result.stdout else ""
            stderr_str = result.stderr.decode('utf-8', errors='replace').strip() if result.stderr else ""
            if not success:
                self.logger.warning(f"Command {cmd_to_run} FAILED. RC: {result.returncode}. Stderr: '{stderr_str}'. Stdout: '{stdout_str}'")
            elif not silent:
                self.logger.debug(f"Command {cmd_to_run} OK. Stdout: '{stdout_str[:100]}'")
            return success, stdout_str, stderr_str
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timeout: {cmd_to_run}"); return False, "", "Command timeout"
        except FileNotFoundError:
            self.logger.error(f"Command not found: {ECTOOL_EXECUTABLE}. Ensure it's correctly specified and executable.")
            self.ectool_available = False; self.capabilities["ectool_present"] = False
            return False, "", f"{ECTOOL_EXECUTABLE} not found"
        except Exception as e:
            self.logger.error(f"Unexpected error in _run_ectool_cmd_internal for '{cmd_to_run}': {e}", exc_info=True)
            return False, "", str(e)

    # --- EC Direct Functional Placeholder Methods ---
    def _ec_direct_set_brightness(self, brightness_percent: int) -> bool:
        self.logger.debug(f"EC DIRECT: Using ectool wrapper to set brightness to {brightness_percent}%.")
        return self._run_ectool_cmd_internal(['pwmsetkblight', str(brightness_percent)], silent=False)[0]

    def _ec_direct_get_brightness(self) -> Optional[int]:
        self.logger.debug("EC DIRECT: Using ectool wrapper to get brightness.")
        success, stdout, _ = self._run_ectool_cmd_internal(['pwmgetkblight'], silent=False)
        if success and stdout:
            match = re.search(r'(\d+)', stdout)
            if match:
                return SafeInputValidation.validate_integer(match.group(1), 0, 100, 100)
        return None

    def _ec_direct_set_zone_color(self, zone_0_based: int, color: RGBColor) -> bool:
        self.logger.debug(f"EC DIRECT: Using ectool wrapper to set zone {zone_0_based + 1} to {color.to_hex()}.")
        packed_color_val = (color.r << 16) | (color.g << 8) | color.b
        start_led_index_for_zone = zone_0_based * LEDS_PER_ZONE
        args = ['rgbkbd', str(start_led_index_for_zone), str(packed_color_val), str(packed_color_val), str(packed_color_val)]
        return self._run_ectool_cmd_internal(args, silent=True)[0]

    def _ec_direct_set_all_leds_color(self, color: RGBColor) -> bool:
        self.logger.debug(f"EC DIRECT: Using ectool wrapper to set all LEDs to {color.to_hex()}.")
        packed_color = (color.r << 16) | (color.g << 8) | color.b
        return self._run_ectool_cmd_internal(['rgbkbd', 'clear', str(packed_color)], silent=False)[0]

    def _ec_direct_attempt_stop_hardware_effects(self) -> bool:
        self.logger.debug("EC DIRECT: Using ectool wrapper to stop hardware effects.")
        return self._run_ectool_cmd_internal(['rgbkbd', 'demo', '0'], silent=False)[0]
    # --- End EC Direct Functional Placeholder Methods ---

    def set_brightness(self, brightness_percent: int) -> bool:
        brightness_percent = SafeInputValidation.validate_integer(brightness_percent, 0, 100, self.current_brightness)
        self.logger.debug(f"Setting brightness to {brightness_percent}% using '{self.active_control_method}'")
        with self._lock:
            if self.active_control_method == "ectool":
                if not self.capabilities.get("ectool_pwmsetkblight_ok"):
                    self.logger.warning("ectool: Cannot set brightness: pwmsetkblight capability not OK.")
                    return False
                success, _, stderr_str = self._run_ectool_cmd_internal(['pwmsetkblight', str(brightness_percent)], silent=False)
                if success:
                    self.current_brightness = brightness_percent
                    self.logger.info(f"ectool: Brightness set to {brightness_percent}%.")
                else: self.logger.warning(f"ectool: Failed to set brightness: {stderr_str}")
                return success
            elif self.active_control_method == "ec_direct":
                result = self._ec_direct_set_brightness(brightness_percent)
                if result: self.current_brightness = brightness_percent
                return result
            else:
                self.logger.error(f"Cannot set brightness: No active/valid control method. Current: '{self.active_control_method}'")
                return False

    def get_brightness(self) -> int:
        self.logger.debug(f"Getting brightness using '{self.active_control_method}'")
        with self._lock:
            value_to_return = self.current_brightness
            obtained_new_value = False

            if self.active_control_method == "ectool":
                if not self.capabilities.get("ectool_pwmgetkblight_ok"):
                    self.logger.warning(f"ectool: Cannot get brightness: pwmgetkblight not OK. Returning cached: {value_to_return}%")
                else:
                    success, stdout, stderr_str = self._run_ectool_cmd_internal(['pwmgetkblight'], silent=False)
                    if success and stdout is not None:
                        match = re.search(r'Current KB backlight:\s*(\d+)%?\s*\(requested\s*(\d+)%?\)', stdout)
                        if not match: match = re.search(r'(\d+)', stdout)
                        if match:
                            val_str = match.group(1); val = SafeInputValidation.validate_integer(val_str, 0, 100, value_to_return)
                            self.current_brightness = val; value_to_return = val; obtained_new_value = True
                            self.logger.debug(f"ectool: Got brightness {val}% from output: '{stdout.strip()}'")
                        else: self.logger.warning(f"ectool: Could not parse brightness from output: '{stdout.strip()}'")
                    elif not success: self.logger.warning(f"ectool: pwmgetkblight command failed. Stderr: {stderr_str}")
            elif self.active_control_method == "ec_direct":
                ec_val = self._ec_direct_get_brightness()
                if ec_val is not None:
                    self.current_brightness = ec_val; value_to_return = ec_val; obtained_new_value = True
            else:
                self.logger.error(f"Cannot get brightness: No active/valid control method. Current: '{self.active_control_method}'")

            if not obtained_new_value: self.logger.debug(f"Returning cached brightness: {value_to_return}%.")
            return value_to_return

    def set_zone_color(self, zone_index_1_based: int, color: RGBColor) -> bool:
        if not (1 <= zone_index_1_based <= NUM_ZONES):
            self.logger.error(f"Invalid zone index: {zone_index_1_based}. Must be 1-{NUM_ZONES}."); return False
        if not isinstance(color, RGBColor):
            self.logger.error(f"Invalid color type for set_zone_color: {type(color)}"); return False

        zone_0_based = zone_index_1_based - 1
        self.logger.debug(f"Setting zone {zone_index_1_based} to {color.to_hex()} using '{self.active_control_method}'")
        with self._lock:
            if self.active_control_method == "ectool":
                if not self.capabilities.get("ectool_rgbkbd_functional"):
                    self.logger.warning("ectool: Cannot set zone color: rgbkbd_functional capability is False.")
                    return False
                packed_color_val = (color.r << 16) | (color.g << 8) | color.b
                start_led_index_for_zone = zone_0_based * LEDS_PER_ZONE
                args = ['rgbkbd', str(start_led_index_for_zone), str(packed_color_val), str(packed_color_val), str(packed_color_val)]
                success, _, stderr_str = self._run_ectool_cmd_internal(args, silent=True)
                if success:
                    self._zone_colors_cache[zone_0_based] = color
                    self.logger.debug(f"ectool: Zone {zone_index_1_based} successfully set.")
                else: self.logger.warning(f"ectool: Failed to set zone {zone_index_1_based}. Stderr: {stderr_str}")
                return success
            elif self.active_control_method == "ec_direct":
                result = self._ec_direct_set_zone_color(zone_0_based, color)
                if result: self._zone_colors_cache[zone_0_based] = color
                return result
            else:
                self.logger.error(f"Cannot set zone color: No active/valid control method. Current: '{self.active_control_method}'")
                return False

    def set_zone_colors(self, zone_colors: List[RGBColor]) -> bool:
        if not isinstance(zone_colors, list) or len(zone_colors) != NUM_ZONES:
            self.logger.error(f"set_zone_colors expects {NUM_ZONES} objects. Got: {len(zone_colors) if isinstance(zone_colors, list) else type(zone_colors)}")
            return False
        all_success = True
        with self._lock:
            self.logger.info(f"Batch setting {NUM_ZONES} zone colors using '{self.active_control_method}'.")
            for i, color_obj in enumerate(zone_colors):
                if not isinstance(color_obj, RGBColor):
                    self.logger.error(f"Invalid color object at index {i} for batch set: {type(color_obj)}"); all_success = False; continue
                if not self.set_zone_color(i + 1, color_obj):
                    all_success = False
                if self.active_control_method == "ectool" and i < NUM_ZONES - 1:
                    time.sleep(ECTOOL_INTER_COMMAND_DELAY)
            if all_success: self.logger.info("All zone colors updated successfully in batch.")
            else: self.logger.warning("One or more zones failed to update in batch set_zone_colors.")
        return all_success

    def set_all_leds_color(self, color: RGBColor) -> bool:
        self.logger.debug(f"Setting all LEDs to color: {color.to_hex()} using '{self.active_control_method}'")
        if not isinstance(color, RGBColor):
            self.logger.error(f"Invalid color type for set_all_leds_color: {type(color)}"); return False

        with self._lock:
            if self.active_control_method == "ectool":
                if self.capabilities.get("ectool_rgbkbd_clear_functional"):
                    packed_color = (color.r << 16) | (color.g << 8) | color.b
                    success, _, stderr = self._run_ectool_cmd_internal(['rgbkbd', 'clear', str(packed_color)], silent=False)
                    if success:
                        self.logger.info(f"ectool: Successfully set all LEDs to {color.to_hex()} using 'rgbkbd clear'.")
                        self._zone_colors_cache = [color] * NUM_ZONES
                        return True
                    else:
                        self.logger.warning(f"ectool: 'rgbkbd clear' failed ({stderr}). Falling back to per-zone setting.")
                return self.set_zone_colors([color] * NUM_ZONES)
            elif self.active_control_method == "ec_direct":
                result = self._ec_direct_set_all_leds_color(color)
                if result: self._zone_colors_cache = [color] * NUM_ZONES
                return result
            else:
                self.logger.error(f"Cannot set all LEDs color: No active/valid control method. Current: '{self.active_control_method}'")
                return False

    def attempt_stop_hardware_effects(self) -> bool:
        self.logger.info(f"Attempting to stop hardware effects using '{self.active_control_method}'.")
        with self._lock:
            if self.active_control_method == "ectool":
                if self.capabilities.get("ectool_rgbkbd_demo_off_functional"):
                    success, _, stderr = self._run_ectool_cmd_internal(['rgbkbd', 'demo', '0'], silent=False)
                    if success:
                        self.logger.info("ectool: 'rgbkbd demo 0' command successful. Clearing LEDs to finalize.")
                        return self.clear_all_leds()
                    else:
                        self.logger.warning(f"ectool: 'rgbkbd demo 0' failed: {stderr}. Falling back to clear_all_leds.")
                        return self.clear_all_leds()
                else:
                    self.logger.warning("ectool: 'rgbkbd demo 0' capability not available. Using clear_all_leds as primary stop method.")
                    return self.clear_all_leds()
            elif self.active_control_method == "ec_direct":
                result = self._ec_direct_attempt_stop_hardware_effects()
                if result:
                    return self._ec_direct_set_all_leds_color(RGBColor(0,0,0))
                return False
            else:
                self.logger.error(f"Cannot stop hardware effects: No active/valid control method. Current: '{self.active_control_method}'")
                return False

    def clear_all_leds(self) -> bool:
        self.logger.info(f"Attempting to clear all LEDs (set to black) using '{self.active_control_method}'.")
        return self.set_all_leds_color(RGBColor(0, 0, 0))

    def get_zone_color(self, zone_index_1_based: int) -> Optional[RGBColor]:
        if not (1 <= zone_index_1_based <= NUM_ZONES):
            self.logger.warning(f"Invalid zone index {zone_index_1_based} for get_zone_color."); return None
        with self._lock: return self._zone_colors_cache[zone_index_1_based - 1]

    def get_all_zone_colors(self) -> List[RGBColor]:
        with self._lock: return self._zone_colors_cache[:]

    def get_hardware_info(self) -> Dict[str, Any]:
        if not self.detection_complete.is_set(): self.wait_for_detection(timeout=1.0)
        with self._lock:
            return {
                "ectool_available_flag": self.ectool_available,
                "ectool_executable": ECTOOL_EXECUTABLE,
                "ec_direct_available_flag": self.ec_direct_available,
                "ec_direct_framework_ok_capability": self.capabilities.get("ec_direct_access_ok"),
                "hardware_ready_flag": self.is_operational(),
                "preferred_control_method": self.preferred_control_method,
                "active_control_method": self.active_control_method,
                "capabilities_detail": self.capabilities.copy(),
                "current_brightness_cached": self.current_brightness,
                "cached_zone_colors": [c.to_dict() for c in self._zone_colors_cache],
                "num_logical_zones_app": NUM_ZONES,
                "leds_per_zone_app_config": LEDS_PER_ZONE,
                "TOTAL_LEDS_CONFIG": TOTAL_LEDS,
            }

    def get_active_method_display(self) -> str:
        if not self.detection_complete.is_set(): return "Detecting..."
        if self.active_control_method == "ectool": return "ectool"
        elif self.active_control_method == "ec_direct":
            if self.ec_direct_available: return "EC Direct (Implemented)"
            else: return "EC Direct (NEEDS IMPLEMENTATION)"
        return "None"


    def wait_for_detection(self, timeout: float = 10.0) -> bool:
        if self.detection_complete.is_set(): return True
        self.logger.debug(f"Waiting up to {timeout}s for hardware detection...")
        detected = self.detection_complete.wait(timeout)
        if not detected: self.logger.warning(f"Hardware detection timed out after {timeout}s.")
        return detected

    def is_operational(self) -> bool:
        if not self.detection_complete.is_set(): return False
        return self.hardware_ready

    def is_effect_running(self) -> bool: return self._is_effect_running
    def set_effect_running_status(self, status: bool): self._is_effect_running = status
    def set_app_exiting_cleanly(self, status: bool):
        self.logger.debug(f"Setting app_exiting_cleanly to: {status}"); self._app_exiting_cleanly = status

    def stop_current_effect(self):
        self.set_effect_running_status(False)
        self.logger.debug("HardwareController: User/EffectManager requested stop_current_effect (software effect).")
        self.attempt_stop_hardware_effects()

    def set_reactive_mode(self, enabled: bool, color: RGBColor, anti_mode: bool = False) -> bool:
        self.logger.info(f"Setting reactive mode: enabled={enabled}, anti_mode={anti_mode}, color={color.to_hex()}")

        with self._lock:
            if enabled:
                self._reactive_mode_enabled = True
                self._reactive_color = color
                self._anti_reactive_mode = anti_mode

                if anti_mode:
                    return self.set_all_leds_color(color)
                else:
                    return self.clear_all_leds()
            else:
                self._reactive_mode_enabled = False
                return self.clear_all_leds()
        self.logger.info(f"Setting reactive mode: enabled={enabled}, anti_mode={anti_mode}, color={color.to_hex()}")

        with self._lock:
            if enabled:
                self._reactive_mode_enabled = True
                self._reactive_color = color
                self._anti_reactive_mode = anti_mode

                # Initialize keyboard state
                if anti_mode:
                    # Anti-reactive: start with all keys on
                    return self.set_all_leds_color(color)
                else:
                    # Reactive: start with all keys off
                    return self.clear_all_leds()
            else:
                self._reactive_mode_enabled = False
                return self.clear_all_leds()
        self.logger.info(f"Setting reactive mode: enabled={enabled}, anti_mode={anti_mode}, color={color.to_hex()}")

        with self._lock:
            if enabled:
                self._reactive_mode_enabled = True
                self._reactive_color = color
                self._anti_reactive_mode = anti_mode

                # Initialize keyboard state
                if anti_mode:
                    # Anti-reactive: start with all keys on
                    return self.set_all_leds_color(color)
                else:
                    # Reactive: start with all keys off
                    return self.clear_all_leds()
            else:
                self._reactive_mode_enabled = False
                return self.clear_all_leds()
    def handle_key_press(self, key_position: int, pressed: bool) -> bool:
        """Handle individual key press for reactive effects"""
        if not getattr(self, '_reactive_mode_enabled', False):
            return True  # Not in reactive mode

        try:
            zone_index = min(key_position // (TOTAL_LEDS // NUM_ZONES), NUM_ZONES - 1)

            if getattr(self, '_anti_reactive_mode', False):
                target_color = RGBColor(0, 0, 0) if pressed else getattr(self, '_reactive_color', RGBColor(255, 255, 255))
            else:
                target_color = getattr(self, '_reactive_color', RGBColor(255, 255, 255)) if pressed else RGBColor(0, 0, 0)

            return self.set_zone_color(zone_index + 1, target_color)

        except Exception as e:
            self.logger.error(f"Error handling key press {key_position}: {e}")
            return False
        """Handle individual key press for reactive effects"""
        if not getattr(self, '_reactive_mode_enabled', False):
            return True  # Not in reactive mode

        try:
            # Convert key position to zone using a more robust mapping
            zone_index = min(key_position // (TOTAL_LEDS // NUM_ZONES), NUM_ZONES - 1)

            if getattr(self, '_anti_reactive_mode', False):
                # Anti-reactive: turn off when pressed
                target_color = RGBColor(0, 0, 0) if pressed else getattr(self, '_reactive_color', RGBColor(255, 255, 255))
            else:
                # Reactive: turn on when pressed
                target_color = getattr(self, '_reactive_color', RGBColor(255, 255, 255)) if pressed else RGBColor(0, 0, 0)

            return self.set_zone_color(zone_index + 1, target_color)

        except Exception as e:
            self.logger.error(f"Error handling key press {key_position}: {e}")
            return False
        """Handle individual key press for reactive effects"""
        if not getattr(self, '_reactive_mode_enabled', False):
            return True  # Not in reactive mode

        try:
            # Convert key position to zone (simplified mapping)
            zone_index = min(key_position // (TOTAL_LEDS // NUM_ZONES), NUM_ZONES - 1)

            if getattr(self, '_anti_reactive_mode', False):
                # Anti-reactive: turn off when pressed
                target_color = RGBColor(0, 0, 0) if pressed else getattr(self, '_reactive_color', RGBColor(255, 255, 255))
            else:
                # Reactive: turn on when pressed
                target_color = getattr(self, '_reactive_color', RGBColor(255, 255, 255)) if pressed else RGBColor(0, 0, 0)

            return self.set_zone_color(zone_index + 1, target_color)

        except Exception as e:
            self.logger.error(f"Error handling key press {key_position}: {e}")
            return False
    def simulate_key_press_pattern(self, pattern_name: str = "typing") -> bool:
        if not getattr(self, '_reactive_mode_enabled', False):
            return False

        try:
            if pattern_name == "typing":
                import time
                for zone in range(NUM_ZONES):
                    if getattr(self, '_anti_reactive_mode', False):
                        self.set_zone_color(zone + 1, RGBColor(0, 0, 0))
                        time.sleep(0.1)
                        self.set_zone_color(zone + 1, getattr(self, '_reactive_color', RGBColor(255, 255, 255)))
                    else:
                        self.set_zone_color(zone + 1, getattr(self, '_reactive_color', RGBColor(255, 255, 255)))
                        time.sleep(0.1)
                        self.set_zone_color(zone + 1, RGBColor(0, 0, 0))
                return True

            return False

        except Exception as e:
            self.logger.error(f"Error simulating key press pattern: {e}")
            return False

    def __del__(self):
        self.logger.debug(f"HardwareController instance being deleted. App exiting cleanly: {self._app_exiting_cleanly}, Effect running: {self._is_effect_running}")
        if not self._app_exiting_cleanly:
            self.logger.info("Attempting to clear LEDs on unclean HardwareController deletion.")
            try:
                if hasattr(self, 'detection_complete') and not self.detection_complete.is_set():
                    self.detection_complete.wait(timeout=0.2)

                if self.active_control_method == "ectool" and self.ectool_available:
                    self.clear_all_leds()
                    self.logger.info("LEDs cleared via ectool on HardwareController unclean deletion.")
                elif self.active_control_method == "ec_direct" and self.capabilities.get("ec_direct_access_ok"):
                    self.logger.warning("EC Direct was active on unclean deletion; clear_all_leds called, but depends on user implementation.")
                    self.clear_all_leds()
                else:
                    self.logger.warning(f"Cannot clear LEDs on unclean deletion: No suitable active control method ('{self.active_control_method}').")
            except Exception as e:
                self.logger.warning(f"Error clearing LEDs during HardwareController unclean deletion: {e}")
        else:
            self.logger.info("LEDs not cleared on HardwareController deletion due to clean exit flag.")
