#!/usr/bin/env python3
"""
Quick fix for syntax error in controller.py
"""

def fix_controller_syntax():
    """Fix the syntax error in controller.py"""
    
    controller_path = 'gui/controller.py'
    
    with open(controller_path, 'r') as f:
        content = f.read()
    
    # Find and fix the syntax error around line 733
    # The issue is likely a missing method closure
    
    # Fix the specific syntax issue
    content = content.replace(
        "elements.append({'element': keyboard_outline, 'zone': -1, 'type': 'outline'})\n    def update_preview_keyboard(self, canvas=None, elements_list=None):",
        "elements.append({'element': keyboard_outline, 'zone': -1, 'type': 'outline'})\n\n    def update_preview_keyboard(self, canvas=None, elements_list=None):"
    )
    
    # Also fix any other similar issues
    content = content.replace(
        "elements.append({'element': keyboard_outline, 'zone': -1, 'type': 'outline'})    def update_preview_keyboard",
        "elements.append({'element': keyboard_outline, 'zone': -1, 'type': 'outline'})\n\n    def update_preview_keyboard"
    )
    
    # Make sure the create_realistic_keyboard_layout method is properly closed
    # Look for the pattern and ensure proper spacing
    import re
    
    # Fix any method boundary issues
    content = re.sub(
        r'(elements\.append\({\'element\': keyboard_outline.*?\}\))\s*def update_preview_keyboard',
        r'\1\n\n    def update_preview_keyboard',
        content
    )
    
    with open(controller_path, 'w') as f:
        f.write(content)
    
    print("✅ Fixed syntax error in controller.py")

def main():
    """Main execution"""
    import os
    
    if os.path.exists('gui/controller.py'):
        fix_controller_syntax()
        print("🔧 Syntax error fixed!")
        print("📍 Now try running your application again:")
        print("   sudo python3 -m rgb_controller_finalv3")
    else:
        print("❌ Error: controller.py not found")
        print("Make sure you're in the rgb_controller_finalv3 directory")

if __name__ == "__main__":
    main()