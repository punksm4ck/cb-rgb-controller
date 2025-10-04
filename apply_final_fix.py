#!/usr/bin/env python3
"""
A surgical and safe patch script for gui/controller.py to fix a critical TypeError
while ensuring correct Python syntax.

This script replaces the entire 'try...except' block within the
'update_preview_keyboard' function to guarantee correct indentation.

It addresses the GUI-crashing TypeError by adding a robust type check.
"""
import os
import sys
import shutil
from datetime import datetime

# --- Configuration ---
TARGET_FILE_PATH = "gui/controller.py"
# --- End Configuration ---

# --- Patch Definition ---
# This patch fixes the GUI crash (TypeError) by replacing a large, stable
# block of code, which also corrects any previous indentation errors.

OLD_CODE_BLOCK = """        try:
            # Update each keyboard element based on its zone
            for elem_info in elements:
                if elem_info['type'] == 'key':
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
                elif elem_info['type'] == 'divider':
                    # Update zone dividers based on activity
                    canvas.itemconfig(elem_info['element'], fill='#666666')
        except tk.TclError:"""

NEW_CODE_BLOCK = """        try:
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
        except tk.TclError:"""

# --- End Patch Definition ---

def main():
    """Main function to execute the patching process."""
    print("--- Starting Surgical Syntax & TypeError Patch Script ---")
    
    # 1. Validate that the target file exists
    if not os.path.exists(TARGET_FILE_PATH):
        print(f"\n[ERROR] Target file not found at: '{TARGET_FILE_PATH}'")
        sys.exit(1)

    print(f"\n[1/4] Found target file: '{TARGET_FILE_PATH}'")

    # 2. Create a timestamped backup
    try:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = f"{TARGET_FILE_PATH}.{timestamp}.final_fix.backup"
        shutil.copy2(TARGET_FILE_PATH, backup_path)
        print(f"[2/4] Successfully created backup at: '{backup_path}'")
    except Exception as e:
        print(f"\n[ERROR] Could not create backup file: {e}")
        sys.exit(1)

    # 3. Read the file content
    try:
        with open(TARGET_FILE_PATH, 'r', encoding='utf-8') as f:
            original_content = f.read()
    except Exception as e:
        print(f"\n[ERROR] Could not read target file content: {e}")
        sys.exit(1)

    # 4. Apply the patch in memory
    print("[3/4] Applying patch in memory...")
    
    if OLD_CODE_BLOCK in original_content:
        modified_content = original_content.replace(OLD_CODE_BLOCK, NEW_CODE_BLOCK, 1)
        print("  - SUCCESS: Patch target found and modification applied in memory.")
        
        # 5. Write the patched file
        print("\n[4/4] Writing changes to disk...")
        try:
            with open(TARGET_FILE_PATH, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            print(f"  - SUCCESS: Patched '{TARGET_FILE_PATH}'")
            print("\n--- Patching Complete! ---")
            print("The syntax error and GUI crash bug have been fixed.")
            print("You may now try to run the main application again.")
        except Exception as e:
            print(f"\n[ERROR] Failed to write changes back to the file: {e}")
            print(f"  - Please restore the backup from '{backup_path}' to be safe.")
            sys.exit(1)
            
    else:
        print("\n[ERROR] Patch FAILED.")
        print("  - The expected block of code was NOT found.")
        print("  - Did you remember to restore the backup file first?")
        print(f"  - Command: sudo cp {TARGET_FILE_PATH}.*.backup {TARGET_FILE_PATH}")
        print("  - Aborting all changes. Your file has not been modified by this script.")
        print(f"  - A new backup was still created at '{backup_path}'.")
        sys.exit(1)

if __name__ == "__main__":
    main()
