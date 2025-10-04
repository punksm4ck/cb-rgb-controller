#!/usr/bin/env python3
"""Enhanced RGB Keyboard Controller GUI with universal controls and rainbow effects - Combined Best Features"""

import tkinter as tk
from tkinter import ttk, colorchooser, messagebox, scrolledtext, filedialog
import logging
import logging.handlers
import threading
import time
import colorsys
import math
import random
import json
import os
import sys
import platform
import subprocess
from typing import List, Dict, Any, Callable, Tuple, Optional
from pathlib import Path
from datetime import datetime
from functools import partial
import queue
import io

# For system tray functionality
PYSTRAY_AVAILABLE = False
PIL_AVAILABLE = False

try:
    import pystray
    PYSTRAY_AVAILABLE = True
    try:
        from PIL import Image, ImageDraw
        PIL_AVAILABLE = True
    except ImportError:
        print("WARNING: PIL (Pillow) not found. System tray icon will be very basic or might fail. Install with 'pip install Pillow'.", file=sys.stderr)
except ImportError:
    print("WARNING: pystray not found. System tray functionality will be disabled. Install with 'pip install pystray'.", file=sys.stderr)

# For global keyboard hotkeys
KEYBOARD_LIB_AVAILABLE = False
try:
    import keyboard
    KEYBOARD_LIB_AVAILABLE = True
except ImportError:
    print("WARNING: 'keyboard' library not found. ALT+Brightness hotkeys will be disabled. Install with 'pip install keyboard'. Note: May require root/admin privileges to run.", file=sys.stderr)

# Import core modules
from .core.rgb_color import RGBColor
from .core.settings import SettingsManager
from .core.constants import (
    NUM_ZONES, LEDS_PER_ZONE, TOTAL_LEDS,
    PREVIEW_WIDTH, PREVIEW_HEIGHT, PREVIEW_LED_SIZE,
    PREVIEW_LED_SPACING, PREVIEW_KEYBOARD_COLOR,
    ANIMATION_FRAME_DELAY, APP_NAME, VERSION,
    REACTIVE_DELAY, default_settings, SETTINGS_FILE,
    HARDWARE_DETECTION_TIMEOUT
)
from .core.exceptions import HardwareError, ConfigurationError
from .hardware.controller import HardwareController
from .effects.manager import EffectManager
from .utils.system_info import log_system_info, log_error_with_context


