# force_fix.py
import os

file_to_correct = os.path.join("gui", "controller.py")
line_with_error = 2667  # Line number from the traceback

print(f"Attempting to directly patch Line {line_with_error} in '{file_to_correct}'...")

try:
    with open(file_to_correct, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Convert to 0-based index for list access
    line_index = line_with_error - 1

    if 0 <= line_index < len(lines):
        original_line = lines[line_index]
        if '}' in original_line:
            # Replace the first occurrence of } with ] on the specific line
            lines[line_index] = original_line.replace('}', ']', 1)

            # Write the corrected content back to the file
            with open(file_to_correct, 'w', encoding='utf-8') as f:
                f.writelines(lines)

            print(f"\n✅ Success! Line {line_with_error} was corrected.")
            print(f"   - OLD: {original_line.strip()}")
            print(f"   + NEW: {lines[line_index].strip()}")
        else:
            print(f"[WARNING] Line {line_with_error} did not contain the expected '}}' character. File may already be fixed.")
    else:
        print(f"[ERROR] Line number {line_with_error} is out of range for the file.")

except FileNotFoundError:
    print(f"[ERROR] File not found: '{file_to_correct}'. Please run this script from the 'rgb_controller_finalv3' directory.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
