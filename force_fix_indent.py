# force_fix_indent.py
import os

file_to_fix = os.path.join("gui", "controller.py")
error_line_number = 31 # The line with the IndentationError


print(f"Attempting to force-fix the indent on line {error_line_number} of {file_to_fix}...")

try:
    with open(file_to_fix, 'r') as f:
        lines = f.readlines()

    # Convert to a 0-based index
    line_index = error_line_number - 1

    if 0 <= line_index < len(lines):
        original_line = lines[line_index]
        # Remove all leading whitespace from the specific line
        corrected_line = original_line.lstrip()

        if original_line != corrected_line:
            print(f"Found and fixed incorrect indentation on line {error_line_number}.")
            lines[line_index] = corrected_line
            
            # Write the corrected lines back to the file
            with open(file_to_fix, 'w') as f:
                f.writelines(lines)
            
            print("\n✅ File has been rewritten. The IndentationError should be resolved.")
        else:
            print("Line was already correct. No changes made.")
    else:
        print(f"[ERROR] Line {error_line_number} does not exist in the file.")

except FileNotFoundError:
    print(f"[ERROR] Could not find the file: {file_to_fix}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
