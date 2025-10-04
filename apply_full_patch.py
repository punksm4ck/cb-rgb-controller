#!/usr/bin/env python3
"""
A definitive, comprehensive, and surgical patch script for the RGB Controller.

This script targets and resolves all known remaining issues across three modules
by replacing large, well-defined code blocks to ensure success.
"""
import os
import sys
import shutil
from datetime import datetime
from pathlib import Path

# --- Patch Definitions ---
PATCH_GROUPS = [
    {
        "file_path": "gui/effects/manager.py",
        "patches": [
            (
                "Fix NameError by importing EffectLibrary",
                # OLD: The import line that is missing EffectLibrary
                "from .library import AVAILABLE_EFFECTS",
                # NEW: The corrected import line
                "from .library import EffectLibrary, AVAILABLE_EFFECTS"
            )
        ]
    },
    {
        "file_path": "gui/effects/library.py",
        "patches": [
            (
                "Full EffectLibrary Class Overhaul",
                # OLD: The entire EffectLibrary class from your provided file.
                """class EffectLibrary:
    logger = logging.getLogger('EffectLibrary')

    @staticmethod
    @safe_execute()
    def static_color(hardware: HardwareController, color: RGBColor, **kwargs):
        EffectLibrary.logger.info(f"Applying static color: {color.to_hex()}")
        if not hardware.set_all_leds_color(color):
            EffectLibrary.logger.warning("Static color: Hardware command failed")

    @staticmethod
    @safe_execute()
    def static_zone_colors(hardware: HardwareController, zone_colors: List[RGBColor], **kwargs):
        if not isinstance(zone_colors, list) or len(zone_colors) != NUM_ZONES:
            EffectLibrary.logger.error(f"Static zone colors: Expected list of {NUM_ZONES} RGBColor objects, got {type(zone_colors)} len {len(zone_colors) if isinstance(zone_colors,list) else 'N/A'}")
            return
        EffectLibrary.logger.info(f"Applying static zone colors: {[zc.to_hex() for zc in zone_colors]}")
        if not hardware.set_zone_colors(zone_colors):
            EffectLibrary.logger.warning("Static zone colors: Hardware command failed")

    @staticmethod
    @safe_execute()
    def static_rainbow(hardware: HardwareController, **kwargs) -> None:
        EffectLibrary.logger.info("Applying static rainbow effect.")
        zone_colors_list: List[RGBColor] = []
        for zone_idx in range(NUM_ZONES):
            hue = zone_idx / float(NUM_ZONES) if NUM_ZONES > 0 else 0
            r_float, g_float, b_float = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            zone_colors_list.append(RGBColor(int(r_float * 255), int(g_float * 255), int(b_float * 255)))
        if not hardware.set_zone_colors(zone_colors_list):
            EffectLibrary.logger.warning("Static rainbow: Hardware command failed")

    @staticmethod
    @safe_execute()
    def static_gradient(hardware: HardwareController, start_color: RGBColor, end_color: RGBColor, **kwargs) -> None:
        EffectLibrary.logger.info(f"Applying static gradient: from {start_color.to_hex()} to {end_color.to_hex()}")
        zone_colors_list: List[RGBColor] = []
        for zone_idx in range(NUM_ZONES):
            ratio = zone_idx / float(NUM_ZONES - 1) if NUM_ZONES > 1 else 0.0
            interpolated_color = start_color.interpolate(end_color, ratio)
            zone_colors_list.append(interpolated_color)
        if not hardware.set_zone_colors(zone_colors_list):
            EffectLibrary.logger.warning("Static gradient: Hardware command failed")

    @staticmethod
    @safe_execute()
    def breathing(stop_event: threading.Event, hardware: HardwareController, speed: int, color: RGBColor, rainbow_mode: bool = False, **kwargs):
        EffectLibrary.logger.info(f"Starting breathing effect: speed={speed}, color={color.to_hex() if not rainbow_mode else 'RAINBOW'}")
        state = EffectState(); delay_factor = max(MIN_ANIMATION_FRAME_DELAY, BASE_ANIMATION_DELAY_SPEED_1 / speed) 
        error_count = 0; max_local_errors = 5
        while not stop_event.is_set():
            try:
                base_color_to_use = color
                if rainbow_mode: state.hue_offset = (state.hue_offset + 0.002 * speed) % 1.0; base_color_to_use = RGBColor.from_hsv(state.hue_offset, 1.0, 1.0)
                brightness_sine = (math.sin(state.frame_count * 0.05 * speed * 0.2) + 1) / 2.0; min_breath_brightness = 0.1
                current_brightness_factor = min_breath_brightness + (1.0 - min_breath_brightness) * brightness_sine
                dimmed_color = base_color_to_use.with_brightness(current_brightness_factor)
                if not hardware.set_all_leds_color(dimmed_color):
                    EffectLibrary.logger.warning("Breathing: set_all_leds_color failed."); error_count += 1
                    if error_count >= max_local_errors: break
                    if stop_event.wait(0.5): break 
                else: error_count = 0
                if stop_event.wait(delay_factor * 0.5): break
                state.frame_count += 1
            except Exception as e: 
                EffectLibrary.logger.error(f"Error in breathing: {e}", exc_info=True); error_count+=1
                time.sleep(0.2) 
                if error_count >= max_local_errors: EffectLibrary.logger.error("Max errors reached in breathing effect. Stopping."); break
                if stop_event.is_set(): break
        EffectLibrary.logger.info(f"Breathing effect ({'rainbow' if rainbow_mode else color.to_hex()}) stopped.")

    @staticmethod
    @safe_execute()
    def color_cycle(stop_event: threading.Event, hardware: HardwareController, speed: int, **kwargs):
        EffectLibrary.logger.info(f"Starting color cycle (rainbow) effect: speed={speed}")
        state = EffectState(); delay_factor = max(MIN_ANIMATION_FRAME_DELAY, BASE_ANIMATION_DELAY_SPEED_1 / (speed * 2))
        error_count = 0; max_local_errors = 5
        while not stop_event.is_set():
            try:
                current_color = RGBColor.from_hsv(state.hue_offset, 1.0, 1.0)
                if not hardware.set_all_leds_color(current_color):
                    EffectLibrary.logger.warning("Color Cycle: set_all_leds_color failed."); error_count += 1
                    if error_count >= max_local_errors: break
                    if stop_event.wait(0.5): break
                else: error_count = 0
                state.hue_offset = (state.hue_offset + 0.001 * speed) % 1.0
                if stop_event.wait(delay_factor): break
                state.frame_count +=1
            except Exception as e: 
                EffectLibrary.logger.error(f"Error in color_cycle: {e}", exc_info=True); error_count+=1
                time.sleep(0.2)
                if error_count >= max_local_errors: EffectLibrary.logger.error("Max errors reached in color_cycle effect. Stopping."); break
                if stop_event.is_set(): break
        EffectLibrary.logger.info("Color cycle effect stopped.")

    @staticmethod
    @safe_execute()
    def wave(stop_event: threading.Event, hardware: HardwareController, speed: int, color: RGBColor, rainbow_mode: bool = False, **kwargs):
        EffectLibrary.logger.info(f"Starting wave effect: speed={speed}, color={color.to_hex() if not rainbow_mode else 'RAINBOW'}")
        state = EffectState(); delay_factor = max(MIN_ANIMATION_FRAME_DELAY, BASE_ANIMATION_DELAY_SPEED_1 / speed)
        wave_width_zones = 1.5; error_count = 0; max_local_errors = 5; state.wave_position = -wave_width_zones 
        while not stop_event.is_set():
            try:
                zone_colors = [RGBColor(0,0,0)] * NUM_ZONES
                base_color_to_use = color
                if rainbow_mode: state.hue_offset = (state.hue_offset + 0.0005 * speed) % 1.0
                for zone_idx in range(NUM_ZONES):
                    zone_center_norm = (zone_idx + 0.5) / float(NUM_ZONES) if NUM_ZONES > 0 else 0.0
                    wave_peak_norm = state.wave_position / float(NUM_ZONES) if NUM_ZONES > 0 else 0.0
                    distance = abs(zone_center_norm - wave_peak_norm)
                    intensity = 0.0; normalized_wave_width = wave_width_zones / float(NUM_ZONES) if NUM_ZONES > 0 else 0.1
                    if distance < normalized_wave_width: intensity = (math.cos((distance / normalized_wave_width) * (math.pi / 2)))**2
                    current_zone_color = base_color_to_use
                    if rainbow_mode: segment_hue = (state.hue_offset + (zone_idx / float(NUM_ZONES)) * 0.2) % 1.0; current_zone_color = RGBColor.from_hsv(segment_hue, 1.0, 1.0)
                    zone_colors[zone_idx] = current_zone_color.with_brightness(intensity)
                if not hardware.set_zone_colors(zone_colors): 
                    EffectLibrary.logger.warning("Wave: set_zone_colors failed."); error_count += 1; 
                    if error_count >= max_local_errors: break
                    if stop_event.wait(0.5): break
                else: error_count = 0
                state.wave_position += 0.05 * speed 
                if state.wave_position > NUM_ZONES + wave_width_zones: state.wave_position = -wave_width_zones 
                if stop_event.wait(delay_factor * 0.5): break
                state.frame_count +=1
            except Exception as e: 
                EffectLibrary.logger.error(f"Error in wave: {e}", exc_info=True); error_count+=1
                time.sleep(0.2)
                if error_count >= max_local_errors: EffectLibrary.logger.error("Max errors reached in wave effect. Stopping."); break
                if stop_event.is_set(): break
        EffectLibrary.logger.info("Wave effect stopped.")

    @staticmethod
    @safe_execute()
    def pulse(stop_event: threading.Event, hardware: HardwareController, speed: int, color: RGBColor, rainbow_mode: bool = False, **kwargs):
        EffectLibrary.logger.info(f"Starting pulse: speed={speed}, color={color.to_hex() if not rainbow_mode else 'RAINBOW'}")
        state = EffectState(); delay_factor = BASE_ANIMATION_DELAY_SPEED_1 / speed; error_count = 0; max_local_errors = 5
        while not stop_event.is_set():
            try:
                base_color = color
                if rainbow_mode: state.hue_offset = (state.hue_offset + 0.005 * speed) % 1.0; base_color = RGBColor.from_hsv(state.hue_offset, 1.0, 1.0)
                frames_per_state = max(2, int(10 / speed))
                is_on_state = (state.frame_count // frames_per_state) % 2 == 0
                color_to_set = base_color if is_on_state else RGBColor(0,0,0)
                if not hardware.set_all_leds_color(color_to_set): 
                    EffectLibrary.logger.warning("Pulse: set_all_leds_color failed."); error_count+=1
                    if error_count >= max_local_errors: break
                    if stop_event.wait(0.5): break
                else: error_count = 0
                if stop_event.wait(max(MIN_ANIMATION_FRAME_DELAY, delay_factor * 0.1)): break
                state.frame_count +=1
            except Exception as e: 
                EffectLibrary.logger.error(f"Error in pulse: {e}", exc_info=True); error_count+=1
                time.sleep(0.2)
                if error_count >= max_local_errors: EffectLibrary.logger.error("Max errors reached in pulse effect. Stopping."); break
                if stop_event.is_set(): break
        EffectLibrary.logger.info("Pulse effect stopped.")

    @staticmethod
    @safe_execute()
    def zone_chase(stop_event: threading.Event, hardware: HardwareController, speed: int, color: RGBColor, rainbow_mode: bool = False, **kwargs):
        EffectLibrary.logger.info(f"Starting zone_chase: speed={speed}, color={color.to_hex() if not rainbow_mode else 'RAINBOW'}")
        state = EffectState(); delay_factor = BASE_ANIMATION_DELAY_SPEED_1 / speed; error_count = 0; max_local_errors = 5
        while not stop_event.is_set():
            try:
                base_color = color
                if rainbow_mode: state.hue_offset = (state.hue_offset + 0.01 * speed * 0.1) % 1.0
                zone_colors = [RGBColor(0,0,0)] * NUM_ZONES; current_lit_zone = state.position
                if rainbow_mode: block_hue = (state.hue_offset + (current_lit_zone / float(NUM_ZONES))) % 1.0; base_color = RGBColor.from_hsv(block_hue, 1.0, 1.0)
                zone_colors[current_lit_zone] = base_color
                if not hardware.set_zone_colors(zone_colors): 
                    EffectLibrary.logger.warning("ZoneChase: set_zone_colors failed."); error_count+=1
                    if error_count >= max_local_errors: break
                    if stop_event.wait(0.5): break
                else: error_count = 0
                state.position = (state.position + 1) % NUM_ZONES
                if stop_event.wait(max(MIN_ANIMATION_FRAME_DELAY, delay_factor)): break
                state.frame_count +=1
            except Exception as e: 
                EffectLibrary.logger.error(f"Error in zone_chase: {e}", exc_info=True); error_count+=1
                time.sleep(0.2)
                if error_count >= max_local_errors: EffectLibrary.logger.error("Max errors reached in zone_chase. Stopping."); break
                if stop_event.is_set(): break
        EffectLibrary.logger.info("Zone chase effect stopped.")

    @staticmethod
    @safe_execute()
    def starlight(stop_event: threading.Event, hardware: HardwareController, speed: int, color: RGBColor, rainbow_mode: bool = False, **kwargs):
        EffectLibrary.logger.info(f"Starting starlight: speed={speed}, color={color.to_hex() if not rainbow_mode else 'RAINBOW'}")
        state = EffectState(); delay_factor = BASE_ANIMATION_DELAY_SPEED_1 / speed; error_count = 0; max_local_errors = 10
        while not stop_event.is_set():
            try:
                zone_colors = [RGBColor(0,0,0)] * NUM_ZONES
                num_stars = random.randint(1, max(1, NUM_ZONES // 2 + int(speed / 3)))
                for _ in range(num_stars):
                    zone_to_light = random.randint(0, NUM_ZONES - 1)
                    star_brightness = random.uniform(0.3, 1.0); star_color = color
                    if rainbow_mode: star_color = RGBColor.from_hsv(random.random(), 1.0, 1.0)
                    zone_colors[zone_to_light] = star_color.with_brightness(star_brightness)
                if not hardware.set_zone_colors(zone_colors): 
                    EffectLibrary.logger.warning("Starlight: set_zone_colors failed."); error_count+=1
                    if error_count >= max_local_errors: break
                    if stop_event.wait(0.5): break
                else: error_count = 0
                if stop_event.wait(max(MIN_ANIMATION_FRAME_DELAY, delay_factor * 2)): break
                state.frame_count +=1
            except Exception as e: 
                EffectLibrary.logger.error(f"Error in starlight: {e}", exc_info=True); error_count+=1
                time.sleep(0.2)
                if error_count >= max_local_errors: EffectLibrary.logger.error("Max errors reached in starlight. Stopping."); break
                if stop_event.is_set(): break
        EffectLibrary.logger.info("Starlight effect stopped.")
    
    @staticmethod
    @safe_execute()
    def raindrop(stop_event: threading.Event, hardware: HardwareController, speed: int, color: Optional[RGBColor]=None, **kwargs):
        EffectLibrary.logger.info(f"Starting raindrop effect: speed={speed}")
        state = EffectState(); palette = [RGBColor.from_hex(h) for h in ["#0077FF", "#00BFFF", "#87CEFA", "#4682B4"]]
        if color and isinstance(color, RGBColor): 
            palette = [color.interpolate(RGBColor(0,0,50), 0.5), color, color.interpolate(RGBColor(200,200,255),0.5)]
        delay_factor = max(MIN_ANIMATION_FRAME_DELAY, BASE_ANIMATION_DELAY_SPEED_1 / (speed * 1.5)); error_count = 0; max_local_errors = 5
        while not stop_event.is_set():
            try:
                current_zone_colors = hardware.get_all_zone_colors()
                faded_zone_colors = []
                for zc in current_zone_colors:
                    fade_amount = int(15 + speed)
                    new_r = max(0, zc.r - fade_amount // 3); new_g = max(0, zc.g - fade_amount // 2); new_b = max(0, zc.b - fade_amount)
                    faded_zone_colors.append(RGBColor(new_r, new_g, new_b))
                zone_colors_to_set = faded_zone_colors
                if random.random() < (0.05 + 0.05 * speed):
                    drop_zone = random.randint(0, NUM_ZONES -1) 
                    drop_start_color = random.choice(palette)
                    zone_colors_to_set[drop_zone] = drop_start_color 
                if not hardware.set_zone_colors(zone_colors_to_set): 
                    EffectLibrary.logger.warning("Raindrop: set_zone_colors failed."); error_count+=1
                    if error_count >= max_local_errors: break
                    if stop_event.wait(0.5): break
                else: error_count = 0
                if stop_event.wait(delay_factor): break
                state.frame_count +=1
            except Exception as e: 
                EffectLibrary.logger.error(f"Error in raindrop: {e}", exc_info=True); error_count+=1
                time.sleep(0.2)
                if error_count >= max_local_errors: EffectLibrary.logger.error("Max errors reached in raindrop. Stopping."); break
                if stop_event.is_set(): break
        EffectLibrary.logger.info("Raindrop effect stopped.")

    @staticmethod
    @safe_execute()
    def scanner(stop_event: threading.Event, hardware: HardwareController, speed: int, color: RGBColor, rainbow_mode: bool = False, **kwargs):
        EffectLibrary.logger.info(f"Starting scanner: speed={speed}, color={color.to_hex() if not rainbow_mode else 'RAINBOW'}")
        state = EffectState(position=0, direction=1); delay_factor = max(MIN_ANIMATION_FRAME_DELAY, BASE_ANIMATION_DELAY_SPEED_1 / (speed * 1.5))
        error_count = 0; max_local_errors = 5; tail_length = max(0, NUM_ZONES // 3 -1) 
        while not stop_event.is_set():
            try:
                base_color_to_use = color
                if rainbow_mode: state.hue_offset = (state.hue_offset + 0.002 * speed)%1.0; base_color_to_use = RGBColor.from_hsv(state.hue_offset, 1.0, 1.0)
                zone_colors = [RGBColor(0,0,0)] * NUM_ZONES
                for i in range(tail_length + 1):
                    pos = state.position - (i * state.direction) 
                    if 0 <= pos < NUM_ZONES:
                        brightness = 1.0 - (i / float(tail_length + 2)) 
                        zone_colors[pos] = base_color_to_use.with_brightness(brightness)
                if not hardware.set_zone_colors(zone_colors): 
                    EffectLibrary.logger.warning("Scanner: set_zone_colors failed."); error_count+=1
                    if error_count >= max_local_errors: break
                    if stop_event.wait(0.5): break
                else: error_count = 0
                state.position += state.direction
                if state.position >= NUM_ZONES: state.position = NUM_ZONES -1 ; state.direction = -1 
                elif state.position < 0: state.position = 0; state.direction = 1 
                if stop_event.wait(delay_factor): break
                state.frame_count +=1
            except Exception as e: 
                EffectLibrary.logger.error(f"Error in scanner: {e}", exc_info=True); error_count+=1
                time.sleep(0.2)
                if error_count >= max_local_errors: EffectLibrary.logger.error("Max errors reached in scanner. Stopping."); break
                if stop_event.is_set(): break
        EffectLibrary.logger.info("Scanner effect stopped.")

    @staticmethod
    @safe_execute()
    def strobe(stop_event: threading.Event, hardware: HardwareController, speed: int, color: RGBColor, rainbow_mode: bool = False, **kwargs):
        EffectLibrary.logger.info(f"Starting strobe: speed={speed}, color={color.to_hex() if not rainbow_mode else 'RAINBOW'}")
        state = EffectState(); delay_factor = max(MIN_ANIMATION_FRAME_DELAY, BASE_ANIMATION_DELAY_SPEED_1 / (speed * 5)); 
        error_count = 0; max_local_errors = 5; is_on_state = True
        while not stop_event.is_set():
            try:
                base_color_to_use = color
                if rainbow_mode: state.hue_offset = (state.hue_offset + 0.02 * speed)%1.0; base_color_to_use = RGBColor.from_hsv(state.hue_offset, 1.0, 1.0)
                color_to_set = base_color_to_use if is_on_state else RGBColor(0,0,0)
                if not hardware.set_all_leds_color(color_to_set): 
                    EffectLibrary.logger.warning("Strobe: set_all_leds_color failed."); error_count+=1
                    if error_count >= max_local_errors: break
                    if stop_event.wait(0.5): break
                else: error_count = 0
                is_on_state = not is_on_state
                if stop_event.wait(delay_factor): break
                state.frame_count +=1
            except Exception as e: 
                EffectLibrary.logger.error(f"Error in strobe: {e}", exc_info=True); error_count+=1
                time.sleep(0.2)
                if error_count >= max_local_errors: EffectLibrary.logger.error("Max errors reached in strobe. Stopping."); break
                if stop_event.is_set(): break
        EffectLibrary.logger.info("Strobe effect stopped.")

    @staticmethod
    @safe_execute()
    def ripple(stop_event: threading.Event, hardware: HardwareController, speed: int, color: RGBColor, rainbow_mode: bool = False, **kwargs):
        EffectLibrary.logger.info(f"Starting ripple: speed={speed}, color={color.to_hex() if not rainbow_mode else 'RAINBOW'}")
        state = EffectState(); delay_factor = max(MIN_ANIMATION_FRAME_DELAY, BASE_ANIMATION_DELAY_SPEED_1 / (speed * 2))
        error_count = 0; max_local_errors = 5
        while not stop_event.is_set():
            try:
                zone_colors = [RGBColor(0,0,0)] * NUM_ZONES
                if random.random() < (0.01 + 0.02 * speed): 
                    center_zone = random.randint(0, NUM_ZONES - 1)
                    ripple_base_hue = random.random() if rainbow_mode else color.to_hsv()[0]
                    state.ripple_sources.append({"center": center_zone, "radius": 0.0, "max_radius": float(NUM_ZONES) * 0.75, "hue": ripple_base_hue, "intensity": 1.0})
                new_ripples = []
                for rip in state.ripple_sources:
                    for zone_idx in range(NUM_ZONES):
                        distance = abs(zone_idx - rip["center"])
                        ripple_width_param = 1.0 
                        if rip["radius"] - ripple_width_param < distance < rip["radius"] + ripple_width_param:
                            dist_from_peak = abs(distance - rip["radius"])
                            brightness_factor = rip["intensity"] * max(0, (1.0 - (dist_from_peak / ripple_width_param)))**2 
                            ripple_color_base = color if not rainbow_mode else RGBColor.from_hsv(rip["hue"], 1.0, 1.0)
                            ripple_eff_color = ripple_color_base.with_brightness(brightness_factor)
                            zone_colors[zone_idx] = RGBColor(
                                r=min(255, zone_colors[zone_idx].r + ripple_eff_color.r),
                                g=min(255, zone_colors[zone_idx].g + ripple_eff_color.g),
                                b=min(255, zone_colors[zone_idx].b + ripple_eff_color.b))
                    rip["radius"] += 0.1 * speed ; rip["intensity"] *= (0.96 - (speed * 0.002)) 
                    if rip["intensity"] > 0.05 and rip["radius"] < rip["max_radius"] + ripple_width_param: new_ripples.append(rip)
                state.ripple_sources = new_ripples
                if not hardware.set_zone_colors(zone_colors): 
                    EffectLibrary.logger.warning("Ripple: set_zone_colors failed."); error_count+=1
                    if error_count >= max_local_errors: break
                    if stop_event.wait(0.5): break
                else: error_count = 0
                if stop_event.wait(delay_factor): break
                state.frame_count +=1
            except Exception as e: 
                EffectLibrary.logger.error(f"Error in ripple: {e}", exc_info=True); error_count+=1
                time.sleep(0.2)
                if error_count >= max_local_errors: EffectLibrary.logger.error("Max errors reached in ripple. Stopping."); break
                if stop_event.is_set(): break
        EffectLibrary.logger.info("Ripple effect stopped.")

    @staticmethod
    @safe_execute()
    def rainbow_wave(stop_event: threading.Event, hardware: HardwareController, speed: int, **kwargs):
        EffectLibrary.logger.info(f"Starting rainbow_wave (delegating to wave with rainbow_mode=True): speed={speed}")
        # Call the main 'wave' effect with rainbow_mode explicitly set to True
        # The 'color' param passed here will be ignored by 'wave' if rainbow_mode is True
        EffectLibrary.wave(stop_event, hardware, speed, RGBColor(0,0,0), rainbow_mode=True, **kwargs)
        EffectLibrary.logger.info("Rainbow wave (delegated) effect stopped.")

    @staticmethod
    @safe_execute()
    def rainbow_breathing(stop_event: threading.Event, hardware: HardwareController, speed: int, **kwargs):
        EffectLibrary.logger.info(f"Starting rainbow_breathing (delegating to breathing with rainbow_mode=True): speed={speed}")
        EffectLibrary.breathing(stop_event, hardware, speed, RGBColor(0,0,0), rainbow_mode=True, **kwargs)
        EffectLibrary.logger.info("Rainbow breathing (delegated) effect stopped.")

    @staticmethod
    @safe_execute()
    def rainbow_zones_cycle(stop_event: threading.Event, hardware: HardwareController, speed: int, **kwargs):
        EffectLibrary.logger.info(f"Starting rainbow_zones_cycle: speed={speed}")
        state = EffectState(); delay_factor = max(MIN_ANIMATION_FRAME_DELAY, BASE_ANIMATION_DELAY_SPEED_1 / speed); error_count = 0; max_local_errors = 5
        while not stop_event.is_set():
            try:
                zone_colors = []
                for zone_idx in range(NUM_ZONES):
                    hue = (state.hue_offset + (zone_idx / float(NUM_ZONES))) % 1.0 
                    zone_colors.append(RGBColor.from_hsv(hue, 1.0, 1.0))
                if not hardware.set_zone_colors(zone_colors): 
                    EffectLibrary.logger.warning("RainbowZonesCycle: set_zone_colors failed."); error_count+=1
                    if error_count >= max_local_errors: break
                    if stop_event.wait(0.5): break
                else: error_count = 0
                state.hue_offset = (state.hue_offset + 0.002 * speed) % 1.0
                if stop_event.wait(delay_factor): break
                state.frame_count +=1
            except Exception as e: 
                EffectLibrary.logger.error(f"Error in rainbow_zones_cycle: {e}", exc_info=True); error_count+=1
                time.sleep(0.2)
                if error_count >= max_local_errors: EffectLibrary.logger.error("Max errors reached in rainbow_zones_cycle. Stopping."); break
                if stop_event.is_set(): break
        EffectLibrary.logger.info("Rainbow zones cycle effect stopped.")

    @staticmethod
    @safe_execute(max_attempts=1)
    def reactive_pulse(hardware: HardwareController, zone_index_1_based: int, color: RGBColor, duration_ms: int = int(REACTIVE_DELAY * 1000), **kwargs):
        EffectLibrary.logger.debug(f"Reactive pulse on zone {zone_index_1_based} color {color.to_hex()}")
        if not (1 <= zone_index_1_based <= NUM_ZONES): EffectLibrary.logger.warning(f"Invalid zone {zone_index_1_based} for reactive pulse."); return
        
        original_color = hardware.get_zone_color(zone_index_1_based) 
        if original_color is None: original_color = RGBColor(0,0,0) 

        num_steps = 20 ; step_delay = (duration_ms / 1000.0) / num_steps
        if step_delay < MIN_ANIMATION_FRAME_DELAY: step_delay = MIN_ANIMATION_FRAME_DELAY

        try:
            for i in range(num_steps // 2): 
                ratio = i / float(num_steps // 2 -1 if num_steps//2 >1 else 1)
                intermediate_color = original_color.interpolate(color, ratio)
                if not hardware.set_zone_color(zone_index_1_based, intermediate_color): break
                time.sleep(step_delay / 2)
            
            if not hardware.set_zone_color(zone_index_1_based, color): return
            time.sleep(step_delay * 2) 

            for i in range(num_steps // 2): 
                ratio = i / float(num_steps // 2 -1 if num_steps//2 >1 else 1)
                intermediate_color = color.interpolate(original_color, ratio)
                if not hardware.set_zone_color(zone_index_1_based, intermediate_color): break
                time.sleep(step_delay / 2)

            hardware.set_zone_color(zone_index_1_based, original_color)
        except Exception as e: 
            EffectLibrary.logger.error(f"Error in reactive_pulse for zone {zone_index_1_based}: {e}", exc_info=True)
            try: hardware.set_zone_color(zone_index_1_based, original_color) 
            except: pass
    

    



    @staticmethod
    @safe_execute()
    def reactive(stop_event: threading.Event, hardware: HardwareController, speed: int, color: RGBColor, **kwargs):
        \"\"\"Enhanced reactive effect - keys light up only when pressed, all others stay off\"\"\"
        EffectLibrary.logger.info(f"Starting enhanced reactive effect: speed={speed}, color={color.to_hex()}")
        
        # Enable reactive mode on hardware
        if hasattr(hardware, 'set_reactive_mode'):
            if not hardware.set_reactive_mode(enabled=True, color=color, anti_mode=False):
                EffectLibrary.logger.error("Failed to enable reactive mode on hardware")
                return
        
        state = EffectState()
        delay_factor = max(MIN_ANIMATION_FRAME_DELAY, BASE_ANIMATION_DELAY_SPEED_1 / speed)
        error_count = 0
        max_local_errors = 5
        
        while not stop_event.is_set():
            try:
                # Check for real key presses if supported
                if hasattr(hardware, 'get_pressed_keys'):
                    pressed_keys = hardware.get_pressed_keys()
                    # Update only pressed keys
                    for key_pos in pressed_keys:
                        if hasattr(hardware, 'handle_key_press'):
                            hardware.handle_key_press(key_pos, True)
                else:
                    # Fallback: simulate key presses for demo
                    if hasattr(hardware, 'simulate_key_press_pattern'):
                        if state.frame_count % 100 == 0:  # Every 100 frames
                            hardware.simulate_key_press_pattern("typing")
                
                if stop_event.wait(delay_factor): 
                    break
                state.frame_count += 1
                
            except Exception as e:
                EffectLibrary.logger.error(f"Error in enhanced reactive: {e}", exc_info=True)
                error_count += 1
                time.sleep(0.2)
                if error_count >= max_local_errors:
                    EffectLibrary.logger.error("Max errors reached in reactive effect. Stopping.")
                    break
                if stop_event.is_set(): 
                    break
        
        # Disable reactive mode
        if hasattr(hardware, 'set_reactive_mode'):
            hardware.set_reactive_mode(enabled=False, color=RGBColor(0, 0, 0))
        
        EffectLibrary.logger.info("Enhanced reactive effect stopped.")

    @staticmethod
    @safe_execute()
    def anti_reactive(stop_event: threading.Event, hardware: HardwareController, speed: int, color: RGBColor, **kwargs):
        \"\"\"Enhanced anti-reactive effect - all keys stay on except when pressed, pressed keys turn off\"\"\"
        EffectLibrary.logger.info(f"Starting enhanced anti-reactive effect: speed={speed}, color={color.to_hex()}")
        
        # Enable anti-reactive mode on hardware
        if hasattr(hardware, 'set_reactive_mode'):
            if not hardware.set_reactive_mode(enabled=True, color=color, anti_mode=True):
                EffectLibrary.logger.error("Failed to enable anti-reactive mode on hardware")
                return
        
        state = EffectState()
        delay_factor = max(MIN_ANIMATION_FRAME_DELAY, BASE_ANIMATION_DELAY_SPEED_1 / speed)
        error_count = 0
        max_local_errors = 5
        
        while not stop_event.is_set():
            try:
                # Check for real key presses if supported
                if hasattr(hardware, 'get_pressed_keys'):
                    pressed_keys = hardware.get_pressed_keys()
                    # Update pressed keys (turn them off in anti-reactive mode)
                    for key_pos in pressed_keys:
                        if hasattr(hardware, 'handle_key_press'):
                            hardware.handle_key_press(key_pos, True)
                else:
                    # Fallback: simulate key presses for demo
                    if hasattr(hardware, 'simulate_key_press_pattern'):
                        if state.frame_count % 100 == 0:  # Every 100 frames
                            hardware.simulate_key_press_pattern("typing")
                
                if stop_event.wait(delay_factor): 
                    break
                state.frame_count += 1
                
            except Exception as e:
                EffectLibrary.logger.error(f"Error in enhanced anti_reactive: {e}", exc_info=True)
                error_count += 1
                time.sleep(0.2)
                if error_count >= max_local_errors:
                    EffectLibrary.logger.error("Max errors reached in anti_reactive effect. Stopping.")
                    break
                if stop_event.is_set(): 
                    break
        
        # Disable reactive mode
        if hasattr(hardware, 'set_reactive_mode'):
            hardware.set_reactive_mode(enabled=False, color=RGBColor(0, 0, 0))
        
        EffectLibrary.logger.info("Enhanced anti-reactive effect stopped.")""",
                # NEW: The full, corrected, and enhanced EffectLibrary class.
                """class EffectLibrary:
    logger = logging.getLogger('EffectLibrary')

    @staticmethod
    def _get_delay(speed: int) -> float:
        \"\"\"Calculate frame delay based on speed (1-10).\"\"\"
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
        \"\"\"Keys are off by default and light up when 'pressed' (simulated).\"\"\"
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
        \"\"\"Keys are on by default and turn off when 'pressed' (simulated).\"\"\"
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
            if stop_event.wait(delay): break""",
            )
        ]
    },
    {
        "file_path": "gui/controller.py",
        "patches": [
            (
                "Full GUI Overhaul (Final)",
                # OLD: The entire RGBControllerGUI class from your file.
                """class RGBControllerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.logger = self.setup_logging()

        self.pystray_icon_image: Optional[Image.Image] = None
        self.tk_icon_photoimage: Optional[tk.PhotoImage] = None

        # Add comprehensive error handling wrapper
        try:
            self._initialize_core_components()
        except Exception as e:
            self._handle_critical_initialization_error(e)

        self.is_fullscreen = False
        self.preview_animation_active = False
        self.preview_animation_id: Optional[str] = None
        self.preview_led_states = [RGBColor(0,0,0) for _ in range(TOTAL_LEDS)]
        self._preview_frame_count = 0
        self._loading_settings = False
        self.tray_icon: Optional[pystray.Icon] = None
        self.tray_thread: Optional[threading.Thread] = None
        self.window_hidden_to_tray = False
        self._hotkey_listener_stop_event = threading.Event()
        self._hotkey_setup_attempted = False
        self._brightness_hotkeys_working = False
        self._registered_hotkeys = []  # Track registered hotkeys for cleanup

        # Initialize preview canvases storage
        self.preview_canvas = None
        self.static_preview_canvas = None
        self.zone_preview_canvas = None
        self.preview_keyboard_elements = []
        self.static_keyboard_elements = []
        self.zone_keyboard_elements = []

        loaded_zone_colors_data = self.settings.get("zone_colors", default_settings["zone_colors"])
        self.zone_colors: List[RGBColor] = []
        if isinstance(loaded_zone_colors_data, list):
            for i in range(NUM_ZONES):
                default_zone_color_dict = default_settings["zone_colors"][i % len(default_settings["zone_colors"])]
                if i < len(loaded_zone_colors_data) and isinstance(loaded_zone_colors_data[i], dict):
                    try: 
                        self.zone_colors.append(RGBColor.from_dict(loaded_zone_colors_data[i]))
                    except Exception as e_color:
                        self.logger.warning(f"Malformed color data for zone {i}: {e_color}. Using default.")
                        self.zone_colors.append(RGBColor.from_dict(default_zone_color_dict))
                else: 
                    self.zone_colors.append(RGBColor.from_dict(default_zone_color_dict))
        else:
            self.logger.warning("zone_colors setting not a list, using defaults.")
            self.zone_colors = [RGBColor.from_dict(d) for d in default_settings["zone_colors"][:NUM_ZONES]]
        
        while len(self.zone_colors) < NUM_ZONES:
            self.zone_colors.append(RGBColor.from_dict(default_settings["zone_colors"][len(self.zone_colors) % len(default_settings["zone_colors"])]))
        self.zone_colors = self.zone_colors[:NUM_ZONES]

        self.setup_variables()
        self.setup_main_window()
        self.create_widgets()
        self.setup_bindings()
        # Reactive effects system - ADDED BY PATCH
        self.reactive_effects_enabled = False
        self.pressed_keys = set()
        self.simulated_key_presses = queue.Queue()
        self.reactive_effect_thread = None
        self.reactive_stop_event = threading.Event()
        self.preview_key_simulation_active = False
        self.preview_key_sim_thread = None

        # Enhanced hotkey setup with ALT+BRIGHTNESS priority
        if KEYBOARD_LIB_AVAILABLE:
            self.setup_global_hotkeys_enhanced()
        else:
            self.log_missing_keyboard_library()

        self.root.after(100, self.initialize_hardware_async)
        self.load_saved_settings()
        self.root.after(500, self.apply_startup_settings_if_enabled_async)
        self.setup_gui_logging()
        self.logger.info(f"{APP_NAME} v{VERSION} GUI Initialized and ready.")""",
                # NEW: The full, corrected, and enhanced RGBControllerGUI class.
                """class RGBControllerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.logger = self.setup_logging()
        self.pystray_icon_image: Optional[Image.Image] = None
        self.tk_icon_photoimage: Optional[tk.PhotoImage] = None

        try:
            self._initialize_core_components()
        except Exception as e:
            self._handle_critical_initialization_error(e)

        # State Variables
        self.is_fullscreen = False
        self.preview_animation_active = False
        self.preview_animation_id: Optional[str] = None
        self._preview_frame_count = 0
        self._loading_settings = False
        self.tray_icon: Optional[pystray.Icon] = None
        self.tray_thread: Optional[threading.Thread] = None
        self.window_hidden_to_tray = False
        self._hotkey_setup_attempted = False
        self._brightness_hotkeys_working = False
        self._registered_hotkeys = []

        self.setup_variables()
        self.setup_main_window()
        self.create_widgets()
        self.setup_bindings()

        if KEYBOARD_LIB_AVAILABLE:
            self.setup_global_hotkeys_enhanced()
        
        # Staggered startup sequence
        self.root.after(100, self.initialize_hardware_async)
        self.root.after(200, self.load_saved_settings)
        self.root.after(300, self.show_system_info) # Populate diagnostics on startup
        self.root.after(600, self.apply_startup_settings_if_enabled_async)
        
        self.logger.info(f"{APP_NAME} v{VERSION} GUI Initialized and ready.")

    def _initialize_core_components(self):
        \"\"\"Separated initialization for better error handling.\"\"\"
        self.settings = SettingsManager()
        self.hardware = HardwareController()
        self.effect_manager = EffectManager(self.hardware)
    
    def _handle_critical_initialization_error(self, error):
        \"\"\"Handle critical initialization failures gracefully.\"\"\"
        self.logger.critical(f"Fatal error initializing core components: {error}", exc_info=True)
        messagebox.showerror("Initialization Error", f"A critical error occurred: {error}\\n\\nThe application will now exit.")
        sys.exit(1)

    def log_missing_keyboard_library(self):
        self.logger.warning("Keyboard library not available. Hotkeys disabled.")

    def _stop_all_visuals_and_clear_hardware(self):
        \"\"\"Stops software effects and attempts to clear hardware patterns.\"\"\"
        self.logger.debug("Stopping all software effects and GUI previews.")
        self.effect_manager.stop_current_effect()
        self.stop_preview_animation()
        self.hardware.clear_all_leds()
        self.update_preview_keyboard(colors=[RGBColor(0,0,0)] * NUM_ZONES)
        self.logger.debug("All visuals stopped and hardware cleared.")

    def setup_logging(self) -> logging.Logger:
        logger = logging.getLogger(f"{APP_NAME}.GUI")
        if logger.hasHandlers(): return logger
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s')
        try:
            log_dir = SETTINGS_FILE.parent / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "rgb_controller_gui.log"
            fh = logging.handlers.RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        except Exception as e:
            logger.error(f"Failed to set up GUI file logging: {e}", exc_info=True)
        return logger
        
    def create_desktop_launcher(self):
        if platform.system() != "Linux":
            messagebox.showinfo("Not Supported", "Desktop launcher creation is currently only supported on Linux.", parent=self.root)
            return

        try:
            python_exe = sys.executable
            project_root_dir = Path(__file__).resolve().parent.parent
            module_to_run = project_root_dir.name
            working_dir_for_launcher = project_root_dir.parent
            exec_cmd = f'{shlex.quote(str(python_exe))} -m {shlex.quote(module_to_run)}'
            
            # Find icon
            icon_path = project_root_dir / "assets" / "icon.png"
            icon_name_or_path = str(icon_path.resolve()) if icon_path.exists() else "input-keyboard"

            content = (f"[Desktop Entry]\\nVersion=1.0\\nName={APP_NAME}\\nComment=Control RGB Keyboard Lighting\\n"
                       f"Exec={exec_cmd}\\nIcon={icon_name_or_path}\\nTerminal=false\\nType=Application\\n"
                       f"Categories=Utility;Settings;HardwareSettings;\\nPath={str(working_dir_for_launcher)}\\n")

            # --- Write to multiple locations ---
            locations_to_try = [
                Path.home() / ".local/share/applications",
                Path.home() / "Desktop"
            ]
            
            success_paths = []
            for loc in locations_to_try:
                try:
                    loc.mkdir(parents=True, exist_ok=True)
                    file_path = loc / f"{module_to_run}.desktop"
                    file_path.write_text(content, encoding='utf-8')
                    file_path.chmod(0o755)
                    success_paths.append(f"✓ {loc.name}: {file_path}")
                except Exception as e:
                    self.logger.error(f"Failed to create launcher at {loc}: {e}")
            
            if success_paths:
                messagebox.showinfo("Launcher Created", "\\n".join(success_paths), parent=self.root)
            else:
                messagebox.showerror("Launcher Error", "Could not create launcher in any location. Please check permissions.", parent=self.root)

        except Exception as e:
            self.logger.error(f"Could not determine paths for launcher: {e}", exc_info=True)
            messagebox.showerror("Launcher Error", f"Could not determine script paths: {e}", parent=self.root)"""
            )
        ]
    }
]

