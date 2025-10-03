#!/usr/bin/env python3
"""RGB Keyboard Controller - Main Entry Point - Enhanced & Robust"""

import sys
import os
import logging
import subprocess
from pathlib import Path

def setup_python_path():
    """Setup Python path for imports"""
    current_dir = Path(__file__).parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))

def setup_logging():
    """Setup basic logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger('RGB_Controller_Main')

def check_root_privileges():
    """Check if running with root privileges"""
    if os.name == 'nt':  # Windows
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    else:  # Unix-like (Linux, macOS)
        return os.geteuid() == 0

def install_keyboard_library_safe(logger):
    """Safe keyboard library installation with fallbacks"""
    try:
        import keyboard
        logger.info("✓ Keyboard library already available")
        return True
    except ImportError:
        pass
    
    if not check_root_privileges():
        logger.warning("Not running as root - keyboard library installation skipped")
        return False
    
    logger.info("Attempting to install keyboard library...")
    
    # Method 1: Try apt install
    try:
        result = subprocess.run(['apt', 'install', '-y', 'python3-keyboard'], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            logger.info("✓ Keyboard library installed via apt")
            try:
                import keyboard
                return True
            except ImportError:
                pass
    except:
        pass
    
    # Method 2: Try pip with --break-system-packages (last resort)
    try:
        logger.warning("Attempting pip install with system override...")
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'install', 'keyboard', '--break-system-packages'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            logger.info("✓ Keyboard library installed via pip (system override)")
            try:
                import keyboard
                return True
            except ImportError:
                pass
    except:
        pass
    
    logger.warning("⚠ Keyboard library installation failed")
    logger.warning("ALT+Brightness hotkeys will be disabled")
    return False

def create_required_directories(project_dir, logger):
    """Ensure all required directories exist"""
    
    # Security Fix: Define content as an explicit, safe, hardcoded constant 
    # to resolve the static analysis false positive.
    INIT_DOCSTRING = '"""Package initialization"""\n' 
    
    required_dirs = [
        project_dir / "gui",
        project_dir / "gui" / "core",
        project_dir / "gui" / "effects", 
        project_dir / "gui" / "hardware",
        project_dir / "gui" / "utils",
        project_dir / "logs"
    ]
    
    for dir_path in required_dirs:
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            # Create __init__.py if it's a Python package directory
            if "gui" in str(dir_path) and dir_path.name != "gui":
                init_file = dir_path / "__init__.py"
                if not init_file.exists():
                    init_file.write_text(INIT_DOCSTRING) 
        except Exception as e:
            logger.warning(f"Could not create directory {dir_path}: {e}")

def setup_enhanced_logging(project_dir, logger):
    """Setup enhanced file logging"""
    try:
        log_dir = project_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / "rgb_controller_startup.log"
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        root_logger.setLevel(logging.DEBUG)
        
        logger.info(f"✓ Enhanced logging to: {log_file}")
    except Exception as e:
        logger.warning(f"Could not set up enhanced logging: {e}")

def run_gui_application(logger):
    """Run the main GUI application with robust error handling"""
    try:
        logger.info("Starting RGB Controller GUI...")
        
        # Check privileges
        if not check_root_privileges():
            logger.error("ERROR: This application requires root privileges")
            logger.error("Please run: sudo python3 -m rgb_controller_finalv3")
            return False
        
        # Try to install keyboard library
        keyboard_available = install_keyboard_library_safe(logger)
        if not keyboard_available:
            logger.warning("Keyboard library not available - hotkeys disabled")
        
        # Try importing GUI modules with detailed error reporting
        try:
            logger.info("Importing GUI core modules...")
            from gui.core.rgb_color import RGBColor
            from gui.core.constants import APP_NAME, NUM_ZONES
            logger.info("✓ Core modules imported")
            
            logger.info("Importing hardware controller...")
            from gui.hardware.controller import HardwareController
            logger.info("✓ Hardware controller imported")
            
            logger.info("Importing effects system...")
            from gui.effects.manager import EffectManager
            logger.info("✓ Effects system imported")
            
            logger.info("Importing main GUI controller...")
            from gui.controller import main as start_gui_main_loop
            logger.info("✓ All GUI modules imported successfully")
            
            # Start the GUI
            logger.info("Launching GUI...")
            start_gui_main_loop()
            return True
            
        except ImportError as e:
            logger.critical(f"Import error: {e}")
            logger.critical("Missing or corrupted module files")
            
            # Try to provide specific guidance
            missing_module = str(e).replace("No module named ", "").strip("'")
            logger.critical(f"Missing module: {missing_module}")
            
            if "gui.hardware.controller" in missing_module:
                logger.critical("Hardware controller module missing!")
                logger.critical("Run the comprehensive fix script to recreate missing files")
            elif "gui.core" in missing_module:
                logger.critical("Core modules missing!")
                logger.critical("Ensure all core files are present in gui/core/")
            elif "gui.effects" in missing_module:
                logger.critical("Effects modules missing!")
                logger.critical("Ensure effects files are present in gui/effects/")
            
            return False
            
        except SyntaxError as e:
            logger.critical(f"Syntax error in module: {e}")
            logger.critical(f"File: {e.filename}, Line: {e.lineno}")
            logger.critical("Fix syntax errors in the specified file")
            return False
            
        except Exception as e:
            logger.critical(f"Unexpected error importing GUI: {e}")
            import traceback
            logger.critical(traceback.format_exc())
            return False
            
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        return True
    except Exception as e:
        logger.critical(f"Critical error in main application: {e}")
        import traceback
        logger.critical(traceback.format_exc())
        return False

def main():
    """Enhanced main entry point"""
    print("🌈 RGB Keyboard Controller v3 - Enhanced")
    print("=========================================")
    
    # Setup Python path first
    setup_python_path()
    
    # Setup logging
    logger = setup_logging()
    
    # Get project directory
    project_dir = Path(__file__).parent
    
    # Create required directories
    create_required_directories(project_dir, logger)
    
    # Setup enhanced logging
    setup_enhanced_logging(project_dir, logger)
    
    # Log system info
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Platform: {sys.platform}")
    logger.info(f"Running as root: {check_root_privileges()}")
    logger.info(f"Project directory: {project_dir}")
    
    # Run the application
    success = run_gui_application(logger)
    
    if success:
        logger.info("Application completed successfully")
        sys.exit(0)
    else:
        logger.error("Application failed - check logs for details")
        sys.exit(1)

if __name__ == "__main__":
    main()
