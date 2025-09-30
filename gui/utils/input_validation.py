# gui/utils/input_validation.py

import logging
import math
import re
import os # Added for os.fspath
from pathlib import Path
from typing import Any, Optional, Union

class SafeInputValidation:
    """
    Provides methods for safe input validation and sanitization.
    Each method logs warnings on invalid input and returns a default or coerced value.
    """
    @staticmethod
    def validate_integer(value: Any, min_val: Optional[int] = None, max_val: Optional[int] = None,
                        default: int = 0) -> int:
        logger = logging.getLogger('SafeInputValidation.integer')
        try:
            if isinstance(value, bool): return int(value)
            if isinstance(value, str):
                val_str = value.strip()
                if not val_str: return default
                # Handle hex, octal, binary if prefixed (e.g. "0xFF", "0o7", "0b10")
                # otherwise decimal (can be float string like "123.0")
                if val_str.startswith(('0x', '0X', '0o', '0O', '0b', '0B')):
                    num_val = int(val_str, 0)
                else:
                    num_val = int(float(val_str)) # Allows "123.0" but fails "123.4"
            elif isinstance(value, (int, float)):
                num_val = int(value)
            else:
                raise TypeError(f"Cannot convert type {type(value)} to int")

            if min_val is not None: num_val = max(min_val, num_val)
            if max_val is not None: num_val = min(max_val, num_val)
            return num_val
        except (ValueError, TypeError, OverflowError) as e:
            logger.warning(f"Invalid integer input '{value}': {e}. Using default: {default}")
            if min_val is not None: default = max(min_val, default)
            if max_val is not None: default = min(max_val, default)
            return default

    @staticmethod
    def validate_float(value: Any, min_val: Optional[float] = None, max_val: Optional[float] = None,
                      default: float = 0.0) -> float:
        logger = logging.getLogger('SafeInputValidation.float')
        try:
            if isinstance(value, bool): return float(value)
            if isinstance(value, str):
                val_str = value.strip()
                if not val_str: return default
                num_val = float(val_str)
            elif isinstance(value, (int, float)):
                num_val = float(value)
            else:
                raise TypeError(f"Cannot convert type {type(value)} to float")

            if not math.isfinite(num_val):
                logger.warning(f"Invalid float input (NaN/Inf) '{value}'. Using default: {default}")
                return default
            
            if min_val is not None: num_val = max(min_val, num_val)
            if max_val is not None: num_val = min(max_val, num_val)
            return num_val
        except (ValueError, TypeError, OverflowError) as e:
            logger.warning(f"Invalid float input '{value}': {e}. Using default: {default}")
            if min_val is not None: default = max(min_val, default)
            if max_val is not None: default = min(max_val, default)
            return default

    @staticmethod
    def validate_string(value: Any, max_length: int = 1000, 
                       allowed_chars_re: Optional[str] = None, default: str = "") -> str:
        logger = logging.getLogger('SafeInputValidation.string')
        try:
            if value is None: return default
            
            result = str(value).strip()
            result = result.replace('\x00', '') # Remove null bytes

            if len(result) > max_length:
                result = result[:max_length]
                logger.info(f"String input truncated to {max_length} characters.")
            
            if allowed_chars_re:
                # Ensure it's a valid regex pattern
                try:
                    compiled_re = re.compile(allowed_chars_re)
                    result = "".join(compiled_re.findall(result))
                except re.error as re_err:
                    logger.warning(f"Invalid regex for allowed_chars_re '{allowed_chars_re}': {re_err}. Not filtering.")
            
            return result
        except Exception as e:
            logger.warning(f"Invalid string input processing for '{value}': {e}. Using default: '{default}'")
            return default

    @staticmethod
    def validate_color_hex(value: Any, default: str = "#000000") -> str:
        logger = logging.getLogger('SafeInputValidation.color_hex')
        try:
            if value is None: return default
            
            color_str = str(value).strip().lower()
            
            if not color_str.startswith('#'):
                if re.fullmatch(r'[0-9a-f]{3}(?:[0-9a-f]{3})?', color_str): # Match 3 or 6 hex chars
                    color_str = '#' + color_str
                else:
                    logger.warning(f"Invalid hex color format (no # and not hex chars) '{value}'. Using default: {default}")
                    return default

            if re.fullmatch(r'#[0-9a-f]{3}', color_str):
                return '#' + ''.join(c*2 for c in color_str[1:])
            elif re.fullmatch(r'#[0-9a-f]{6}', color_str):
                return color_str
            else:
                logger.warning(f"Invalid hex color format '{value}'. Using default: {default}")
                return default
        except Exception as e:
            logger.warning(f"Error validating hex color '{value}': {e}. Using default: {default}")
            return default

    @staticmethod
    def validate_bool(value: Any, default: bool = False) -> bool:
        logger = logging.getLogger('SafeInputValidation.boolean')
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value) # 0/0.0 is False, others True
        if isinstance(value, str):
            val_lower = value.strip().lower()
            if val_lower in ['true', 'yes', '1', 'on', 't', 'y']:
                return True
            if val_lower in ['false', 'no', '0', 'off', 'f', 'n']:
                return False
        logger.warning(f"Could not interpret '{value}' (type: {type(value)}) as boolean. Using default: {default}")
        return default

    @staticmethod
    def validate_path_str(value: Any, must_exist: bool = False, 
                     create_if_not_exist: bool = False,
                     must_be_dir: bool = False, default_str: Optional[str] = None) -> Optional[str]:
        logger = logging.getLogger('SafeInputValidation.path_str')
        try:
            if value is None: return default_str
            
            try:
                # os.fspath handles Path-like objects as well as strings
                path_obj = Path(os.fspath(value)).resolve()
            except (TypeError, ValueError) as e:
                logger.warning(f"Invalid input type for path '{value}': {e}")
                return default_str

            # Basic security check for excessive parent directory traversals.
            # This is a simple heuristic. More robust checks might be needed for specific use cases.
            if str(path_obj).count("..") > 4: # Allowing a few '..' for relative paths within project
                 logger.warning(f"Path '{path_obj}' contains many '..' components. Please verify path validity.")
                 # Depending on security policy, could return default_str or raise an error here.

            if create_if_not_exist and not path_obj.exists():
                try:
                    if must_be_dir:
                        path_obj.mkdir(parents=True, exist_ok=True)
                        logger.info(f"Created directory: {path_obj}")
                    else: # For a file path, ensure its parent directory exists
                        path_obj.parent.mkdir(parents=True, exist_ok=True)
                        logger.info(f"Ensured parent directory exists for: {path_obj}")
                except OSError as os_e:
                    logger.error(f"Could not create path or parent for '{path_obj}': {os_e}")
                    return default_str # Failed to create

            if must_exist and not path_obj.exists():
                logger.debug(f"Path '{path_obj}' must exist but doesn't.")
                return default_str
            
            if path_obj.exists(): # Only check type if it exists
                if must_be_dir and not path_obj.is_dir():
                    logger.debug(f"Path '{path_obj}' must be a directory but is a file.")
                    return default_str
                # If it must be a file (not a dir), and it exists and is a dir
                if not must_be_dir and path_obj.is_dir() and must_exist: 
                    logger.debug(f"Path '{path_obj}' must be a file but is a directory.")
                    return default_str
            return str(path_obj)
            
        except Exception as e:
            logger.warning(f"Path validation error for '{value}': {e}. Using default: {default_str}", exc_info=True)
            return default_str

