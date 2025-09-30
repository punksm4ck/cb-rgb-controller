#!/usr/bin/env python3
"""Effect Manager for RGB Keyboard Effects - Uses EffectLibrary"""

import logging
import threading
from typing import Callable, Dict, Any, Optional, List

from ..core.rgb_color import RGBColor
from ..core.constants import default_settings 
from ..hardware.controller import HardwareController
from .library import EffectLibrary 

class EffectManager:
    """Manages the execution of RGB keyboard effects from EffectLibrary."""
    
    def __init__(self, hardware: HardwareController):
        self.logger = logging.getLogger('EffectManager')
        self.hardware = hardware
        self.current_effect_name: Optional[str] = None
        self.effect_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event() # Initialized as self.stop_event (no underscore)
        self.current_effect_params: Dict[str, Any] = {}
        self._is_effect_running_flag = False 

        self.effect_map: Dict[str, Callable] = {
            "Static Color": EffectLibrary.static_color,
            "Static Zone Colors": EffectLibrary.static_zone_colors,
            "Static Rainbow": EffectLibrary.static_rainbow,
            "Static Gradient": EffectLibrary.static_gradient,
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
        }
        self.logger.info("EffectManager initialized with %d effects mapped.", len(self.effect_map))

    def get_available_effects(self) -> List[str]:
        animated_effects = [name for name in self.effect_map.keys() if not name.lower().startswith("static")]
        return animated_effects

    def effect_supports_rainbow(self, effect_name: str) -> bool:
        rainbow_capable_by_param = [
            "Breathing", "Wave", "Pulse", "Zone Chase", "Starlight", 
            "Scanner", "Strobe", "Ripple"
        ]
        inherently_rainbow = ["Color Cycle", "Rainbow Wave", "Rainbow Breathing", "Rainbow Zones Cycle"]
        return effect_name in rainbow_capable_by_param or effect_name in inherently_rainbow

    def start_effect(self, effect_name: str, **params: Any) -> bool:
        if effect_name == "None" or effect_name is None:
            self.stop_current_effect()
            if self.hardware: 
                self.hardware.clear_all_leds() 
            return True

        if effect_name not in self.effect_map:
            self.logger.error(f"Effect '{effect_name}' not found in effect map.")
            return False

        self.stop_current_effect()  
        
        self.current_effect_name = effect_name
        self.current_effect_params = params.copy()
        self.stop_event.clear() # Use self.stop_event (without underscore)
        
        effect_func = self.effect_map[effect_name]
        
        static_effects = ["Static Color", "Static Zone Colors", "Static Rainbow", "Static Gradient"]

        if effect_name in static_effects:
            self.logger.info(f"Applying static effect: {effect_name} with params: {params}")
            try:
                effect_func(hardware=self.hardware, **params)
                self.current_effect_name = None 
                self.current_effect_params = {}
                self._is_effect_running_flag = False
            except Exception as e:
                self.logger.error(f"Error applying static effect '{effect_name}': {e}", exc_info=True)
                return False
            return True
        else: 
            self.logger.info(f"Starting animated effect: {effect_name} with params: {params}")
            thread_kwargs = params.copy()
            if 'speed' not in thread_kwargs: thread_kwargs['speed'] = 5 
            if not thread_kwargs.get('rainbow_mode', False) and 'color' not in thread_kwargs:
                default_color_hex = default_settings.get('effect_color', "#FFFFFF")
                thread_kwargs['color'] = RGBColor.from_hex(default_color_hex)

            self.effect_thread = threading.Thread(
                target=effect_func, 
                args=(self.stop_event, self.hardware), # Pass self.stop_event
                kwargs=thread_kwargs,                  
                daemon=True,
                name=f"EffectThread-{effect_name}"
            )
            try:
                self.effect_thread.start()
                self._is_effect_running_flag = True
            except Exception as e:
                 self.logger.error(f"Failed to start thread for effect '{effect_name}': {e}", exc_info=True)
                 self.current_effect_name = None
                 self._is_effect_running_flag = False
                 return False
            return True

    def stop_current_effect(self) -> None:
        if self.effect_thread and self.effect_thread.is_alive():
            self.logger.info(f"Stopping current effect: {self.current_effect_name}")
            self.stop_event.set() # Use self.stop_event (without underscore)
            try:
                self.effect_thread.join(timeout=1.0) 
                if self.effect_thread.is_alive():
                    self.logger.warning(f"Effect thread for '{self.current_effect_name}' did not join cleanly.")
            except Exception as e:
                self.logger.error(f"Error joining effect thread: {e}", exc_info=True)
        
        self.effect_thread = None
        self.current_effect_name = None 
        self.current_effect_params = {}
        self._is_effect_running_flag = False
        if hasattr(self.hardware, 'set_effect_running_status'):
            self.hardware.set_effect_running_status(False)


    def is_effect_running(self) -> bool:
        return self._is_effect_running_flag and bool(self.effect_thread and self.effect_thread.is_alive())

    def update_effect_speed(self, new_speed: int):
        if self.is_effect_running() and self.current_effect_name:
            validated_speed = max(1, min(10, new_speed))
            self.logger.info(f"Updating speed for effect '{self.current_effect_name}' to {validated_speed}.")
            updated_params = self.current_effect_params.copy()
            updated_params["speed"] = validated_speed
            self.start_effect(self.current_effect_name, **updated_params)
        else:
            self.logger.debug("No effect running or name unknown, cannot update speed.")

    def update_effect_color(self, new_color: RGBColor):
        if self.is_effect_running() and self.current_effect_name and \
           not self.current_effect_params.get("rainbow_mode", False):
            
            self.logger.info(f"Updating color for effect '{self.current_effect_name}' to {new_color.to_hex()}.")
            updated_params = self.current_effect_params.copy()
            updated_params["color"] = new_color
            self.start_effect(self.current_effect_name, **updated_params)
        else:
            self.logger.debug("Cannot update color: No effect running, is in rainbow mode, or effect doesn't use single color.")

    def toggle_effect_rainbow_mode(self, rainbow_on: bool):
        if self.is_effect_running() and self.current_effect_name and \
           self.effect_supports_rainbow(self.current_effect_name):
            
            self.logger.info(f"Toggling rainbow mode to {rainbow_on} for effect '{self.current_effect_name}'.")
            updated_params = self.current_effect_params.copy()
            updated_params["rainbow_mode"] = rainbow_on
            
            if not rainbow_on and "color" not in updated_params:
                default_color_hex = default_settings.get('effect_color', "#FFFFFF")
                fallback_color_hex = self.current_effect_params.get("color_fallback_hex", default_color_hex)
                updated_params["color"] = RGBColor.from_hex(fallback_color_hex)

            self.start_effect(self.current_effect_name, **updated_params)
        else:
            self.logger.debug("Cannot toggle rainbow: No effect running or effect does not support rainbow mode.")

