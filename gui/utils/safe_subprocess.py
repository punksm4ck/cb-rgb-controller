#!/usr/bin/env python3
"""Safe subprocess handling with comprehensive error checking"""

import subprocess
import logging
import shlex 
import re # <<< Added missing import 're'
from typing import List, Tuple, Optional, Union 

from ..core.exceptions import SecurityError, HardwareError, ResourceError
from .decorators import safe_execute

def run_command(cmd: List[str], 
                timeout: float = 5.0, 
                check: bool = False, 
                input_data: Optional[Union[str, bytes]] = None,
                text_mode: bool = True
                ) -> subprocess.CompletedProcess:
    """
    Run a command safely without shell injection risks.
    Manages timeouts, captures output, and logs errors.
    """
    logger = logging.getLogger('SafeSubprocess.run_command')

    if not cmd or not isinstance(cmd, list):
        logger.error("Invalid command format: Command must be a non-empty list.")
        raise SecurityError("Invalid command format: Command must be a non-empty list.")
    
    sanitized_cmd: List[str] = []
    for i, arg in enumerate(cmd):
        if not isinstance(arg, (str, bytes)):
            logger.error(f"Invalid command argument type at index {i}: {type(arg)}. Must be str or bytes.")
            raise SecurityError(f"Invalid command argument type at index {i}: {type(arg)}.")
        if isinstance(arg, bytes):
            try:
                sanitized_cmd.append(arg.decode('utf-8', errors='strict'))
            except UnicodeDecodeError:
                logger.error(f"Command argument at index {i} is bytes but not valid UTF-8.")
                raise SecurityError(f"Non-UTF8 byte string in command argument at index {i}.")
        else: 
            sanitized_cmd.append(arg)

    if not all(s.strip() for s in sanitized_cmd):
        logger.error(f"Command contains empty or whitespace-only arguments: {sanitized_cmd}")
        raise SecurityError("Command arguments cannot be empty or solely whitespace.")

    dangerous_chars_pattern = re.compile(r"[;&|<>`$()]")
    for arg_str in sanitized_cmd:
        if dangerous_chars_pattern.search(arg_str):
            logger.warning(f"Potentially problematic characters found in command argument: '{arg_str}'")

    processed_input: Optional[Union[str,bytes]] = None
    if input_data is not None:
        if text_mode:
            if isinstance(input_data, bytes):
                try:
                    processed_input = input_data.decode('utf-8', errors='strict')
                except UnicodeDecodeError:
                    logger.error("Input data for text mode is bytes but not valid UTF-8.")
                    raise ValueError("Invalid input_data encoding for text mode (expected str or UTF-8 bytes).")
            elif not isinstance(input_data, str):
                processed_input = str(input_data)
            else:
                processed_input = input_data
        else: 
            if isinstance(input_data, str):
                processed_input = input_data.encode('utf-8')
            elif not isinstance(input_data, bytes):
                logger.error(f"Input data for binary mode is not bytes or str: {type(input_data)}")
                raise ValueError("Invalid input_data type for binary mode (expected bytes or str).")
            else:
                processed_input = input_data

    cmd_display = ' '.join(shlex.quote(s) for s in sanitized_cmd)
    logger.debug(f"Executing command: {cmd_display[:250]}{'...' if len(cmd_display)>250 else ''} (Timeout: {timeout}s)")

    try:
        result = subprocess.run(
            sanitized_cmd,
            input=processed_input,
            capture_output=True,
            text=text_mode, 
            timeout=timeout,
            check=check,    
            shell=False     
        )
        if result.returncode != 0 and not check: 
             logger.warning(f"Command '{sanitized_cmd[0]}' exited with code {result.returncode}. Stderr: '{result.stderr.strip()[:200] if result.stderr else ''}'")
        elif result.returncode == 0:
             logger.debug(f"Command '{sanitized_cmd[0]}' completed successfully. Stdout: '{result.stdout.strip()[:100] if result.stdout else ''}'")
        return result
        
    except subprocess.TimeoutExpired as e:
        logger.error(f"Command '{sanitized_cmd[0]}' timed out after {timeout} seconds.", exc_info=True)
        raise HardwareError(f"Command '{sanitized_cmd[0]}' timed out: {e}") from e
    except subprocess.CalledProcessError as e: 
        logger.error(f"Command '{sanitized_cmd[0]}' failed with return code {e.returncode}. Stderr: {e.stderr.strip() if e.stderr else 'N/A'}", exc_info=True)
        raise HardwareError(f"Command '{sanitized_cmd[0]}' failed: {e}") from e
    except FileNotFoundError as e: 
        logger.error(f"Command executable not found: '{sanitized_cmd[0]}'. Error: {e}", exc_info=True)
        raise ResourceError(f"Executable '{sanitized_cmd[0]}' not found.") from e
    except Exception as e: 
        logger.critical(f"Unexpected OS error running command '{sanitized_cmd[0]}': {e}", exc_info=True)
        raise HardwareError(f"Unexpected OS error during command execution: {e}") from e
