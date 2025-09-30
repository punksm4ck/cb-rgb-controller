# gui/utils/system_info.py

import logging
import platform
import sys
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
import json # Added import
import traceback # Added import

# Attempt to import psutil for more detailed info, but make it optional
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Placeholder for APP_NAME and VERSION if not imported from constants
# These should ideally come from your project's constants.py
APP_NAME_FALLBACK = "RGBControllerApp" # Default if constants can't be imported
VERSION_FALLBACK = "0.0.0"      # Default if constants can't be imported

def get_system_info_list() -> List[str]:
    """Gathers system information as a list of formatted strings."""
    info_parts = []
    
    app_name_val = APP_NAME_FALLBACK
    app_version_val = VERSION_FALLBACK
    
    try:
        # Adjust relative import based on your project structure
        # If system_info.py is in gui/utils/ and constants.py is in gui/core/
        from ..core.constants import APP_NAME as app_name_const, VERSION as version_const
        app_name_val = app_name_const
        app_version_val = version_const
    except ImportError:
        # Fallback if the relative import fails (e.g. running script directly from utils)
        try:
            # This assumes 'core' might be a sibling directory or in PYTHONPATH
            from core.constants import APP_NAME as app_name_const, VERSION as version_const
            app_name_val = app_name_const
            app_version_val = version_const
        except ImportError:
            # Get a logger instance specifically for this module if one isn't passed
            module_logger = logging.getLogger(__name__) # or a fixed name like "SystemInfoUtil"
            module_logger.warning("Could not import APP_NAME/VERSION from core.constants for system info. Using fallbacks.")


    info_parts.append(f"Application: {app_name_val} v{app_version_val}")
    info_parts.append(f"Python Version: {sys.version.splitlines()[0]}")
    info_parts.append(f"Python Executable: {sys.executable}")
    info_parts.append(f"Platform: {platform.platform()} ({platform.architecture()[0]})")
    info_parts.append(f"System: {platform.system()}, Release: {platform.release()}, Version: {platform.version()}")
    info_parts.append(f"Machine Type: {platform.machine()}")
    info_parts.append(f"Processor: {platform.processor() if platform.processor() else 'N/A'}")

    info_parts.append(f"Current User: {os.getenv('USER', os.getenv('USERNAME', 'N/A'))} (UID: {os.geteuid() if hasattr(os, 'geteuid') else 'N/A'})")
    info_parts.append(f"Script Path: {Path(sys.argv[0]).resolve() if sys.argv else 'N/A'}")
    info_parts.append(f"Working Directory: {Path.cwd()}")
    path_env_val = os.getenv('PATH', 'N/A')
    info_parts.append(f"Path Environment Variable: {path_env_val[:200]}{'...' if len(path_env_val) > 200 else ''}")


    if PSUTIL_AVAILABLE:
        try:
            mem = psutil.virtual_memory()
            info_parts.append(f"Memory: Total {mem.total/(1024**3):.2f}GB, Available {mem.available/(1024**3):.2f}GB, Used {mem.percent}%")
            
            cpu_times = psutil.cpu_times_percent(interval=0.1, percpu=False)
            info_parts.append(f"CPU Usage: User {cpu_times.user}%, System {cpu_times.system}%, Idle {cpu_times.idle}%")
            info_parts.append(f"CPU Cores: Logical {psutil.cpu_count(logical=True)}, Physical {psutil.cpu_count(logical=False)}")
            
            boot_time_ts = psutil.boot_time()
            boot_time_dt = datetime.fromtimestamp(boot_time_ts)
            uptime_delta = datetime.now() - boot_time_dt
            info_parts.append(f"System Boot Time: {boot_time_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            info_parts.append(f"System Uptime: {str(uptime_delta).split('.')[0]}") 

            try:
                disk_root = psutil.disk_usage('/')
                info_parts.append(f"Disk Usage (/): Total {disk_root.total/(1024**3):.2f}GB, Used {disk_root.percent}%")
                home_path = Path.home()
                if home_path.exists() and home_path != Path('/'): # Check if home path exists and is not root
                    disk_home = psutil.disk_usage(str(home_path))
                    info_parts.append(f"Disk Usage ({home_path}): Total {disk_home.total/(1024**3):.2f}GB, Used {disk_home.percent}%")
            except Exception as e_disk:
                info_parts.append(f"Disk usage info error: {e_disk}")

        except Exception as e_psutil:
            info_parts.append(f"psutil system information retrieval error: {e_psutil}")
    else:
        info_parts.append("psutil module not available - detailed system statistics (memory, CPU, uptime, disk) are limited.")
    
    return info_parts

def get_system_info_string() -> str:
    """Gathers and formats a string containing system information."""
    return "\n".join(get_system_info_list())


def log_system_info(logger: logging.Logger):
    """Logs detailed system information using the provided logger."""
    if not isinstance(logger, logging.Logger):
        print("Error: Valid logger not provided to log_system_info.", file=sys.stderr)
        return 
    
    logger.info("======== SYSTEM INFORMATION ========")
    info_lines = get_system_info_list()
    for line in info_lines:
        logger.info(line)
    logger.info("====================================")

def log_error_with_context(logger: logging.Logger, error: Exception, context: Optional[Dict[str, Any]] = None):
    """Logs an error with optional context, including traceback if it's an Exception."""
    if not isinstance(logger, logging.Logger):
        # Fallback if logger is invalid
        print(f"--- Logger Error --- \nError (Logger N/A): {error}", file=sys.stderr)
        if context:
            try:
                print(f"Context: {json.dumps(context, default=str, indent=2)}", file=sys.stderr)
            except:
                 print(f"Context (raw): {context}", file=sys.stderr)
        if isinstance(error, Exception):
             traceback.print_exc() # Print traceback to stderr
        print("--- End Logger Error ---", file=sys.stderr)
        return

    message = f"Error Encountered: {type(error).__name__} - {str(error) or 'No error message.'}"
    if context:
        try:
            # json.dumps is now available due to import
            context_str = json.dumps(context, default=str, indent=2) 
            message += f"\n  Context: {context_str}"
        except TypeError:
            message += f"\n  Context (raw - not JSON serializable): {context}" 
    
    # Log with exc_info=True to include traceback for actual exceptions
    logger.error(message, exc_info=isinstance(error, Exception))

if __name__ == '__main__':
    # Example usage if run directly
    logging.basicConfig(level=logging.DEBUG, 
                        format='%(asctime)s - %(name)s - [%(levelname)s] %(module)s.%(funcName)s:%(lineno)d - %(message)s')
    test_logger = logging.getLogger("TestSystemInfo") # Use a specific name for the test logger
    
    print("--- System Info String ---")
    print(get_system_info_string())
    print("\n--- Logging System Info ---")
    log_system_info(test_logger)
    
    test_logger.info("\n--- Testing Error Logging ---")
    try:
        a = {}
        b = a['missing_key'] # Cause a KeyError
    except KeyError as e:
        log_error_with_context(test_logger, e, {"operation": "dictionary_access", "key_tried": "missing_key"})
    
    try:
        x = 1 / 0
    except ZeroDivisionError as e:
        log_error_with_context(test_logger, e, {"operation": "division_test", "numerator": 1, "denominator": 0})
        
    log_error_with_context(test_logger, ValueError("A test value error without traceback."), {"custom_field": 123})
