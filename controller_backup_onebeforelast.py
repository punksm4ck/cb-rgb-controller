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
    def __init__(self):
        self.logger = logging.getLogger(f"{APP_NAME}.HardwareController")
        self.detection_complete = threading.Event()
        self.ectool_available = False
        self.ec_direct_available = False 
        self.hardware_ready = False 

        self.capabilities: Dict[str, bool] = {
            "ectool_present": False, "ectool_version_ok": False,
            "ectool_rgbkbd_functional": False, # For general rgbkbd <key> <RGB>...
            "ectool_rgbkbd_clear_functional": False, # Specifically for 'rgbkbd clear <RGB>'
            "ectool_rgbkbd_demo_off_functional": False, # Specifically for 'rgbkbd demo 0'
            "ectool_pwmsetkblight_ok": False,
            "ectool_pwmgetkblight_ok": False, "ec_direct_access_ok": False,
        }

        self.current_brightness = 100 
        self._lock = threading.RLock() 
        self._zone_colors_cache: List[RGBColor] = [RGBColor(0,0,0) for _ in range(NUM_ZONES)]
        self._is_effect_running = False 
        self._app_exiting_cleanly = False 

        self._detection_thread = threading.Thread(target=self._perform_hardware_detection, daemon=True, name="HardwareDetectionThread")
        self._detection_thread.start()

    @safe_execute(max_attempts=1, severity="critical")
    def _perform_hardware_detection(self) -> None:
        self.logger.info("Starting hardware detection process...")
        time.sleep(0.5) 
        self.logger.info("Initial delay complete, proceeding with ectool detection.")
        try:
            self._detect_ectool()
            self._detect_ec_direct() 
            self.hardware_ready = self.ectool_available # EC Direct not implemented
            if not self.hardware_ready:
                self.logger.warning("No primary RGB control methods (ectool) detected or functional after all checks.")
            else:
                self.logger.info("Hardware detection checks completed successfully.")
        except Exception as e:
            self.logger.error(f"Critical error during hardware detection: {e}", exc_info=True)
            self.hardware_ready = False 
        finally:
            self.detection_complete.set()
            self.logger.info(f"Hardware detection process finished. ectool_available={self.ectool_available}, hardware_ready={self.hardware_ready}")
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
            if success_version: 
                self.logger.info(f"ectool version OK: {stdout_version.splitlines()[0] if stdout_version else 'No version string output'}")
            else: 
                self.logger.warning(f"ectool 'version' command failed. Stderr: {stderr_version}, Stdout: {stdout_version}"); return

            # Test basic rgbkbd functionality: rgbkbd <key> <RGB>
            self.logger.debug("Testing 'ectool rgbkbd 0 0' (basic single LED to black)...")
            success_rgbkbd_single, _, stderr_rgbkbd_single = self._run_ectool_cmd_internal(['rgbkbd', '0', '0'], timeout=2.0, silent=False)
            self.capabilities["ectool_rgbkbd_functional"] = success_rgbkbd_single
            if success_rgbkbd_single: self.logger.info("ectool 'rgbkbd <key> <RGB>' basic test successful.")
            else: self.logger.warning(f"ectool 'rgbkbd <key> <RGB>' basic test failed. Stderr: {stderr_rgbkbd_single}")

            # Test 'rgbkbd clear <RGB>'
            self.logger.debug("Testing 'ectool rgbkbd clear 0' (clear to black)...")
            success_clear, _, stderr_clear = self._run_ectool_cmd_internal(['rgbkbd', 'clear', '0'], timeout=3.0, silent=False)
            self.capabilities["ectool_rgbkbd_clear_functional"] = success_clear # Specifically for this command
            if success_clear: self.logger.info("ectool 'rgbkbd clear <RGB>' command is functional.")
            else: self.logger.warning(f"ectool 'rgbkbd clear <RGB>' test failed. Stderr: {stderr_clear}")
            
            # Test 'rgbkbd demo 0'
            self.logger.debug("Testing 'ectool rgbkbd demo 0' (demo off)...")
            success_demo_off, _, stderr_demo_off = self._run_ectool_cmd_internal(['rgbkbd', 'demo', '0'], timeout=2.0, silent=False)
            self.capabilities["ectool_rgbkbd_demo_off_functional"] = success_demo_off
            if success_demo_off: self.logger.info("ectool 'rgbkbd demo 0' command is functional.")
            else: self.logger.warning(f"ectool 'rgbkbd demo 0' test failed. Stderr: {stderr_demo_off}")

            self.logger.debug("Testing 'ectool pwmgetkblight'...")
            success_pwmget, stdout_pwmget, stderr_pwmget = self._run_ectool_cmd_internal(['pwmgetkblight'], timeout=2.0)
            if success_pwmget and stdout_pwmget is not None:
                match = re.search(r'(\d+)', stdout_pwmget)
                if match:
                    self.current_brightness = SafeInputValidation.validate_integer(match.group(1), 0, 100, 100)
                    self.capabilities["ectool_pwmgetkblight_ok"] = True
                    self.logger.info(f"ectool 'pwmgetkblight' available. Current brightness: {self.current_brightness}%")
                else: self.logger.warning(f"ectool 'pwmgetkblight' output not recognized: '{stdout_pwmget}'")
            else: self.logger.warning(f"ectool 'pwmgetkblight' failed or no output. Success: {success_pwmget}, Stderr: {stderr_pwmget}, Stdout: '{stdout_pwmget}'")

            test_brightness = self.current_brightness if self.capabilities["ectool_pwmgetkblight_ok"] else 50
            self.logger.debug(f"Testing 'ectool pwmsetkblight {test_brightness}'...")
            success_pwmset, _, stderr_pwmset = self._run_ectool_cmd_internal(['pwmsetkblight', str(test_brightness)], timeout=2.0)
            self.capabilities["ectool_pwmsetkblight_ok"] = success_pwmset
            if not success_pwmset: self.logger.warning(f"ectool 'pwmsetkblight' command failed. Stderr: {stderr_pwmset}")

            # ectool is considered available if present, version is OK, and at least one core function works.
            self.ectool_available = (self.capabilities["ectool_present"] and 
                                     self.capabilities["ectool_version_ok"] and
                                     (self.capabilities["ectool_rgbkbd_functional"] or 
                                      self.capabilities["ectool_rgbkbd_clear_functional"] or 
                                      self.capabilities["ectool_rgbkbd_demo_off_functional"] or
                                      (self.capabilities["ectool_pwmgetkblight_ok"] and self.capabilities["ectool_pwmsetkblight_ok"])))
            if self.ectool_available: self.logger.info("Core ectool functionalities (presence, version, some RGB/brightness) detected.")
            else: self.logger.warning("Not all core ectool functionalities detected or working.")
        except Exception as e:
            self.logger.error(f"Unexpected error during ectool functional detection: {e}", exc_info=True)
            self.ectool_available = False

    def _detect_ec_direct(self) -> None:
        self.ec_direct_available = False; self.capabilities["ec_direct_access_ok"] = False
        self.logger.debug("Direct EC access detection logic not implemented.")

    def log_capabilities(self):
        self.logger.info("--- Detected Hardware Capabilities Summary ---")
        for cap, status in self.capabilities.items(): self.logger.info(f"  {cap}: {'OK' if status else 'FAIL/Unavailable'}")
        self.logger.info("------------------------------------------")

    @safe_execute(max_attempts=2, severity="medium")
    def _run_ectool_cmd_internal(self, args: List[str], timeout: float = 1.5, silent: bool = True) -> Tuple[bool, str, str]:
        cmd_to_run = [ECTOOL_EXECUTABLE] + args
        self.logger.debug(f"Executing ectool command: {' '.join(cmd_to_run)}")
        try:
            result = subprocess.run(cmd_to_run, capture_output=True, timeout=timeout, check=False)
            success = result.returncode == 0
            stdout_str, stderr_str = "", ""
            if result.stdout:
                try: stdout_str = result.stdout.decode('utf-8', errors='replace').strip()
                except UnicodeDecodeError: 
                    self.logger.debug(f"Stdout for {' '.join(cmd_to_run)} not utf-8, trying latin-1."); stdout_str = result.stdout.decode('latin-1', errors='replace').strip()
            if result.stderr:
                try: stderr_str = result.stderr.decode('utf-8', errors='replace').strip()
                except UnicodeDecodeError:
                    self.logger.debug(f"Stderr for {' '.join(cmd_to_run)} not utf-8, trying latin-1."); stderr_str = result.stderr.decode('latin-1', errors='replace').strip()
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

    def set_brightness(self, brightness_percent: int) -> bool:
        brightness_percent = SafeInputValidation.validate_integer(brightness_percent, 0, 100, self.current_brightness)
        self.logger.debug(f"Attempting to set brightness to {brightness_percent}%")
        with self._lock:
            if not self.capabilities.get("ectool_pwmsetkblight_ok"):
                self.logger.warning("Cannot set brightness: ectool_pwmsetkblight capability not available/OK.")
                return False
            success, _, stderr_str = self._run_ectool_cmd_internal(['pwmsetkblight', str(brightness_percent)], silent=False)
            if success:
                self.current_brightness = brightness_percent
                self.logger.info(f"Brightness set to {brightness_percent}% via ectool.")
            else: self.logger.warning(f"Failed to set brightness via ectool: {stderr_str}")
            return success

    def get_brightness(self) -> int:
        with self._lock:
            if not self.capabilities.get("ectool_pwmgetkblight_ok"):
                self.logger.warning(f"Cannot get brightness: ectool_pwmgetkblight not OK. Returning cached: {self.current_brightness}%")
                return self.current_brightness
            success, stdout, stderr_str = self._run_ectool_cmd_internal(['pwmgetkblight'], silent=False)
            if success and stdout is not None:
                match = re.search(r'Current KB backlight:\s*(\d+)%?\s*\(requested\s*(\d+)%?\)', stdout)
                if not match: match = re.search(r'(\d+)', stdout)
                if match:
                    val_str = match.group(1); val = SafeInputValidation.validate_integer(val_str, 0, 100, self.current_brightness)
                    self.current_brightness = val
                    self.logger.debug(f"Got brightness {val}% from ectool output: '{stdout.strip()}'"); return val
                else: self.logger.warning(f"Could not parse brightness from ectool output: '{stdout.strip()}'")
            elif not success: self.logger.warning(f"ectool pwmgetkblight command failed. Stderr: {stderr_str}")
            self.logger.debug(f"Returning cached brightness due to issue: {self.current_brightness}%.")
            return self.current_brightness

    def set_zone_color(self, zone_index_1_based: int, color: RGBColor) -> bool:
        if not (1 <= zone_index_1_based <= NUM_ZONES):
            self.logger.error(f"Invalid zone index: {zone_index_1_based}. Must be 1-{NUM_ZONES}."); return False
        if not isinstance(color, RGBColor):
            self.logger.error(f"Invalid color type for set_zone_color: {type(color)}"); return False

        with self._lock:
            if not self.capabilities.get("ectool_rgbkbd_functional"):
                self.logger.warning("Cannot set zone color: ectool_rgbkbd_functional capability overall is False.")
                return False

            zone_0_based = zone_index_1_based - 1
            packed_color_val = (color.r << 16) | (color.g << 8) | color.b
            
            # Usage1: rgbkbd <key> <RGB> [<RGB> ...]
            # LEDS_PER_ZONE is 3 from constants.py.
            # This means each logical zone in the app corresponds to 3 physical LEDs controlled by one ectool command.
            start_led_index_for_zone = zone_0_based * LEDS_PER_ZONE # This is the <key>
            
            # Command: rgbkbd <start_key_for_zone> <color_for_led1> <color_for_led2> <color_for_led3>
            # All LEDs in this logical zone get the same color.
            args = ['rgbkbd', str(start_led_index_for_zone), 
                    str(packed_color_val), str(packed_color_val), str(packed_color_val)]
            
            self.logger.debug(f"Setting zone {zone_index_1_based} (start LED {start_led_index_for_zone}) with args: {args}")
            success, _, stderr_str = self._run_ectool_cmd_internal(args, silent=True) 
            
            if success:
                self._zone_colors_cache[zone_0_based] = color
                self.logger.debug(f"Zone {zone_index_1_based} successfully set to {color.to_hex()}")
                return True
            else:
                self.logger.warning(f"Failed to set zone {zone_index_1_based} (start LED {start_led_index_for_zone}). Stderr: {stderr_str}")
                return False

    def set_zone_colors(self, zone_colors: List[RGBColor]) -> bool:
        if not isinstance(zone_colors, list) or len(zone_colors) != NUM_ZONES:
            self.logger.error(f"set_zone_colors expects {NUM_ZONES} objects. Got: {len(zone_colors) if isinstance(zone_colors, list) else type(zone_colors)}")
            return False
        all_success = True
        with self._lock:
            for i, color_obj in enumerate(zone_colors):
                if not isinstance(color_obj, RGBColor):
                    self.logger.error(f"Invalid color object at index {i}: {type(color_obj)}"); all_success = False; continue
                if not self.set_zone_color(i + 1, color_obj): all_success = False
                if i < NUM_ZONES - 1 : time.sleep(ECTOOL_INTER_COMMAND_DELAY)
            if all_success: self.logger.info("All zone colors updated successfully via batch.")
            else: self.logger.warning("One or more zones failed to update in batch set_zone_colors.")
        return all_success

    def set_all_leds_color(self, color: RGBColor) -> bool:
        self.logger.debug(f"Setting all LEDs to color: {color.to_hex()}")
        if not isinstance(color, RGBColor):
            self.logger.error(f"Invalid color type: {type(color)}"); return False
        
        # Try 'rgbkbd clear <RGB>' if available
        if self.capabilities.get("ectool_rgbkbd_clear_functional"):
            packed_color = (color.r << 16) | (color.g << 8) | color.b
            success, _, stderr = self._run_ectool_cmd_internal(['rgbkbd', 'clear', str(packed_color)], silent=False)
            if success:
                self.logger.info(f"Successfully set all LEDs to {color.to_hex()} using 'rgbkbd clear'.")
                self._zone_colors_cache = [color] * NUM_ZONES
                return True
            else:
                self.logger.warning(f"'rgbkbd clear' failed ({stderr}). Falling back to per-zone setting.")
        
        return self.set_zone_colors([color] * NUM_ZONES)

    def attempt_stop_hardware_effects(self) -> bool:
        """Attempts to stop ongoing hardware effects using 'rgbkbd demo 0'."""
        self.logger.info("Attempting to stop hardware effects using 'rgbkbd demo 0'.")
        with self._lock:
            if self.capabilities.get("ectool_rgbkbd_demo_off_functional"): # Check specific capability
                success, _, stderr = self._run_ectool_cmd_internal(['rgbkbd', 'demo', '0'], silent=False)
                if success:
                    self.logger.info("'rgbkbd demo 0' command successful.")
                    # Clearing to black might be needed if 'demo 0' doesn't guarantee LEDs off
                    return self.clear_all_leds() 
                else:
                    self.logger.warning(f"'rgbkbd demo 0' command failed: {stderr}. Trying clear_all_leds as fallback.")
                    return self.clear_all_leds() # Fallback to clear
            else:
                self.logger.warning("'rgbkbd demo 0' capability not available. Falling back to clear_all_leds.")
                return self.clear_all_leds()


    def clear_all_leds(self) -> bool:
        self.logger.info("Attempting to clear all LEDs (set to black).")
        # This uses the 'rgbkbd clear 0' or fallback logic in set_all_leds_color(RGBColor(0,0,0))
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
                "ectool_available": self.ectool_available, "ectool_executable": ECTOOL_EXECUTABLE,
                "ec_direct_available": self.ec_direct_available, "hardware_ready": self.is_operational(),
                "capabilities": self.capabilities.copy(), "current_brightness": self.current_brightness,
                "cached_zone_colors": [c.to_dict() for c in self._zone_colors_cache],
                "num_logical_zones_app": NUM_ZONES, "leds_per_zone_app_config": LEDS_PER_ZONE,
                "TOTAL_LEDS_CONFIG": TOTAL_LEDS,
            }

    def wait_for_detection(self, timeout: float = 10.0) -> bool:
        if self.detection_complete.is_set(): return True
        self.logger.debug(f"Waiting up to {timeout}s for hardware detection...")
        return self.detection_complete.wait(timeout)

    def is_operational(self) -> bool:
        return self.detection_complete.is_set() and self.hardware_ready
        
    def is_effect_running(self) -> bool: return self._is_effect_running
    def set_effect_running_status(self, status: bool): self._is_effect_running = status
    def set_app_exiting_cleanly(self, status: bool):
        self.logger.debug(f"Setting app_exiting_cleanly to: {status}"); self._app_exiting_cleanly = status
    def stop_current_effect(self): # Called by GUI/EffectManager to stop software effects
        self.set_effect_running_status(False) 
        self.logger.debug("HardwareController: User/EffectManager requested stop_current_effect.")
        # Attempt to also stop any direct hardware pattern if possible
        self.attempt_stop_hardware_effects()


    def __del__(self):
        self.logger.debug(f"HardwareController instance being deleted. App exiting cleanly: {self._app_exiting_cleanly}, Effect running: {self._is_effect_running}")
        if not self._app_exiting_cleanly:
            self.logger.info("Attempting to clear LEDs on unclean HardwareController deletion.")
            try:
                if hasattr(self, 'detection_complete') and not self.detection_complete.is_set(): self.wait_for_detection(timeout=0.1)
                if hasattr(self, 'ectool_available') and self.ectool_available and self.capabilities.get("ectool_present"):
                    self.clear_all_leds(); self.logger.info("LEDs cleared attempt on HardwareController unclean deletion.")
                else: self.logger.warning("Cannot clear LEDs on unclean deletion: ectool not marked available or present.")
            except Exception as e: self.logger.warning(f"Error clearing LEDs during HardwareController unclean deletion: {e}")
        else: self.logger.info("LEDs not cleared on HardwareController deletion due to clean exit flag.")
