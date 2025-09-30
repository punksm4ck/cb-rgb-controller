#!/usr/bin/env python3
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
    
    def __init__(self, logger, hardware_controller, settings_manager):
        self.logger = logger.getChild('EffectManager')
        self.hardware = hardware_controller
        self.settings = settings_manager
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
            return list(self.effect_map.keys())
        except:
            # Fallback list
            return ["Breathing", "Wave", "Pulse", "Reactive", "Anti-Reactive"]

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
        if self.is_effect_running() and self.current_effect_name and \
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
        if self.is_effect_running() and self.current_effect_name and \
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
