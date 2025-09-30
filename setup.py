#!/usr/bin/env python3
"""
Setup script for RGB Keyboard Controller with GUI directory structure.
Creates the proper directory structure, checks basic dependencies,
and provides setup instructions.
"""

import os
import sys # For checking Python version if needed
from pathlib import Path

# This should match the name of your root project folder for clarity in instructions
PROJECT_ROOT_DIR_NAME = "rgb_controller_final2" # Or "rgb_controller_final" as per your initial prompt

def create_directory_structure():
    """Create the required directory structure within the current working directory."""
    
    # Assumes this script is in the project root directory (e.g., rgb_controller_final2/)
    base_dir = Path.cwd()
    
    if base_dir.name != PROJECT_ROOT_DIR_NAME:
        print(f"Warning: This script is intended to be run from the root of the '{PROJECT_ROOT_DIR_NAME}' project directory.")
        print(f"Currently in: {base_dir}")
        # Optionally, create the project root if it doesn't exist and we are one level above
        # if not (base_dir / PROJECT_ROOT_DIR_NAME).exists():
        #     (base_dir / PROJECT_ROOT_DIR_NAME).mkdir()
        #     print(f"Created project directory: {base_dir / PROJECT_ROOT_DIR_NAME}")
        # base_dir = base_dir / PROJECT_ROOT_DIR_NAME # Adjust base_dir if created

    gui_base = base_dir / "gui"

    # Directories to create and the docstring for their __init__.py
    directories_to_create = {
        gui_base: f'"""Main GUI package for {PROJECT_ROOT_DIR_NAME}."""',
        gui_base / "core": '"""Core components: constants, settings, color models, custom exceptions."""',
        gui_base / "utils": '"""Utility functions: decorators, input validation, system info, safe subprocess."""',
        gui_base / "hardware": '"""Hardware interaction and control layer."""',
        gui_base / "effects": '"""Lighting effects logic, library, and management."""',
        gui_base / "assets": '"""Static assets like icons, images, etc. (Optional)"""'
    }
    
    print("\nCreating directory structure...")
    for dir_path, init_docstring in directories_to_create.items():
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            init_file = dir_path / "__init__.py"
            if not init_file.exists():
                # Create __init__.py with a minimal docstring
                init_file.write_text(f"# {init_file.relative_to(base_dir)}\n{init_docstring}\n", encoding='utf-8')
            print(f"✓ Ensured {dir_path.relative_to(base_dir)}/ and __init__.py")
        except OSError as e:
            print(f"✗ Error creating {dir_path.relative_to(base_dir)}: {e}")
            
    print("\nDirectory structure creation/verification complete!")
    print("\nExpected file organization:")
    print(f"{PROJECT_ROOT_DIR_NAME}/")
    print("├── __main__.py")
    print("├── setup.py (this script)")
    print("├── README.md")
    print("└── gui/")
    print("    ├── __init__.py")
    print("    ├── controller.py")
    print("    ├── assets/ (optional)")
    print("    │   └── icon.png (example)")
    print("    ├── core/")
    print("    │   ├── __init__.py, constants.py, settings.py, rgb_color.py, exceptions.py")
    print("    ├── utils/")
    print("    │   ├── __init__.py, decorators.py, safe_subprocess.py, system_info.py, input_validation.py")
    print("    ├── hardware/")
    print("    │   ├── __init__.py, controller.py")
    print("    └── effects/")
    print("        ├── __init__.py, library.py, manager.py")

def check_dependencies():
    """Check for required and optional dependencies."""
    print("\nChecking dependencies...")
    
    required_packages = [
        ("tkinter", "Tkinter (GUI framework - standard library, ensure python3-tk is installed on Linux)")
    ]
    optional_packages = [
        ("psutil", "psutil (for detailed system information)")
    ]
    
    missing_required = []
    missing_optional = []
    
    for package_name, description in required_packages:
        try:
            __import__(package_name)
            print(f"✓ {description} - Found")
        except ImportError:
            print(f"✗ {description} - MISSING (Required)")
            missing_required.append(package_name)

    for package_name, description in optional_packages:
        try:
            __import__(package_name)
            print(f"✓ {description} - Found")
        except ImportError:
            print(f"◦ {description} - Missing (Optional)")
            missing_optional.append(package_name)
            
    if missing_required:
        print(f"\nERROR: Missing required Python packages: {', '.join(missing_required)}")
        print("Please install them. For Tkinter on Debian/Ubuntu, try: sudo apt-get install python3-tk")
        print(f"For other packages, try: pip3 install {' '.join(missing_required)}")
        sys.exit(1) # Exit if required dependencies are missing
        
    if missing_optional:
        print(f"\nNote: Optional packages not found: {', '.join(missing_optional)}. Some features might be limited.")
        print(f"  To install, e.g., for psutil: pip3 install psutil (or sudo apt-get install python3-psutil)")
    
    if not missing_required:
        print("\nAll critical Python dependencies seem satisfied.")

def show_file_placement_guide():
    """Provides a guide for placing user's Python files into the created structure."""
    print("\nFile Placement Guide:")
    print("Please ensure your Python module files are placed in the correct subdirectories within 'gui/'.")
    file_mapping = {
        "__main__.py": f"Project root ({PROJECT_ROOT_DIR_NAME}/)",
        "controller.py (GUI logic)": "gui/",
        "constants.py": "gui/core/",
        "settings.py": "gui/core/",
        "rgb_color.py": "gui/core/",
        "exceptions.py": "gui/core/",
        "decorators.py": "gui/utils/",
        "safe_subprocess.py": "gui/utils/",
        "system_info.py": "gui/utils/",
        "input_validation.py": "gui/utils/",
        "controller.py (Hardware logic)": "gui/hardware/",
        "library.py (Effects definitions)": "gui/effects/",
        "manager.py (Effects manager)": "gui/effects/",
    }
    for filename, location in file_mapping.items():
        print(f"  - {filename:30s} ->  {location}")
    print("\nAlso, ensure each subdirectory under 'gui/' has an '__init__.py' file (this script attempts to create them).")

def main():
    print(f"RGB Keyboard Controller Setup Utility ({PROJECT_ROOT_DIR_NAME})")
    print("=" * 60)
    
    create_directory_structure()
    check_dependencies()
    show_file_placement_guide()
    
    print("\nSetup utility finished!")
    print("\nNext Steps:")
    print("1. Carefully place all your Python source files into the newly created 'gui' subdirectories as per the guide.")
    print("2. This application typically requires root/administrator privileges for hardware control.")
    print(f"3. To run the application (assuming your project root is named '{PROJECT_ROOT_DIR_NAME}'):")
    print(f"   a. Navigate to the directory *containing* '{PROJECT_ROOT_DIR_NAME}' (e.g., your Downloads folder).")
    print(f"   b. Then run: sudo python3 -m {PROJECT_ROOT_DIR_NAME}")
    print(f"      (This executes {PROJECT_ROOT_DIR_NAME}/__main__.py as a runnable package)")
    print("\n   Alternatively, if you are *inside* the '{PROJECT_ROOT_DIR_NAME}' directory:")
    print("      Run: sudo python3 .")
    print("      (This executes __main__.py directly from the current directory)")
    print("\nEnsure all relative imports within your 'gui' package (e.g., 'from .core import ...') are correct.")

if __name__ == "__main__":
    main()