class RGBControllerGUI:
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

        # Enhanced hotkey setup with ALT+BRIGHTNESS priority
        if KEYBOARD_LIB_AVAILABLE:
            self.setup_global_hotkeys_enhanced()
        else:
            self.log_missing_keyboard_library()

        self.root.after(100, self.initialize_hardware_async)
        self.load_saved_settings()
        self.root.after(500, self.apply_startup_settings_if_enabled_async)
        self.setup_gui_logging()
        self.logger.info(f"{APP_NAME} v{VERSION} GUI Initialized and ready.")

    def _initialize_core_components(self):
        """Separated initialization for better error handling"""
        self.settings = SettingsManager()
        self.hardware = HardwareController()
        self.effect_manager = EffectManager(self.hardware)
    
    def _handle_critical_initialization_error(self, error):
        """Handle critical initialization failures gracefully"""
        self.logger.critical(f"Fatal error initializing core components: {error}", exc_info=True)
        error_msg = f"Could not initialize core components: {error}\n\nPlease check:\n• Hardware permissions\n• Required dependencies\n• System compatibility\n\nApplication will exit."
        
        try:
            if self.root and self.root.winfo_exists():
                messagebox.showerror("Initialization Error", error_msg)
        except tk.TclError:
            print(f"FATAL ERROR: {error_msg}", file=sys.stderr)
        
        if self.root:
            try: 
                self.root.destroy()
            except: 
                pass
        sys.exit(1)

    def log_missing_keyboard_library(self):
        """Provide detailed instructions for installing keyboard library"""
        missing_msg = """
KEYBOARD HOTKEYS DISABLED - Missing Dependencies:

The 'keyboard' library is required for ALT+Brightness hotkey functionality.

INSTALLATION INSTRUCTIONS:
=========================

1. Install the keyboard library:
   pip install keyboard

2. IMPORTANT - PERMISSIONS REQUIRED:
   • Linux: Run application with sudo for global hotkeys
     sudo python -m rgb_controller_finalv2
   • Windows: Run as Administrator
   • macOS: Grant Accessibility permissions in System Preferences

3. Alternative installation methods:
   • conda install -c conda-forge keyboard
   • pip3 install keyboard (if pip points to Python 2)

4. Troubleshooting:
   • If installation fails, try: pip install --user keyboard
   • On Ubuntu/Debian: sudo apt install python3-dev first
   • On CentOS/RHEL: sudo yum install python3-devel first

5. After installation, restart the application

Note: Global hotkeys require elevated privileges to capture system-wide key events.
This is a security feature of operating systems.
        """
        self.logger.warning("Keyboard library not available. ALT+Brightness hotkeys disabled.")
        self.log_to_gui_diag_area(missing_msg.strip(), "warning")
        print(missing_msg, file=sys.stderr)

    def _stop_all_visuals_and_clear_hardware(self):
        """Stops software effects and attempts to clear hardware patterns."""
        self.logger.debug("Stopping all software effects and GUI previews.")
        if hasattr(self, 'effect_manager') and self.effect_manager:
            self.effect_manager.stop_current_effect()

        self.stop_preview_animation()

        if hasattr(self, 'hardware') and self.hardware and self.hardware.is_operational():
            self.logger.debug("Attempting to clear hardware effects/LEDs.")
            if hasattr(self.hardware, 'attempt_stop_hardware_effects'):
                self.hardware.attempt_stop_hardware_effects()
            else:
                self.logger.warning("hardware.attempt_stop_hardware_effects not found, falling back to clear_all_leds.")
                self.hardware.clear_all_leds()

        self.preview_led_states = [RGBColor(0,0,0)] * TOTAL_LEDS
        self.update_preview_leds()
        self.logger.debug("All visuals stopped and hardware clear attempted.")

    def _update_brightness_text_display(self, *args):
        if hasattr(self, 'brightness_text_var') and self.brightness_text_var:
            try:
                current_val = self.brightness_var.get()
                if hasattr(self, 'brightness_label') and self.brightness_label.winfo_exists():
                    self.brightness_label.config(text=f"{current_val}%")
                self.brightness_text_var.set(f"{current_val}%")
            except tk.TclError: 
                self.logger.debug("TclError in _update_brightness_text_display.")
            except Exception as e: 
                self.logger.warning(f"Error updating brightness text display: {e}")

    def setup_logging(self) -> logging.Logger:
        logger = logging.getLogger(f"{APP_NAME}.GUI")
        if logger.hasHandlers() and any(isinstance(h, logging.FileHandler) for h in logger.handlers): 
            return logger
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s')
        if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
            ch = logging.StreamHandler(sys.stdout)
            ch.setLevel(logging.INFO)
            ch.setFormatter(formatter)
            logger.addHandler(ch)
        try:
            log_base_dir = SETTINGS_FILE.parent
            log_dir = log_base_dir / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / f"rgb_controller_gui_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            fh = logging.handlers.RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(formatter)
            logger.addHandler(fh)
            logger.info(f"GUI logging to file: {log_file}")
        except Exception as e:
            logger.error(f"Failed to set up GUI file logging: {e}", exc_info=True)
            try:
                fallback_log = Path.home() / f".{APP_NAME.lower().replace(' ','_')}_gui_fallback.log"
                fh_fallback = logging.FileHandler(fallback_log, encoding='utf-8')
                fh_fallback.setLevel(logging.DEBUG)
                fh_fallback.setFormatter(formatter)
                logger.addHandler(fh_fallback)
                logger.warning(f"Using fallback log file due to error: {fallback_log}")
            except Exception as fb_e: 
                logger.error(f"Failed to set up fallback file logging: {fb_e}")
        return logger

    def setup_variables(self):
        self.brightness_var = tk.IntVar(value=self.settings.get("brightness", default_settings["brightness"]))
        self.brightness_text_var = tk.StringVar(value=f"{self.brightness_var.get()}%")
        self.brightness_var.trace_add("write", self._update_brightness_text_display)
        effect_speed_setting = self.settings.get("effect_speed", default_settings["effect_speed"])
        self.speed_var = tk.IntVar(value=effect_speed_setting * 10)
        current_color_dict = self.settings.get("current_color", default_settings["current_color"])
        self.current_color_var = tk.StringVar(value=RGBColor.from_dict(current_color_dict).to_hex())
        self.effect_var = tk.StringVar(value=self.settings.get("effect_name", default_settings["effect_name"]))
        self.status_var = tk.StringVar(value="Initializing...")
        self.effect_color_var = tk.StringVar(value=self.settings.get("effect_color", default_settings["effect_color"]))
        self.effect_rainbow_mode_var = tk.BooleanVar(value=self.settings.get("effect_rainbow_mode", default_settings["effect_rainbow_mode"]))
        self.gradient_start_color_var = tk.StringVar(value=self.settings.get("gradient_start_color", default_settings["gradient_start_color"]))
        self.gradient_end_color_var = tk.StringVar(value=self.settings.get("gradient_end_color", default_settings["gradient_end_color"]))
        self.restore_startup_var = tk.BooleanVar(value=self.settings.get("restore_on_startup", default_settings["restore_on_startup"]))
        self.auto_apply_var = tk.BooleanVar(value=self.settings.get("auto_apply_last_setting", default_settings["auto_apply_last_setting"]))
        self.control_method_var = tk.StringVar(value=self.settings.get("last_control_method", default_settings["last_control_method"]))
        self.minimize_to_tray_var = tk.BooleanVar(value=self.settings.get("minimize_to_tray", True))

    def _try_load_icon_from_file(self):
        if self.tk_icon_photoimage: 
            return
        try:
            script_dir = Path(__file__).resolve().parent
            icon_path_candidate1 = script_dir / "assets" / "icon.png"
            icon_path_candidate2 = script_dir.parent / "assets" / "icon.png" # Check one level up if assets is sibling to gui dir
            icon_path_candidate3 = Path(sys.prefix) / "share" / APP_NAME.lower().replace(" ", "_") / "icon.png" # For installed case

            final_icon_path = None
            if icon_path_candidate1.exists(): 
                final_icon_path = icon_path_candidate1
            elif icon_path_candidate2.exists(): 
                final_icon_path = icon_path_candidate2
            elif icon_path_candidate3.exists(): 
                final_icon_path = icon_path_candidate3

            if final_icon_path:
                self.tk_icon_photoimage = tk.PhotoImage(file=str(final_icon_path))
                self.root.iconphoto(True, self.tk_icon_photoimage)
                self.logger.info(f"Set Tkinter window icon from file: {final_icon_path}")
                if PYSTRAY_AVAILABLE and PIL_AVAILABLE and self.pystray_icon_image is None:
                    try:
                        self.pystray_icon_image = Image.open(final_icon_path)
                        self.logger.info(f"Loaded PIL Image for pystray from file: {final_icon_path}")
                    except Exception as e_pil_load:
                        self.logger.warning(f"Could not load PIL Image for pystray from file {final_icon_path}: {e_pil_load}")
            else: 
                self.logger.warning(f"No icon.png found at expected paths for file loading: {icon_path_candidate1}, {icon_path_candidate2}, {icon_path_candidate3}")
        except Exception as e_file_icon:
            self.logger.warning(f"Could not load Tkinter window icon from file: {e_file_icon}")

    def setup_main_window(self):
        self.root.title(f"{APP_NAME} v{VERSION}")
        self.root.geometry("1000x750")
        self.root.minsize(900, 700)

        # Enhanced icon setup with better error handling
        self.setup_application_icons()

        self.style = ttk.Style(self.root)
        try:
            themes = self.style.theme_names()
            desired_themes = ['clam', 'alt', 'default'] # Some common good-looking themes
            for t in desired_themes:
                if t in themes: 
                    self.style.theme_use(t)
                    break
            else: 
                self.logger.info(f"Using system default theme: {self.style.theme_use()}")
        except tk.TclError: 
            self.logger.warning("Failed to set ttk theme.")
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TLabelframe', background='#f0f0f0', padding=5)
        self.style.configure('TLabelframe.Label', background='#f0f0f0', font=('Helvetica', 10, 'bold'))
        self.style.configure('TLabel', background='#f0f0f0', padding=2)
        self.style.configure('TButton', padding=5)
        self.style.configure('Accent.TButton', font=('Helvetica', 10, 'bold'), relief=tk.RAISED)
        self.style.map('Accent.TButton', background=[('active', '#e0e0e0'), ('pressed', '#cccccc')])

    def setup_application_icons(self):
        """Enhanced icon setup with better error handling and fallbacks"""
        icon_created = False
        
        if PYSTRAY_AVAILABLE and PIL_AVAILABLE:
            try:
                icon_size = 64
                temp_pil_image = Image.new('RGBA', (icon_size, icon_size), (0, 0, 0, 0))
                draw = ImageDraw.Draw(temp_pil_image)
                # Create a more appealing RGB icon
                draw.rectangle((0, 0, icon_size//2, icon_size//2), fill="#FF4444")      # Red
                draw.rectangle((icon_size//2, 0, icon_size, icon_size//2), fill="#44FF44")  # Green
                draw.rectangle((0, icon_size//2, icon_size//2, icon_size), fill="#4444FF")  # Blue
                draw.rectangle((icon_size//2, icon_size//2, icon_size, icon_size), fill="#FF44FF")  # Magenta
                
                # Add a border
                draw.rectangle((0, 0, icon_size, icon_size), outline="#FFFFFF", width=2)
                
                self.pystray_icon_image = temp_pil_image
                self.logger.debug("Created default PIL image for pystray icon.")
                
                try:
                    # For Tkinter, use a smaller size
                    img_buffer = io.BytesIO()
                    temp_pil_image.resize((32, 32)).save(img_buffer, format='PNG')
                    img_buffer.seek(0)
                    self.tk_icon_photoimage = tk.PhotoImage(data=img_buffer.getvalue())
                    self.root.iconphoto(True, self.tk_icon_photoimage)
                    self.logger.info("Set Tkinter window icon using generated PIL image.")
                    icon_created = True
                except Exception as tk_icon_e:
                    self.logger.warning(f"Could not convert/set Tkinter window icon from PIL image: {tk_icon_e}.")
            except Exception as e_pil:
                self.logger.warning(f"Could not create icon image using PIL: {e_pil}.")
                self.pystray_icon_image = None

        if not icon_created:
            self._try_load_icon_from_file()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=5)
        main_frame.pack(fill=tk.BOTH, expand=True)
        common_controls_frame = self.create_common_controls(main_frame)
        common_controls_frame.pack(fill=tk.X, pady=(0,5), padx=5)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.create_tabs()
        self.create_status_bar()

    def setup_bindings(self):
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Escape>", self.exit_fullscreen)
        self.root.protocol("WM_DELETE_WINDOW", self.handle_close_button_press)
        self.root.bind("<Unmap>", self.on_minimize_event)

    def create_common_controls(self, parent: ttk.Frame) -> ttk.Frame:
        controls_frame = ttk.LabelFrame(parent, text="Universal Controls", padding=10)
        controls_frame.pack(fill=tk.X, pady=5)
        bf = ttk.Frame(controls_frame)
        bf.pack(fill=tk.X, pady=5)
        ttk.Label(bf, text="Brightness:").pack(side=tk.LEFT, padx=(0,5))
        bs = ttk.Scale(bf, from_=0, to=100, variable=self.brightness_var, orient=tk.HORIZONTAL, command=self.on_brightness_change)
        bs.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        self.brightness_label = ttk.Label(bf, textvariable=self.brightness_text_var, width=5)
        self.brightness_label.pack(side=tk.LEFT)
        
        # Add hotkey status indicator
        hotkey_frame = ttk.Frame(controls_frame)
        hotkey_frame.pack(fill=tk.X, pady=2)
        self.hotkey_status_label = ttk.Label(hotkey_frame, text="Hotkeys: Checking...", font=('Helvetica', 8))
        self.hotkey_status_label.pack(side=tk.LEFT)
        
        sf = ttk.Frame(controls_frame)
        sf.pack(fill=tk.X, pady=5)
        ttk.Label(sf, text="Effect Speed (1-100):").pack(side=tk.LEFT, padx=(0,5))
        ss = ttk.Scale(sf, from_=1, to=100, variable=self.speed_var, orient=tk.HORIZONTAL, command=self.on_speed_change)
        ss.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        self.speed_label = ttk.Label(sf, text=f"{self.speed_var.get()}%", width=5)
        self.speed_var.trace_add("write", lambda *args: self.speed_label.config(text=f"{self.speed_var.get()}%") if hasattr(self, 'speed_label') and self.speed_label.winfo_exists() else None)
        self.speed_label.pack(side=tk.LEFT)
        btn_f = ttk.Frame(controls_frame)
        btn_f.pack(fill=tk.X, pady=10)
        ttk.Button(btn_f, text="All White", command=lambda: self.apply_static_color("#ffffff")).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_f, text="All Off (Clear)", command=self.clear_all_zones_and_effects).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_f, text="Stop Current Effect", command=self.stop_current_effect, style="Accent.TButton").pack(side=tk.LEFT, padx=2)
        return controls_frame

    def _create_tab_content_frame(self, tab_parent: ttk.Frame) -> ttk.Frame:
        outer_frame = ttk.Frame(tab_parent)
        outer_frame.pack(fill=tk.BOTH, expand=True)
        bg_color = self.style.lookup('TFrame', 'background')
        canvas = tk.Canvas(outer_frame, highlightthickness=0, borderwidth=0, background=bg_color)
        scrollbar = ttk.Scrollbar(outer_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, padding=10)
        scrollable_frame.bind("<Configure>", lambda e, c=canvas: c.configure(scrollregion=c.bbox("all")))
        canvas.item_frame_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.bind("<Configure>", lambda e, c=canvas: c.itemconfig(c.item_frame_id, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        def _on_mousewheel(event, c=canvas):
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
                c.yview_scroll(delta, "units")
        
        for widget in [canvas, scrollable_frame]: # Bind to both canvas and inner frame
            widget.bind_all("<MouseWheel>", _on_mousewheel) # Use bind_all for wider capture if needed, or stick to bind
            widget.bind("<Button-4>", _on_mousewheel) # For Linux scroll up
            widget.bind("<Button-5>", _on_mousewheel) # For Linux scroll down
        return scrollable_frame

    def create_tabs(self):
        static_tab = ttk.Frame(self.notebook)
        self.notebook.add(static_tab, text="Static Color")
        self.create_static_controls(self._create_tab_content_frame(static_tab))
        zone_tab = ttk.Frame(self.notebook)
        self.notebook.add(zone_tab, text="Zone Control")
        self.create_zone_controls(self._create_tab_content_frame(zone_tab))
        effects_tab = ttk.Frame(self.notebook)
        self.notebook.add(effects_tab, text="Effects")
        self.create_effects_controls(self._create_tab_content_frame(effects_tab))
        settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(settings_tab, text="Settings")
        self.create_settings_controls(self._create_tab_content_frame(settings_tab))
        diag_tab = ttk.Frame(self.notebook)
        self.notebook.add(diag_tab, text="Diagnostics")
        self.create_diagnostics_tab(self._create_tab_content_frame(diag_tab))

    def create_static_controls(self, parent: ttk.Frame):
        color_frame = ttk.LabelFrame(parent, text="Color Selection", padding=10)
        color_frame.pack(fill=tk.X, padx=5, pady=5, expand=True)
        self.color_display = tk.Label(color_frame, width=10, height=2, bg=self.current_color_var.get(), relief=tk.SUNKEN, borderwidth=2)
        self.color_display.pack(side=tk.LEFT, padx=10, pady=5)
        ttk.Button(color_frame, text="Choose Color", command=self.open_color_picker).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(color_frame, text="Apply to All Zones", command=lambda: self.apply_static_color(self.current_color_var.get()), style="Accent.TButton").pack(side=tk.LEFT, padx=5, pady=5)
        preset_frame = ttk.LabelFrame(parent, text="Preset Colors", padding=10)
        preset_frame.pack(fill=tk.X, padx=5, pady=5, expand=True)
        presets = [("Red","#ff0000"),("Green","#00ff00"),("Blue","#0000ff"),("Yellow","#ffff00"),("Cyan","#00ffff"),("Magenta","#ff00ff"),("Orange","#ff8800"),("Purple","#800080"),("Pink","#ff88ff")]
        preset_grid = ttk.Frame(preset_frame)
        preset_grid.pack(pady=5)
        for i, (name, color_hex) in enumerate(presets):
            btn = tk.Button(preset_grid, text=name, bg=color_hex, width=8, relief=tk.RAISED, borderwidth=2, command=partial(self.apply_static_color, color_hex))
            btn.grid(row=i//3, column=i%3, padx=3, pady=3, sticky="ew")
        self.create_preview_canvas(parent, "Static Color Preview")

    def create_zone_controls(self, parent: ttk.Frame):
        zones_frame = ttk.LabelFrame(parent, text="Individual Zone Colors", padding=10)
        zones_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.zone_displays: List[tk.Label] = []
        for i in range(NUM_ZONES):
            zf = ttk.Frame(zones_frame, padding=(0,2))
            zf.pack(fill=tk.X)
            ttk.Label(zf, text=f"Zone {i+1}:").pack(side=tk.LEFT, padx=(0,5))
            initial_zc_obj = self.zone_colors[i] if i < len(self.zone_colors) else RGBColor(0,0,0)
            zd = tk.Label(zf, width=8, height=1, bg=initial_zc_obj.to_hex(), relief=tk.SUNKEN, borderwidth=2)
            zd.pack(side=tk.LEFT, padx=5)
            self.zone_displays.append(zd)
            ttk.Button(zf, text="Set Color", command=partial(self.set_zone_color_interactive, i)).pack(side=tk.LEFT, padx=5)
        action_frame = ttk.Frame(zones_frame, padding=(0,10))
        action_frame.pack(fill=tk.X, pady=(5,0))
        ttk.Button(action_frame, text="Apply Zone Colors to HW", command=self.apply_current_zone_colors_to_hardware, style="Accent.TButton").pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="Rainbow Across Zones", command=self.apply_rainbow_zones).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="Gradient Across Zones", command=self.apply_gradient_zones).pack(side=tk.LEFT, padx=2)
        gradient_ctrl_frame = ttk.Frame(zones_frame, padding=(0,5))
        gradient_ctrl_frame.pack(fill=tk.X, pady=10)
        ttk.Label(gradient_ctrl_frame, text="Gradient Start:").pack(side=tk.LEFT)
        self.gradient_start_display = tk.Label(gradient_ctrl_frame, width=8, height=1, bg=self.gradient_start_color_var.get(), relief=tk.SUNKEN, borderwidth=2)
        self.gradient_start_display.pack(side=tk.LEFT, padx=5)
        ttk.Button(gradient_ctrl_frame, text="...", width=3, command=self.choose_gradient_start).pack(side=tk.LEFT)
        ttk.Label(gradient_ctrl_frame, text="Gradient End:").pack(side=tk.LEFT, padx=(10,5))
        self.gradient_end_display = tk.Label(gradient_ctrl_frame, width=8, height=1, bg=self.gradient_end_color_var.get(), relief=tk.SUNKEN, borderwidth=2)
        self.gradient_end_display.pack(side=tk.LEFT, padx=5)
        ttk.Button(gradient_ctrl_frame, text="...", width=3, command=self.choose_gradient_end).pack(side=tk.LEFT)
        self.create_preview_canvas(parent, "Zone Preview")

    def create_effects_controls(self, parent: ttk.Frame):
        effect_frame = ttk.LabelFrame(parent, text="Effect Selection", padding=10)
        effect_frame.pack(fill=tk.X, padx=5, pady=5, expand=True)
        ttk.Label(effect_frame, text="Effect:").pack(side=tk.LEFT, padx=(0,10))

        all_effects = self.effect_manager.get_available_effects()
        effects_to_remove = {"Rainbow Wave", "Rainbow Breathing"} # Example: if these are handled by rainbow mode toggle now
        filtered_effects = [effect for effect in all_effects if effect not in effects_to_remove]
        available_effects = ["None"] + filtered_effects # Ensure "None" is an option

        effect_combo = ttk.Combobox(effect_frame, textvariable=self.effect_var, values=available_effects, state="readonly", width=25)
        effect_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        effect_combo.bind("<<ComboboxSelected>>", self.on_effect_change)
        ttk.Button(effect_frame, text="Start Effect", command=self.start_current_effect, style="Accent.TButton").pack(side=tk.LEFT, padx=5)

        color_frame = ttk.LabelFrame(parent, text="Effect Color Options", padding=10)
        color_frame.pack(fill=tk.X, padx=5, pady=5, expand=True)
        self.effect_color_rainbow_frame = ttk.Frame(color_frame) # Container for both check and color picker

        self.rainbow_mode_check = ttk.Checkbutton(self.effect_color_rainbow_frame, text="Use Rainbow Mode for Effect", variable=self.effect_rainbow_mode_var, command=self.on_rainbow_mode_change)
        # self.rainbow_mode_check.pack(side=tk.LEFT, padx=(0,10)) # Packing handled by update_effect_controls_visibility

        self.effect_color_frame = ttk.Frame(self.effect_color_rainbow_frame) # Specific frame for color picker parts
        self.effect_color_display = tk.Label(self.effect_color_frame, width=10, height=2, bg=self.effect_color_var.get(), relief=tk.SUNKEN, borderwidth=2)
        self.effect_color_display.pack(side=tk.LEFT, padx=10, pady=5)
        ttk.Button(self.effect_color_frame, text="Choose Effect Color", command=self.choose_effect_color).pack(side=tk.LEFT, padx=5, pady=5)
        # self.effect_color_frame.pack(side=tk.LEFT, fill=tk.X, expand=True) # Packing handled by update_effect_controls_visibility

        self.update_effect_controls_visibility() # Initial setup of visibility
        self.create_preview_canvas(parent, "Effect Preview")

    def create_settings_controls(self, parent: ttk.Frame):
        frame = ttk.LabelFrame(parent, text="Application Settings", padding=10)
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        persist_lf = ttk.LabelFrame(frame, text="Persistence", padding="10")
        persist_lf.pack(fill=tk.X, pady=(5, 10), anchor="n")
        ttk.Checkbutton(persist_lf, text="Restore settings on startup", variable=self.restore_startup_var, command=self.save_persistence_settings).pack(anchor=tk.W, padx=5)
        ttk.Checkbutton(persist_lf, text="Auto-apply last setting on startup (if restore is enabled)", variable=self.auto_apply_var, command=self.save_persistence_settings).pack(anchor=tk.W, padx=5)

        method_lf = ttk.LabelFrame(frame, text="Hardware Control Method Preference", padding="10")
        method_lf.pack(fill=tk.X, pady=(0, 10), anchor="n")
        ttk.Radiobutton(method_lf, text="ectool (Recommended if available)", variable=self.control_method_var, value="ectool", command=self.save_control_method).pack(anchor=tk.W, padx=5)
        ttk.Radiobutton(method_lf, text="EC Direct (Advanced)", variable=self.control_method_var, value="ec_direct", command=self.save_control_method, state=tk.NORMAL).pack(anchor=tk.W, padx=5) # Enabled

        display_lf = ttk.LabelFrame(frame, text="Display Options", padding="10")
        display_lf.pack(fill=tk.X, pady=(0, 10), anchor="n")
        self.fullscreen_button = ttk.Button(display_lf, text="Enter Fullscreen (F11)", command=self.toggle_fullscreen)
        self.fullscreen_button.pack(anchor=tk.W, pady=2, padx=5)
        ttk.Label(display_lf, text="Press ESC to exit fullscreen.", font=('Helvetica', 9, 'italic')).pack(anchor=tk.W, padx=5)

        # Enhanced tray settings with dependency info
        self.create_tray_settings_section(frame)

        mgmt_lf = ttk.LabelFrame(frame, text="Settings Management", padding="10")
        mgmt_lf.pack(fill=tk.X, pady=(0, 10), anchor="n")
        mgmt_btns_frm = ttk.Frame(mgmt_lf)
        mgmt_btns_frm.pack(fill=tk.X, pady=5)
        ttk.Button(mgmt_btns_frm, text="Reset Defaults", command=self.reset_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(mgmt_btns_frm, text="Export Settings", command=self.export_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(mgmt_btns_frm, text="Import Settings", command=self.import_settings).pack(side=tk.LEFT, padx=5)

        launcher_lf = ttk.LabelFrame(frame, text="Desktop Integration (Linux)", padding="10")
        launcher_lf.pack(fill=tk.X, anchor="n")
        ttk.Button(launcher_lf, text="Create/Update Desktop Launcher", command=self.create_desktop_launcher).pack(anchor=tk.W, padx=5, pady=5)

    def create_tray_settings_section(self, parent):
        """Enhanced tray settings with dependency information"""
        if PYSTRAY_AVAILABLE:
            tray_lf = ttk.LabelFrame(parent, text="System Tray Options", padding="10")
            tray_lf.pack(fill=tk.X, pady=(0, 10), anchor="n")
            
            # Status indicator
            status_frame = ttk.Frame(tray_lf)
            status_frame.pack(fill=tk.X, pady=2)
            
            status_text = "✓ System tray available"
            if not PIL_AVAILABLE:
                status_text += " (Icons will be basic - install Pillow for better icons)"
            
            ttk.Label(status_frame, text=status_text, font=('Helvetica', 9), foreground='green').pack(anchor=tk.W)
            
            if not hasattr(self, 'minimize_to_tray_var'):
                self.minimize_to_tray_var = tk.BooleanVar(value=self.settings.get("minimize_to_tray", True))
            ttk.Checkbutton(tray_lf, text="Minimize to system tray when closing/minimizing",
                           variable=self.minimize_to_tray_var, command=self.save_tray_settings).pack(anchor=tk.W, padx=5)
            ttk.Label(tray_lf, text="When enabled, clicking 'X' or Minimize will send to tray.",
                     font=('Helvetica', 9, 'italic')).pack(anchor=tk.W, padx=5)
            ttk.Label(tray_lf, text="Use 'Quit' from tray menu to exit completely.",
                     font=('Helvetica', 9, 'italic')).pack(anchor=tk.W, padx=5)
        else:
            # Detailed instructions for missing dependencies
            no_tray_lf = ttk.LabelFrame(parent, text="System Tray Options", padding="10")
            no_tray_lf.pack(fill=tk.X, pady=(0,10), anchor="n")
            
            ttk.Label(no_tray_lf, text="⚠ System tray functionality is unavailable",
                     font=('Helvetica', 9, 'bold'), foreground='orange').pack(anchor=tk.W, padx=5)
            
            install_text = """To enable system tray functionality:

1. Install required packages:
   pip install pystray Pillow

2. Restart the application

3. Alternative installation:
   • conda install -c conda-forge pystray pillow
   • On Ubuntu: sudo apt install python3-pil

Note: Some systems may require additional notification packages"""
            
            ttk.Label(no_tray_lf, text=install_text, font=('Helvetica', 8),
                     justify=tk.LEFT, wraplength=500).pack(anchor=tk.W, padx=5, pady=5)

    def create_diagnostics_tab(self, parent: ttk.Frame):
        diag_pane = ttk.PanedWindow(parent, orient=tk.VERTICAL)
        diag_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        hw_frame = ttk.LabelFrame(diag_pane, text="Hardware Status & Capabilities", padding=10)
        diag_pane.add(hw_frame, weight=1)
        self.hardware_status_text = scrolledtext.ScrolledText(hw_frame, height=8, state=tk.DISABLED, relief=tk.SUNKEN, borderwidth=1, wrap=tk.WORD, font=("monospace", 9))
        self.hardware_status_text.pack(fill=tk.BOTH, expand=True, pady=(0,5))
        ttk.Button(hw_frame, text="Refresh Hardware Status", command=self.refresh_hardware_status).pack(pady=5)

        sys_log_frame = ttk.LabelFrame(diag_pane, text="System Information & Application Log", padding=10)
        diag_pane.add(sys_log_frame, weight=2)
        log_notebook = ttk.Notebook(sys_log_frame)
        log_notebook.pack(fill=tk.BOTH, expand=True, pady=5)

        sys_info_tab = ttk.Frame(log_notebook)
        log_notebook.add(sys_info_tab, text="System Details")
        self.system_info_display_text = scrolledtext.ScrolledText(sys_info_tab, height=10, state=tk.DISABLED, relief=tk.SUNKEN, borderwidth=1, wrap=tk.WORD, font=("monospace", 9))
        self.system_info_display_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        sys_info_btn_frame = ttk.Frame(sys_info_tab)
        sys_info_btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(sys_info_btn_frame, text="Refresh System Info", command=self.show_system_info).pack(side=tk.LEFT, padx=5)

        app_log_tab = ttk.Frame(log_notebook)
        log_notebook.add(app_log_tab, text="Application Log")
        self.gui_log_text_widget = scrolledtext.ScrolledText(app_log_tab, height=10, state=tk.DISABLED, relief=tk.SUNKEN, borderwidth=1, wrap=tk.WORD, font=("monospace", 9))
        self.gui_log_text_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        log_actions_frame = ttk.Frame(app_log_tab)
        log_actions_frame.pack(fill=tk.X, pady=5)
        ttk.Button(log_actions_frame, text="Open Log Directory", command=self.show_log_locations).pack(side=tk.LEFT, padx=5)
        if KEYBOARD_LIB_AVAILABLE: # Add button to test hotkey names
            ttk.Button(log_actions_frame, text="Test Keyboard Hotkey Names", command=self.test_hotkey_names_util).pack(side=tk.LEFT, padx=5)

        test_frame = ttk.LabelFrame(diag_pane, text="Hardware Tests (Use with Caution)", padding=10)
        diag_pane.add(test_frame, weight=0) # test_frame has less weight
        ttk.Button(test_frame, text="Run Basic Test Cycle", command=self.run_comprehensive_test).pack(side=tk.LEFT, padx=5, pady=2)
        ttk.Button(test_frame, text="Test ectool Version", command=self.test_ectool).pack(side=tk.LEFT, padx=5, pady=2)

    def create_status_bar(self):
        status_frame = ttk.Frame(self.root, relief=tk.SUNKEN, padding=2)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.connection_label = ttk.Label(status_frame, text="HW: Unknown", relief=tk.FLAT, width=15, anchor=tk.E)
        self.connection_label.pack(side=tk.RIGHT, padx=2)

    def create_preview_canvas(self, parent: ttk.Frame, title: str) -> ttk.Frame:
        preview_frame = ttk.LabelFrame(parent, text=title, padding=10)
        preview_frame.pack(fill=tk.X, expand=False, padx=5, pady=10)
        canvas_container = ttk.Frame(preview_frame)
        canvas_container.pack(pady=5)

        # Compact rectangular keyboard dimensions - much narrower background
        canvas_width = 480  # Reduced from 900 to ~half width
        canvas_height = 140  # Slightly reduced height for perfect fit
        current_canvas = tk.Canvas(canvas_container, width=canvas_width, height=canvas_height, bg='#1a1a1a', relief=tk.GROOVE, borderwidth=2)
        current_canvas.pack()

        if title == "Effect Preview": # This is the primary canvas for dynamic effect previews
            self.preview_canvas = current_canvas
            self.preview_keyboard_elements = []
            self.create_realistic_keyboard_layout()
        elif title == "Static Color Preview":
            self.static_preview_canvas = current_canvas
            self.static_keyboard_elements = []
            self.create_realistic_keyboard_layout(canvas=current_canvas, elements_list='static_keyboard_elements')
        elif title == "Zone Preview":
            self.zone_preview_canvas = current_canvas
            self.zone_keyboard_elements = []
            self.create_realistic_keyboard_layout(canvas=current_canvas, elements_list='zone_keyboard_elements')

        return preview_frame

    def create_realistic_keyboard_layout(self, canvas=None, elements_list='preview_keyboard_elements'):
        """Create perfect rectangular keyboard layout with equal-width rows"""
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
        
        # Perfect rectangular dimensions
        canvas_width = 480
        canvas_height = 140
        
        # Calculate perfect rectangular keyboard area
        margin_x = 20
        margin_y = 12
        keyboard_width = canvas_width - (margin_x * 2)  # 440px total keyboard width
        keyboard_height = 90  # Fixed height for 6 rows
        
        # Standard dimensions for perfect rectangle
        row_height = 14
        row_gap = 1
        key_gap = 1
        
        # Each row will be exactly keyboard_width pixels wide
        # Calculate unit width based on the most complex row (bottom row has most logical units)
        total_units_per_row = 15  # Standardized unit count for perfect rectangle
        unit_width = (keyboard_width - (total_units_per_row - 1) * key_gap) / total_units_per_row
        
        start_x = margin_x
        start_y = margin_y
        
        # Left-to-right zone assignment
        zone_width = keyboard_width / NUM_ZONES
        
        # Define perfect rectangular keyboard layout - all rows same width
        keyboard_layout = [
            # Row 1: Function keys - 15 equal units
            {
                'y': start_y,
                'keys': [
                    {'units': 1} for _ in range(15)  # 15 equal F-keys across full width
                ]
            },
            # Row 2: Number row - 15 units total
            {
                'y': start_y + (row_height + row_gap) * 1,
                'keys': [
                    *[{'units': 1} for _ in range(13)],  # 13 regular keys
                    {'units': 2}  # Backspace takes 2 units
                ]
            },
            # Row 3: QWERTY row - 15 units total  
            {
                'y': start_y + (row_height + row_gap) * 2,
                'keys': [
                    {'units': 1.5},  # Tab
                    *[{'units': 1} for _ in range(12)],  # Q-P and brackets
                    {'units': 1.5}   # Enter/backslash
                ]
            },
            # Row 4: ASDF row - 15 units total
            {
                'y': start_y + (row_height + row_gap) * 3,
                'keys': [
                    {'units': 1.8},  # Caps Lock
                    *[{'units': 1} for _ in range(11)],  # A-L keys
                    {'units': 2.2}   # Enter
                ]
            },
            # Row 5: ZXCV row - 15 units total
            {
                'y': start_y + (row_height + row_gap) * 4,
                'keys': [
                    {'units': 2.2},  # Left Shift
                    *[{'units': 1} for _ in range(10)],  # Z-M keys
                    {'units': 2.8}   # Right Shift
                ]
            },
            # Row 6: Bottom row - 15 units total (IMPROVED: removed Fn, extended spacebar)
            {
                'y': start_y + (row_height + row_gap) * 5,
                'keys': [
                    {'units': 1.2},  # Left Ctrl
                    {'units': 1.2},  # Alt (removed Fn key)
                    {'units': 7.2, 'special': 'dual_zone_spacebar'},  # Extended spacebar (zones 2+3)
                    {'units': 1.2},  # Right Alt
                    {'units': 1.2},  # Menu
                    {'units': 1.0},  # Left arrow
                    {'units': 1.0, 'special': 'up_down_arrows'},  # Up/Down arrows (stacked)
                    {'units': 1.0}   # Right arrow
                ]
            }
        ]
        
        # Create all keys with perfect rectangular positioning
        for row_idx, row in enumerate(keyboard_layout):
            current_x = start_x
            for key_idx, key_data in enumerate(row['keys']):
                # Calculate key dimensions
                key_units = key_data['units']
                key_width = (unit_width * key_units) + (key_gap * (key_units - 1))
                key_height = row_height
                
                # Handle special cases
                if key_data.get('special') == 'up_down_arrows':
                    # Handle up/down arrow stack (already fixed)
                    zone = int((current_x - start_x) / zone_width)
                    zone = max(0, min(NUM_ZONES - 1, zone))
                    
                    # Create up arrow (top half of normal key height, aligned with row)
                    up_key = canvas.create_rectangle(
                        current_x, row['y'],
                        current_x + key_width, row['y'] + int(key_height/2),
                        fill='#404040', outline='#707070', width=1
                    )
                    elements.append({'element': up_key, 'zone': zone, 'type': 'key'})
                    
                    # Create down arrow (bottom half of normal key height, perfectly aligned)
                    down_key = canvas.create_rectangle(
                        current_x, row['y'] + int(key_height/2),
                        current_x + key_width, row['y'] + key_height,
                        fill='#404040', outline='#707070', width=1
                    )
                    elements.append({'element': down_key, 'zone': zone, 'type': 'key'})
                    
                elif key_data.get('special') == 'dual_zone_spacebar':
                    # Handle dual-zone spacebar (zones 2 and 3)
                    spacebar_half_width = key_width / 2
                    
                    # Left half of spacebar (zone 2)
                    left_spacebar = canvas.create_rectangle(
                        current_x, row['y'],
                        current_x + spacebar_half_width, row['y'] + key_height,
                        fill='#404040', outline='#707070', width=1
                    )
                    elements.append({'element': left_spacebar, 'zone': 2, 'type': 'key'})
                    
                    # Right half of spacebar (zone 3)
                    right_spacebar = canvas.create_rectangle(
                        current_x + spacebar_half_width, row['y'],
                        current_x + key_width, row['y'] + key_height,
                        fill='#404040', outline='#707070', width=1
                    )
                    elements.append({'element': right_spacebar, 'zone': 3, 'type': 'key'})
                    
                else:
                    # Regular key
                    key_rect = canvas.create_rectangle(
                        current_x, row['y'],
                        current_x + key_width, row['y'] + key_height,
                        fill='#404040', outline='#707070', width=1
                    )
                    
                    # Left-to-right zone assignment based on X position
                    zone = int((current_x - start_x) / zone_width)
                    zone = max(0, min(NUM_ZONES - 1, zone))
                    elements.append({'element': key_rect, 'zone': zone, 'type': 'key'})
                
                # Move to next key position
                current_x += key_width + key_gap
        
        # Add zone divider lines
        for zone_idx in range(1, NUM_ZONES):
            divider_x = start_x + (zone_idx * zone_width)
            divider_line = canvas.create_line(
                divider_x, start_y, divider_x, start_y + keyboard_height,
                fill='#555555', width=1, dash=(2, 2)
            )
            elements.append({'element': divider_line, 'zone': -1, 'type': 'divider'})
        
        # Add compact zone labels
        zone_label_y = start_y + keyboard_height + 8
        for zone_idx in range(NUM_ZONES):
            zone_label_x = start_x + (zone_idx * zone_width) + (zone_width / 2)
            text_element = canvas.create_text(
                zone_label_x, zone_label_y,
                text=f'Z{zone_idx + 1}',
                fill='#aaaaaa', font=('Arial', 7, 'bold')
            )
            elements.append({'element': text_element, 'zone': zone_idx, 'type': 'label'})
        
        # Perfect rectangular outline
        keyboard_outline = canvas.create_rectangle(
            start_x - 2, start_y - 2,
            start_x + keyboard_width + 2, start_y + keyboard_height + 2,
            fill='', outline='#888888', width=2
        )
        elements.append({'element': keyboard_outline, 'zone': -1, 'type': 'outline'})

    def update_preview_keyboard(self, canvas=None, elements_list=None):
        """Update the keyboard preview with current LED states - improved real-time accuracy"""
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
                if elem_info['type'] == 'key':
                    zone = elem_info['zone']
                    if 0 <= zone < len(self.zone_colors):
                        color = self.zone_colors[zone].to_hex()
                        
                        # Add subtle brightness effect for better visual feedback
                        zone_color_obj = self.zone_colors[zone]
                        if zone_color_obj.r + zone_color_obj.g + zone_color_obj.b > 50:
                            # Key is lit - add subtle glow effect with brighter outline
                            canvas.itemconfig(elem_info['element'], fill=color, outline='#ffffff', width=2)
                        else:
                            # Key is off - darker appearance
                            canvas.itemconfig(elem_info['element'], fill=color, outline='#606060', width=1)
                    else:
                        # Default inactive key appearance
                        canvas.itemconfig(elem_info['element'], fill='#303030', outline='#505050', width=1)
                elif elem_info['type'] == 'divider':
                    # Update zone dividers based on activity
                    canvas.itemconfig(elem_info['element'], fill='#666666')
        except tk.TclError:
            # Canvas might be destroyed during shutdown
            pass

    def update_preview_leds(self):
        """Legacy method for compatibility - now redirects to keyboard preview"""
        self.update_preview_keyboard()

    def log_to_gui_diag_area(self, message: str, level: str = "info"):
        """Helper to write messages to the GUI's diagnostic log text widget."""
        self.logger.log(getattr(logging, level.upper(), logging.INFO), message) # Also log it normally
        if hasattr(self, 'gui_log_text_widget') and self.gui_log_text_widget and self.gui_log_text_widget.winfo_exists():
            try:
                prefix = f"[{level.upper()}] "
                self.gui_log_text_widget.config(state=tk.NORMAL)
                self.gui_log_text_widget.insert(tk.END, prefix + message + '\n')
                self.gui_log_text_widget.see(tk.END)
                num_lines = int(self.gui_log_text_widget.index('end-1c').split('.')[0])
                max_log_lines = 500 # Keep this consistent with GuiLogHandler
                if num_lines > max_log_lines:
                    self.gui_log_text_widget.delete('1.0', f'{num_lines - max_log_lines + 1}.0')
                self.gui_log_text_widget.config(state=tk.DISABLED)
            except tk.TclError as e:
                self.logger.debug(f"TclError writing to GUI log widget: {e}")
            except Exception as e:
                self.logger.error(f"Error writing to GUI log widget: {e}")

    def setup_gui_logging(self):
        if not hasattr(self, 'gui_log_text_widget') or not self.gui_log_text_widget:
            self.logger.error("gui_log_text_widget not available for GUI logging.")
            return

        class GuiLogHandler(logging.Handler):
            def __init__(self, text_widget: scrolledtext.ScrolledText, master_tk: tk.Tk):
                super().__init__()
                self.text_widget = text_widget
                self.master_tk = master_tk
                self.log_queue = queue.Queue()
                self._check_queue_interval_ms = 200
                self._schedule_queue_check()
                
            def emit(self, record: logging.LogRecord): 
                self.log_queue.put(self.format(record))
                
            def _schedule_queue_check(self):
                if self.master_tk.winfo_exists(): 
                    self.master_tk.after(self._check_queue_interval_ms, self._process_log_queue)
                    
            def _process_log_queue(self):
                try:
                    while not self.log_queue.empty():
                        message = self.log_queue.get_nowait()
                        if self.text_widget.winfo_exists():
                            self.text_widget.config(state=tk.NORMAL)
                            self.text_widget.insert(tk.END, message + '\n')
                            self.text_widget.see(tk.END)
                            num_lines = int(self.text_widget.index('end-1c').split('.')[0])
                            max_log_lines = 500 # Consistent max lines
                            if num_lines > max_log_lines: 
                                self.text_widget.delete('1.0', f'{num_lines - max_log_lines + 1}.0')
                            self.text_widget.config(state=tk.DISABLED)
                except queue.Empty: 
                    pass
                except tk.TclError: 
                    pass # Widget might be destroyed during shutdown
                except Exception as e: 
                    print(f"Error processing GUI log queue: {e}", file=sys.stderr)
                finally:
                    if self.master_tk.winfo_exists() and not getattr(self.master_tk, '_is_being_destroyed', False): # Check before rescheduling
                        self._schedule_queue_check()

        try:
            gui_handler = GuiLogHandler(self.gui_log_text_widget, self.root)
            gui_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s', datefmt='%H:%M:%S'))
            gui_handler.setLevel(logging.INFO)
            logging.getLogger().addHandler(gui_handler) # Add to root logger
            self.logger.info("GUI logging handler initialized and attached to root logger.")
        except Exception as e: 
            self.logger.error(f"Failed to set up GUI logging handler: {e}", exc_info=True)

    def setup_tray_icon(self): # This method actually creates and runs the icon
        if not PYSTRAY_AVAILABLE:
            self.logger.warning("pystray not available, cannot minimize to tray.")
            self._show_tray_dependency_error()
            self.on_closing(from_tray_setup_failure=True)
            return
        if self.tray_icon and self.tray_thread and self.tray_thread.is_alive():
            self.logger.debug("Tray icon already running.")
            return

        def create_icon_for_tray():
            icon_img = getattr(self, 'pystray_icon_image', None)
            if icon_img is None: # If file loading and PIL generation both failed
                self.logger.warning("self.pystray_icon_image is None for tray. Creating minimal fallback if PIL is available.")
                try:
                    if PIL_AVAILABLE:
                        icon_img = Image.new('RGBA', (64, 64), (100, 100, 255, 255)) # A simple blue square
                        if PIL_AVAILABLE:  # Double check PIL for drawing
                            draw = ImageDraw.Draw(icon_img)
                            draw.text((10,10), "RGB", fill="white") # Basic text
                    else:
                        self.logger.error("Cannot create fallback tray icon image: PIL (Pillow) is not available.")
                        return None # No icon possible
                except Exception as e_fb:
                    self.logger.error(f"Could not create minimal fallback icon for tray: {e_fb}")
                    return None
            return icon_img

        def on_open_gui():
            self.logger.info("Restoring GUI from tray.")
            self.window_hidden_to_tray = False
            self.root.after(0, self.root.deiconify)
            self.root.after(0, self.root.wm_deiconify)
            self.root.after(0, self.root.focus_set) # Make sure it's visible and focused
            if self.tray_icon: # Stop the tray icon once GUI is shown
                self.logger.info("Stopping tray icon as GUI is now visible.")
                try:
                    self.tray_icon.stop()
                except Exception as e_stop:
                    self.logger.error(f"Error stopping tray icon: {e_stop}")
                self.tray_icon = None
                if self.tray_thread and self.tray_thread.is_alive():
                    self.logger.debug("Tray thread should exit soon after icon.stop().")
                self.tray_thread = None

        def on_quit_app_from_tray():
            self.logger.info("Quitting application from tray icon.")
            self.root.after(0, self.on_closing, False, True) # False=not_from_tray_failure, True=confirmed_quit

        tray_image = create_icon_for_tray()
        if tray_image is None:
            self.logger.error("No image for tray icon, cannot create. Tray functionality disabled for this session.")
            self.root.after(0, self._handle_tray_failure)
            return # Ensure GUI is shown if it was hidden

        self.logger.info("Creating tray icon (GUI will be hidden if successful).")
        menu_items = [
            pystray.MenuItem('Open GUI', on_open_gui, default=True), # Default action on click
            pystray.MenuItem('Stop Effect', lambda: self.root.after(0, self.stop_current_effect)),
            pystray.MenuItem('Clear LEDs', lambda: self.root.after(0, self.clear_all_zones_and_effects)),
            pystray.Menu.SEPARATOR, 
            pystray.MenuItem('Quit', on_quit_app_from_tray)
        ]

        try:
            self.tray_icon = pystray.Icon('rgb_controller', tray_image, APP_NAME, pystray.Menu(*menu_items))
        except Exception as e: # Catch potential pystray.Icon creation errors
            self.logger.error(f"Failed to create pystray.Icon object: {e}", exc_info=True)
            self.root.after(0, self._handle_tray_failure)
            return

        def run_tray():
            try:
                self.logger.debug(f"Pystray icon ({self.tray_icon.name if self.tray_icon else 'None'}) run starting.")
                self.tray_icon.run()
            except Exception as e: # Catch errors during tray run (e.g., X server issues)
                self.logger.error(f"Tray icon run loop crashed: {e}", exc_info=True)
                # If the GUI was hidden and tray crashes, we need to recover the window
                if self.root.winfo_exists() and self.window_hidden_to_tray:
                    self.root.after(0, self._handle_tray_failure) # This should deiconify
            finally:
                self.logger.info("Tray icon run loop finished.")

        self.tray_thread = threading.Thread(target=run_tray, daemon=True, name="TrayIconThread")
        self.tray_thread.start()
        self.root.after(1000, self._check_tray_status) # Check if tray started successfully

    def _show_tray_dependency_error(self):
        """Show detailed error message for missing tray dependencies"""
        error_msg = """System Tray Dependencies Missing

Required packages are not installed:
• pystray - System tray functionality
• Pillow (PIL) - Icon image support

INSTALLATION INSTRUCTIONS:
========================

1. Install both packages:
   pip install pystray Pillow

2. Alternative methods:
   • conda install -c conda-forge pystray pillow
   • On Ubuntu: sudo apt install python3-pil
   • pip3 install pystray Pillow (if pip points to Python 2)

3. For system-specific issues:
   • Ubuntu/Debian: sudo apt install python3-dev libxss1
   • Some systems need: sudo apt install notification-daemon
   • GNOME: sudo apt install gir1.2-appindicator3-0.1

4. Restart the application after installation

The application will continue without tray functionality."""
        
        self.log_to_gui_diag_area(error_msg, "error")
        if self.root.winfo_exists():
            messagebox.showerror("System Tray Unavailable", error_msg, parent=self.root)

    def _check_tray_status(self):
        if self.window_hidden_to_tray: # Only if we expect the tray to be running
            is_tray_thread_alive = self.tray_thread and self.tray_thread.is_alive()

            if not is_tray_thread_alive:
                self.logger.warning("Tray icon thread died prematurely or did not start. Assuming tray startup failure.")
                self._handle_tray_failure()
            elif self.tray_icon is None and is_tray_thread_alive: # Thread running but icon object gone wrong
                self.logger.warning("Tray icon object became None unexpectedly while thread is alive. Assuming failure.")
                self._handle_tray_failure()
            # No else needed; if thread is alive and icon exists, it's presumably fine.

    def _handle_tray_failure(self):
        """Handle tray failures gracefully by restoring the main window"""
        self.logger.warning("Tray failure recovery initiated.")
        
        # Strategy 1: Try to restore window
        if self.window_hidden_to_tray and self.root.winfo_exists():
            try:
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
                self.window_hidden_to_tray = False
                self.logger.info("Window restored successfully from tray failure.")
            except Exception as e:
                self.logger.error(f"Failed to restore window from tray failure: {e}")
        
        # Strategy 2: Cleanup tray resources
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except:
                pass
            self.tray_icon = None
        
        if self.tray_thread:
            try:
                self.tray_thread.join(timeout=1.0)
            except:
                pass
            self.tray_thread = None
        
        # Strategy 3: Disable tray functionality temporarily
        if hasattr(self, 'minimize_to_tray_var'):
            self.minimize_to_tray_var.set(False)
            self.settings.set("minimize_to_tray", False)
            
        self.log_status("System tray disabled due to technical issues. Window will remain visible.")

    def handle_close_button_press(self):
        self.logger.info("WM_DELETE_WINDOW protocol called (X button click).")
        minimize_to_tray_enabled = self.minimize_to_tray_var.get() if hasattr(self, 'minimize_to_tray_var') else self.settings.get("minimize_to_tray", True)

        if PYSTRAY_AVAILABLE and minimize_to_tray_enabled:
            self.logger.info("Minimizing to system tray (minimize_to_tray=True).")
            self.window_hidden_to_tray = True
            self.root.withdraw()
            self.setup_tray_icon()
        else:
            self.logger.info("Proceeding with normal quit sequence (minimize_to_tray=False or pystray unavailable).")
            self.on_closing()

    def on_closing(self, from_tray_setup_failure=False, confirmed_quit=False):
        self.logger.info(f"on_closing called (from_tray_setup_failure={from_tray_setup_failure}, confirmed_quit={confirmed_quit}).")
        should_quit = confirmed_quit
        if not confirmed_quit:
            if self.root.winfo_exists() and messagebox.askokcancel("Quit", f"Are you sure you want to quit {APP_NAME}?", parent=self.root):
                self.logger.info("User confirmed quit via messagebox.")
                should_quit = True
            else:
                self.logger.info("User cancelled quit.")
                # If quit was cancelled after a tray setup failure, ensure window is visible
                if from_tray_setup_failure and self.root.winfo_exists() and self.window_hidden_to_tray:
                    self.logger.info("Restoring window as quit was cancelled after tray failure.")
                    self.root.deiconify()
                    self.root.focus_set()
                    self.window_hidden_to_tray = False # No longer hidden
                should_quit = False

        if should_quit:
            self.perform_final_shutdown(clean_shutdown=True)

    def on_minimize_event(self, event): # Bound to <Unmap>
        # Check if the unmap was due to minimization (state becomes 'iconic')
        if self.root.winfo_exists() and self.root.state() == 'iconic':
            self.logger.debug(f"Minimize event detected (state: {self.root.state()}).")
            minimize_to_tray_enabled = self.minimize_to_tray_var.get() if hasattr(self, 'minimize_to_tray_var') else self.settings.get("minimize_to_tray", True)
            if PYSTRAY_AVAILABLE and minimize_to_tray_enabled:
                self.logger.info("Window minimized via button/taskbar, hiding to tray.")
                self.window_hidden_to_tray = True
                self.root.withdraw()
                self.setup_tray_icon()
                return 'break' # Prevent further processing if handled
            else: 
                self.logger.info("Window minimized via button/taskbar, using normal taskbar minimize.")

    def save_tray_settings(self):
        if hasattr(self, 'minimize_to_tray_var'):
            self.settings.set("minimize_to_tray", self.minimize_to_tray_var.get())
            self.log_status("System tray settings saved.")
        else: 
            self.logger.warning("minimize_to_tray_var not found, cannot save tray settings.")

    def initialize_hardware_async(self):
        self.status_var.set("Initializing hardware...")
        self.connection_label.config(text="HW: Init...")
        
        def init_thread_target():
            # Pass preferred control method to detection if relevant
            preferred_method = self.settings.get("last_control_method", default_settings["last_control_method"])
            self.logger.info(f"Hardware initialization: Preferred method from settings: {preferred_method}")

            if self.hardware.wait_for_detection(timeout=HARDWARE_DETECTION_TIMEOUT, preferred_method=preferred_method):
                if self.hardware.is_operational():
                    self.root.after(0, lambda: self.status_var.set("Hardware initialized."))
                    self.root.after(0, lambda: self.connection_label.config(text=f"HW: Ready ({self.hardware.get_active_method_display()})"))
                    # If EC Direct was preferred but not active, or active but with caveats
                    active_method = self.hardware.get_active_method_display() # Assuming this method exists
                    if preferred_method == "ec_direct" and "EC Direct" not in active_method:
                        msg = "Preferred control method 'EC Direct' is not currently active. Hardware might be using a fallback (e.g., ectool) or EC Direct is not fully implemented/available. Check Diagnostics."
                        self.logger.warning(msg)
                        self.root.after(0, lambda: self.log_to_gui_diag_area(msg, "warning"))
                else:
                    self.root.after(0, lambda: self.status_var.set("Hardware: No control methods found or not operational."))
                    self.root.after(0, lambda: self.connection_label.config(text="HW: Not Found/Ready"))
                    if self.root.winfo_exists():
                        self.root.after(0, lambda: messagebox.showwarning("Hardware Warning", "No RGB keyboard control methods were detected or hardware is not operational. Functionality will be limited.", parent=self.root))
            else:
                self.root.after(0, lambda: self.status_var.set("Hardware detection timed out/failed."))
                self.root.after(0, lambda: self.connection_label.config(text="HW: Error"))
                if self.root.winfo_exists():
                    self.root.after(0, lambda: messagebox.showerror("Hardware Error", "Hardware detection failed or timed out. Please check system setup, permissions, and logs.", parent=self.root))
            if self.root.winfo_exists(): 
                self.root.after(0, self.refresh_hardware_status)
        
        threading.Thread(target=init_thread_target, daemon=True, name="HWInitThread").start()

    def apply_startup_settings_if_enabled_async(self):
        if self.settings.get("restore_on_startup", default_settings["restore_on_startup"]):
            self.logger.info("Applying saved settings on startup...")
            if not self.hardware.detection_complete.is_set():
                self.logger.info("Delaying startup settings application until hardware detection completes.")
                self.root.after(1000, self.apply_startup_settings_if_enabled_async)
                return
            if not self.hardware.is_operational():
                self.logger.warning("Hardware not operational. Skipping startup settings application.")
                self.log_status("Hardware not ready, cannot apply startup settings.", "warning")
                return
            self._restore_settings_on_startup()
        else: 
            self.logger.info("Restore on startup is disabled by user settings.")

    def _restore_settings_on_startup(self):
        try:
            self.logger.info("Restoring settings on startup...")
            if self.auto_apply_var.get() and self.settings.was_previous_session_clean():
                self.logger.info("Auto-applying last settings (clean shutdown detected).")
                last_effect_name = self.settings.get("effect_name", default_settings["effect_name"])
                last_mode = self.settings.get("last_mode", "static") # 'static', 'zones', 'rainbow_zones', 'gradient_zones', 'effect'
                brightness = self.settings.get("brightness", default_settings["brightness"])

                if self.hardware.is_operational(): 
                    self.hardware.set_brightness(brightness)
                self.brightness_var.set(brightness) # This will also update the text var via trace

                is_static_type_effect = last_effect_name in ["Static Color", "Static Zone Colors", "Static Rainbow", "Static Gradient"]

                if last_effect_name != "None" and not is_static_type_effect and last_effect_name in self.effect_manager.get_available_effects():
                    self.logger.info(f"Restoring last dynamic effect: {last_effect_name}")
                    self.effect_var.set(last_effect_name)
                    self.effect_color_var.set(self.settings.get("effect_color", default_settings["effect_color"]))
                    self.effect_rainbow_mode_var.set(self.settings.get("effect_rainbow_mode", default_settings["effect_rainbow_mode"]))
                    self.speed_var.set(self.settings.get("effect_speed", default_settings["effect_speed"]) * 10) # speed is 1-10 internally, 10-100 in GUI
                    self.update_effect_controls_visibility()
                    self.start_current_effect() # Start the effect
                elif last_mode == "static" or last_effect_name == "Static Color":
                    static_color = RGBColor.from_dict(self.settings.get("current_color", default_settings["current_color"]))
                    self.apply_static_color(static_color.to_hex())
                elif last_mode == "zones" or last_effect_name == "Static Zone Colors": 
                    self.apply_current_zone_colors_to_hardware()
                elif last_mode == "rainbow_zones" or last_effect_name == "Static Rainbow": 
                    self.apply_rainbow_zones()
                elif last_mode == "gradient_zones" or last_effect_name == "Static Gradient": 
                    self.apply_gradient_zones()
                else: # Fallback if no specific mode matches or effect is "None"
                    self.logger.info("No specific valid effect/mode to restore, applying default static color.")
                    default_color = RGBColor.from_dict(default_settings["current_color"])
                    self.apply_static_color(default_color.to_hex())
            else:
                if not self.auto_apply_var.get(): 
                    self.logger.info("Auto-apply disabled, not restoring last effect.")
                else: 
                    self.logger.info("Previous session was not clean, not restoring last effect for safety.")
                # Apply a default state (e.g. off or a default color)
                default_color = RGBColor.from_dict(default_settings["current_color"]) # Or black if preferred
                self.apply_static_color(default_color.to_hex()) # Apply a known safe state
            self.log_status("Startup settings restoration completed.")
        except Exception as e:
            self.logger.error(f"Error during startup settings restoration: {e}", exc_info=True)
            self.log_status(f"Error restoring startup settings: {e}", "error")
            try: # Attempt to set a very basic state on error
                default_color = RGBColor.from_dict(default_settings["current_color"])
                self.apply_static_color(default_color.to_hex())
            except: 
                pass # Suppress errors during emergency fallback

    def on_brightness_change(self, val_str: str): # Called by Scale widget
        if self._loading_settings: 
            return # Avoid hardware calls while loading settings
        try:
            value = int(float(val_str))
            self._apply_brightness_value(value, "slider")
        except ValueError: 
            self.logger.warning(f"Invalid brightness value from slider: {val_str}")
        except tk.TclError: 
            self.logger.debug("Brightness label no longer exists during on_brightness_change.")

    def _apply_brightness_value(self, value: int, source: str = "unknown"):
        """Applies brightness value to hardware and settings."""
        # self.brightness_var is already updated by slider or hotkey handler
        # This method is primarily for the hardware call and logging
        clamped_value = max(0, min(100, value))
        if self.hardware.set_brightness(clamped_value):
            self.settings.set("brightness", clamped_value)
            self.log_status(f"Brightness set to {clamped_value}% (source: {source})")
        else:
            self.log_status(f"Failed to set brightness to {clamped_value}% (source: {source})", "error")
        # UI text update is handled by trace on self.brightness_var

    def on_speed_change(self, val_str: str):
        if self._loading_settings: 
            return
        try:
            gui_speed_value = int(float(val_str)) # GUI scale 1-100
            effect_speed_internal = max(1, min(10, int(gui_speed_value / 10.0 + 0.5))) # Internal 1-10
            self.settings.set("effect_speed", effect_speed_internal) # Save internal speed
            if self.effect_manager.is_effect_running(): 
                self.effect_manager.update_effect_speed(effect_speed_internal)
            self.log_status(f"Effect speed set to {effect_speed_internal} (UI: {gui_speed_value}%)")
            if hasattr(self, 'speed_label') and self.speed_label.winfo_exists(): 
                self.speed_label.config(text=f"{gui_speed_value}%")
        except ValueError: 
            self.logger.warning(f"Invalid speed value: {val_str}")
        except tk.TclError: 
            self.logger.debug("Speed label no longer exists.")

    def on_rainbow_mode_change(self):
        if self._loading_settings: 
            return
        rainbow_enabled = self.effect_rainbow_mode_var.get()
        self.settings.set("effect_rainbow_mode", rainbow_enabled)
        self.update_effect_controls_visibility() # Show/hide color picker

        current_effect_name = self.effect_var.get()
        is_static_effect = current_effect_name in ["Static Color", "Static Zone Colors", "Static Rainbow", "Static Gradient"]

        # Only update preview, don't apply to hardware automatically
        if not is_static_effect and current_effect_name != "None":
            # Effect is selected but parameters changed, update preview only
            self._update_effect_preview_only()

    def _update_effect_preview_only(self):
        """Update only the preview without applying to hardware"""
        current_effect_name = self.effect_var.get()
        if current_effect_name == "None" or current_effect_name in ["Static Color", "Static Zone Colors", "Static Rainbow", "Static Gradient"]:
            return

        # Stop current preview animation
        self.stop_preview_animation()
        
        # Start preview for the selected effect
        preview_method_name = f"preview_{current_effect_name.lower().replace(' ','_').replace('(','').replace(')','')}"
        if hasattr(self, preview_method_name) and callable(getattr(self, preview_method_name)):
            self.start_preview_animation(getattr(self, preview_method_name))
        else:
            self._update_generic_preview_on_param_change()

    def _update_generic_preview_on_param_change(self):
        self.stop_preview_animation() # Stop any existing complex preview
        effect_name = self.effect_var.get()
        if effect_name == "None" or effect_name in ["Static Color", "Static Zone Colors", "Static Rainbow", "Static Gradient"]: 
            return

        if not self.effect_rainbow_mode_var.get(): # Single color
            try:
                color = RGBColor.from_hex(self.effect_color_var.get())
                # Update zone colors for preview (without applying to hardware)
                for i in range(NUM_ZONES):
                    self.zone_colors[i] = color
                self.update_preview_keyboard()
            except ValueError: # Invalid hex
                # Default to black
                for i in range(NUM_ZONES):
                    self.zone_colors[i] = RGBColor(0,0,0)
                self.update_preview_keyboard()
        else: # Rainbow mode for preview
            for i in range(NUM_ZONES):
                hue = (i / NUM_ZONES) % 1.0
                rgb_float = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                self.zone_colors[i] = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
            self.update_preview_keyboard()

    def on_effect_change(self, *args): # Called by Combobox selection or direct set of effect_var
        if self._loading_settings: 
            return
        effect_name = self.effect_var.get()
        self.settings.set("effect_name", effect_name)
        self.update_effect_controls_visibility()

        # CHANGED: Only update preview, don't apply to hardware automatically
        self.stop_preview_animation() # Stop any current preview animation

        # Handle static "effects" which show immediate preview
        static_effects_map = {
            "Static Color": lambda: self.preview_static_color(),
            "Static Zone Colors": lambda: self.preview_static_per_zone(0),
            "Static Rainbow": lambda: self.preview_static_rainbow(0),
            "Static Gradient": lambda: self.preview_static_gradient(0)
        }
        if effect_name in static_effects_map:
            static_effects_map[effect_name]()
            self.update_preview_keyboard()
            self.log_status(f"Effect '{effect_name}' selected. Click 'Start Effect' to apply to hardware.")
            return

        if effect_name != "None":
            # For dynamic effects, start their specific GUI preview (not hardware effect)
            preview_method_name = f"preview_{effect_name.lower().replace(' ','_').replace('(','').replace(')','')}"
            if hasattr(self, preview_method_name) and callable(getattr(self, preview_method_name)):
                self.logger.debug(f"Activating specific GUI preview for {effect_name}")
                self.start_preview_animation(getattr(self, preview_method_name))
            else: # No specific preview, show a generic static representation based on params
                self.logger.debug(f"No specific GUI preview for {effect_name}. Setting static representation for preview.")
                self._update_generic_preview_on_param_change()
            self.log_status(f"Effect '{effect_name}' selected. Click 'Start Effect' to apply to hardware.")
        else:
            # Effect is "None", show black preview
            for i in range(NUM_ZONES):
                self.zone_colors[i] = RGBColor(0,0,0)
            self.update_preview_keyboard()
            self.log_status("No effect selected.")

    def preview_static_color(self):
        """Preview static color in the keyboard layout"""
        try:
            color = RGBColor.from_hex(self.current_color_var.get())
        except ValueError:
            color = RGBColor(0,0,0)
        
        for i in range(NUM_ZONES):
            self.zone_colors[i] = color

    def update_effect_controls_visibility(self):
        effect_name = self.effect_var.get()
        # Define which effects can have their color configured
        color_configurable_effects = ["Breathing", "Wave", "Pulse", "Zone Chase", "Starlight", "Scanner", "Strobe", "Ripple", "Raindrop"] # Add other effects as needed
        is_color_configurable = effect_name in color_configurable_effects

        if hasattr(self, 'effect_color_rainbow_frame') and self.effect_color_rainbow_frame.winfo_exists():
            if is_color_configurable:
                if not self.effect_color_rainbow_frame.winfo_ismapped():
                    self.effect_color_rainbow_frame.pack(fill=tk.X, pady=(0,5), anchor='w') # Pack the main container

                if hasattr(self, 'rainbow_mode_check') and self.rainbow_mode_check.winfo_exists():
                    if not self.rainbow_mode_check.winfo_ismapped():
                        self.rainbow_mode_check.pack(side=tk.LEFT, padx=(0,10), pady=(0,5))

                if hasattr(self, 'effect_color_frame') and self.effect_color_frame.winfo_exists():
                    if not self.effect_rainbow_mode_var.get(): # If not rainbow mode, show color picker
                        if not self.effect_color_frame.winfo_ismapped():
                            self.effect_color_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=0, padx=5)
                    else: # Rainbow mode is on, hide color picker
                        if self.effect_color_frame.winfo_ismapped():
                            self.effect_color_frame.pack_forget()
            else: # Effect is not color configurable (or "None"), hide the whole section
                if self.effect_color_rainbow_frame.winfo_ismapped():
                    self.effect_color_rainbow_frame.pack_forget()

    def apply_static_color(self, hex_color_str: str):
        self._stop_all_visuals_and_clear_hardware() # Stop effects, clear HW before applying new static state
        try:
            color = RGBColor.from_hex(hex_color_str)
            if not color.is_valid():
                self.log_status(f"Invalid hex color for static apply: {hex_color_str}", "error")
                return

            if self.hardware.set_all_leds_color(color):
                self.current_color_var.set(hex_color_str) # Update GUI variable
                if hasattr(self, 'color_display') and self.color_display.winfo_exists(): 
                    self.color_display.config(bg=hex_color_str)
                self.settings.set("current_color", color.to_dict())
                self.settings.set("last_mode", "static")
                self.log_status(f"Applied static color {hex_color_str} to all zones")
                
                # Update zone colors for consistent preview
                for i in range(NUM_ZONES):
                    self.zone_colors[i] = color
                self.update_preview_keyboard()
            else:
                # If hardware call fails, it might raise an exception or return False
                raise HardwareError("HardwareController.set_all_leds_color returned false or failed.")
        except Exception as e:
            log_error_with_context(self.logger, e, {"color": hex_color_str, "action": "apply_static_color"})
            if self.root.winfo_exists(): 
                messagebox.showerror("Error", f"Failed to apply static color: {e}", parent=self.root)

    def set_zone_color_interactive(self, zone_index: int):
        # Don't stop hardware effects - this is just for GUI/preview setup
        if not (0 <= zone_index < NUM_ZONES and zone_index < len(self.zone_displays)):
            self.logger.error(f"Invalid zone index {zone_index}. Max zones: {NUM_ZONES}, displays: {len(self.zone_displays)}")
            return

        initial_color_hex = self.zone_colors[zone_index].to_hex()
        new_color_tuple = colorchooser.askcolor(initialcolor=initial_color_hex, title=f"Set Color for Zone {zone_index + 1}", parent=self.root)

        if new_color_tuple and new_color_tuple[1]: # Color chosen and is a valid hex
            chosen_hex = new_color_tuple[1]
            self.zone_colors[zone_index] = RGBColor.from_hex(chosen_hex)
            if self.zone_displays[zone_index].winfo_exists(): 
                self.zone_displays[zone_index].config(bg=chosen_hex)
            self.log_status(f"Zone {zone_index+1} GUI color changed. Click 'Apply Zone Colors to HW'.")
            self.settings.set("zone_colors", [zc.to_dict() for zc in self.zone_colors]) # Save new set of zone colors

            # Update the preview to reflect the change without applying to hardware yet
            self.update_preview_keyboard()

    def apply_current_zone_colors_to_hardware(self):
        self._stop_all_visuals_and_clear_hardware() # Stop effects, clear HW
        try:
            if self.hardware.set_zone_colors(self.zone_colors):
                self.log_status("Applied current zone colors to hardware.")
                self.settings.set("zone_colors", [zc.to_dict() for zc in self.zone_colors]) # Persist
                self.settings.set("last_mode", "zones")
                self.update_preview_keyboard() # Update preview
            else:
                raise HardwareError("HardwareController.set_zone_colors returned false.")
        except Exception as e:
            log_error_with_context(self.logger, e)
            if self.root.winfo_exists(): 
                messagebox.showerror("Error", f"Failed to apply zone colors: {e}", parent=self.root)

    def apply_rainbow_zones(self):
        self._stop_all_visuals_and_clear_hardware() # Stop effects, clear HW
        try:
            rainbow_zone_colors_list = []
            for i in range(NUM_ZONES):
                hue = i / float(NUM_ZONES) if NUM_ZONES > 0 else 0
                rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0) # Full saturation and value
                rainbow_zone_colors_list.append(RGBColor(int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255)))

            if self.hardware.set_zone_colors(rainbow_zone_colors_list):
                self.zone_colors = rainbow_zone_colors_list # Update internal state
                for i, color_obj in enumerate(self.zone_colors): # Update GUI displays for zones
                    if i < len(self.zone_displays) and self.zone_displays[i].winfo_exists():
                        self.zone_displays[i].config(bg=color_obj.to_hex())
                self.settings.set("zone_colors", [c.to_dict() for c in self.zone_colors]) # Persist
                self.settings.set("last_mode", "rainbow_zones")
                self.log_status("Applied rainbow pattern to zones.")
                self.update_preview_keyboard() # Update preview
            else:
                raise HardwareError("Failed to set rainbow colors to hardware (set_zone_colors returned false)")
        except Exception as e:
            log_error_with_context(self.logger, e)
            if self.root.winfo_exists(): 
                messagebox.showerror("Error", f"Failed to apply rainbow zones: {e}", parent=self.root)

    def apply_gradient_zones(self):
        self._stop_all_visuals_and_clear_hardware() # Stop effects, clear HW
        try:
            start_color = RGBColor.from_hex(self.gradient_start_color_var.get())
            end_color = RGBColor.from_hex(self.gradient_end_color_var.get())
            gradient_zone_colors_list = []
            for i in range(NUM_ZONES):
                ratio = i / float(NUM_ZONES - 1) if NUM_ZONES > 1 else 0.0 # Avoid division by zero if NUM_ZONES is 1
                r = int(start_color.r*(1-ratio)+end_color.r*ratio)
                g = int(start_color.g*(1-ratio)+end_color.g*ratio)
                b = int(start_color.b*(1-ratio)+end_color.b*ratio)
                gradient_zone_colors_list.append(RGBColor(r, g, b))

            if self.hardware.set_zone_colors(gradient_zone_colors_list):
                self.zone_colors = gradient_zone_colors_list # Update internal state
                for i, color_obj in enumerate(self.zone_colors): # Update GUI displays
                    if i < len(self.zone_displays) and self.zone_displays[i].winfo_exists():
                        self.zone_displays[i].config(bg=color_obj.to_hex())
                self.settings.set("zone_colors", [c.to_dict() for c in self.zone_colors]) # Persist
                self.settings.set("last_mode", "gradient_zones")
                self.log_status("Applied gradient to zones.")
                self.update_preview_keyboard() # Update preview
            else:
                raise HardwareError("Failed to set gradient colors to hardware (set_zone_colors returned false)")
        except Exception as e:
            log_error_with_context(self.logger, e)
            if self.root.winfo_exists(): 
                messagebox.showerror("Error", f"Failed to apply gradient: {e}", parent=self.root)

    def clear_all_zones_and_effects(self):
        self._stop_all_visuals_and_clear_hardware() # This does the main work
        self.log_status("All effects stopped & LEDs cleared by user action.")

        black = RGBColor(0,0,0)
        # Update GUI elements to reflect the cleared state
        self.zone_colors = [black] * NUM_ZONES
        for zd in self.zone_displays:
            if hasattr(zd, 'winfo_exists') and zd.winfo_exists(): 
                zd.config(bg=black.to_hex())

        self.current_color_var.set(black.to_hex())
        if hasattr(self, 'color_display') and self.color_display.winfo_exists(): 
            self.color_display.config(bg=black.to_hex())

        self.effect_var.set("None") # This will trigger on_effect_change, which handles UI updates

        # Persist this cleared state
        self.settings.set("current_color", black.to_dict())
        self.settings.set("zone_colors", [black.to_dict()]*NUM_ZONES)
        self.settings.set("effect_name", "None")

        # Update preview
        self.update_preview_keyboard()

    def open_color_picker(self):
        # Don't stop effects automatically - just for preview
        self.stop_preview_animation() # Stop preview if it was running for an effect

        result = colorchooser.askcolor(initialcolor=self.current_color_var.get(), title="Choose Static Color", parent=self.root)
        if result and result[1]: # Color chosen
            self.current_color_var.set(result[1])
            if hasattr(self, 'color_display') and self.color_display.winfo_exists(): 
                self.color_display.config(bg=result[1])

            # If the current "effect" is static color, update its preview
            if self.effect_var.get() == "Static Color":
                self.preview_static_color()
                self.update_preview_keyboard()

    def choose_effect_color(self):
        result = colorchooser.askcolor(initialcolor=self.effect_color_var.get(), title="Choose Effect Base Color", parent=self.root)
        if result and result[1]: # Color chosen
            self.effect_color_var.set(result[1])
            if hasattr(self,'effect_color_display') and self.effect_color_display.winfo_exists():
                self.effect_color_display.config(bg=result[1])
            self.settings.set("effect_color", result[1]) # Save setting

            # Update preview only, don't apply to hardware
            self._update_effect_preview_only()

    def choose_gradient_start(self):
        result = colorchooser.askcolor(initialcolor=self.gradient_start_color_var.get(), title="Choose Gradient Start Color", parent=self.root)
        if result and result[1]:
            self.gradient_start_color_var.set(result[1])
            if hasattr(self,'gradient_start_display') and self.gradient_start_display.winfo_exists(): 
                self.gradient_start_display.config(bg=result[1])
            self.settings.set("gradient_start_color", result[1])
            # If current effect is Static Gradient, update its preview
            if self.effect_var.get() == "Static Gradient":
                self.preview_static_gradient(0)
                self.update_preview_keyboard()

    def choose_gradient_end(self):
        result = colorchooser.askcolor(initialcolor=self.gradient_end_color_var.get(), title="Choose Gradient End Color", parent=self.root)
        if result and result[1]:
            self.gradient_end_color_var.set(result[1])
            if hasattr(self,'gradient_end_display') and self.gradient_end_display.winfo_exists(): 
                self.gradient_end_display.config(bg=result[1])
            self.settings.set("gradient_end_color", result[1])
            # If current effect is Static Gradient, update its preview
            if self.effect_var.get() == "Static Gradient":
                self.preview_static_gradient(0)
                self.update_preview_keyboard()

    def start_current_effect(self):
        effect_name = self.effect_var.get()

        # Stop any previously running hardware effect and clear hardware LEDs.
        # Also stops software previews.
        self._stop_all_visuals_and_clear_hardware()

        # Handle static "effects" which are direct hardware settings
        static_effects_map = { # These apply directly to hardware and update their own previews
            "Static Color": lambda: self.apply_static_color(self.current_color_var.get()),
            "Static Zone Colors": self.apply_current_zone_colors_to_hardware,
            "Static Rainbow": self.apply_rainbow_zones,
            "Static Gradient": self.apply_gradient_zones
        }
        if effect_name in static_effects_map:
            static_effects_map[effect_name]()
            self.settings.set("effect_name", effect_name) # Ensure this is saved as the "active" effect
            # last_mode is set within each apply_ method
            return

        if effect_name == "None":
            self.log_status("Effect set to None. All effects stopped and LEDs cleared.")
            # _stop_all_visuals_and_clear_hardware already handled clearing.
            self.settings.set("effect_name", "None")
            return

        # Proceed with starting a dynamic effect
        params: Dict[str, Any] = {}
        try:
            params["speed"] = max(1, min(10, int(self.speed_var.get() / 10.0 + 0.5))) # Internal speed 1-10
            is_rainbow = self.effect_rainbow_mode_var.get()
            params["rainbow_mode"] = is_rainbow
            # Use default black if color is invalid, effect might handle it or use rainbow
            try:
                params["color"] = RGBColor.from_hex(self.effect_color_var.get()) if not is_rainbow else RGBColor(0,0,0) # Base color if not rainbow
            except ValueError:
                self.logger.warning(f"Invalid effect color hex {self.effect_color_var.get()}, using black for effect params.")
                params["color"] = RGBColor(0,0,0)

            if self.effect_manager.start_effect(effect_name, **params):
                self.log_status(f"Started effect: {effect_name}")
                self.settings.set("effect_name", effect_name)
                self.settings.set("last_mode", "effect")

                # Continue showing the GUI preview animation for this dynamic effect
                preview_method_name = f"preview_{effect_name.lower().replace(' ','_').replace('(','').replace(')','')}"
                if hasattr(self, preview_method_name) and callable(getattr(self, preview_method_name)):
                    self.start_preview_animation(getattr(self, preview_method_name))
                else: # No specific preview, show generic based on params
                    self._update_generic_preview_on_param_change()
            else:
                # Effect manager failed to start it (e.g., effect not found in its library)
                self.log_status(f"Effect '{effect_name}' not found by manager or failed to start.", "warning")
                if self.root.winfo_exists(): 
                    messagebox.showwarning("Effect Error", f"Could not start effect: {effect_name}. It might not be available in the effect library.", parent=self.root)
                self.effect_var.set("None") # Reset to None as it failed
        except Exception as e:
            log_error_with_context(self.logger, e, {"effect": effect_name, "params": str(params)}) # Log with context
            if self.root.winfo_exists(): 
                messagebox.showerror("Effect Error", f"Failed to start effect '{effect_name}': {e}", parent=self.root)
            self.effect_var.set("None") # Reset to None on error

    def stop_current_effect(self):
        # This method is for explicitly stopping the currently active dynamic effect
        # and clearing the hardware.
        self._stop_all_visuals_and_clear_hardware() # This stops EffectManager, GUI preview, and clears HW
        self.log_status("Current effect stopped by user action. LEDs cleared.")

        # If an effect was selected (not "None"), set it back to "None" to reflect that no effect is active.
        # This will also trigger on_effect_change, which will ensure UI consistency (e.g., hiding color pickers).
        if self.effect_var.get() != "None":
            self.effect_var.set("None")
        # If it was already "None", _stop_all_visuals_and_clear_hardware still ensures LEDs are off.

    def restart_current_effect(self):
        effect_name = self.effect_var.get()
        # Only restart if it's a dynamic effect (not None or a static type)
        if effect_name != "None" and effect_name not in ["Static Color", "Static Zone Colors", "Static Rainbow", "Static Gradient"]:
            self.log_status(f"Restarting effect: {effect_name} due to parameter change.")
            # _stop_all_visuals_and_clear_hardware() is called by start_current_effect
            # A small delay can sometimes help if hardware/software is still processing the stop command
            self.root.after(50, self.start_current_effect)
        elif self.preview_animation_active: # If it was a static effect but had a preview, restart that preview logic
            self.log_status(f"Restarting preview for: {effect_name} due to parameter change.")
            # For static types, their "start" action is just applying them
            self.start_current_effect() # This will call the appropriate apply_ method for static types

    def save_persistence_settings(self):
        self.settings.set("restore_on_startup", self.restore_startup_var.get())
        self.settings.set("auto_apply_last_setting", self.auto_apply_var.get())
        self.log_status("Persistence settings saved.")

    def save_control_method(self):
        method = self.control_method_var.get()
        self.settings.set("last_control_method", method)
        self.log_status(f"Control method preference set to: {method}")

        if method == "ec_direct":
            self._show_ec_direct_implementation_guide()

        # Attempt to inform the hardware controller about the change, if it supports it
        if hasattr(self.hardware, 'set_control_method_preference'):
            try:
                self.hardware.set_control_method_preference(method)
                self.logger.info(f"Notified HardwareController of preference: {method}")
                # Optionally, re-initialize or refresh hardware status if method change requires it
                # self.initialize_hardware_async() # Or a lighter refresh
            except Exception as e:
                self.logger.error(f"Error notifying HardwareController of preference change: {e}")
        else:
            self.logger.info("HardwareController does not have 'set_control_method_preference'. Preference saved; hardware layer may pick it up on next init.")

    def _show_ec_direct_implementation_guide(self):
        """Show comprehensive EC Direct implementation guide"""
        msg_title = "EC Direct Mode - Implementation Required"
        msg_body = """EC Direct mode selected. This is an ADVANCED feature that requires manual implementation.

IMPLEMENTATION STEPS:
====================

1. HARDWARE-SPECIFIC RESEARCH:
   • Find your device's Embedded Controller (EC) documentation
   • Identify RGB control commands and registers
   • Determine I/O port addresses or memory locations
   • Research your specific laptop/keyboard model's EC interface

2. MODIFY HardwareController CLASS:
   Edit: gui/hardware/controller.py

   Implement these methods for EC Direct:
   • _detect_ec_direct() - Detect EC availability
   • _ec_set_brightness(value) - Direct brightness control
   • _ec_set_all_leds_color(color) - Set all LEDs via EC
   • _ec_set_zone_colors(colors) - Set individual zones via EC
   • _ec_clear_all_leds() - Clear LEDs via EC

3. COMMON EC ACCESS METHODS:
   Linux:
   • /dev/port access (requires root): os.open('/dev/port', os.O_RDWR)
   • outb/inb operations: ctypes or custom kernel module
   • ACPI interface: /sys/kernel/debug/ec/ec0/io (if available)

   Windows:
   • Direct port I/O via WinIo, InpOut32, or similar libraries
   • WMI interface if available
   • Custom driver development

4. EXAMPLE LINUX IMPLEMENTATION:
   ```python
   import os
   import ctypes

   def ec_write_byte(port, value):
       # Requires root privileges
       with open('/dev/port', 'r+b', 0) as f:
           f.seek(port)
           f.write(bytes([value]))

   def ec_read_byte(port):
       with open('/dev/port', 'rb', 0) as f:
           f.seek(port)
           return ord(f.read(1))
   ```

5. SAFETY WARNINGS:
   ⚠ CAUTION: Incorrect EC commands can cause:
   • System instability or crashes
   • Hardware damage
   • BIOS/UEFI corruption
   • Permanent device malfunction

   ⚠ ALWAYS:
   • Test on disposable hardware first
   • Create system backups
   • Document all commands before use
   • Start with read-only operations
   • Implement proper error handling

6. DEVICE-SPECIFIC EXAMPLES:
   Different manufacturers use different EC interfaces:
   • Framework laptops: Specific EC protocol
   • System76: Open-source EC firmware
   • Chromebooks: Chrome EC with specific commands
   • Gaming laptops: Often proprietary protocols

7. PERMISSIONS REQUIRED:
   • Linux: root privileges or specific group membership
   • Windows: Administrator privileges or driver installation
   • macOS: System-level access (may require SIP disable)

8. TESTING PROCEDURE:
   • Start with reading EC status registers
   • Test brightness control first (safest)
   • Implement color control incrementally
   • Add comprehensive error handling
   • Test all edge cases thoroughly

CURRENT STATUS:
===============
This is currently a PLACEHOLDER implementation. The GUI provides the interface,
but the actual EC communication must be implemented by you based on your
specific hardware requirements.

If you implement EC Direct successfully, please consider contributing your
implementation back to the project to help other users with similar hardware!
"""

        self.logger.warning(f"{msg_title}: EC Direct selected but requires implementation")
        self.log_to_gui_diag_area(f"{msg_title}:\n{msg_body}", "warning")

        if self.root.winfo_exists():
            # Show a condensed version in the popup, with full details in the log
            popup_msg = """EC Direct mode requires manual implementation for your specific hardware.

This is an ADVANCED feature that involves:
• Direct Embedded Controller (EC) communication
• Hardware-specific research and coding
• Root/Administrator privileges
• Risk of system instability if done incorrectly

FULL IMPLEMENTATION GUIDE has been written to:
• Application Log (Diagnostics tab)
• Log files in the logs directory

⚠ WARNING: Incorrect EC commands can damage hardware!
Only proceed if you have embedded systems experience.

The application will use fallback methods (ectool) until EC Direct is implemented."""
            messagebox.showwarning(msg_title, popup_msg, parent=self.root)

    def reset_settings(self):
        if self.root.winfo_exists() and messagebox.askyesno("Confirm Reset", "Reset all settings to defaults? This cannot be undone.", parent=self.root):
            self._stop_all_visuals_and_clear_hardware() # Stop effects, clear HW based on old settings
            self.settings.reset_to_defaults()
            self.load_saved_settings() # Load default values into GUI controls
            # Apply a default visual state (e.g., default color or off)
            default_color_on_reset = RGBColor.from_dict(default_settings["current_color"]) # Or RGBColor(0,0,0) for off
            self.apply_static_color(default_color_on_reset.to_hex())
            self.log_status("All settings reset to defaults.")
            if self.root.winfo_exists(): 
                messagebox.showinfo("Settings Reset", "All settings have been reset to their default values.", parent=self.root)

    def export_settings(self):
        self.save_current_gui_state_to_settings() # Ensure current GUI state is in self.settings before export
        fpath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Settings File","*.json"), ("All Files","*.*")], title="Export Application Settings", parent=self.root)
        if fpath:
            try:
                with open(fpath, 'w', encoding='utf-8') as f: 
                    json.dump(self.settings._settings, f, indent=2) # Access underlying dict
                self.log_status(f"Settings exported to {fpath}")
                if self.root.winfo_exists(): 
                    messagebox.showinfo("Export Successful", f"Settings exported to:\n{fpath}", parent=self.root)
            except Exception as e:
                self.log_status(f"Export failed: {e}", "error")
                if self.root.winfo_exists(): 
                    messagebox.showerror("Export Error", f"Could not export settings: {e}", parent=self.root)

    def import_settings(self):
        fpath = filedialog.askopenfilename(filetypes=[("JSON Settings File","*.json"), ("All Files","*.*")], title="Import Application Settings", parent=self.root)
        if fpath:
            try:
                self._stop_all_visuals_and_clear_hardware() # Prepare for new settings
                with open(fpath, 'r', encoding='utf-8') as f: 
                    imported_data = json.load(f)
                self.settings.update(imported_data)
                self.settings.save_settings() # Update and save
                self.load_saved_settings() # Load newly imported settings into GUI

                # After loading, attempt to apply the startup settings based on the new configuration
                # This will effectively "activate" the imported settings
                self.log_status(f"Settings imported from {fpath}. Attempting to apply.")
                self._restore_settings_on_startup() # Try to apply, similar to startup
                if self.root.winfo_exists(): 
                    messagebox.showinfo("Import Successful", f"Settings imported from:\n{fpath}\nApplied active settings.", parent=self.root)

            except json.JSONDecodeError as e_json:
                self.log_status(f"Import failed: Invalid JSON file. {e_json}", "error")
                if self.root.winfo_exists(): 
                    messagebox.showerror("Import Error", f"Failed to import settings: Invalid JSON file.\n{e_json}", parent=self.root)
            except Exception as e:
                self.log_status(f"Import failed: {e}", "error")
                if self.root.winfo_exists(): 
                    messagebox.showerror("Import Error", f"Failed to import settings: {e}", parent=self.root)

    def create_desktop_launcher(self):
        try:
            python_exe = sys.executable # Path to current python interpreter
            app_file_path = Path(__file__).resolve() # Full path to this controller.py
            
            # Determine the top-level package directory and module to run
            # Assuming structure: .../rgb_controller_finalv2/gui/controller.py
            # And main execution is via: python -m rgb_controller_finalv2
            # where rgb_controller_finalv2/__main__.py exists.

            module_to_run = None
            working_dir_for_launcher = None
            
            # Try to find the 'rgb_controller_finalv2' directory assuming __file__ is inside gui/
            # Path(__file__) is .../rgb_controller_finalv2/gui/controller.py
            # Path(__file__).parent is .../rgb_controller_finalv2/gui/
            # Path(__file__).parent.parent is .../rgb_controller_finalv2/
            project_root_dir = app_file_path.parent.parent
            
            if (project_root_dir / "__main__.py").exists() and project_root_dir.name == "rgb_controller_finalv2":
                module_to_run = project_root_dir.name # Should be "rgb_controller_finalv2"
                working_dir_for_launcher = project_root_dir.parent # Dir *containing* "rgb_controller_finalv2"
                self.logger.info(f"Desktop Launcher: Determined module '{module_to_run}' and working dir '{working_dir_for_launcher}'")
            else:
                # Fallback or alternative structure logic
                self.logger.warning("Desktop Launcher: Could not reliably determine project root and module for '-m' execution from standard structure. Using fallback logic.")
                if module_to_run is None: # Fallback if previous logic failed
                    module_to_run = APP_NAME.lower().replace(" ", "_").replace("-","_") # A guess
                    working_dir_for_launcher = Path.cwd() # Default to CWD
                    self.logger.warning(f"Desktop Launcher: Fallback to module '{module_to_run}' and CWD '{working_dir_for_launcher}'. This might not be optimal.")

            if not module_to_run or not working_dir_for_launcher:
                self.logger.error("Desktop Launcher: Critical failure to determine module or working directory.")
                if self.root.winfo_exists(): 
                    messagebox.showerror("Launcher Error", "Could not determine necessary paths for launcher script. Please check logs.", parent=self.root)
                return

            import shlex
            exec_cmd = f"{shlex.quote(str(python_exe))} -m {shlex.quote(str(module_to_run))}"
            launcher_filename_base = module_to_run # Use the module name for the .desktop file too

            self.logger.info(f"Launcher details: Exec='{exec_cmd}', Path='{str(working_dir_for_launcher)}', FilenameBase='{launcher_filename_base}'")

        except Exception as e:
            self.logger.error(f"Could not determine execution paths for launcher: {e}", exc_info=True)
            if self.root.winfo_exists(): 
                messagebox.showerror("Launcher Error", f"Could not determine script/package path: {e}", parent=self.root)
            return

        if platform.system() == "Linux":
            desktop_dir = Path.home() / ".local" / "share" / "applications"
            desktop_dir.mkdir(parents=True, exist_ok=True)
            desktop_file_path = desktop_dir / f"{launcher_filename_base}.desktop"

            # Try to find an icon
            icon_name_or_path = "input-keyboard" # Generic fallback
            # Check for assets/icon.png relative to controller.py, then relative to project root
            icon_path_candidates = [
                app_file_path.parent / "assets" / "icon.png",       # gui/assets/icon.png
                project_root_dir / "assets" / "icon.png" if project_root_dir else None # rgb_controller_finalv2/assets/icon.png
            ]
            for candidate in icon_path_candidates:
                if candidate and candidate.exists() and candidate.is_file():
                    icon_name_or_path = str(candidate.resolve())
                    self.logger.info(f"Desktop Launcher: Using icon path '{icon_name_or_path}'")
                    break

            content = (f"[Desktop Entry]\nVersion=1.0\nName={APP_NAME}\nComment=Control RGB Keyboard Lighting (v{VERSION})\nExec={exec_cmd}\n"
                      f"Icon={icon_name_or_path}\nTerminal=false\nType=Application\nCategories=Utility;Settings;HardwareSettings;System;\n"
                      f"Keywords=RGB;Keyboard;Chromebook;LED;Lighting;Control;\nPath={str(working_dir_for_launcher)}\nStartupNotify=true\nX-GNOME-UsesNotifications=true\n")
            try:
                desktop_file_path.write_text(content, encoding='utf-8')
                desktop_file_path.chmod(0o755) # rwxr-xr-x
                msg = f"Desktop launcher created/updated:\n{desktop_file_path}\n\nIt may require a logout/login or running 'update-desktop-database ~/.local/share/applications' in your terminal for your desktop environment to see it."
                if self.root.winfo_exists(): 
                    messagebox.showinfo("Launcher Created", msg, parent=self.root)
                self.logger.info(f"Desktop launcher created/updated: {desktop_file_path}")
            except Exception as e:
                log_error_with_context(self.logger, e, {"path": str(desktop_file_path)})
                if self.root.winfo_exists(): 
                    messagebox.showerror("Launcher Error", f"Failed to write desktop file: {e}", parent=self.root)
        else:
            if self.root.winfo_exists(): 
                messagebox.showinfo("Not Supported", "Desktop launcher creation is currently only supported on Linux.", parent=self.root)

    def load_saved_settings(self):
        self._loading_settings = True
        self.logger.info("Loading saved settings into GUI controls...")
        try:
            self.brightness_var.set(self.settings.get("brightness", default_settings['brightness'])) # Text var updates via trace
            current_color_data = self.settings.get("current_color", default_settings['current_color'])
            current_color_obj = RGBColor.from_dict(current_color_data)
            if hasattr(self, 'color_display') and self.color_display.winfo_exists(): 
                self.color_display.config(bg=current_color_obj.to_hex())
            self.current_color_var.set(current_color_obj.to_hex())

            effect_speed_setting = self.settings.get("effect_speed", default_settings['effect_speed']) # Internal 1-10
            self.speed_var.set(effect_speed_setting * 10) # GUI 10-100
            if hasattr(self, 'speed_label') and self.speed_label.winfo_exists(): 
                self.speed_label.config(text=f"{self.speed_var.get()}%")

            zone_colors_list_data = self.settings.get("zone_colors", default_settings['zone_colors'])
            self.zone_colors = [RGBColor.from_dict(d) for d in zone_colors_list_data[:NUM_ZONES]]
            while len(self.zone_colors) < NUM_ZONES: 
                self.zone_colors.append(RGBColor(0,0,0)) # Pad if needed
            self.zone_colors = self.zone_colors[:NUM_ZONES] # Truncate if too many
            if hasattr(self, 'zone_displays'):
                for i, zd_widget in enumerate(self.zone_displays): # zd_widget is the tk.Label
                    if i < len(self.zone_colors) and zd_widget.winfo_exists():
                        zd_widget.config(bg=self.zone_colors[i].to_hex())

            self.gradient_start_color_var.set(self.settings.get("gradient_start_color", default_settings['gradient_start_color']))
            if hasattr(self, 'gradient_start_display') and self.gradient_start_display.winfo_exists(): 
                self.gradient_start_display.config(bg=self.gradient_start_color_var.get())
            self.gradient_end_color_var.set(self.settings.get("gradient_end_color", default_settings['gradient_end_color']))
            if hasattr(self, 'gradient_end_display') and self.gradient_end_display.winfo_exists(): 
                self.gradient_end_display.config(bg=self.gradient_end_color_var.get())

            self.effect_var.set(self.settings.get("effect_name", default_settings['effect_name'])) # This will trigger on_effect_change if not loading
            self.effect_color_var.set(self.settings.get("effect_color", default_settings['effect_color']))
            if hasattr(self, 'effect_color_display') and self.effect_color_display.winfo_exists(): 
                self.effect_color_display.config(bg=self.effect_color_var.get())
            self.effect_rainbow_mode_var.set(self.settings.get("effect_rainbow_mode", default_settings['effect_rainbow_mode']))

            self.update_effect_controls_visibility() # Crucial after effect vars are set

            self.restore_startup_var.set(self.settings.get("restore_on_startup", default_settings['restore_on_startup']))
            self.auto_apply_var.set(self.settings.get("auto_apply_last_setting", default_settings['auto_apply_last_setting']))
            self.control_method_var.set(self.settings.get("last_control_method", default_settings['last_control_method']))
            if hasattr(self, 'minimize_to_tray_var'): 
                self.minimize_to_tray_var.set(self.settings.get("minimize_to_tray", default_settings.get("minimize_to_tray", True)))

            self.logger.info("GUI controls updated from loaded settings.")
        except Exception as e:
            log_error_with_context(self.logger, e, {"action":"load_settings_into_gui_controls"})
            if self.root.winfo_exists(): 
                messagebox.showwarning("Settings Load Issue", f"Could not fully load settings into GUI: {e}", parent=self.root)
        finally:
            self._loading_settings = False
            
        # After all settings are loaded, show preview for loaded effect without applying to hardware
        effect_name_on_load = self.effect_var.get()
        if effect_name_on_load != "None" and effect_name_on_load not in ["Static Color", "Static Zone Colors", "Static Rainbow", "Static Gradient"]:
            preview_method_name = f"preview_{effect_name_on_load.lower().replace(' ','_').replace('(','').replace(')','')}"
            if hasattr(self, preview_method_name) and callable(getattr(self, preview_method_name)):
                self.start_preview_animation(getattr(self, preview_method_name))
            else:
                self._update_generic_preview_on_param_change()
        elif effect_name_on_load == "Static Color":
            self.preview_static_color()
            self.update_preview_keyboard()
        elif effect_name_on_load == "Static Zone Colors":
            self.update_preview_keyboard()
        elif effect_name_on_load == "Static Rainbow":
            self.preview_static_rainbow(0)
            self.update_preview_keyboard()
        elif effect_name_on_load == "Static Gradient":
            self.preview_static_gradient(0)
            self.update_preview_keyboard()
        else:
            # Clear preview for "None"
            for i in range(NUM_ZONES):
                self.zone_colors[i] = RGBColor(0,0,0)
            self.update_preview_keyboard()

    def save_current_gui_state_to_settings(self):
        self.logger.debug("Saving current GUI state to settings...")
        settings_to_update = {
            "brightness": self.brightness_var.get(),
            "effect_speed": max(1,min(10, int(self.speed_var.get()/10.0 + 0.5))), # internal 1-10
            "current_color": RGBColor.from_hex(self.current_color_var.get()).to_dict(),
            "zone_colors": [zc.to_dict() for zc in self.zone_colors],
            "effect_name": self.effect_var.get(),
            "effect_color": self.effect_color_var.get(),
            "effect_rainbow_mode": self.effect_rainbow_mode_var.get(),
            "gradient_start_color": self.gradient_start_color_var.get(),
            "gradient_end_color": self.gradient_end_color_var.get(),
            "restore_on_startup": self.restore_startup_var.get(),
            "auto_apply_last_setting": self.auto_apply_var.get(),
            "last_control_method": self.control_method_var.get(),
        }
        if hasattr(self, 'minimize_to_tray_var'): 
            settings_to_update["minimize_to_tray"] = self.minimize_to_tray_var.get()

        # Determine last_mode based on current effect_var selection
        current_effect = self.effect_var.get()
        if current_effect == "Static Color": 
            settings_to_update["last_mode"] = "static"
        elif current_effect == "Static Zone Colors": 
            settings_to_update["last_mode"] = "zones"
        elif current_effect == "Static Rainbow": 
            settings_to_update["last_mode"] = "rainbow_zones"
        elif current_effect == "Static Gradient": 
            settings_to_update["last_mode"] = "gradient_zones"
        elif current_effect != "None": 
            settings_to_update["last_mode"] = "effect"
        # else: Do not update last_mode if effect is "None"

        self.settings.update(settings_to_update)
        self.settings.save_settings()
        self.logger.info("Current GUI state saved to settings.")

    # Preview methods for effects
    def preview_color_cycle(self, frame_count: int):
        """Preview color cycle effect - cycles through different colors"""
        cycle_speed = 0.1
        hue = (frame_count * cycle_speed) % 1.0
        rgb_float = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
        color = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
        
        for i in range(NUM_ZONES):
            self.zone_colors[i] = color
        self.update_preview_keyboard()

    def preview_color_cycle_advanced(self, frame_count: int):
        """Advanced color cycle with smooth transitions"""
        try:
            # Multi-zone color cycling with phase offset
            base_hue = (frame_count * 0.02) % 1.0
            
            for i in range(NUM_ZONES):
                # Each zone has a slight phase offset for wave effect
                zone_hue = (base_hue + (i * 0.1)) % 1.0
                
                # Add breathing effect
                saturation = 0.8 + 0.2 * math.sin(frame_count * 0.1)
                value = 0.7 + 0.3 * math.sin(frame_count * 0.15 + i * 0.2)
                
                rgb_float = colorsys.hsv_to_rgb(zone_hue, saturation, value)
                self.zone_colors[i] = RGBColor(
                    int(rgb_float[0] * 255), 
                    int(rgb_float[1] * 255), 
                    int(rgb_float[2] * 255)
                )
            
            self.update_preview_keyboard()
        except Exception as e:
            self.logger.error(f"Error in advanced color cycle preview: {e}")
            # Fallback to simple preview
            self.preview_color_cycle(frame_count)

    def preview_rainbow_zones_cycle(self, frame_count: int):
        """Preview rainbow zones cycle - rainbow pattern that shifts"""
        for i in range(NUM_ZONES):
            hue = ((i + frame_count * 0.05) / NUM_ZONES) % 1.0
            rgb_float = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            self.zone_colors[i] = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
        self.update_preview_keyboard()

    def preview_reactive(self, frame_count: int):
        """Preview reactive effect - keys light up when 'pressed' """
        # Simulate random key presses for preview
        for i in range(NUM_ZONES):
            # Create pseudo-random activation pattern
            activation = (frame_count + i * 7) % 40
            if activation < 5:  # Key "pressed" for 5 frames
                try:
                    color = RGBColor.from_hex(self.effect_color_var.get())
                except ValueError:
                    color = RGBColor(255, 255, 255)
                self.zone_colors[i] = color
            else:
                self.zone_colors[i] = RGBColor(0, 0, 0)  # Off when not pressed
        self.update_preview_keyboard()

    def preview_anti_reactive(self, frame_count: int):
        """Preview anti-reactive effect - all on except when 'pressed' """
        try:
            base_color = RGBColor.from_hex(self.effect_color_var.get())
        except ValueError:
            base_color = RGBColor(255, 255, 255)
            
        for i in range(NUM_ZONES):
            # Create pseudo-random activation pattern
            activation = (frame_count + i * 7) % 40
            if activation < 5:  # Key "pressed" for 5 frames
                self.zone_colors[i] = RGBColor(0, 0, 0)  # Off when pressed
            else:
                self.zone_colors[i] = base_color  # On when not pressed
        self.update_preview_keyboard()

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

    def preview_wave(self, frame_count: int):
        """Preview wave effect - sine wave moving across zones"""
        try:
            base_color_rgb = RGBColor.from_hex(self.effect_color_var.get())
        except ValueError:
            base_color_rgb = RGBColor(0,100,255)
        is_rainbow = self.effect_rainbow_mode_var.get()

        for i in range(NUM_ZONES):
            # Sine wave pattern moving across zones
            wave_position = (frame_count * 0.3 + i * 2) % (NUM_ZONES * 4)
            intensity = (math.sin(wave_position * 0.5) + 1) / 2
            
            if is_rainbow:
                hue = ((i + frame_count * 0.02) / NUM_ZONES) % 1.0
                rgb_float = colorsys.hsv_to_rgb(hue, 1.0, intensity)
                self.zone_colors[i] = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
            else:
                self.zone_colors[i] = RGBColor(
                    int(base_color_rgb.r * intensity),
                    int(base_color_rgb.g * intensity),
                    int(base_color_rgb.b * intensity)
                )
        
        self.update_preview_keyboard()

    def preview_raindrop(self, frame_count: int):
        if not hasattr(self, 'zone_colors') or len(self.zone_colors) < NUM_ZONES: 
            return
        try: 
            base_color_rgb = RGBColor.from_hex(self.effect_color_var.get())
        except ValueError: 
            base_color_rgb = RGBColor(0,0,0) # Default to black on error
        is_rainbow = self.effect_rainbow_mode_var.get()

        # Animate colors across zones for raindrop effect
        for i in range(NUM_ZONES):
            if is_rainbow:
                # Moving rainbow pattern
                hue = ((i + frame_count * 0.1) / NUM_ZONES) % 1.0
                rgb_float = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                self.zone_colors[i] = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
            else:
                # Raindrop effect with base color
                drop_position = (frame_count % (NUM_ZONES * 2))
                if drop_position < NUM_ZONES and drop_position == i:
                    self.zone_colors[i] = base_color_rgb
                else:
                    # Fade to black
                    fade = max(0, 1.0 - abs(i - drop_position) * 0.3)
                    self.zone_colors[i] = RGBColor(
                        int(base_color_rgb.r * fade),
                        int(base_color_rgb.g * fade),
                        int(base_color_rgb.b * fade)
                    )
        
        self.update_preview_keyboard()

    def preview_static_per_zone(self, frame_count): # frame_count is unused but part of signature
        # zone_colors is already set correctly, just update display
        self.update_preview_keyboard()

    def preview_static_rainbow(self, frame_count): # frame_count is unused
        for i in range(NUM_ZONES):
            hue = (i / float(NUM_ZONES)) % 1.0 if NUM_ZONES > 0 else 0.0
            rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            self.zone_colors[i] = RGBColor(int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))

    def preview_static_gradient(self, frame_count): # frame_count is unused
        try:
            sc = RGBColor.from_hex(self.gradient_start_color_var.get())
            ec = RGBColor.from_hex(self.gradient_end_color_var.get())
        except ValueError: # Handle invalid hex string gracefully
            sc, ec = RGBColor(0,0,0), RGBColor(0,0,0) # Default to black gradient

        for i in range(NUM_ZONES):
            ratio = i / float(NUM_ZONES - 1) if NUM_ZONES > 1 else 0.0
            r = int(sc.r*(1-ratio)+ec.r*ratio)
            g = int(sc.g*(1-ratio)+ec.g*ratio)
            b = int(sc.b*(1-ratio)+ec.b*ratio)
            self.zone_colors[i] = RGBColor(r, g, b)

    def preview_breathing(self, frame_count: int):
        """Preview breathing effect"""
        try: 
            base_color_rgb = RGBColor.from_hex(self.effect_color_var.get())
        except ValueError: 
            base_color_rgb = RGBColor(255,255,255)
        is_rainbow = self.effect_rainbow_mode_var.get()

        # Breathing effect with sine wave
        breath_cycle = (math.sin(frame_count * 0.1) + 1) / 2  # 0 to 1
        
        for i in range(NUM_ZONES):
            if is_rainbow:
                hue = (i / NUM_ZONES) % 1.0
                rgb_float = colorsys.hsv_to_rgb(hue, 1.0, breath_cycle)
                self.zone_colors[i] = RGBColor(int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))
            else:
                self.zone_colors[i] = RGBColor(
                    int(base_color_rgb.r * breath_cycle),
                    int(base_color_rgb.g * breath_cycle),
                    int(base_color_rgb.b * breath_cycle)
                )
        
        self.update_preview_keyboard()

    def start_preview_animation(self, preview_function: Callable[[int], None]):
        self.stop_preview_animation() # Cancel any existing animation
        self.preview_animation_active = True
        self.preview_function_callable = preview_function # Store the function to call
        self._preview_frame_count = 0 # Reset frame count for the new animation
        self._run_preview_animation() # Start the animation loop

    def stop_preview_animation(self):
        if self.preview_animation_id:
            self.root.after_cancel(self.preview_animation_id)
            self.preview_animation_id = None
        self.preview_animation_active = False

    def _run_preview_animation(self):
        if not self.preview_animation_active or not hasattr(self, 'preview_function_callable') or not callable(self.preview_function_callable):
            self.preview_animation_active = False
            return # Stop if no longer active or no function
        try:
            self.preview_function_callable(self._preview_frame_count) # Call the effect's preview logic
            self._preview_frame_count += 1
        except Exception as e:
            self.logger.error(f"Error in preview animation function '{getattr(self.preview_function_callable, '__name__', 'unknown')}': {e}", exc_info=True)
            self.stop_preview_animation()
            return # Stop on error

        if self.preview_animation_active: # If still active, schedule next frame
            delay_ms = int(ANIMATION_FRAME_DELAY * 1000) # Convert seconds to ms
            self.preview_animation_id = self.root.after(delay_ms, self._run_preview_animation)

    def toggle_fullscreen(self, event=None):
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes("-fullscreen", self.is_fullscreen)
        text = "Exit Fullscreen (F11/ESC)" if self.is_fullscreen else "Enter Fullscreen (F11)"
        if hasattr(self, 'fullscreen_button') and self.fullscreen_button.winfo_exists(): 
            self.fullscreen_button.config(text=text)

    def exit_fullscreen(self, event=None):
        if self.is_fullscreen: 
            self.toggle_fullscreen()

    def log_status(self, message, level="info"): # Level can be "info", "warning", "error"
        log_level_map = {"info": logging.INFO, "warning": logging.WARNING, "error": logging.ERROR}
        self.logger.log(log_level_map.get(level.lower(), logging.INFO), message)

        if hasattr(self, 'status_var') and self.status_var: # Check if status_var exists
            try:
                self.status_var.set(message[:100]) # Truncate for status bar display
            except tk.TclError:
                self.logger.debug("TclError setting status_var (likely during shutdown).")

    def refresh_hardware_status(self):
        if not hasattr(self, 'hardware_status_text') or not self.hardware_status_text.winfo_exists(): 
            return
        try:
            hw_info = self.hardware.get_hardware_info() # This should return a dict or well-formatted string
            # If hw_info is a dict, pretty print it. If string, use as is.
            if isinstance(hw_info, dict):
                status_text = json.dumps(hw_info, indent=2, default=str) # Use default=str for non-serializable types
            else:
                status_text = str(hw_info) # Assume it's already formatted

            self.hardware_status_text.config(state=tk.NORMAL)
            self.hardware_status_text.delete("1.0", tk.END)
            self.hardware_status_text.insert("1.0", status_text)
            self.hardware_status_text.config(state=tk.DISABLED)
            self.log_status("Hardware status refreshed.")
        except Exception as e:
            self.logger.error(f"Failed to refresh hardware status: {e}", exc_info=True)
            if self.hardware_status_text.winfo_exists(): # Check again before writing error
                self.hardware_status_text.config(state=tk.NORMAL)
                self.hardware_status_text.insert(tk.END, f"\nError refreshing hardware status: {e}")
                self.hardware_status_text.config(state=tk.DISABLED)

    def show_system_info(self):
        target_widget = getattr(self, 'system_info_display_text', None)
        if not target_widget or not target_widget.winfo_exists():
            self.logger.warning("System info display widget not available.")
            return

        log_system_info(self.logger) # Log detailed info to file/console via existing utility

        target_widget.config(state=tk.NORMAL)
        target_widget.delete("1.0", tk.END)
        try:
            log_base_dir = SETTINGS_FILE.parent
            log_dir_path = log_base_dir / "logs"
            info_lines = [
                f"Application Name: {APP_NAME} v{VERSION}",
                f"System: {platform.system()} {platform.release()} ({platform.machine()})",
                f"Platform: {platform.platform()}",
                f"Python Version: {sys.version.splitlines()[0]}",
                f"Python Executable: {sys.executable}",
                f"GUI Controller Script Path: {Path(__file__).resolve()}",
                f"Current Working Directory: {Path.cwd()}",
                f"Settings File Path: {self.settings.config_file if hasattr(self.settings, 'config_file') else 'N/A'}",
                f"Log Directory: {log_dir_path.resolve()}",
                f"Pystray Available: {PYSTRAY_AVAILABLE}",
                f"PIL (Pillow) Available: {PIL_AVAILABLE}",
                f"Keyboard Library Available: {KEYBOARD_LIB_AVAILABLE}",
                f"Hotkey Setup Attempted: {self._hotkey_setup_attempted}",
                f"Brightness Hotkeys Working: {self._brightness_hotkeys_working}",
            ]
            if platform.system() == "Linux":
                info_lines.append(f"XDG_SESSION_TYPE: {os.environ.get('XDG_SESSION_TYPE', 'Not set')}")
                info_lines.append(f"DISPLAY: {os.environ.get('DISPLAY', 'Not set')}")
        except Exception as e:
            info_lines = [f"Error gathering system info for display: {e}"]

        target_widget.insert(tk.END, "\n".join(info_lines))
        target_widget.config(state=tk.DISABLED)
        self.log_status("System info display updated in GUI.")

    def show_log_locations(self):
        target_widget = getattr(self, 'gui_log_text_widget', None) # Changed to gui_log_text_widget for relevance
        if not target_widget or not target_widget.winfo_exists():
            self.logger.warning("GUI log display widget not available for showing log locations.")
            return

        log_dir = SETTINGS_FILE.parent / "logs"
        fallback_log_dir = Path.home()
        fallback_log_name_pattern = f".{APP_NAME.lower().replace(' ','_')}_gui_fallback.log"

        target_widget.config(state=tk.NORMAL)
        target_widget.delete("1.0", tk.END)
        target_widget.insert(tk.END, "Log File Locations:\n" + "="*20 + "\n\n")
        target_widget.insert(tk.END, f"Primary GUI Application Log Directory:\n  {log_dir.resolve()}\n\n")

        if log_dir.exists():
            log_files = sorted(log_dir.glob("rgb_controller_gui_*.log"), key=os.path.getmtime, reverse=True)[:5] # Get 5 most recent
            target_widget.insert(tk.END, "Recent GUI log files (in primary directory):\n")
            if log_files:
                for lf in log_files: 
                    target_widget.insert(tk.END, f"  - {lf.name} ({(lf.stat().st_size / 1024):.1f} KB)\n")
            else: 
                target_widget.insert(tk.END, "  (No GUI .log files matching pattern found in primary log directory)\n")
        else: 
            target_widget.insert(tk.END, "Primary application log directory does not exist.\n")

        target_widget.insert(tk.END, f"\nFallback GUI Log File (if primary fails):\n  {fallback_log_dir.resolve() / fallback_log_name_pattern}\n")
        # Add other log locations if your app has them (e.g., core module logs)

        target_widget.config(state=tk.DISABLED)
        self.log_status("Log file locations displayed in GUI log area.")

    def run_comprehensive_test(self):
        self.log_status("--- Comprehensive Hardware Test Start ---", "info")
        self.log_to_gui_diag_area("--- Starting Comprehensive Hardware Test ---", "info")

        if not self.hardware.wait_for_detection(timeout=2.0) or not self.hardware.is_operational():
            msg = "Hardware not detected, not operational, or detection timed out. Cannot run tests."
            if self.root.winfo_exists(): 
                messagebox.showerror("Test Error", msg, parent=self.root)
            self.log_status(f"Comprehensive Test: {msg}", "error")
            self.log_to_gui_diag_area(f"Test Error: {msg}", "error")
            return

        self.effect_manager.stop_current_effect() # Stop any software effects
        original_brightness = self.hardware.get_brightness()
        if original_brightness is None: 
            original_brightness = self.settings.get("brightness", default_settings['brightness']) # Fallback

        test_results = []
        self.log_to_gui_diag_area(f"Initial brightness from hardware: {original_brightness}% (or fallback/setting).", "info")

        # Test 1: Set Brightness
        self.log_to_gui_diag_area("Test: Setting brightness to 50%...", "info")
        if self.hardware.set_brightness(50):
            time.sleep(0.2)
            current_hw_brightness = self.hardware.get_brightness()
            if current_hw_brightness is not None and abs(current_hw_brightness - 50) <= 10: # Allow some tolerance
                test_results.append("✓ Brightness set to 50% OK.")
                self.log_to_gui_diag_area("  ✓ Brightness set to 50% reported OK by hardware.", "info")
            else:
                test_results.append(f"✗ Brightness to 50% FAILED (reads {current_hw_brightness}% from hardware).")
                self.log_to_gui_diag_area(f"  ✗ Brightness to 50% seems to have FAILED (hardware reports {current_hw_brightness}%).", "error")
        else:
            test_results.append("✗ Set brightness to 50% command failed (hardware.set_brightness returned False).")
            self.log_to_gui_diag_area("  ✗ Set brightness to 50% command failed at hardware layer.", "error")

        # Restore original brightness
        self.hardware.set_brightness(original_brightness)
        self.brightness_var.set(original_brightness) # Update GUI too
        self.log_to_gui_diag_area(f"Test: Brightness restored to {original_brightness}%.", "info")
        time.sleep(0.2)

        # Test 2: Set all zones to RED
        self.log_to_gui_diag_area("Test: Setting all zones to RED (255,0,0)...", "info")
        red_color = RGBColor(255,0,0)
        if self.hardware.set_all_leds_color(red_color):
            test_results.append("✓ All zones RED OK.")
            self.log_to_gui_diag_area("  ✓ All zones RED command sent successfully.", "info")
            time.sleep(1) # Visual confirmation time
        else:
            test_results.append("✗ All zones RED FAILED (set_all_leds_color returned False).")
            self.log_to_gui_diag_area("  ✗ All zones RED command failed at hardware layer.", "error")

        # Test 3: Clear all LEDs
        self.log_to_gui_diag_area("Test: Clearing all LEDs (setting to BLACK)...", "info")
        if self.hardware.clear_all_leds(): # Assumes clear_all_leds sets to black
            test_results.append("✓ Clear LEDs OK.")
            self.log_to_gui_diag_area("  ✓ Clear LEDs command sent successfully.", "info")
            time.sleep(0.2)
        else:
            test_results.append("✗ Clear LEDs FAILED (clear_all_leds returned False).")
            self.log_to_gui_diag_area("  ✗ Clear LEDs command failed at hardware layer.", "error")

        self.log_status("--- Comprehensive Test End ---", "info")
        self.log_to_gui_diag_area("--- Comprehensive Hardware Test Finished ---", "info")
        self.log_to_gui_diag_area("Test Results Summary:\n" + "\n".join(test_results if test_results else ["No tests effectively run or all failed."]), "info")

        if self.root.winfo_exists():
            messagebox.showinfo("Hardware Test Results", "\n".join(test_results) if test_results else "No tests were effectively run or all failed.", parent=self.root)

        self.log_status("Restoring previous settings after test...")
        self.log_to_gui_diag_area("Attempting to restore previous settings post-test...", "info")
        self._restore_settings_on_startup() # Restore the actual user settings

    def test_ectool(self):
        self.log_status("Testing ectool availability/functionality...")
        self.log_to_gui_diag_area("--- Testing ectool ---", "info")
        if hasattr(self.hardware, '_detect_ectool'):
            self.log_to_gui_diag_area("Re-running ectool detection via hardware controller...", "info")
            self.hardware._detect_ectool() # Re-run detection if method exists (might be private)
            # Or call a public method like: self.hardware.check_control_method_availability("ectool")
        elif hasattr(self.hardware, 'get_ectool_version_or_status'): # Prefer a dedicated method
            ectool_status = self.hardware.get_ectool_version_or_status()
            self.log_to_gui_diag_area(f"ectool status from hardware controller: {ectool_status}", "info")
        else:
            self.log_to_gui_diag_area("Hardware controller does not have a direct ectool test method. Refreshing general status.", "warning")

        self.refresh_hardware_status() # Update diagnostics tab
        msg = "ectool detection/status check initiated. Check Diagnostics tab for updated hardware status. Functionality might change based on results."
        self.log_to_gui_diag_area(msg, "info")
        if self.root.winfo_exists():
            messagebox.showinfo("ectool Test", msg, parent=self.root)

    def setup_global_hotkeys_enhanced(self):
        """Enhanced hotkey setup with ALT+BRIGHTNESS priority for Ubuntu/Chromebook compatibility"""
        if not KEYBOARD_LIB_AVAILABLE:
            self.log_missing_keyboard_library()
            return

        self._hotkey_setup_attempted = True
        self.logger.info("Setting up enhanced global brightness hotkeys with ALT+BRIGHTNESS priority...")
        
        # Update UI to show setup is being attempted
        if hasattr(self, 'hotkey_status_label'):
            self.hotkey_status_label.config(text="Hotkeys: Setting up...", foreground='orange')

        try:
            # Platform-specific hotkey detection with ALT+BRIGHTNESS priority
            hotkey_config = self._detect_brightness_keys_with_alt_priority()
            
            if not hotkey_config:
                self._log_hotkey_setup_failure("No suitable brightness keys detected")
                return

            # Try to register the detected hotkeys
            success_count = 0
            for direction, config in hotkey_config.items():
                try:
                    if direction == "up":
                        keyboard.add_hotkey(config['combo'], self._handle_brightness_up_hotkey, suppress=False)
                    else:  # down
                        keyboard.add_hotkey(config['combo'], self._handle_brightness_down_hotkey, suppress=False)
                    
                    success_count += 1
                    self.logger.info(f"Successfully registered hotkey: {config['name']}")
                    
                except Exception as e_reg:
                    self.logger.error(f"Failed to register hotkey '{config['name']}': {e_reg}")
                    self.log_to_gui_diag_area(f"ERROR: Could not register hotkey '{config['name']}': {e_reg}", "error")

            if success_count > 0:
                self._brightness_hotkeys_working = True
                self._log_hotkey_success(hotkey_config, success_count)
            else:
                self._log_hotkey_setup_failure("Failed to register any hotkeys")

        except Exception as e:
            self.logger.error(f"Critical error setting up global hotkeys: {e}", exc_info=True)
            self._log_hotkey_setup_failure(f"Critical setup error: {e}")

    def _detect_brightness_keys_with_alt_priority(self) -> Optional[Dict[str, Dict[str, str]]]:
        """Detect brightness keys with priority for ALT+BRIGHTNESS combinations for Ubuntu/Chromebook"""
        system = platform.system().lower()
        
        # Priority key combinations with ALT+BRIGHTNESS first for your specific request
        key_candidates = {
            "linux": [
                # PRIORITY: ALT + actual brightness keys (for your specific request)
                {"up": "alt+XF86MonBrightnessUp", "down": "alt+XF86MonBrightnessDown"},
                {"up": "alt+XF86BrightnessUp", "down": "alt+XF86BrightnessDown"},
                # Common ALT + function key combinations
                {"up": "alt+f6", "down": "alt+f5"},  # Very common on Chromebooks
                {"up": "alt+f8", "down": "alt+f7"},
                {"up": "alt+f12", "down": "alt+f11"},
                {"up": "alt+f2", "down": "alt+f1"},
                # Direct brightness keys (without ALT) as fallback
                {"up": "XF86MonBrightnessUp", "down": "XF86MonBrightnessDown"},
                {"up": "XF86BrightnessUp", "down": "XF86BrightnessDown"},
                # Other combinations as final fallback
                {"up": "ctrl+alt+up", "down": "ctrl+alt+down"},
                {"up": "ctrl+shift+up", "down": "ctrl+shift+down"},
            ],
            "windows": [
                # Windows brightness combinations
                {"up": "alt+fn+f6", "down": "alt+fn+f5"},
                {"up": "alt+fn+f8", "down": "alt+fn+f7"},
                {"up": "fn+f6", "down": "fn+f5"},
                {"up": "fn+f8", "down": "fn+f7"},
                {"up": "alt+f6", "down": "alt+f5"},
                {"up": "ctrl+alt+up", "down": "ctrl+alt+down"},
            ],
            "darwin": [  # macOS
                {"up": "alt+fn+f2", "down": "alt+fn+f1"},
                {"up": "fn+f2", "down": "fn+f1"},
                {"up": "alt+f2", "down": "alt+f1"},
                {"up": "ctrl+alt+up", "down": "ctrl+alt+down"},
            ]
        }
        
        candidates = key_candidates.get(system, key_candidates["linux"])  # Default to Linux
        
        # Test each candidate to see if it's valid and prioritize ALT combinations
        for candidate in candidates:
            try:
                test_up = candidate["up"]
                test_down = candidate["down"]
                
                # Log the attempt with priority indication
                priority_note = " [HIGH PRIORITY - ALT+BRIGHTNESS]" if "alt+" in test_up.lower() and ("brightness" in test_up.lower() or "xf86" in test_up.lower()) else ""
                self.logger.info(f"Testing brightness key combination: Up='{test_up}', Down='{test_down}'{priority_note}")
                
                # Return the first valid combination (prioritized list)
                return {
                    "up": {
                        "combo": test_up,
                        "name": f"{test_up.replace('alt+', 'ALT + ').replace('ctrl+', 'CTRL + ').replace('fn+', 'FN + ').upper()}"
                    },
                    "down": {
                        "combo": test_down,
                        "name": f"{test_down.replace('alt+', 'ALT + ').replace('ctrl+', 'CTRL + ').replace('fn+', 'FN + ').upper()}"
                    }
                }
                
            except Exception as e:
                self.logger.debug(f"Brightness key candidate failed: {candidate}, error: {e}")
                continue
        
        return None

    def _validate_hotkey_combination(self, combo: str) -> bool:
        """Validate if a hotkey combination is actually available"""
        try:
            # Test if the key combination can be registered
            test_callback = lambda: None
            keyboard.add_hotkey(combo, test_callback, suppress=False)
            keyboard.remove_hotkey(combo)
            return True
        except Exception as e:
            self.logger.debug(f"Hotkey combination '{combo}' validation failed: {e}")
            return False

    def _log_hotkey_success(self, hotkey_config: Dict, success_count: int):
        """Log successful hotkey setup with ALT+BRIGHTNESS specific messaging"""
        up_combo = hotkey_config.get("up", {}).get("name", "Unknown")
        down_combo = hotkey_config.get("down", {}).get("name", "Unknown")
        
        # Special message for ALT+BRIGHTNESS combinations
        alt_brightness_detected = "ALT" in up_combo and ("BRIGHTNESS" in up_combo or "XF86" in up_combo)
        priority_note = "\n🎯 PERFECT! ALT+BRIGHTNESS detected - ideal for Ubuntu/Chromebook setups!" if alt_brightness_detected else ""
        
        success_msg = f"""BRIGHTNESS HOTKEYS ENABLED ✓{priority_note}

Successfully registered {success_count}/2 brightness hotkeys:
• Brightness Up: {up_combo}
• Brightness Down: {down_combo}

USAGE:
• Press the above key combinations to adjust keyboard backlight brightness
• Brightness changes in 10% increments
• Changes are immediately applied to hardware and saved to settings
• These hotkeys work independently of screen brightness controls

UBUNTU/CHROMEBOOK USERS:
• ALT+BRIGHTNESS keys are ideal since regular brightness keys control screen
• This allows independent control of keyboard vs screen brightness
• Works perfectly alongside ChromeOS/Ubuntu screen brightness controls

NOTES:
• Hotkeys work globally (even when application is not in focus)
• Some systems may require running as administrator/root for global hotkeys
• If hotkeys don't work, try the 'Test Keyboard Hotkey Names' button in Diagnostics
• You can always use the brightness slider in the GUI as an alternative"""

        self.logger.info("Brightness hotkeys successfully enabled with ALT+BRIGHTNESS priority")
        self.log_to_gui_diag_area(success_msg, "info")
        
        # Update UI status with special indication for ALT+BRIGHTNESS
        if hasattr(self, 'hotkey_status_label'):
            status_color = 'green'
            status_text = f"Hotkeys: {up_combo} / {down_combo}"
            if alt_brightness_detected:
                status_text = f"🎯 {status_text}"
            self.hotkey_status_label.config(text=status_text, foreground=status_color)

    def _log_hotkey_setup_failure(self, reason: str):
        """Log hotkey setup failure with ALT+BRIGHTNESS specific troubleshooting"""
        failure_msg = f"""BRIGHTNESS HOTKEYS DISABLED ✗

Reason: {reason}

TROUBLESHOOTING FOR ALT+BRIGHTNESS KEYS:
======================================

1. PERMISSIONS (Most Important):
   • Linux: Run with sudo for global hotkeys
     sudo python -m rgb_controller_finalv2
   • Windows: Run as Administrator
   • macOS: Grant Accessibility permissions

2. UBUNTU/CHROMEBOOK SPECIFIC:
   • Try running: sudo python -m rgb_controller_finalv2
   • Ensure you're in a graphical session (not SSH)
   • Test if ALT+F5/F6 work for screen brightness first
   • Some ChromeOS/Ubuntu setups need: sudo apt install xinput

3. LIBRARY INSTALLATION:
   • Ensure 'keyboard' library is installed: pip install keyboard
   • Try reinstalling: pip uninstall keyboard && pip install keyboard
   • On Ubuntu: sudo apt install python3-dev first

4. SYSTEM-SPECIFIC ISSUES:
   Linux/Ubuntu:
   • Install X11 development headers: sudo apt install libx11-dev
   • Some systems need: sudo apt install python3-dev
   • ChromeOS Linux container: May need additional permissions

   Windows:
   • May need Visual C++ Build Tools
   • Try: pip install keyboard --no-cache-dir

   macOS:
   • Grant Accessibility permissions in System Preferences
   • May need to disable System Integrity Protection temporarily

5. TESTING YOUR SPECIFIC KEYS:
   • Use 'Test Keyboard Hotkey Names' in Diagnostics tab
   • Look for your actual brightness key names
   • Common names: XF86MonBrightnessUp, XF86BrightnessUp, f5, f6, f7, f8

6. ALTERNATIVE SOLUTIONS:
   • Use the brightness slider in the GUI (always works)
   • Create custom keyboard shortcuts in Ubuntu Settings
   • Use xbindkeys for system-wide key binding

7. FOR YOUR UBUNTU/CHROMEBOOK SETUP:
   Since regular brightness keys control screen brightness:
   • Try: sudo python -m rgb_controller_finalv2
   • ALT+F5/F6 should control keyboard brightness
   • This is the ideal setup for your use case!

If you successfully identify your brightness key names, you can modify
the _detect_brightness_keys_with_alt_priority() method in the source code."""

        self.logger.warning(f"Brightness hotkeys setup failed: {reason}")
        self.log_to_gui_diag_area(failure_msg, "warning")
        print(failure_msg, file=sys.stderr)
        
        # Update UI status with failure indication
        if hasattr(self, 'hotkey_status_label'):
            self.hotkey_status_label.config(text="Hotkeys: Failed (see log)", foreground='red')

    def _handle_brightness_up_hotkey(self):
        """Handle brightness up hotkey press"""
        if not self.root.winfo_exists(): 
            return # App shutting down
        self.logger.debug("Brightness Up Hotkey Pressed (ALT+BRIGHTNESS)")
        current_brightness = self.brightness_var.get()
        new_brightness = min(100, current_brightness + 10) # Increase by 10, max 100
        if new_brightness != current_brightness:
            self.brightness_var.set(new_brightness) # This will trigger its trace for UI text
            # Apply to hardware via root.after to ensure it's run in main thread
            self.root.after(0, self._apply_brightness_value, new_brightness, "ALT+BRIGHTNESS_UP")

    def _handle_brightness_down_hotkey(self):
        """Handle brightness down hotkey press"""
        if not self.root.winfo_exists(): 
            return # App shutting down
        self.logger.debug("Brightness Down Hotkey Pressed (ALT+BRIGHTNESS)")
        current_brightness = self.brightness_var.get()
        new_brightness = max(0, current_brightness - 10) # Decrease by 10, min 0
        if new_brightness != current_brightness:
            self.brightness_var.set(new_brightness) # Triggers trace for UI text
            self.root.after(0, self._apply_brightness_value, new_brightness, "ALT+BRIGHTNESS_DOWN")

    def test_hotkey_names_util(self):
        """Enhanced hotkey name detection utility with ALT+BRIGHTNESS focus"""
        if not KEYBOARD_LIB_AVAILABLE:
            error_msg = """Keyboard Library Missing

The 'keyboard' library is required for hotkey name detection.

INSTALLATION:
   pip install keyboard

PERMISSIONS:
   • Linux: sudo python -m rgb_controller_finalv2
   • Windows: Run as Administrator
   • macOS: Grant Accessibility permissions"""
            
            messagebox.showerror("Keyboard Library Missing", error_msg, parent=self.root)
            self.log_to_gui_diag_area(error_msg, "error")
            return

        self.log_to_gui_diag_area("--- Starting Enhanced Keyboard Key Name Detection ---", "info")
        instructions = """BRIGHTNESS KEY DETECTION HELPER - ALT+BRIGHTNESS FOCUS

INSTRUCTIONS:
   1. A detection window will appear
   2. First try: ALT + your brightness up/down keys
   3. Then try: regular brightness keys (F5, F6, etc.)
   4. Key names will appear in the Application Log below
   5. Press ESC in the detection window to stop

UBUNTU/CHROMEBOOK USERS - WHAT TO LOOK FOR:
   • ALT + XF86MonBrightnessUp / ALT + XF86MonBrightnessDown
   • ALT + XF86BrightnessUp / ALT + XF86BrightnessDown
   • ALT + f5 / ALT + f6 (very common)
   • Look for combinations that DON'T conflict with screen brightness

This will help identify the perfect key combination for your setup!"""
        
        self.log_to_gui_diag_area(instructions, "info")
        
        if self.root.winfo_exists():
            messagebox.showinfo("Enhanced ALT+BRIGHTNESS Detection", instructions, parent=self.root)

        # Create enhanced detection window
        detection_window = tk.Toplevel(self.root)
        detection_window.title("ALT+BRIGHTNESS Key Detector - Test Your Keys!")
        detection_window.geometry("450x250")
        detection_window.transient(self.root)
        detection_window.configure(bg='#f0f0f0')
        
        # Create more informative interface
        main_frame = ttk.Frame(detection_window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        title_label = ttk.Label(main_frame, text="🔍 ALT+BRIGHTNESS Key Detection",
                               font=('Helvetica', 12, 'bold'))
        title_label.pack(pady=5)
        
        instruction_label = ttk.Label(main_frame,
                                     text="Try: ALT + brightness keys, then regular brightness keys\nKey names will appear below and in the main log",
                                     justify=tk.CENTER)
        instruction_label.pack(pady=5)
        
        self.detection_log = tk.Text(main_frame, height=8, width=55, font=('monospace', 9))
        self.detection_log.pack(pady=5, fill=tk.BOTH, expand=True)
        
        close_button = ttk.Button(main_frame, text="Close (or press ESC)",
                                 command=lambda: self._close_detection_window(detection_window))
        close_button.pack(pady=5)
        
        detection_window.focus_set()
        
        # Enhanced callback with ALT+BRIGHTNESS focus
        def enhanced_key_event_handler(event):
            try:
                # Log detailed information about the key event
                timestamp = datetime.now().strftime("%H:%M:%S")
                event_info = f"[{timestamp}] Key: '{event.name}'"
                
                if hasattr(event, 'scan_code'):
                    event_info += f", Scan: {event.scan_code}"
                
                event_info += f", Type: {event.event_type}"
                
                # Special highlighting for ALT+BRIGHTNESS combinations
                is_alt_brightness = "alt" in event.name.lower() and any(keyword in event.name.lower() for keyword in
                                                                       ['brightness', 'xf86', 'f5', 'f6', 'f7', 'f8'])
                is_brightness_key = any(keyword in event.name.lower() for keyword in
                                       ['brightness', 'xf86', 'f5', 'f6', 'f7', 'f8'])
                
                if is_alt_brightness:
                    event_info += " 🎯 PERFECT ALT+BRIGHTNESS COMBO!"
                elif is_brightness_key:
                    event_info += " ⭐ BRIGHTNESS KEY (try with ALT)"
                
                # Log to both GUI log and detection window
                log_msg = f"Key Event: {event_info}"
                self.logger.info(log_msg)
                self.root.after(0, self.log_to_gui_diag_area, log_msg, "info")
                
                # Update detection window log
                if hasattr(self, 'detection_log') and self.detection_log.winfo_exists():
                    self.detection_log.insert(tk.END, event_info + "\n")
                    self.detection_log.see(tk.END)
                
                # Close on ESC
                if event.name == 'esc' and event.event_type == keyboard.KEY_DOWN:
                    self.root.after(0, lambda: self._close_detection_window(detection_window))
                    return False  # Signal to unhook
                    
            except Exception as e:
                error_msg = f"Error in key detection: {e}"
                self.logger.error(error_msg)
                self.root.after(0, self.log_to_gui_diag_area, error_msg, "error")
            
            return True  # Continue capturing

        # Set up keyboard hook
        try:
            hook_id = keyboard.hook(enhanced_key_event_handler)
            detection_window._hook_id = hook_id  # Store for cleanup
            
            def on_window_close():
                self._close_detection_window(detection_window)
            
            detection_window.protocol("WM_DELETE_WINDOW", on_window_close)
            detection_window.bind('<Escape>', lambda e: on_window_close())
            
        except Exception as e:
            error_msg = f"Failed to start key detection: {e}"
            self.logger.error(error_msg)
            self.log_to_gui_diag_area(error_msg, "error")
            detection_window.destroy()

    def _close_detection_window(self, window):
        """Clean up detection window and unhook keyboard"""
        try:
            if hasattr(window, '_hook_id'):
                keyboard.unhook(window._hook_id)
            
            self.log_to_gui_diag_area("--- Enhanced ALT+BRIGHTNESS Key Detection Stopped ---", "info")
            
            summary_msg = """DETECTION COMPLETE - ALT+BRIGHTNESS ANALYSIS

Review the key names above to identify your brightness keys.

IDEAL COMBINATIONS FOR UBUNTU/CHROMEBOOK:
   • ALT + XF86MonBrightnessUp / ALT + XF86MonBrightnessDown
   • ALT + XF86BrightnessUp / ALT + XF86BrightnessDown
   • ALT + f5 / ALT + f6
   • ALT + f7 / ALT + f8

NEXT STEPS:
   1. If you found ALT+BRIGHTNESS combinations, restart the app with sudo
   2. If only regular brightness keys were found, they can still work with ALT
   3. Submit your key names to help improve automatic detection

Your setup is perfect for independent keyboard vs screen brightness control!"""
            
            self.log_to_gui_diag_area(summary_msg, "info")
            window.destroy()
            
        except Exception as e:
            self.logger.error(f"Error closing detection window: {e}")
            try:
                window.destroy()
            except:
                pass

    def perform_final_shutdown(self, clean_shutdown: bool = False):
        self.logger.info(f"Performing final shutdown (clean_shutdown={clean_shutdown}).")
        self.root.attributes('-alpha', 0.5) # Visual cue of shutdown
        
        # Stop hotkey listener if it was a separate thread (keyboard lib handles its own)
        if hasattr(self, '_hotkey_listener_stop_event'):
            self._hotkey_listener_stop_event.set()
        if KEYBOARD_LIB_AVAILABLE:
            try:
                keyboard.unhook_all_hotkeys() # Remove specific hotkeys
                keyboard.unhook_all() # Remove all general hooks if any
                self.logger.info("Unhooked all keyboard listeners.")
            except Exception as e_unhook:
                self.logger.error(f"Error unhooking keyboard listeners: {e_unhook}")

        self.save_current_gui_state_to_settings() # Save one last time
        if hasattr(self, 'effect_manager') and self.effect_manager:
            self.effect_manager.stop_current_effect()

        if clean_shutdown:
            self.logger.info("Marking clean shutdown in settings.")
            if hasattr(self.settings, 'mark_clean_shutdown'): 
                self.settings.mark_clean_shutdown()
            if hasattr(self.hardware, 'set_app_exiting_cleanly'): 
                self.hardware.set_app_exiting_cleanly(True)
            self.logger.info("LEDs will remain in their last state (not cleared on clean exit by default).")
            # Some users might prefer LEDs off on clean exit, this could be a setting.
            # For now, matching existing logic of leaving them as is.
        else:
            self.logger.warning("Application performing an unclean shutdown (or user chose not to save state). Attempting to clear LEDs for safety.")
            try:
                if hasattr(self, 'hardware') and self.hardware.is_operational():
                    self.hardware.clear_all_leds()
                    self.logger.info("LEDs cleared on non-clean/explicit-clear shutdown.")
            except Exception as e: 
                self.logger.error(f"Failed to clear LEDs during non-clean shutdown: {e}")

        if self.tray_icon:
            self.logger.info("Stopping tray icon...")
            self.tray_icon.stop()
        if self.tray_thread and self.tray_thread.is_alive():
            self.tray_thread.join(timeout=0.5) # Give thread a moment to close
        self.tray_icon = None
        self.tray_thread = None

        # Indicate to GuiLogHandler's queue processor that Tkinter is going away
        if self.root and hasattr(self.root, 'winfo_exists') and self.root.winfo_exists():
            setattr(self.root, '_is_being_destroyed', True)

        self.logger.info(f"{APP_NAME} shutting down now.")
        if self.root and hasattr(self.root, 'winfo_exists') and self.root.winfo_exists():
            try:
                self.root.destroy()
            except tk.TclError as e_destroy:
                self.logger.error(f"Error destroying Tk root: {e_destroy}")
        sys.exit(0)


def main():
    # Basic config for standalone run, GUI handler will add to it
    logging.basicConfig(level=logging.DEBUG, 
                       format='%(asctime)s - %(name)s [%(levelname)s] %(module)s.%(funcName)s:%(lineno)d - %(message)s', 
                       handlers=[logging.StreamHandler(sys.stdout)])
    module_logger = logging.getLogger(f"{APP_NAME}.controller_standalone")
    app_instance_ref = [None] # Use a list to pass by reference for the excepthook

    def handle_exception_standalone(exc_type, exc_value, exc_traceback):
        app_instance = app_instance_ref[0]
        if issubclass(exc_type, KeyboardInterrupt):
            module_logger.info("KeyboardInterrupt received. Shutting down.")
            sys.__excepthook__(exc_type, exc_value, exc_traceback) # Call original hook
            if app_instance and hasattr(app_instance, 'perform_final_shutdown'):
                app_instance.perform_final_shutdown(clean_shutdown=False) # Treat as unclean for safety
            sys.exit(1) # Exit after cleanup attempt
        
        # For other exceptions
        module_logger.critical("Unhandled exception in controller_standalone:", exc_info=(exc_type, exc_value, exc_traceback))
        
        # Try to show a Tkinter messagebox if possible
        temp_root_for_msg = None
        parent_for_msg = None
        can_use_tkinter_for_msg = False

        try:
            if tk._default_root and tk._default_root.winfo_exists():
                parent_for_msg = tk._default_root
                can_use_tkinter_for_msg = True
            elif not tk._default_root: # No default root, try to create a temporary one
                try:
                    temp_root_for_msg = tk.Tk()
                    temp_root_for_msg.withdraw() # Create and hide
                    parent_for_msg = temp_root_for_msg
                    can_use_tkinter_for_msg = True
                except tk.TclError: # Failed to create even a temp root
                    print(f"FATAL ERROR (TKINTER TEMP ROOT CREATION FAILED FOR ERROR MSG): {exc_value}", file=sys.stderr)
            
            if can_use_tkinter_for_msg:
                messagebox.showerror("Unhandled Exception", 
                                   f"An unexpected error occurred: {exc_value}\n\nThe application will now exit. Please check logs for details.", 
                                   parent=parent_for_msg)
            else: # Tkinter completely unavailable for error message
                print(f"FATAL ERROR (TKINTER UNAVAILABLE FOR ERROR MSG BOX): {exc_value}", file=sys.stderr)
        except Exception as e_msg_display: # Error trying to display the error message
            print(f"FATAL ERROR (ERROR DISPLAYING ERROR MESSAGE DIALOG): {e_msg_display}", file=sys.stderr)
            print(f"ORIGINAL FATAL ERROR WAS: {exc_value}", file=sys.stderr)
        finally:
            if temp_root_for_msg: # Clean up temporary root if created
                try: 
                    temp_root_for_msg.destroy()
                except: 
                    pass

        if app_instance and hasattr(app_instance, 'perform_final_shutdown'):
            module_logger.info("Attempting unclean shutdown from unhandled exception handler.")
            app_instance.perform_final_shutdown(clean_shutdown=False)
        else:
            module_logger.critical("Unhandled exception, and app_instance not available for controlled shutdown.")
            # Minimal attempt to clear hardware if possible, as a last resort
            try:
                # Conditional import based on how the script might be run
                # This is highly dependent on the project structure if run directly
                # Assuming controller.py is in a 'gui' subdirectory of the main package
                if __package__ and __package__.startswith("rgb_controller_finalv2.gui"): # e.g. rgb_controller_finalv2.gui
                    from ..hardware.controller import HardwareController as EmergHW # relative from gui package
                elif __package__ == "gui": # If gui is top-level for this script
                    from .hardware.controller import HardwareController as EmergHW
                else: # Fallback for direct run or unknown structure - this might fail
                    # This assumes hardware.controller is findable in sys.path
                    # which might be true if the __main__ block below modified sys.path
                    from hardware.controller import HardwareController as EmergHW
                    
                temp_hw = EmergHW(emergency_mode=True) # Pass a flag if constructor supports it
                if temp_hw.wait_for_detection(timeout=0.2): 
                    temp_hw.clear_all_leds()
                module_logger.info("Emergency hardware clear attempted.")
            except Exception as e_emerg:
                module_logger.warning(f"Emergency hardware clear failed during fatal exit: {e_emerg}")

        if tk._default_root and tk._default_root.winfo_exists(): # Destroy default root if it still exists
            try: 
                tk._default_root.destroy()
            except: 
                pass
        sys.exit(1) # Exit with error status

    sys.excepthook = handle_exception_standalone

    root = None # Initialize root to None
    try:
        root = tk.Tk()
        # Hide root window initially if it's going to tray or for cleaner startup
        # root.withdraw() # Can withdraw if splash screen or tray startup is intended
        
        app_instance_ref[0] = RGBControllerGUI(root) # Store instance for excepthook
        # root.deiconify() # Show window after init, if withdrawn
        
        root.mainloop()
    except SystemExit: # Raised by perform_final_shutdown
        module_logger.info("SystemExit caught in main, application will exit as planned.")
    except Exception as e_main:
        module_logger.critical("Fatal error during standalone GUI startup or mainloop (after excepthook setup).", exc_info=True)
        # Exception hook should handle this, but as a fallback:
        if app_instance_ref[0] and hasattr(app_instance_ref[0], 'perform_final_shutdown'):
            app_instance_ref[0].perform_final_shutdown(clean_shutdown=False)
        elif root and hasattr(root, 'winfo_exists') and root.winfo_exists():
            try: 
                root.destroy()
            except: 
                pass
        sys.exit(1) # Ensure exit


if __name__ == "__main__":
    # This block is for when controller.py is run directly (e.g., python controller.py)
    # It attempts to adjust sys.path to make relative imports like ".core" work.
    if not __package__: # Only if not run as part of a package (e.g. python -m some.module)
        script_dir = Path(__file__).resolve().parent # .../rgb_controller_finalv2/gui
        # To make ".core" (from .core import RGBColor) work, "gui" directory's parent needs to be in sys.path
        # so that "gui" itself can be treated as a package.
        # The imports are `from .core...`, so `script_dir` (i.e. `gui`) itself needs to be seen as a package.
        # For this to work, its parent (`rgb_controller_finalv2`) should be in `sys.path`.
        
        path_to_add = script_dir.parent # This should be .../rgb_controller_finalv2
        
        if str(path_to_add) not in sys.path:
            sys.path.insert(0, str(path_to_add))
            print(f"[controller.py __main__] Added to sys.path for direct run: {path_to_add}")
            print(f"[controller.py __main__] Current sys.path[0]: {sys.path[0]}")
            print(f"[controller.py __main__] Attempting to run as if 'gui' is a package within '{path_to_add.name}'.")

        # To properly run this file which uses relative imports like `from .core...`,
        # it should ideally be invoked as a module, e.g., `python -m gui.controller`
        # from the `rgb_controller_finalv2` directory.
        # The sys.path modification above helps if it's run as `python gui/controller.py` from `rgb_controller_finalv2`.

    print(f"Running {Path(__file__).name} (invoked as: {__name__}, package: {__package__})...")
    if os.name != 'nt' and hasattr(os, 'geteuid') and os.geteuid() != 0:
        print("WARNING: Root/administrator privileges may be required for full hardware functionality (like direct EC access or global hotkeys).", file=sys.stderr)
        print("For ALT+BRIGHTNESS hotkeys on Ubuntu/Chromebook, try: sudo python -m rgb_controller_finalv2", file=sys.stderr)

    main()