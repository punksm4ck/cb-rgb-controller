# fix_syntax.py
import os

# The file with the syntax error, based on your project tree. 
file_to_correct = os.path.join("gui", "controller.py")

# The line number from the traceback.
line_number_with_error = 2667

def patch_file():
    """
    Reads the file, corrects the specific syntax error, and writes the changes back.
    """
    print(f"Attempting to patch '{file_to_correct}'...")

    try:
        # Read all lines from the file
        with open(file_to_correct, 'r') as f:
            lines = f.readlines()

        # Convert to 0-based index for list access
        line_index = line_number_with_error - 1

        # Check if the line number is valid
        if line_index < 0 or line_index >= len(lines):
            print(f"[ERROR] Line {line_number_with_error} is out of the file's range.")
            return

        # Replace the incorrect closing brace with a bracket
        if '}' in lines[line_index]:
            print(f"Line {line_number_with_error} before correction: {lines[line_index].strip()}")
            lines[line_index] = lines[line_index].replace('}', ']', 1)
            print(f"Line {line_number_with_error} after correction:  {lines[line_index].strip()}")

            # Write the corrected lines back to the file
            with open(file_to_correct, 'w') as f:
                f.writelines(lines)

            print(f"\n✅ Successfully corrected the SyntaxError in '{file_to_correct}'.")
        else:
            print(f"[WARNING] The expected '}}' was not found on line {line_number_with_error}. No changes were made.")

    except FileNotFoundError:
        print(f"[ERROR] File not found: '{file_to_correct}'")
        print("Please ensure this script is located in the root 'rgb_controller_finalv2' directory before running.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    patch_file()
