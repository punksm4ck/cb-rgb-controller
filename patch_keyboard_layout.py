#!/usr/bin/env python3
"""
One-time patch script to fix keyboard layout preview in controller.py
Run this once to update the keyboard preview to show horizontal zones.
"""

import re

def patch_keyboard_layout(file_path='gui/controller.py'):
    """Apply keyboard layout patches to controller.py"""
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # 1. Replace canvas dimensions in create_preview_canvas
    content = content.replace(
        'canvas_width = 600\n        canvas_height = 200',
        'canvas_width = 800\n        canvas_height = 180'
    )
    
    # 2. Replace method name calls
    content = content.replace(
        'self.create_realistic_keyboard_layout()',
        'self.create_horizontal_keyboard_layout()'
    )
    content = content.replace(
        'self.create_realistic_keyboard_layout(canvas=current_canvas, elements_list=\'static_keyboard_elements\')',
        'self.create_horizontal_keyboard_layout(canvas=current_canvas, elements_list=\'static_keyboard_elements\')'
    )
    content = content.replace(
        'self.create_realistic_keyboard_layout(canvas=current_canvas, elements_list=\'zone_keyboard_elements\')',
        'self.create_horizontal_keyboard_layout(canvas=current_canvas, elements_list=\'zone_keyboard_elements\')'
    )
    
    # 3. Replace the entire create_realistic_keyboard_layout method
    old_method_pattern = r'    def create_realistic_keyboard_layout\(self, canvas=None, elements_list=\'preview_keyboard_elements\'\):.*?(?=    def \w+|$)'
    
    new_method = '''    def create_horizontal_keyboard_layout(self, canvas=None, elements_list='preview_keyboard_elements'):
        """Create a realistic horizontal keyboard layout with proper zone mapping"""
        if canvas is None:
            canvas = self.preview_canvas
        
        # Get the elements list to store in
        if elements_list == 'static_keyboard_elements':
            elements = self.static_keyboard_elements = []
        elif elements_list == 'zone_keyboard_elements':
            elements = self.zone_keyboard_elements = []
        else:
            elements = self.preview_keyboard_elements = []
        
        # Clear existing elements
        canvas.delete("all")
        elements.clear()
        
        # Keyboard dimensions and spacing for horizontal layout
        canvas_width = 800
        canvas_height = 180
        key_width = 18
        key_height = 18
        key_gap = 2
        
        # Zone layout - HORIZONTAL zones (left to right across keyboard)
        zone_width = canvas_width // NUM_ZONES
        zone_colors = ['#404040'] * NUM_ZONES  # Default colors
        
        # Create horizontal zone sections
        for zone_idx in range(NUM_ZONES):
            zone_x_start = zone_idx * zone_width
            zone_x_end = (zone_idx + 1) * zone_width
            
            # Create zone background
            zone_bg = canvas.create_rectangle(
                zone_x_start + 5, 10, zone_x_end - 5, canvas_height - 10,
                fill='#2a2a2a', outline='#555555', width=1
            )
            elements.append({'element': zone_bg, 'zone': zone_idx, 'type': 'zone_bg'})
            
            # Create keys within this zone
            keys_per_zone = 12  # Approximate keys per zone
            key_rows = 4
            keys_per_row = keys_per_zone // key_rows
            
            for row in range(key_rows):
                for key_in_row in range(keys_per_row):
                    # Calculate key position within zone
                    key_x = zone_x_start + 15 + (key_in_row * (key_width + key_gap))
                    key_y = 25 + (row * (key_height + key_gap))
                    
                    # Ensure key fits within zone
                    if key_x + key_width < zone_x_end - 10:
                        key_rect = canvas.create_rectangle(
                            key_x, key_y, key_x + key_width, key_y + key_height,
                            fill='#404040', outline='#606060', width=1
                        )
                        elements.append({'element': key_rect, 'zone': zone_idx, 'type': 'key'})
            
            # Add zone label
            zone_label_x = zone_x_start + (zone_width // 2)
            zone_label_y = canvas_height - 25
            text_element = canvas.create_text(
                zone_label_x, zone_label_y, 
                text=f'Zone {zone_idx + 1}', 
                fill='#888888', font=('Arial', 10, 'bold')
            )
            elements.append({'element': text_element, 'zone': zone_idx, 'type': 'label'})
        
        # Add keyboard outline
        keyboard_outline = canvas.create_rectangle(
            5, 5, canvas_width - 5, canvas_height - 5,
            fill='', outline='#777777', width=2
        )
        elements.append({'element': keyboard_outline, 'zone': -1, 'type': 'outline'})

'''
    
    content = re.sub(old_method_pattern, new_method, content, flags=re.DOTALL)
    
    # 4. Replace the update_preview_keyboard method
    old_update_pattern = r'    def update_preview_keyboard\(self, canvas=None, elements_list=None\):.*?(?=    def \w+|$)'
    
    new_update_method = '''    def update_preview_keyboard(self, canvas=None, elements_list=None):
        """Update the horizontal keyboard preview with current LED states"""
        if canvas is None:
            canvas = self.preview_canvas
        
        if elements_list is None:
            elements = self.preview_keyboard_elements
        elif elements_list == 'static_keyboard_elements':
            elements = self.static_keyboard_elements
        elif elements_list == 'zone_keyboard_elements':
            elements = self.zone_keyboard_elements
        else:
            elements = self.preview_keyboard_elements
        
        if not canvas or not canvas.winfo_exists() or not elements:
            return
        
        try:
            # Update each keyboard element based on its zone
            for elem_info in elements:
                if elem_info['type'] in ['key', 'zone_bg']:
                    zone = elem_info['zone']
                    if 0 <= zone < len(self.zone_colors):
                        color = self.zone_colors[zone].to_hex()
                        # Make zone backgrounds slightly darker
                        if elem_info['type'] == 'zone_bg':
                            # Darken the zone background color
                            zone_color = self.zone_colors[zone]
                            darker_color = RGBColor(
                                max(0, zone_color.r - 30),
                                max(0, zone_color.g - 30),
                                max(0, zone_color.b - 30)
                            ).to_hex()
                            canvas.itemconfig(elem_info['element'], fill=darker_color)
                        else:
                            canvas.itemconfig(elem_info['element'], fill=color)
                    else:
                        default_color = '#404040' if elem_info['type'] == 'key' else '#2a2a2a'
                        canvas.itemconfig(elem_info['element'], fill=default_color)
        except tk.TclError:
            # Canvas might be destroyed during shutdown
            pass

'''
    
    content = re.sub(old_update_pattern, new_update_method, content, flags=re.DOTALL)
    
    # Write the updated content back
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Successfully patched {file_path}")
    print("Applied changes:")
    print("  - Updated canvas dimensions to 800x180")
    print("  - Replaced create_realistic_keyboard_layout with create_horizontal_keyboard_layout") 
    print("  - Updated keyboard layout to show horizontal zones")
    print("  - Enhanced update_preview_keyboard with zone background darkening")
    print("  - Updated all method calls to use new horizontal layout")

def main():
    """Main execution function"""
    import os
    
    # Check if we're in the right directory
    if os.path.exists('gui/controller.py'):
        patch_keyboard_layout('gui/controller.py')
    elif os.path.exists('controller.py'):
        patch_keyboard_layout('controller.py')
    else:
        print("❌ Error: Could not find controller.py file")
        print("Make sure you're running this from the directory containing:")
        print("  - gui/controller.py (if in project root)")
        print("  - controller.py (if in gui directory)")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
