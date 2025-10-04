# fix_indent_block.py
import os

file_to_fix = os.path.join("gui", "controller.py")
# The first line where we know the indentation errors started.
start_line_of_errors = 29

print(f"Attempting to fix block indentation in {file_to_fix} starting from line {start_line_of_errors}...")

try:
    with open(file_to_fix, 'r') as f:
        lines = f.readlines()

    corrected_lines = []
    lines_fixed_count = 0
    in_bad_block = False

    for i, line in enumerate(lines):
        line_number = i + 1
        
        if line_number >= start_line_of_errors and not in_bad_block:
            print(f"\n--- Starting fix at line {line_number} ---")
            in_bad_block = True

        if in_bad_block:
            stripped_line = line.lstrip()
            # Stop fixing when we hit the start of a class or function definition.
            if stripped_line.startswith('class ') or stripped_line.startswith('def '):
                print(f"--- Reached end of block at line {line_number}. Stopping fix. ---")
                in_bad_block = False
                corrected_lines.append(line)
                continue

            # If the line was changed (i.e., it was indented)
            if line != stripped_line:
                print(f"  - Fixed line {line_number}: {stripped_line.rstrip()}")
                corrected_lines.append(stripped_line)
                lines_fixed_count += 1
            else:
                corrected_lines.append(line)
        else:
            corrected_lines.append(line)
            
    if lines_fixed_count > 0:
        # Write the completely fixed content back to the file
        with open(file_to_fix, 'w') as f:
            f.writelines(corrected_lines)
        print(f"\n✅ Successfully fixed {lines_fixed_count} lines. The block indentation issue should now be fully resolved.")
    else:
        print("\nNo incorrectly indented lines were found in the suspected block. No changes made.")

except FileNotFoundError:
    print(f"[ERROR] Could not find the file: {file_to_fix}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
