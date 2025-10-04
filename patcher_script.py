#!/usr/bin/env python3
import fileinput
import sys
import os

def apply_patch():
    """
    Corrects the indentation of the for loop and its contents in the
    apply_rainbow_zones method to resolve the SyntaxError.
    """
    if len(sys.argv) < 2:
        print("Usage: python3 patcher_script.py <path_to_controller.py>")
        return 1

    target_file = sys.argv[1]

    if not os.path.isfile(target_file):
        print(f"❌ Error: The file {target_file} was not found.")
        return 1

    try:
        with fileinput.FileInput(target_file, inplace=True, backup='.bak') as file:
            in_function = False
            for line in file:
                if line.strip().startswith("def apply_rainbow_zones(self):"):
                    in_function = True
                if in_function and line.strip().startswith("for i in range(NUM_ZONES):"):
                    line = " " * 12 + line.strip() + "\n"
                    in_function = False
                print(line, end='')

        print(f"✅ Successfully patched {target_file}. A backup file '{target_file}.bak' has been created.")
        return 0
    except FileNotFoundError:
        print(f"❌ Error: The file {target_file} was not found.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ An error occurred during patching: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(apply_patch())