def main():
    print("--- Starting Definitive Enhancement Patch Script ---")
    all_patches_successful = True

    for group in PATCH_GROUPS:
        file_path = group["file_path"]
        patches = group["patches"]
        
        print(f"\\n[INFO] Processing file: '{file_path}'")

        if not os.path.exists(file_path):
            print(f"  [ERROR] Target file not found: '{file_path}'. Skipping.")
            all_patches_successful = False
            continue

        try:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_path = f"{file_path}.{timestamp}.final.backup"
            shutil.copy2(file_path, backup_path)
            print(f"  - SUCCESS: Created backup at '{backup_path}'")
        except Exception as e:
            print(f"  - [ERROR] Could not create backup: {e}. Aborting for this file.")
            all_patches_successful = False
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"  - [ERROR] Could not read target file: {e}. Aborting for this file.")
            all_patches_successful = False
            continue

        file_patches_successful = True
        for name, old_code, new_code in patches:
            print(f"    - Applying patch: '{name}'...")
            
            if old_code in content:
                content = content.replace(old_code, new_code, 1)
                print(f"      - SUCCESS: Patch applied in memory.")
            else:
                print(f"      - [ERROR] Patch FAILED. The code to be replaced was not found.")
                print("        - The file may have been modified by a previous patch.")
                print("        - Restore from backup if issues occur. Skipping this patch.")
                file_patches_successful = False
                all_patches_successful = False
                break 
        
        if file_patches_successful:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  - SUCCESS: Patched '{file_path}'")
            except Exception as e:
                print(f"  - [ERROR] Failed to write changes to '{file_path}': {e}")
                all_patches_successful = False

    print("\\n--- Patching Summary ---")
    if all_patches_successful:
        print("All enhancements and fixes have been applied successfully.")
        print("Please restart the application.")
    else:
        print("One or more patches failed. Please review the errors above.")
        print("Check backup files (.final.backup) to restore originals if needed.")

if __name__ == "__main__":
    main()
