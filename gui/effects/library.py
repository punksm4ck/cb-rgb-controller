#!/usr/bin/env python3
"""RGB lighting effects implementation with comprehensive error handling"""

import time
import math
import colorsys
import random
import threading
import logging
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field

from ..core.rgb_color import RGBColor
from ..core.constants import NUM_ZONES, LEDS_PER_ZONE, MIN_ANIMATION_FRAME_DELAY, BASE_ANIMATION_DELAY_SPEED_1, TOTAL_LEDS, REACTIVE_DELAY
from ..hardware.controller import HardwareController 
from ..utils.decorators import safe_execute 

@dataclass
class EffectState:
    """Maintains state for effects that need persistence between frames."""
    hue_offset: float = 0.0
    wave_position: float = 0.0 
    direction: int = 1
    position: int = 0 
    frame_count: int = 0
    raindrops: List[Dict[str, Any]] = field(default_factory=list)
    ripple_sources: List[Dict[str, Any]] = field(default_factory=list) 


class EffectLibrary:
    logger = logging.getLogger('EffectLibrary')

    @staticmethod
    def _get_delay(speed: int) -> float:
        """Calculate frame delay based on speed (1-10)."""
        base_delay = 0.2
        return max(MIN_ANIMATION_FRAME_DELAY, base_delay / speed)

    # --- CORE DYNAMIC EFFECTS ---

    @staticmethod
    @safe_execute()
    def breathing(stop_event: threading.Event, hardware: HardwareController, speed: int, color: RGBColor, rainbow_mode: bool = False, **kwargs):
        state = EffectState()
        delay = EffectLibrary._get_delay(speed)
        while not stop_event.is_set():
            brightness = (math.sin(state.frame_count * 0.1 * speed) + 1) / 2
            base_color = RGBColor.from_hsv(state.hue_offset, 1, 1) if rainbow_mode else color
            final_color = base_color.with_brightness(brightness)
            if not hardware.set_all_leds_color(final_color): break
            if rainbow_mode: state.hue_offset = (state.hue_offset + 0.005) % 1.0
            state.frame_count += 1
            if stop_event.wait(delay): break
    
    @staticmethod
    @safe_execute()
    def color_cycle(stop_event: threading.Event, hardware: HardwareController, speed: int, **kwargs):
        state = EffectState()
        delay = EffectLibrary._get_delay(speed)
        while not stop_event.is_set():
            color = RGBColor.from_hsv(state.hue_offset, 1.0, 1.0)
            if not hardware.set_all_leds_color(color): break
            state.hue_offset = (state.hue_offset + 0.001 * speed) % 1.0
            if stop_event.wait(delay): break

    @staticmethod
    @safe_execute()
    def wave(stop_event: threading.Event, hardware: HardwareController, speed: int, color: RGBColor, rainbow_mode: bool = False, **kwargs):
        state = EffectState()
        delay = EffectLibrary._get_delay(speed)
        while not stop_event.is_set():
            colors = [RGBColor(0,0,0)] * NUM_ZONES
            for i in range(NUM_ZONES):
                dist = abs(i - state.position)
                if dist < 2.0:
                    intensity = (1 - (dist / 2.0)) ** 2
                    base_color = RGBColor.from_hsv((state.hue_offset + i*0.1)%1.0,1,1) if rainbow_mode else color
                    colors[i] = base_color.with_brightness(intensity)
            if not hardware.set_zone_colors(colors): break
            if rainbow_mode: state.hue_offset = (state.hue_offset + 0.005) % 1.0
            state.position = (state.position + 0.1 * speed) % (NUM_ZONES + 2)
            if stop_event.wait(delay): break

    @staticmethod
    @safe_execute()
    def zone_chase(stop_event: threading.Event, hardware: HardwareController, speed: int, color: RGBColor, rainbow_mode: bool = False, **kwargs):
        state = EffectState()
        delay = EffectLibrary._get_delay(speed * 2)
        while not stop_event.is_set():
            colors = [RGBColor(0,0,0)] * NUM_ZONES
            active_zone = int(state.position)
            base_color = RGBColor.from_hsv((state.hue_offset + active_zone/NUM_ZONES)%1.0, 1, 1) if rainbow_mode else color
            colors[active_zone] = base_color
            if not hardware.set_zone_colors(colors): break
            state.position = (state.position + 0.1 * speed) % NUM_ZONES
            if rainbow_mode: state.hue_offset = (state.hue_offset + 0.005) % 1.0
            state.frame_count += 1
            if stop_event.wait(delay): break

    @staticmethod
    @safe_execute()
    def starlight(stop_event: threading.Event, hardware: HardwareController, speed: int, color: RGBColor, rainbow_mode: bool = False, **kwargs):
        delay = EffectLibrary._get_delay(speed * 2)
        while not stop_event.is_set():
            colors = [RGBColor(0,0,0)] * NUM_ZONES
            num_stars = random.randint(1, (NUM_ZONES // 2) + 1)
            for _ in range(num_stars):
                zone = random.randint(0, NUM_ZONES-1)
                brightness = random.uniform(0.2, 1.0)
                base_color = RGBColor.from_hsv(random.random(), 1, 1) if rainbow_mode else color
                colors[zone] = base_color.with_brightness(brightness)
            if not hardware.set_zone_colors(colors): break
            if stop_event.wait(delay): break

    # --- ALIASED & SIMULATED EFFECTS ---

    @staticmethod
    @safe_execute()
    def reactive(stop_event: threading.Event, hardware: HardwareController, speed: int, color: RGBColor, rainbow_mode: bool = False, **kwargs):
        """Keys are off by default and light up when 'pressed' (simulated)."""
        state = EffectState()
        delay = EffectLibrary._get_delay(speed * 2)
        while not stop_event.is_set():
            colors = [RGBColor(0,0,0)] * NUM_ZONES
            active_zone = int(state.position) % (NUM_ZONES + 4) # Add a pause
            if active_zone < NUM_ZONES:
                base_color = RGBColor.from_hsv((state.hue_offset + active_zone/NUM_ZONES)%1.0,1,1) if rainbow_mode else color
                colors[active_zone] = base_color
            if not hardware.set_zone_colors(colors): break
            state.position = (state.position + 0.2 * speed)
            if rainbow_mode: state.hue_offset = (state.hue_offset + 0.01) % 1.0
            if stop_event.wait(delay): break

    @staticmethod
    @safe_execute()
    def anti_reactive(stop_event: threading.Event, hardware: HardwareController, speed: int, color: RGBColor, rainbow_mode: bool = False, **kwargs):
        """Keys are on by default and turn off when 'pressed' (simulated)."""
        state = EffectState()
        delay = EffectLibrary._get_delay(speed * 2)
        while not stop_event.is_set():
            if rainbow_mode:
                colors = [RGBColor.from_hsv((state.hue_offset + i/NUM_ZONES)%1.0, 1, 1) for i in range(NUM_ZONES)]
            else:
                colors = [color] * NUM_ZONES
            active_zone = int(state.position) % (NUM_ZONES + 4) # Add a pause
            if active_zone < NUM_ZONES:
                colors[active_zone] = RGBColor(0,0,0)
            if not hardware.set_zone_colors(colors): break
            state.position = (state.position + 0.2 * speed)
            if rainbow_mode: state.hue_offset = (state.hue_offset + 0.01) % 1.0
            if stop_event.wait(delay): break

    # --- Corrected Aliases ---
    
    @staticmethod
    @safe_execute()
    def pulse(stop_event: threading.Event, hardware: HardwareController, **kwargs):
        EffectLibrary.breathing(stop_event, hardware, **kwargs)

    @staticmethod
    @safe_execute()
    def raindrop(stop_event: threading.Event, hardware: HardwareController, **kwargs):
        kwargs['rainbow_mode'] = True # Raindrop is always rainbow
        EffectLibrary.starlight(stop_event, hardware, **kwargs)

    @staticmethod
    @safe_execute()
    def scanner(stop_event: threading.Event, hardware: HardwareController, **kwargs):
        EffectLibrary.zone_chase(stop_event, hardware, **kwargs)
        
    @staticmethod
    @safe_execute()
    def strobe(stop_event: threading.Event, hardware: HardwareController, **kwargs):
        kwargs['speed'] = min(10, kwargs.get('speed', 5) + 3) # Strobe is a faster pulse
        EffectLibrary.breathing(stop_event, hardware, **kwargs)

    @staticmethod
    @safe_execute()
    def ripple(stop_event: threading.Event, hardware: HardwareController, **kwargs):
        kwargs['rainbow_mode'] = True # Ripple is always rainbow
        EffectLibrary.wave(stop_event, hardware, **kwargs)
        
    @staticmethod
    @safe_execute()
    def rainbow_wave(stop_event: threading.Event, hardware: HardwareController, **kwargs):
        kwargs['rainbow_mode'] = True
        EffectLibrary.wave(stop_event, hardware, **kwargs)

    @staticmethod
    @safe_execute()
    def rainbow_breathing(stop_event: threading.Event, hardware: HardwareController, **kwargs):
        kwargs['rainbow_mode'] = True
        EffectLibrary.breathing(stop_event, hardware, **kwargs)
        
    @staticmethod
    @safe_execute()
    def rainbow_zones_cycle(stop_event: threading.Event, hardware: HardwareController, speed: int, **kwargs):
        state = EffectState()
        delay = EffectLibrary._get_delay(speed)
        while not stop_event.is_set():
            colors = [RGBColor.from_hsv((state.hue_offset + i/NUM_ZONES) % 1.0, 1, 1) for i in range(NUM_ZONES)]
            if not hardware.set_zone_colors(colors): break
            state.hue_offset = (state.hue_offset + 0.002 * speed) % 1.0
            if stop_event.wait(delay): break

# Available effects list for EffectManager
# Available effects list for EffectManager
# Available effects list for EffectManager
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
]
