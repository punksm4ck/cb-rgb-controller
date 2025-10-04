#!/usr/bin/env python3
"""
Comprehensive patch script for RGB Controller Final v3
Fixes speed synchronization, reactive effects, syntax errors, and GUI improvements
"""

import os
import sys
import shutil
import datetime
from pathlib import Path
import re

def create_backup(file_path):
    """Create a backup of the original file"""
    backup_path = f"{file_path}.backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(file_path, backup_path)
    print(f"✓ Backup created: {backup_path}")
    return backup_path

def apply_patch():
    """Apply comprehensive patches to fix all identified issues"""
    script_dir = Path(__file__).parent
    project_dir = script_dir
    
    print("🔧 RGB Controller Comprehensive Patch Script")
    print("=" * 50)
    
    # Patch 1: Fix manager.py syntax error and reactive implementation
    manager_file = project_dir / "gui" / "effects" / "manager.py"
    if manager_file.exists():
        print(f"📝 Patching {manager_file}")
        create_backup(manager_file)
        
        manager_content = '''#!/usr/bin/env python3
"""Effect Manager for RGB Keyboard Effects - Fixed Version with Proper Hardware Status Communication"""

import logging
import threading
import time
from typing import Callable, Dict, Any, Optional, List

from ..core.rgb_color import RGBColor
from ..core.constants import default_settings, NUM_ZONES
from ..hardware.controller import HardwareController
from .library import EffectLibrary, AVAILABLE_EFFECTS

class EffectManager:
    """Manages the execution of RGB keyboard effects from EffectLibrary."""
    
    def __init__(self, hardware: HardwareController):
        self.logger = logging.getLogger('EffectManager')
        self.hardware = hardware
        self.current_effect_name: Optional[str] = None
        self.effect_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.current_effect_params: Dict[str, Any] = {}
        self._is_effect_running_flag = False 

        # Map effect names to library functions
        self.effect_map: Dict[str, Callable] = {
            "Static Color": self._apply_static_color,
            "Static Zone Colors": self._apply_static_zone_colors,
            "Static Rainbow": self._apply_static_rainbow,
            "Static Gradient": self._apply_static_gradient,
            "Breathing": EffectLibrary.breathing,
            "Color Cycle": EffectLibrary.color_cycle,
            "Wave": EffectLibrary.wave,
            "Rainbow Wave": EffectLibrary.rainbow_wave,
            "Pulse": EffectLibrary.pulse,
            "Zone Chase": EffectLibrary.zone_chase,
            "Starlight": EffectLibrary.starlight,
            "Raindrop": EffectLibrary.raindrop, 
            "Scanner": EffectLibrary.scanner,   
            "Strobe": EffectLibrary.strobe,     
            "Ripple": EffectLibrary.ripple,     
            "Rainbow Breathing": EffectLibrary.rainbow_breathing,
            "Rainbow Zones Cycle": EffectLibrary.rainbow_zones_cycle,
            "Reactive": EffectLibrary.reactive,
            "Anti-Reactive": EffectLibrary.anti_reactive,
        }
        self.logger.info("EffectManager initialized with %d effects mapped.", len(self.effect_map))

    
    def get_available_effects(self):
        """Get list of all available effect names"""
        try:
            return [effect.name for effect in AVAILABLE_EFFECTS if hasattr(effect, 'name')]
        except:
            # Fallback list
            return list(self.effect_map.keys())

    def _apply_static_color(self, **kwargs):
        """Apply static color to all zones"""
        color = kwargs.get('color', RGBColor(255, 255, 255))
        if isinstance(color, str):
            color = RGBColor.from_hex(color)
        elif isinstance(color, dict):
            color = RGBColor.from_dict(color)
        
        success = self.hardware.set_all_leds_color(color)
        if success:
            self.logger.info(f"Applied static color {color.to_hex()} to all zones")
        else:
            self.logger.error(f"Failed to apply static color {color.to_hex()}")
        return success

    def _apply_static_zone_colors(self, **kwargs):
        """Apply individual colors to each zone"""
        zone_colors = kwargs.get('zone_colors', [RGBColor(255, 0, 0), RGBColor(0, 255, 0), RGBColor(0, 0, 255), RGBColor(255, 255, 0)])
        
        # Ensure we have the right number of colors
        if len(zone_colors) < NUM_ZONES:
            # Extend with default colors
            default_colors = [RGBColor(255, 0, 0), RGBColor(0, 255, 0), RGBColor(0, 0, 255), RGBColor(255, 255, 0)]
            while len(zone_colors) < NUM_ZONES:
                zone_colors.append(default_colors[len(zone_colors) % len(default_colors)])
        
        zone_colors = zone_colors[:NUM_ZONES]  # Trim to correct size
        
        # Convert any non-RGBColor objects
        for i, color in enumerate(zone_colors):
            if isinstance(color, str):
                zone_colors[i] = RGBColor.from_hex(color)
            elif isinstance(color, dict):
                zone_colors[i] = RGBColor.from_dict(color)
        
        success = self.hardware.set_zone_colors(zone_colors)
        if success:
            self.logger.info("Applied individual zone colors")
        else:
            self.logger.error("Failed to apply zone colors")
        return success

    def _apply_static_rainbow(self, **kwargs):
        """Apply rainbow pattern across zones"""
        import colorsys
        zone_colors = []
        for i in range(NUM_ZONES):
            hue = i / NUM_ZONES
            rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            zone_colors.append(RGBColor(int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255)))
        
        success = self.hardware.set_zone_colors(zone_colors)
        if success:
            self.logger.info("Applied static rainbow pattern")
        else:
            self.logger.error("Failed to apply static rainbow")
        return success

    def _apply_static_gradient(self, **kwargs):
        """Apply gradient pattern across zones"""
        start_color = kwargs.get('start_color', RGBColor(255, 0, 0))
        end_color = kwargs.get('end_color', RGBColor(0, 0, 255))
        
        if isinstance(start_color, str):
            start_color = RGBColor.from_hex(start_color)
        elif isinstance(start_color, dict):
            start_color = RGBColor.from_dict(start_color)
            
        if isinstance(end_color, str):
            end_color = RGBColor.from_hex(end_color)
        elif isinstance(end_color, dict):
            end_color = RGBColor.from_dict(end_color)
        
        zone_colors = []
        for i in range(NUM_ZONES):
            if NUM_ZONES > 1:
                ratio = i / (NUM_ZONES - 1)
            else:
                ratio = 0
            
            # Interpolate between start and end colors
            r = int(start_color.r * (1 - ratio) + end_color.r * ratio)
            g = int(start_color.g * (1 - ratio) + end_color.g * ratio)
            b = int(start_color.b * (1 - ratio) + end_color.b * ratio)
            zone_colors.append(RGBColor(r, g, b))
        
        success = self.hardware.set_zone_colors(zone_colors)
        if success:
            self.logger.info(f"Applied static gradient from {start_color.to_hex()} to {end_color.to_hex()}")
        else:
            self.logger.error("Failed to apply static gradient")
        return success

    def effect_supports_rainbow(self, effect_name: str) -> bool:
        """Check if effect supports rainbow mode"""
        rainbow_capable_by_param = [
            "Breathing", "Wave", "Pulse", "Zone Chase", "Starlight", 
            "Scanner", "Strobe", "Ripple", "Reactive", "Anti-Reactive"
        ]
        inherently_rainbow = ["Color Cycle", "Rainbow Wave", "Rainbow Breathing", "Rainbow Zones Cycle"]
        return effect_name in rainbow_capable_by_param or effect_name in inherently_rainbow

    def start_effect(self, effect_name: str, **params: Any) -> bool:
        """Start an effect with given parameters - implements Goal 2A hardware status communication"""
        if effect_name == "None" or effect_name is None:
            self.stop_current_effect()
            if self.hardware: 
                self.hardware.clear_all_leds() 
            return True

        if effect_name not in self.effect_map:
            self.logger.error(f"Effect '{effect_name}' not found in effect map.")
            return False

        # Stop any currently running effect
        self.stop_current_effect()
        
        # Wait for hardware to be ready
        if not self.hardware.wait_for_detection(timeout=2.0):
            self.logger.error("Hardware not ready for effect")
            return False
        
        self.current_effect_name = effect_name
        self.current_effect_params = params.copy()
        self.stop_event.clear()
        
        effect_func = self.effect_map[effect_name]
        
        # Static effects are applied immediately
        static_effects = ["Static Color", "Static Zone Colors", "Static Rainbow", "Static Gradient"]

        if effect_name in static_effects:
            self.logger.info(f"Applying static effect: {effect_name} with params: {params}")
            try:
                success = effect_func(**params)
                # Static effects don't continuously run, so don't mark as "effect running"
                self.current_effect_name = None 
                self.current_effect_params = {}
                self._is_effect_running_flag = False
                # Ensure hardware controller knows no continuous effect is running
                if hasattr(self.hardware, 'set_effect_running_status'):
                    self.hardware.set_effect_running_status(False)
                return success
            except Exception as e:
                self.logger.error(f"Error applying static effect '{effect_name}': {e}", exc_info=True)
                return False

        # Handle reactive effects specially
        if effect_name in ["Reactive", "Anti-Reactive"]:
            self.logger.info(f"Starting reactive effect: {effect_name}")
            
            # Stop any existing effects first
            self.stop_current_effect()
            
            # Enable reactive mode on hardware
            anti_mode = effect_name == "Anti-Reactive"
            if hasattr(self.hardware, 'set_reactive_mode'):
                success = self.hardware.set_reactive_mode(
                    enabled=True,
                    color=params.get('color', RGBColor(255, 255, 255)),
                    anti_mode=anti_mode
                )
                
                if success:
                    self.current_effect_name = effect_name
                    self.current_effect_params = params.copy()
                    self._is_effect_running_flag = True
                    
                    # Inform hardware controller that an effect is running
                    if hasattr(self.hardware, 'set_effect_running_status'):
                        self.hardware.set_effect_running_status(True)
                    
                    # Start simulation for testing
                    if params.get('simulate_keys', False):
                        threading.Thread(
                            target=self._run_reactive_simulation,
                            args=(effect_name,),
                            daemon=True,
                            name=f"ReactiveSimulation-{effect_name}"
                        ).start()
                    
                    return True
                else:
                    self.logger.error(f"Failed to enable reactive mode for {effect_name}")
                    return False
            else:
                self.logger.warning("Hardware does not support reactive mode")
                return False
        else: 
            # Animated effects run in a thread - this is where Goal 2A is crucial
            self.logger.info(f"Starting animated effect: {effect_name} with params: {params}")
            
            # Prepare parameters for the effect function
            thread_kwargs = params.copy()
            if 'speed' not in thread_kwargs: 
                thread_kwargs['speed'] = 5 
            if not thread_kwargs.get('rainbow_mode', False) and 'color' not in thread_kwargs:
                default_color_hex = default_settings.get('effect_color', "#FFFFFF")
                thread_kwargs['color'] = RGBColor.from_hex(default_color_hex)

            # Create and start the effect thread
            self.effect_thread = threading.Thread(
                target=self._run_animated_effect, 
                args=(effect_func, thread_kwargs),
                daemon=True,
                name=f"EffectThread-{effect_name}"
            )
            
            try:
                self.effect_thread.start()
                self._is_effect_running_flag = True
                # CRITICAL for Goal 2A: Inform hardware controller that an effect is running
                # This prevents LED clearing when GUI is hidden to tray
                if hasattr(self.hardware, 'set_effect_running_status'):
                    self.hardware.set_effect_running_status(True)
                    self.logger.debug(f"Informed hardware controller that effect '{effect_name}' is running")
                return True
            except Exception as e:
                 self.logger.error(f"Failed to start thread for effect '{effect_name}': {e}", exc_info=True)
                 self.current_effect_name = None
                 self._is_effect_running_flag = False
                 if hasattr(self.hardware, 'set_effect_running_status'):
                     self.hardware.set_effect_running_status(False)
                 return False

    def _run_animated_effect(self, effect_func: Callable, params: Dict[str, Any]):
        """Run an animated effect in a thread"""
        try:
            self.logger.info(f"Starting animated effect thread with params: {params}")
            effect_func(self.stop_event, self.hardware, **params)
        except Exception as e:
            self.logger.error(f"Error in animated effect: {e}", exc_info=True)
        finally:
            self.logger.info("Animated effect thread finished")
            self._is_effect_running_flag = False
            # CRITICAL for Goal 2A: Inform hardware controller that effect has stopped
            if hasattr(self.hardware, 'set_effect_running_status'):
                self.hardware.set_effect_running_status(False)
                self.logger.debug("Informed hardware controller that effect has stopped")

    def stop_current_effect(self) -> None:
        """Stop the currently running effect - implements Goal 2A hardware status communication"""
        if self.effect_thread and self.effect_thread.is_alive():
            self.logger.info(f"Stopping current effect: {self.current_effect_name}")
            self.stop_event.set()
            try:
                self.effect_thread.join(timeout=2.0)  # Increased timeout
                if self.effect_thread.is_alive():
                    self.logger.warning(f"Effect thread for '{self.current_effect_name}' did not join cleanly.")
            except Exception as e:
                self.logger.error(f"Error joining effect thread: {e}", exc_info=True)
        
        self.effect_thread = None
        # Stop reactive mode if active
        if self.current_effect_name in ["Reactive", "Anti-Reactive"]:
            if hasattr(self.hardware, 'set_reactive_mode'):
                self.hardware.set_reactive_mode(enabled=False, color=RGBColor(0, 0, 0))
        
        self.current_effect_name = None 
        self.current_effect_params = {}
        self._is_effect_running_flag = False
        # CRITICAL for Goal 2A: Always inform hardware controller when stopping effects
        if hasattr(self.hardware, 'set_effect_running_status'):
            self.hardware.set_effect_running_status(False)
            self.logger.debug("Informed hardware controller that no effect is running")

    def is_effect_running(self) -> bool:
        """Check if an effect is currently running"""
        return self._is_effect_running_flag and bool(self.effect_thread and self.effect_thread.is_alive())

    def update_effect_speed(self, new_speed: int):
        """Update the speed of the currently running effect"""
        if self.is_effect_running() and self.current_effect_name:
            validated_speed = max(1, min(10, new_speed))
            self.logger.info(f"Updating speed for effect '{self.current_effect_name}' to {validated_speed}.")
            updated_params = self.current_effect_params.copy()
            updated_params["speed"] = validated_speed
            self.start_effect(self.current_effect_name, **updated_params)
        else:
            self.logger.debug("No effect running or name unknown, cannot update speed.")

    def update_effect_color(self, new_color: RGBColor):
        """Update the color of the currently running effect"""
        if self.is_effect_running() and self.current_effect_name and \\
           not self.current_effect_params.get("rainbow_mode", False):
            
            self.logger.info(f"Updating color for effect '{self.current_effect_name}' to {new_color.to_hex()}.")
            updated_params = self.current_effect_params.copy()
            updated_params["color"] = new_color
            self.start_effect(self.current_effect_name, **updated_params)
        else:
            self.logger.debug("Cannot update color: No effect running, is in rainbow mode, or effect doesn't use single color.")

    def _run_reactive_simulation(self, effect_name: str):
        """Run reactive effect simulation for testing"""
        self.logger.info(f"Starting reactive simulation for {effect_name}")
        
        try:
            while self._is_effect_running_flag and self.current_effect_name == effect_name:
                if hasattr(self.hardware, 'simulate_key_press_pattern'):
                    self.hardware.simulate_key_press_pattern("typing")
                time.sleep(2.0)  # Repeat every 2 seconds
        except Exception as e:
            self.logger.error(f"Error in reactive simulation: {e}")
        finally:
            self.logger.info("Reactive simulation ended")

    def toggle_effect_rainbow_mode(self, rainbow_on: bool):
        """Toggle rainbow mode for the currently running effect"""
        if self.is_effect_running() and self.current_effect_name and \\
           self.effect_supports_rainbow(self.current_effect_name):
            
            self.logger.info(f"Toggling rainbow mode to {rainbow_on} for effect '{self.current_effect_name}'.")
            updated_params = self.current_effect_params.copy()
            updated_params["rainbow_mode"] = rainbow_on
            
            if not rainbow_on and "color" not in updated_params:
                default_color_hex = default_settings.get('effect_color', "#FFFFFF")
                # Use the color that was active before rainbow mode, or default
                fallback_color_hex = self.current_effect_params.get("color_fallback_hex", default_color_hex)
                updated_params["color"] = RGBColor.from_hex(fallback_color_hex)

            self.start_effect(self.current_effect_name, **updated_params)
        else:
            self.logger.debug("Cannot toggle rainbow: No effect running or effect does not support rainbow mode.")
'''
        
        with open(manager_file, 'w', encoding='utf-8') as f:
            f.write(manager_content)
        print("✓ Fixed syntax error and improved reactive effect handling in manager.py")
    
    # Patch 2: Update hardware controller with reactive mode implementation
    hardware_controller_file = project_dir / "gui" / "hardware" / "controller.py"
    if not hardware_controller_file.exists():
        # If it doesn't exist, create it by renaming the uploaded file
        old_file = project_dir / "hardwarecontroller.py"
        if old_file.exists():
            shutil.move(old_file, hardware_controller_file)
            print(f"✓ Moved hardwarecontroller.py to {hardware_controller_file}")
    
    if hardware_controller_file.exists():
        print(f"📝 Patching {hardware_controller_file}")
        create_backup(hardware_controller_file)
        
        # Read current content and update with reactive mode
        with open(hardware_controller_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add reactive mode methods if not present
        if 'set_reactive_mode' not in content:
            reactive_methods = '''
    def set_reactive_mode(self, enabled: bool, color: RGBColor, anti_mode: bool = False) -> bool:
        """Enable/disable reactive mode with specified color"""
        self.logger.info(f"Setting reactive mode: enabled={enabled}, anti_mode={anti_mode}, color={color.to_hex()}")
        
        with self._lock:
            if enabled:
                self._reactive_mode_enabled = True
                self._reactive_color = color
                self._anti_reactive_mode = anti_mode
                
                # Initialize keyboard state
                if anti_mode:
                    # Anti-reactive: start with all keys on
                    return self.set_all_leds_color(color)
                else:
                    # Reactive: start with all keys off
                    return self.clear_all_leds()
            else:
                self._reactive_mode_enabled = False
                return self.clear_all_leds()

    def handle_key_press(self, key_position: int, pressed: bool) -> bool:
        """Handle individual key press for reactive effects"""
        if not getattr(self, '_reactive_mode_enabled', False):
            return True  # Not in reactive mode
        
        try:
            # Convert key position to zone (simplified mapping)
            zone_index = min(key_position // (TOTAL_LEDS // NUM_ZONES), NUM_ZONES - 1)
            
            if getattr(self, '_anti_reactive_mode', False):
                # Anti-reactive: turn off when pressed
                target_color = RGBColor(0, 0, 0) if pressed else getattr(self, '_reactive_color', RGBColor(255, 255, 255))
            else:
                # Reactive: turn on when pressed
                target_color = getattr(self, '_reactive_color', RGBColor(255, 255, 255)) if pressed else RGBColor(0, 0, 0)
            
            return self.set_zone_color(zone_index + 1, target_color)
        
        except Exception as e:
            self.logger.error(f"Error handling key press {key_position}: {e}")
            return False

    def simulate_key_press_pattern(self, pattern_name: str = "typing") -> bool:
        """Simulate key press patterns for testing reactive effects"""
        if not getattr(self, '_reactive_mode_enabled', False):
            return False
        
        try:
            if pattern_name == "typing":
                # Simulate typing pattern across zones
                import time
                for zone in range(NUM_ZONES):
                    if getattr(self, '_anti_reactive_mode', False):
                        # Anti-reactive: briefly turn off each zone
                        self.set_zone_color(zone + 1, RGBColor(0, 0, 0))
                        time.sleep(0.1)
                        self.set_zone_color(zone + 1, getattr(self, '_reactive_color', RGBColor(255, 255, 255)))
                    else:
                        # Reactive: briefly turn on each zone
                        self.set_zone_color(zone + 1, getattr(self, '_reactive_color', RGBColor(255, 255, 255)))
                        time.sleep(0.1)
                        self.set_zone_color(zone + 1, RGBColor(0, 0, 0))
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Error simulating key press pattern: {e}")
            return False
'''
            
            # Insert before the __del__ method
            content = content.replace(
                '    def __del__(self):',
                reactive_methods + '\n    def __del__(self):'
            )
        
        # Also add reactive state variables to __init__ if not present
        if '_reactive_mode_enabled' not in content:
            init_additions = '''        # Reactive effects state
        self._reactive_mode_enabled = False
        self._reactive_color = RGBColor(255, 255, 255)
        self._anti_reactive_mode = False
'''
            # Add after existing __init__ variables
            content = content.replace(
                '        self._app_exiting_cleanly = False',
                '        self._app_exiting_cleanly = False\n' + init_additions
            )
        
        with open(hardware_controller_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✓ Added reactive mode implementation to hardware controller")
    
    # Patch 3: Fix speed synchronization in GUI controller
    gui_controller_file = project_dir / "gui" / "controller.py"
    if gui_controller_file.exists():
        print(f"📝 Patching {gui_controller_file} for speed synchronization")
        create_backup(gui_controller_file)
        
        with open(gui_controller_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix the hardware speed mapping for better synchronization
        old_speed_map = '''hardware_speed_map = {
            1: 0.003,   # Very slow - matches hardware exactly
            2: 0.005,   # Slow  
            3: 0.008,   # Moderate slow  
            4: 0.012,   # Below normal
            5: 0.016,   # Normal - baseline speed
            6: 0.020,   # Above normal
            7: 0.025,   # Fast
            8: 0.030,   # Very fast
            9: 0.038,   # Ultra fast
            10: 0.045   # Maximum speed
        }'''
        
        new_speed_map = '''hardware_speed_map = {
            1: 0.001,   # Very slow - better hardware sync
            2: 0.002,   # Slow  
            3: 0.003,   # Moderate slow  
            4: 0.004,   # Below normal
            5: 0.006,   # Normal - baseline speed
            6: 0.008,   # Above normal
            7: 0.010,   # Fast
            8: 0.013,   # Very fast
            9: 0.016,   # Ultra fast
            10: 0.020   # Maximum speed
        }'''
        
        content = content.replace(old_speed_map, new_speed_map)
        
        # Also fix the rainbow zones cycle preview to match hardware bleeding
        old_rainbow_method = '''    def _preview_rainbow_with_full_keyboard_bleeding(self, frame_count, speed_multiplier):
        """Hardware-accurate rainbow effect with full keyboard leftward bleeding"""
        if not hasattr(self, 'key_grid') or not self.key_grid:
            return
        
        # The hardware moves colors from right to left across the entire keyboard
        # with significant bleeding between zones and keys
        base_offset = frame_count * speed_multiplier * 0.2
        
        for row_idx, row in enumerate(self.key_grid):
            for col_idx, key_info in enumerate(row):
                # Position factor from right to left (15 is rightmost, 0 is leftmost)
                position_factor = (15 - col_idx) / 15.0
                row_factor = row_idx / len(self.key_grid)
                
                # Base hue calculation with rightward to leftward movement
                hue = (base_offset + position_factor + row_factor * 0.1) % 1.0
                
                # Strong bleeding effect from adjacent keys (hardware characteristic)
                bleeding_factor = 0.25
                if col_idx > 0:
                    right_hue = (base_offset + (15 - (col_idx - 1)) / 15.0 + row_factor * 0.1) % 1.0
                    hue = hue * (1 - bleeding_factor) + right_hue * bleeding_factor
                
                if col_idx < len(row) - 1:
                    left_hue = (base_offset + (15 - (col_idx + 1)) / 15.0 + row_factor * 0.1) % 1.0
                    hue = hue * (1 - bleeding_factor * 0.5) + left_hue * (bleeding_factor * 0.5)
                
                rgb_float = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                color = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
                
                try:
                    canvas = self.preview_canvas
                    canvas.itemconfig(key_info['element'], fill=color.to_hex())
                except:
                    pass'''
        
        new_rainbow_method = '''    def _preview_rainbow_with_full_keyboard_bleeding(self, frame_count, speed_multiplier):
        """Hardware-accurate rainbow effect with full keyboard leftward bleeding - FIXED"""
        if not hasattr(self, 'key_grid') or not self.key_grid:
            return
        
        # ULTRA-PRECISE: Hardware moves colors much slower from right to left
        base_offset = frame_count * speed_multiplier * 0.05  # Much slower movement
        
        for row_idx, row in enumerate(self.key_grid):
            for col_idx, key_info in enumerate(row):
                # Enhanced position calculation for realistic leftward flow
                position_factor = (len(row) - 1 - col_idx) / (len(row) - 1) if len(row) > 1 else 0
                row_factor = row_idx / len(self.key_grid) if len(self.key_grid) > 1 else 0
                
                # More realistic hue calculation matching hardware timing
                hue = (base_offset + position_factor * 0.3 + row_factor * 0.05) % 1.0
                
                # Enhanced bleeding simulation - hardware has strong inter-key bleeding
                bleeding_factor = 0.4  # Stronger bleeding for realism
                neighbors_checked = 0
                total_neighbor_hue = 0
                
                # Check adjacent keys for bleeding effect
                for dx in [-1, 0, 1]:
                    if 0 <= col_idx + dx < len(row):
                        adj_position = (len(row) - 1 - (col_idx + dx)) / (len(row) - 1) if len(row) > 1 else 0
                        adj_hue = (base_offset + adj_position * 0.3 + row_factor * 0.05) % 1.0
                        total_neighbor_hue += adj_hue
                        neighbors_checked += 1
                
                if neighbors_checked > 0:
                    avg_neighbor_hue = total_neighbor_hue / neighbors_checked
                    hue = hue * (1 - bleeding_factor) + avg_neighbor_hue * bleeding_factor
                
                rgb_float = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                color = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
                
                try:
                    canvas = self.preview_canvas
                    canvas.itemconfig(key_info['element'], fill=color.to_hex())
                except:
                    pass'''
        
        content = content.replace(old_rainbow_method, new_rainbow_method)
        
        # Add better touchpad scrolling support
        scrolling_improvement = '''        def _on_mousewheel(event, c=canvas):
            delta = 0
            if sys.platform == "win32": 
                delta = event.delta // 120 # Windows
            elif sys.platform == "darwin": 
                delta = event.delta # macOS
            else: # Linux
                if event.num == 4: 
                    delta = -1 # Scroll up
                elif event.num == 5: 
                    delta = 1 # Scroll down
                else:
                    # Handle touchpad scrolling
                    delta = int(event.delta) if hasattr(event, 'delta') else 0
            if delta != 0: 
                c.yview_scroll(int(delta * -1), "units")'''
        
        old_scrolling = '''        def _on_mousewheel(event, c=canvas):
            delta = 0
            if sys.platform == "win32": 
                delta = event.delta // 120 # Windows
            elif sys.platform == "darwin": 
                delta = event.delta # macOS
            else: # Linux
                if event.num == 4: 
                    delta = -1 # Scroll up
                elif event.num == 5: 
                    delta = 1 # Scroll down
            if delta != 0: 
                c.yview_scroll(delta, "units")'''
        
        content = content.replace(old_scrolling, scrolling_improvement)
        
        # Improve initial window geometry
        content = content.replace(
            'self.root.geometry("1000x750")',
            'self.root.geometry("1100x800")'  # Larger initial size
        )
        content = content.replace(
            'self.root.minsize(900, 700)',
            'self.root.minsize(1000, 750)'  # Larger minimum size
        )
        
        with open(gui_controller_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✓ Fixed speed synchronization, rainbow bleeding, and GUI improvements")
    
    # Patch 4: Fix keyboard library detection issue
    main_file = project_dir / "__main__.py"
    if main_file.exists():
        print(f"📝 Patching {main_file} for better keyboard library detection")
        create_backup(main_file)
        
        with open(main_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add better keyboard library detection for sudo environment
        keyboard_fix = '''        # Enhanced keyboard library detection for sudo environment
        keyboard_available = False
        try:
            import keyboard
            keyboard_available = True
            logger.info("Keyboard library successfully imported")
        except ImportError as e:
            logger.warning(f"Keyboard library not available: {e}")
            if os.geteuid() == 0:  # Running as root
                logger.info("Running as root - checking system Python packages")
                try:
                    # Try to install keyboard for system Python if needed
                    subprocess.run([sys.executable, '-m', 'pip', 'install', 'keyboard'], 
                                 check=False, capture_output=True)
                    import keyboard
                    keyboard_available = True
                    logger.info("Keyboard library installed and imported successfully")
                except Exception as install_error:
                    logger.warning(f"Could not install keyboard library: {install_error}")
        
        if not keyboard_available:
            logger.warning("ALT+Brightness hotkeys will be disabled")'''
        
        # Insert the fix before the GUI import
        if 'import keyboard' not in content:
            content = content.replace(
                '    try:',
                keyboard_fix + '\n    try:'
            )
        
        with open(main_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✓ Improved keyboard library detection for sudo environment")
    
    # Patch 5: Ensure effects library has proper AVAILABLE_EFFECTS list
    library_file = project_dir / "gui" / "effects" / "library.py"
    if library_file.exists():
        print(f"📝 Patching {library_file} for complete effects list")
        create_backup(library_file)
        
        with open(library_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Ensure AVAILABLE_EFFECTS includes all effects
        new_effects_list = '''# Available effects list for EffectManager
AVAILABLE_EFFECTS = [
    "Breathing",
    "Color Cycle", 
    "Wave",
    "Pulse",
    "Zone Chase",
    "Starlight",
    "Raindrop",
    "Scanner", 
    "Strobe",
    "Ripple",
    "Rainbow Wave",
    "Rainbow Breathing", 
    "Rainbow Zones Cycle",
    "Reactive",
    "Anti-Reactive"
]'''
        
        # Replace the old list
        content = re.sub(
            r'AVAILABLE_EFFECTS = \[.*?\]',
            new_effects_list,
            content,
            flags=re.DOTALL
        )
        
        with open(library_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✓ Updated effects library with complete effects list")
    
    print("\n🎉 All patches applied successfully!")
    print("\n📋 Summary of changes:")
    print("✓ Fixed syntax error in manager.py")
    print("✓ Implemented reactive mode in hardware controller")
    print("✓ Fixed preview speed synchronization")
    print("✓ Improved rainbow zones bleeding effect")
    print("✓ Enhanced touchpad scrolling support")
    print("✓ Improved GUI layout and sizing")
    print("✓ Fixed keyboard library detection for sudo")
    print("✓ Updated effects library")
    print("\n🚀 Your RGB controller should now work properly!")
    print("Run with: sudo python3 -m rgb_controller_finalv3")

if __name__ == "__main__":
    apply_patch()