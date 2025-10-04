#!/usr/bin/env python3
"""
A targeted and safe patch script for gui/controller.py.

This script addresses one specific issue:
1. TypeError: Adds a type check to the GUI preview update function to prevent crashes
   when it receives unexpected data.

Features:
- Creates a timestamped backup of the original file before any modifications.
- Validates that the code to be patched exists before attempting a fix.
- Provides clear terminal output on its progress, success, or failure.
"""
import os
import sys
import shutil
from datetime import datetime

# --- Configuration ---
TARGET_FILE_PATH = "gui/controller.py"
# --- End Configuration ---

# --- Patch Definition ---
# This patch fixes the GUI crash (TypeError: string indices must be integers)
PATCH_DATA = (
    "GUI Preview Crash Fix (TypeError)",
    # This is the exact line causing the TypeError.
    "if elem_info['type'] == 'key':",
    # The new code adds a robust check to ensure elem_info is a dictionary
    # before trying to access its keys, preventing the crash.
    "            # --- PATCH: Add type check to prevent TypeError on malformed data ---\n            if isinstance(elem_info, dict) and elem_info.get('type') == 'key':"
)
# --- End Patch Definition ---

def main():
    """Main function to execute the patching process."""
    print("--- Starting Targeted GUI Controller Patch Script ---")
    
    # 1. Validate that the target file exists
    if not os.path.exists(TARGET_FILE_PATH):
        print(f"\n[ERROR] Target file not found at: '{TARGET_FILE_PATH}'")
        print("Please ensure you are running this script from the root of the 'rgb_controller_finalv3' directory.")
        sys.exit(1)

    print(f"\n[1/4] Found target file: '{TARGET_FILE_PATH}'")

    # 2. Create a timestamped backup
    try:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = f"{TARGET_FILE_PATH}.{timestamp}.backup"
        shutil.copy2(TARGET_FILE_PATH, backup_path)
        print(f"[2/4] Successfully created backup at: '{backup_path}'")
    except Exception as e:
        print(f"\n[ERROR] Could not create backup file: {e}")
        print("Aborting to prevent data loss. No changes have been made.")
        sys.exit(1)

    # 3. Read the file content
    try:
        with open(TARGET_FILE_PATH, 'r', encoding='utf-8') as f:
            original_content = f.read()
    except Exception as e:
        print(f"\n[ERROR] Could not read target file content: {e}")
        print("Aborting. No changes have been made.")
        sys.exit(1)

    # 4. Apply the patch in memory
    print("[3/4] Applying patch in memory...")
    name, old_code, new_code = PATCH_DATA
    
    if old_code in original_content:
        modified_content = original_content.replace(old_code, new_code, 1)
        print(f"  - SUCCESS: Patch '{name}' applied in memory.")
        
        # 5. Write the patched file
        print("\n[4/4] Writing changes to disk...")
        try:
            with open(TARGET_FILE_PATH, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            print(f"  - SUCCESS: Patched '{TARGET_FILE_PATH}'")
            print("\n--- Patching Complete! ---")
            print("The required fix has been applied to gui/controller.py.")
            print("You may now try to run the main application again.")
        except Exception as e:
            print(f"\n[ERROR] Failed to write changes back to the file: {e}")
            print(f"  - Please restore the backup from '{backup_path}' to be safe.")
            sys.exit(1)
            
    else:
        # Fallback: If the code isn't found, something is wrong.
        print(f"\n[ERROR] Patch '{name}' FAILED.")
        print("  - The expected code snippet to be replaced was NOT found.")
        print("  - The file may have been modified already or is different than expected.")
        print("  - Aborting all changes to prevent damaging the file.")
        print(f"  - Your original file is safe, and a backup was created at '{backup_path}'.")
        sys.exit(1)

if __name__ == "__main__":
    main()
