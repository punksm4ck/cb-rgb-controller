import subprocess
import logging
import os
import threading
import time
import colorsys

try:
    import keyboard
    KB_AVAIL = True
except ImportError:
    KB_AVAIL = False

class InternalColor:
    def __init__(self, r, g, b):
        self.r, self.g, self.b = r, g, b
    def to_hex(self):
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"

class HardwareController:
    def __init__(self, logger=None, last_control_method='ectool', emergency_mode=False):
        self.logger = logger or logging.getLogger(__name__)
        self.active_method = 'ectool'
        self.hardware_ready = True
        self._ectool_path = '/usr/local/bin/ectool'
        self.detection_complete = threading.Event()
        self.detection_complete.set()
        
        self.reactive_active = False
        self.reactive_mode = None
        self._kb_hook = None
        self.react_thread = None
        
        self.column_indices = [1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        self.col_state = {col: False for col in self.column_indices}
        self.col_timers = {col: 0 for col in self.column_indices}
        self.react_lock = threading.Lock()

    def wait_for_detection(self, timeout=10, preferred_method=None): return True
    def is_operational(self): return True
    def get_active_method_display(self): return "ectool (Total-Matrix Reactive)"
    @property
    def active_control_method(self): return self.active_method

    def _run_ectool_cmd(self, cmd_args):
        try:
            full_cmd = [self._ectool_path] + cmd_args
            subprocess.run(full_cmd, capture_output=True, text=True, check=True)
            # Lightning-fast 5ms delay allows us to broadcast all 11 columns instantly
            time.sleep(0.005) 
            return True, ""
        except Exception as e:
            return False, str(e)

    def set_all_leds_color(self, color_obj):
        hex_color = color_obj.to_hex().lstrip('#') if hasattr(color_obj, 'to_hex') else str(color_obj).lstrip('#')
        for zone in self.column_indices:
            self._run_ectool_cmd(['rgbkbd', str(zone), f"0x{hex_color}"])
        return True

    def set_zone_colors(self, colors_list):
        hw_mapping = {0: [1, 2], 1: [4, 5, 6], 2: [7, 8, 9], 3: [10, 11, 12]}
        for gui_idx, hw_zones in hw_mapping.items():
            if gui_idx < len(colors_list):
                hex_color = colors_list[gui_idx].to_hex().lstrip('#')
                for zone in hw_zones:
                    self._run_ectool_cmd(['rgbkbd', str(zone), f"0x{hex_color}"])
        return True

    def set_brightness(self, value):
        brightness = int((value / 100) * 255)
        try: self._run_ectool_cmd(['pwmsetkblight', str(brightness)])
        except: pass
        return True

    def clear_all_leds(self):
        for zone in self.column_indices:
            self._run_ectool_cmd(['rgbkbd', str(zone), '0x000000'])
        return True

    def attempt_stop_hardware_effects(self):
        self.stop_reactive_mode()
        self._run_ectool_cmd(['rgbkbd', 'demo', '0'])
        return True

    def _get_col_for_key(self, key_name):
        k = str(key_name).lower()
        mapping = {
            'esc':1, '`':1, 'tab':1, 'caps lock':1, 'shift':1, 'ctrl':1, '1':1, 'q':1, 'a':1, 'z':1,
            '2':2, 'w':2, 's':2, 'x':2, 'alt':2,
            '3':4, 'e':4, 'd':4, 'c':4,
            '4':5, 'r':5, 'f':5, 'v':5,
            '5':6, 't':6, 'g':6, 'b':6,
            '6':7, 'y':7, 'h':7, 'n':7, 'space':7,
            '7':8, 'u':8, 'j':8, 'm':8,
            '8':9, 'i':9, 'k':9, ',':9,
            '9':10, 'o':10, 'l':10, '.':10, 'alt gr':10,
            '0':11, 'p':11, ';':11, '/':11, '-':11, '[':11, '\'':11,
            '=':12, 'backspace':12, ']':12, '\\':12, 'enter':12, 'right shift':12, 'up':12, 'down':12, 'left':12, 'right':12
        }
        return mapping.get(k, 7)

    def stop_reactive_mode(self):
        self.reactive_active = False
        if self._kb_hook and KB_AVAIL:
            try: keyboard.unhook(self._kb_hook)
            except: pass
            self._kb_hook = None

    def start_reactive_mode(self, mode, color_obj, is_rainbow):
        self.stop_reactive_mode()
        if not KB_AVAIL:
            self.logger.error("keyboard library missing! Cannot start reactive.")
            return
        
        self.reactive_active = True
        self.reactive_mode = mode
        self.react_color = color_obj
        self.react_rainbow = is_rainbow
        
        with self.react_lock:
            self.col_state = {col: False for col in self.column_indices}
            self.col_timers = {col: 0 for col in self.column_indices}
        
        if mode == "Anti-Reactive":
            self.set_all_leds_color(color_obj if not is_rainbow else InternalColor(255,255,255))
        else:
            self.clear_all_leds()
            
        def on_key(e):
            if e.event_type == keyboard.KEY_DOWN:
                col = self._get_col_for_key(e.name)
                with self.react_lock:
                    self.col_timers[col] = time.time() + 0.35 
        
        self._kb_hook = keyboard.hook(on_key)
        self.react_thread = threading.Thread(target=self._reactive_engine_loop, daemon=True)
        self.react_thread.start()
        self.logger.info(f"Total-Matrix Engine Started: {mode}")

    def _reactive_engine_loop(self):
        while self.reactive_active:
            time.sleep(0.01)
            now = time.time()
            board_needs_update = False
            
            with self.react_lock:
                for col in self.column_indices:
                    is_active = now < self.col_timers[col]
                    if is_active != self.col_state[col]:
                        self.col_state[col] = is_active
                        board_needs_update = True
                        
            # If ANY key changed state, broadcast the exact map to ALL 11 columns
            if board_needs_update:
                for col in self.column_indices:
                    if not self.reactive_active: break
                    is_active = self.col_state[col]
                    
                    c = self.react_color
                    if self.react_rainbow:
                        rgb = colorsys.hsv_to_rgb((now * 0.5 + col*0.05) % 1.0, 1.0, 1.0)
                        c = InternalColor(int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255))
                    
                    if self.reactive_mode == "Reactive":
                        target_hex = f"0x{c.to_hex().lstrip('#')}" if is_active else "0x000000"
                    else:
                        target_hex = "0x000000" if is_active else f"0x{c.to_hex().lstrip('#')}"
                        
                    self._run_ectool_cmd(['rgbkbd', str(col), target_hex])

    def get_hardware_info(self): return {"Status": "Total-Matrix Reactive Active"}
    def get_brightness(self): return None
    def log_capabilities(self): self.logger.info("Osiris Total-Matrix Reactive: Ready")
