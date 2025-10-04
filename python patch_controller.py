#!/usr/bin/env python3
"""
Patch script to add missing features from combined_rgb_controller.py to controller.py
Run this once and it will update your controller.py file.
"""

import re

def patch_controller_file(file_path='controller.py'):
    with open(file_path, 'r') as f:
        content = f.read()
    
    # 1. Add missing imports after existing imports
    if 'import psutil' not in content:
        content = content.replace(
            'from functools import partial',
            'from functools import partial\nimport psutil\nimport fcntl'
        )
    
    # 2. Change class definition to inherit from SingleInstanceMixin
    content = content.replace(
        'class RGBControllerGUI:',
        'class RGBControllerGUI(SingleInstanceMixin):'
    )
    
    # 3. Add SingleInstanceMixin class before RGBControllerGUI
    mixin_code = '''

class SingleInstanceMixin:
    """Mixin to ensure only one instance of the application runs"""
    
    def __init__(self):
        self.lock_file = None
        self.is_single_instance = self._acquire_lock()
    
    def _acquire_lock(self):
        """Acquire a lock to ensure single instance"""
        try:
            lock_dir = Path.home() / ".rgb_controller_locks"
            lock_dir.mkdir(exist_ok=True)
            lock_file_path = lock_dir / f"{APP_NAME.lower().replace(' ', '_')}.lock"
            
            self.lock_file = open(lock_file_path, 'w')
            fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # Write PID to lock file
            self.lock_file.write(str(os.getpid()))
            self.lock_file.flush()
            
            return True
        except (IOError, OSError):
            # Another instance is already running
            return False
    
    def _release_lock(self):
        """Release the instance lock"""
        if self.lock_file:
            try:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
            except (IOError, OSError):
                pass
    
    def check_existing_instance(self):
        """Check if another instance is already running and try to bring it to front"""
        if not self.is_single_instance:
            try:
                # Try to find existing RGB Controller process
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        if 'python' in proc.info['name'].lower():
                            cmdline = proc.info['cmdline']
                            if any('rgb_controller' in arg.lower() for arg in cmdline):
                                # Found existing instance
                                return True
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            except Exception:
                pass
        return False


'''
    
    content = content.replace(
        'class RGBControllerGUI(SingleInstanceMixin):',
        mixin_code + 'class RGBControllerGUI(SingleInstanceMixin):'
    )
    
    # 4. Update __init__ method to include single instance logic
    init_replacement = '''    def __init__(self, root: tk.Tk):
        SingleInstanceMixin.__init__(self)
        
        # Check for existing instance before proceeding
        if not self.is_single_instance:
            if self.check_existing_instance():
                messagebox.showinfo("Already Running", 
                                   f"{APP_NAME} is already running. Please check your system tray or taskbar.")
                if root:
                    root.destroy()
                sys.exit(0)
        
        self.root = root'''
    
    content = content.replace(
        '    def __init__(self, root: tk.Tk):\n        self.root = root',
        init_replacement
    )
    
    # 5. Add _release_lock() call to perform_final_shutdown
    content = content.replace(
        '        self.tray_icon = None; self.tray_thread = None\n\n    # Indicate to GuiLogHandler',
        '        self.tray_icon = None; self.tray_thread = None\n\n        # Release single instance lock\n        self._release_lock()\n\n    # Indicate to GuiLogHandler'
    )
    
    # 6. Add missing preview methods before the existing preview methods
    preview_methods = '''
    def preview_pulse(self, frame_count: int):
        """Preview pulse effect - all zones pulse together"""
        try: 
            base_color_rgb = RGBColor.from_hex(self.effect_color_var.get())
        except ValueError: 
            base_color_rgb = RGBColor(255,0,255)
        is_rainbow = self.effect_rainbow_mode_var.get()

        pulse_cycle = (math.sin(frame_count * 0.2) + 1) / 2
        
        for i in range(NUM_ZONES):
            if is_rainbow:
                hue = (frame_count * 0.02) % 1.0
                rgb_float = colorsys.hsv_to_rgb(hue, 1.0, pulse_cycle)
                self.zone_colors[i] = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
            else:
                self.zone_colors[i] = RGBColor(
                    int(base_color_rgb.r * pulse_cycle),
                    int(base_color_rgb.g * pulse_cycle),
                    int(base_color_rgb.b * pulse_cycle)
                )
        
        self.update_preview_keyboard()

    def preview_zone_chase(self, frame_count: int):
        """Preview zone chase effect - light chases across zones"""
        try: 
            base_color_rgb = RGBColor.from_hex(self.effect_color_var.get())
        except ValueError: 
            base_color_rgb = RGBColor(255,255,0)
        is_rainbow = self.effect_rainbow_mode_var.get()

        active_zone = frame_count % NUM_ZONES
        
        for i in range(NUM_ZONES):
            if i == active_zone:
                if is_rainbow:
                    hue = (frame_count * 0.05) % 1.0
                    rgb_float = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                    self.zone_colors[i] = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
                else:
                    self.zone_colors[i] = base_color_rgb
            else:
                # Fade trailing zones
                distance = min(abs(i - active_zone), NUM_ZONES - abs(i - active_zone))
                fade = max(0, 1.0 - distance * 0.5)
                if is_rainbow:
                    hue = (frame_count * 0.05) % 1.0
                    rgb_float = colorsys.hsv_to_rgb(hue, 1.0, fade)
                    self.zone_colors[i] = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
                else:
                    self.zone_colors[i] = RGBColor(
                        int(base_color_rgb.r * fade),
                        int(base_color_rgb.g * fade),
                        int(base_color_rgb.b * fade)
                    )
        
        self.update_preview_keyboard()

    def preview_starlight(self, frame_count: int):
        """Preview starlight effect - random twinkling"""
        try: 
            base_color_rgb = RGBColor.from_hex(self.effect_color_var.get())
        except ValueError: 
            base_color_rgb = RGBColor(255,255,255)
        is_rainbow = self.effect_rainbow_mode_var.get()

        for i in range(NUM_ZONES):
            # Create pseudo-random twinkling based on frame and zone
            twinkle_seed = (frame_count + i * 17) % 100
            intensity = 0.2 + 0.8 * (math.sin(twinkle_seed * 0.1) + 1) / 2
            
            if is_rainbow:
                hue = (i / NUM_ZONES + frame_count * 0.01) % 1.0
                rgb_float = colorsys.hsv_to_rgb(hue, 1.0, intensity)
                self.zone_colors[i] = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
            else:
                self.zone_colors[i] = RGBColor(
                    int(base_color_rgb.r * intensity),
                    int(base_color_rgb.g * intensity),
                    int(base_color_rgb.b * intensity)
                )
        
        self.update_preview_keyboard()

    def preview_scanner(self, frame_count: int):
        """Preview scanner effect - back and forth sweep"""
        try: 
            base_color_rgb = RGBColor.from_hex(self.effect_color_var.get())
        except ValueError: 
            base_color_rgb = RGBColor(255,0,0)
        is_rainbow = self.effect_rainbow_mode_var.get()

        # Back and forth motion
        cycle_length = NUM_ZONES * 2 - 2
        position_in_cycle = frame_count % cycle_length
        if position_in_cycle < NUM_ZONES:
            scanner_pos = position_in_cycle
        else:
            scanner_pos = cycle_length - position_in_cycle

        for i in range(NUM_ZONES):
            distance = abs(i - scanner_pos)
            intensity = max(0, 1.0 - distance * 0.7)
            
            if is_rainbow:
                hue = (scanner_pos / NUM_ZONES) % 1.0
                rgb_float = colorsys.hsv_to_rgb(hue, 1.0, intensity)
                self.zone_colors[i] = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
            else:
                self.zone_colors[i] = RGBColor(
                    int(base_color_rgb.r * intensity),
                    int(base_color_rgb.g * intensity),
                    int(base_color_rgb.b * intensity)
                )
        
        self.update_preview_keyboard()

    def preview_strobe(self, frame_count: int):
        """Preview strobe effect - rapid on/off"""
        try: 
            base_color_rgb = RGBColor.from_hex(self.effect_color_var.get())
        except ValueError: 
            base_color_rgb = RGBColor(255,255,255)
        is_rainbow = self.effect_rainbow_mode_var.get()

        # Strobe on for 3 frames, off for 2 frames
        strobe_on = (frame_count % 5) < 3
        
        for i in range(NUM_ZONES):
            if strobe_on:
                if is_rainbow:
                    hue = (i / NUM_ZONES) % 1.0
                    rgb_float = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                    self.zone_colors[i] = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
                else:
                    self.zone_colors[i] = base_color_rgb
            else:
                self.zone_colors[i] = RGBColor(0, 0, 0)
        
        self.update_preview_keyboard()

    def preview_ripple(self, frame_count: int):
        """Preview ripple effect - expanding rings"""
        try: 
            base_color_rgb = RGBColor.from_hex(self.effect_color_var.get())
        except ValueError: 
            base_color_rgb = RGBColor(0,255,255)
        is_rainbow = self.effect_rainbow_mode_var.get()

        center = NUM_ZONES // 2
        ripple_radius = (frame_count * 0.5) % (NUM_ZONES + 5)
        
        for i in range(NUM_ZONES):
            distance_from_center = abs(i - center)
            ripple_intensity = max(0, 1.0 - abs(distance_from_center - ripple_radius) * 0.5)
            
            if is_rainbow:
                hue = (ripple_radius * 0.1) % 1.0
                rgb_float = colorsys.hsv_to_rgb(hue, 1.0, ripple_intensity)
                self.zone_colors[i] = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
            else:
                self.zone_colors[i] = RGBColor(
                    int(base_color_rgb.r * ripple_intensity),
                    int(base_color_rgb.g * ripple_intensity),
                    int(base_color_rgb.b * ripple_intensity)
                )
        
        self.update_preview_keyboard()

'''
    
    # Add the preview methods before the existing preview_raindrop method
    content = content.replace(
        '    def preview_raindrop(self, frame_count: int):',
        preview_methods + '    def preview_raindrop(self, frame_count: int):'
    )
    
    # Write the patched content back to file
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Successfully patched {file_path}")
    print("Added:")
    print("  - psutil and fcntl imports")
    print("  - SingleInstanceMixin class")
    print("  - Single instance checking in __init__")
    print("  - _release_lock() call in shutdown")
    print("  - 6 additional preview methods (pulse, zone_chase, starlight, scanner, strobe, ripple)")

if __name__ == "__main__":
    patch_controller_file()
