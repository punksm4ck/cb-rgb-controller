#!/usr/bin/env python3
"""Settings management system for RGB Controller"""

import json
import threading
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import shutil
import time
import os

from .rgb_color import RGBColor
from .constants import SETTINGS_FILE, default_settings, NUM_ZONES
from .exceptions import ConfigurationError, ValidationError

from ..utils.decorators import safe_execute
from ..utils.input_validation import SafeInputValidation

def get_fresh_default_settings() -> Dict[str, Any]:
    """Returns a deep copy of the default settings dictionary."""
    return json.loads(json.dumps(default_settings))


class SettingsManager:
    """
    Manages application settings with validation, loading, and atomic saving.
    Uses default_settings from constants.py as a schema and fallback.
    """

    def __init__(self, config_file_path: Optional[Path] = None):
        self.logger = logging.getLogger('SettingsManager')

        if config_file_path is None:
            self.config_file = SETTINGS_FILE
        else:
            self.config_file = Path(config_file_path).resolve()

        self._lock = threading.RLock()
        self._settings: Dict[str, Any] = get_fresh_default_settings()
        self._last_session_clean_shutdown = False # Stored state from previous session

        self.load_settings()

    @safe_execute(severity="critical", max_attempts=1)
    def load_settings(self) -> None:
        with self._lock:
            loaded_successfully = False
            if self.config_file.exists() and self.config_file.is_file() and self.config_file.stat().st_size > 0:
                try:
                    with open(self.config_file, 'r', encoding='utf-8') as f:
                        loaded_data = json.load(f)

                    if not isinstance(loaded_data, dict):
                        raise ConfigurationError("Settings file root is not a dictionary.")

                    temp_settings = get_fresh_default_settings()
                    for key, default_val_from_schema in temp_settings.items():
                        if key in loaded_data:
                            temp_settings[key] = self._validate_setting_value(key, loaded_data[key], default_val_from_schema)

                    self._settings = temp_settings
                    # Capture the clean_shutdown status from the loaded settings
                    self._last_session_clean_shutdown = SafeInputValidation.validate_bool(self._settings.get("clean_shutdown", False))
                    loaded_successfully = True
                    self.logger.info(f"Settings loaded from {self.config_file}. Previous shutdown was {'clean' if self._last_session_clean_shutdown else 'unclean/first run'}.")

                except json.JSONDecodeError as e:
                    self.logger.error(f"JSON decoding error in {self.config_file}: {e}. Attempting recovery.", exc_info=True)
                except ConfigurationError as e:
                    self.logger.error(f"Configuration error loading settings: {e}. Attempting recovery.", exc_info=True)
                except Exception as e:
                    self.logger.error(f"Unexpected error loading settings from {self.config_file}: {e}. Attempting recovery.", exc_info=True)
            else:
                self.logger.info(f"Settings file {self.config_file} not found or empty. Initializing with defaults.")

            if not loaded_successfully:
                self._attempt_settings_recovery_or_default()

            # Always set clean_shutdown to False immediately after loading/recovering
            # This marks the *current* session as potentially unclean until explicitly marked otherwise
            self._settings["clean_shutdown"] = False
            # Save immediately to persist the False state for the current session start
            self.save_settings()

    def _attempt_settings_recovery_or_default(self):
        backup_file = self.config_file.with_suffix(f"{self.config_file.suffix}.backup")
        ctfn_val = None # Corrupted Temp File Name value
        if backup_file.exists() and backup_file.is_file():
            self.logger.warning(f"Attempting to restore settings from standard backup: {backup_file}")
            try:
                corrupted_file_name = self.config_file.with_suffix(f"{self.config_file.suffix}.corrupted.{int(time.time())}")
                if self.config_file.exists():
                    self.config_file.rename(corrupted_file_name)
                    ctfn_val = corrupted_file_name
                
                shutil.copy2(backup_file, self.config_file)
                
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    restored_data = json.load(f)
                if not isinstance(restored_data, dict):
                    raise ConfigurationError("Restored backup file root is not a dictionary.")
                
                temp_settings = get_fresh_default_settings()
                for key, default_val in temp_settings.items():
                    if key in restored_data:
                        temp_settings[key] = self._validate_setting_value(key, restored_data[key], default_val)
                self._settings = temp_settings
                self._last_session_clean_shutdown = SafeInputValidation.validate_bool(self._settings.get("clean_shutdown", False))
                self.logger.info(f"Successfully restored and validated settings from {backup_file}.")
                return
            except Exception as e_restore:
                self.logger.error(f"Failed to restore or validate settings from backup {backup_file}: {e_restore}. Resetting to defaults.", exc_info=True)
                if ctfn_val and ctfn_val.exists():
                    try: ctfn_val.rename(self.config_file)
                    except Exception as e_revert: self.logger.error(f"Could not revert from corrupted file {ctfn_val} after failed backup restore: {e_revert}")
        
        self.logger.warning(f"Initializing with default settings and saving to {self.config_file} (no usable backup found or backup restore failed).")
        self._settings = get_fresh_default_settings()
        self._last_session_clean_shutdown = False

    def _validate_setting_value(self, key: str, loaded_value: Any, default_value_from_schema: Any) -> Any:
        try:
            if key == "brightness":
                return SafeInputValidation.validate_integer(loaded_value, 0, 100, default_value_from_schema)
            elif key == "effect_speed":
                return SafeInputValidation.validate_integer(loaded_value, 1, 10, default_value_from_schema)
            elif key == "current_color":
                if isinstance(loaded_value, dict): return RGBColor.from_dict(loaded_value).to_dict()
                self.logger.warning(f"Invalid type for '{key}': {type(loaded_value)}, expected dict. Using default.")
                return default_value_from_schema
            elif key == "zone_colors":
                if isinstance(loaded_value, list):
                    valid_colors = []
                    default_palette = default_value_from_schema if isinstance(default_value_from_schema, list) and default_value_from_schema else [{"r":0,"g":0,"b":0}]*NUM_ZONES
                    for i in range(NUM_ZONES):
                        default_zc_dict = default_palette[i % len(default_palette)]
                        if i < len(loaded_value) and isinstance(loaded_value[i], dict):
                            try: valid_colors.append(RGBColor.from_dict(loaded_value[i]).to_dict())
                            except ValidationError: valid_colors.append(default_zc_dict)
                        else: valid_colors.append(default_zc_dict)
                    return valid_colors
                self.logger.warning(f"Invalid type for '{key}': {type(loaded_value)}, expected list. Using default.")
                return default_value_from_schema
            elif key.endswith("_color") and isinstance(default_value_from_schema, str):
                return SafeInputValidation.validate_color_hex(loaded_value, default_value_from_schema)
            elif isinstance(default_value_from_schema, bool):
                return SafeInputValidation.validate_bool(loaded_value, default_value_from_schema)
            elif isinstance(default_value_from_schema, str):
                return SafeInputValidation.validate_string(loaded_value, max_length=100, default=default_value_from_schema)
            
            # For lists/dicts not specifically handled, ensure type matches
            if type(loaded_value) == type(default_value_from_schema): return loaded_value
            else: self.logger.warning(f"Type mismatch for setting '{key}' (loaded: {type(loaded_value)}, expected: {type(default_value_from_schema)}). Using default."); return default_value_from_schema
        except Exception as e:
            self.logger.error(f"Unexpected error validating setting '{key}' (value: {loaded_value}): {e}. Using default '{default_value_from_schema}'.", exc_info=True)
            return default_value_from_schema

    @safe_execute(severity="high", max_attempts=2)
    def save_settings(self) -> None:
        with self._lock:
            try:
                self.config_file.parent.mkdir(parents=True, exist_ok=True)
                data_to_save = self._settings.copy()
                
                # Create a simple, non-timestamped backup file before writing a new one.
                # This file will be overwritten on each successful save, keeping the *last good* version.
                backup_file = self.config_file.with_suffix(f"{self.config_file.suffix}.backup")
                if self.config_file.exists():
                    try: shutil.copy2(self.config_file, backup_file); self.logger.debug(f"Created backup: {backup_file}")
                    except Exception as e_backup: self.logger.warning(f"Could not create backup before saving: {e_backup}")
                
                temp_file_path = self.config_file.with_suffix(f'.tmp.{os.getpid()}')
                with open(temp_file_path, 'w', encoding='utf-8') as f:
                    json.dump(data_to_save, f, indent=2, ensure_ascii=False)
                    f.flush(); os.fsync(f.fileno())
                
                os.replace(temp_file_path, self.config_file)
                self.logger.info(f"Settings successfully saved to {self.config_file}")

            except Exception as e:
                self.logger.error(f"Critical error saving settings to {self.config_file}: {e}", exc_info=True)
                raise ConfigurationError(f"Failed to save settings to {self.config_file}: {e}") from e

    def get(self, key: str, default_override: Optional[Any] = None) -> Any:
        with self._lock:
            default_from_schema = get_fresh_default_settings().get(key)
            effective_default = default_override if default_override is not None else default_from_schema
            return self._settings.get(key, effective_default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if key not in default_settings:
                self.logger.warning(f"Attempted to set unknown setting key: '{key}'. Ignoring.")
                return
            default_val_for_validation = default_settings.get(key)
            validated_value = self._validate_setting_value(key, value, default_val_for_validation)
            if self._settings.get(key) != validated_value or key not in self._settings:
                self._settings[key] = validated_value
                # Settings are saved whenever a single setting changes.
                # This ensures settings are up-to-date even if app crashes shortly after a change.
                self.save_settings()
                self.logger.debug(f"Setting '{key}' updated to: {validated_value}")

    def update(self, new_settings_dict: Dict[str, Any]) -> None:
        with self._lock:
            changed = False
            for key, value in new_settings_dict.items():
                if key not in default_settings:
                    self.logger.warning(f"Update: Ignoring unknown setting key: '{key}'.")
                    continue
                default_val_for_validation = default_settings.get(key)
                validated_value = self._validate_setting_value(key, value, default_val_for_validation)
                if self._settings.get(key) != validated_value or key not in self._settings:
                    self._settings[key] = validated_value
                    changed = True
                    self.logger.debug(f"Update: Setting '{key}' to: {validated_value}")
            if changed:
                self.save_settings()
                self.logger.info(f"Settings updated. {sum(1 for k in new_settings_dict if k in default_settings)} provided keys processed.")
            else:
                self.logger.debug("Update called, but no actual setting values changed after validation.")

    def mark_clean_shutdown(self):
        """Marks the current session as having performed a clean shutdown."""
        self.logger.info("Marking clean shutdown in settings.")
        # Directly update _settings and save to ensure this specific flag is persisted.
        with self._lock:
            self._settings["clean_shutdown"] = True
            self.save_settings()

    def was_previous_session_clean(self) -> bool:
        """Returns True if the previous session exited cleanly, False otherwise."""
        return self._last_session_clean_shutdown

    def reset_to_defaults(self):
        self.logger.info("Resetting all settings to application defaults.")
        with self._lock:
            self._settings = get_fresh_default_settings()
            self._last_session_clean_shutdown = False # After reset, next startup is like first run or unclean
            self._settings["clean_shutdown"] = False # Mark current state as potentially unclean
            self.save_settings()
