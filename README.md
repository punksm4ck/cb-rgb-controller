# 🌈 Enhanced RGB Keyboard Controller (v3)

A comprehensive Python GUI application for controlling RGB lighting on supported Chromebooks and other compatible systems, leveraging the system's hardware control utilities (primarily `ectool`).

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)


---

## ✨ Features

* **Multi-tab Interface**: Control features across tabs for Static Color, Zone Management, Dynamic Effects, Settings, and Diagnostics.
* **12+ Animated Effects**: Including Breathing, Color Cycle, Wave, Pulse, Zone Chase, Starlight, Scanner, Strobe, Ripple, Raindrop, and **Reactive/Anti-Reactive** modes.
* **Hardware-Synchronized Preview**: Live, realistic keyboard simulation on the GUI using `tkinter.Canvas`.
* **Universal Controls**: Persistent settings for brightness, speed, and last-used effect.
* **Enhanced Global Hotkeys**: Priority setup for **ALT + Brightness Keys** (e.g., ALT+F5/F6) on Linux/Chromebooks to control keyboard brightness independently of screen brightness.
* **Diagnostics & Logging**: Detailed hardware status, system info, and GUI logs for troubleshooting.
* **System Tray Support**: Option to minimize to a system tray icon (requires `pystray` and `Pillow`).

---

## 🚀 Requirements & Setup

### Requirements

| Requirement | Rationale |
| :--- | :--- |
| **Root/Admin Access (`sudo`)** | Required for hardware control (via `ectool` or direct EC access) and for global hotkey capturing. |
| **Python 3.8+** | The application requires modern Python features. |
| **Compatible Hardware** | Primarily designed for Chromebooks with RGB keyboards accessible via `ectool`. |
| **`ectool`** | Must be present and accessible in the system's PATH (Chromebooks/Linux). |

### Python Dependencies

| Dependency | Status | Installation Command |
| :--- | :--- | :--- |
| **tkinter** | Required (Standard library, but needs `python3-tk` on Debian/Ubuntu). | `sudo apt-get install python3-tk` |
| **psutil** | Optional (For enhanced system info in Diagnostics tab). | `pip install psutil` |
| **pystray** | Optional (For System Tray functionality). | `pip install pystray` |
| **Pillow (PIL)** | Optional (Required by `pystray` for proper icon support). | `pip install Pillow` |
| **keyboard** | Optional (For Global Hotkeys like ALT+Brightness). | `pip install keyboard` |

### Installation Steps

1.  **Clone the Repository:**
    ```bash
    git clone [your-repo-url] rgb_controller_final2
    cd rgb_controller_final2
    ```

2.  **Run Setup Script:**
    The provided `setup.py` creates the necessary Python package structure and checks basic dependencies.
    ```bash
    python3 setup.py
    ```

3.  **Install Dependencies:**
    Install any packages marked as missing (see table above).

---

## ▶️ Usage

The application must be run as a Python package from the directory *containing* the main project folder (`rgb_controller_final2/`).

1.  **Navigate Up One Level** (if you are inside the project folder):
    ```bash
    cd ..
    ```

2.  **Run with Root Privileges:**
    ```bash
    sudo python3 -m rgb_controller_final2
    ```
    *(If you are already inside the project folder, you can use: `sudo python3 .`)*

### Hotkey Troubleshooting (Linux/Chromebooks)

If global hotkeys (`ALT + Brightness Keys`) are not working:
* **Check Permissions**: Ensure you run the application using `sudo`. Global key capture often requires elevated privileges.
* **Test Key Names**: Use the **Diagnostics tab**'s "Test Keyboard Hotkey Names" utility to verify your system's key-names for brightness and find the correct ALT combination.
* **Dependencies**: Confirm the `keyboard` library is installed and accessible to your root environment.

---

## 📐 Project Structure
rgb_controller_finalfinal/
├── main.py      # Main entry point (initial setup, logging, privilege check)
├── setup.py         # Utility for creating directory/package structure and dependency checks
├── README.md        # This file
├── LICENSE          # Project license
├── CONTRIBUTING.md  # Guide for contributors
└── gui/             # Main application package
├── init.py  # Package initialization
├── controller.py# Main GUI logic (RGBControllerGUI class)
├── assets/      # Icons and images
├── core/        # Core components (constants, settings, color models, exceptions)
├── utils/       # Utility functions (decorators, subprocess, system info)
├── hardware/    # Hardware control layer (HardwareController)
└── effects/     # Lighting effects logic (EffectManager, EffectLibrary)

---

## ⚠️ Disclaimer and Licensing

This software interacts directly with system hardware components. **Use at your own risk.** The developers are not responsible for any damage or issues that may arise from its use.

### License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.
