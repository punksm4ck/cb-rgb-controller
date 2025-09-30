\# Enhanced RGB Keyboard Controller

A comprehensive Python GUI application for controlling RGB lighting on supported Chromebooks and other compatible systems.

\#\# Features

\* \*\*Multi-tab Interface\*\*: Easy navigation through General Controls, Zone Management, Dynamic Effects, Application Settings, and Diagnostics.  
\* \*\*Lighting Effects\*\*:  
    \* Static Colors (all zones or per-zone)  
    \* Static Rainbow & Gradient patterns across zones  
    \* Animated Effects: Breathing, Color Cycle, Wave, Pulse, Zone Chase, Starlight, Scanner, Strobe, Ripple.  
    \* Rainbow versions of many animated effects.  
    \* (Reactive effects are in the library, GUI integration for triggers may vary)  
\* \*\*Live Preview\*\*: Visual LED simulation on the GUI before applying changes to hardware.  
\* \*\*Individual Zone Control\*\*: Customize colors for each of the 4 keyboard zones.  
\* \*\*Hardware Detection\*\*: Attempts to automatically detect and use available control methods (primarily \`ectool\`). Direct EC control is planned for advanced use.  
\* \*\*Settings Management\*\*: Persistent settings for brightness, colors, last effect, and preferences, with import/export functionality.  
\* \*\*Comprehensive Logging\*\*: Detailed application and hardware logs for operation and troubleshooting.  
\* \*\*Desktop Launcher\*\*: Option to create a \`.desktop\` file for easy launching on Linux.

\#\# Requirements

\* \*\*Root Access (sudo)\*\*: Generally required for hardware control via \`ectool\` or direct EC access.  
\* \*\*Python 3.8+\*\*: With \`tkinter\` support.  
\* \*\*Compatible Hardware\*\*: Primarily designed for Chromebooks with RGB keyboard support via \`ectool\`. Functionality on other systems or with other control methods may vary.  
\* \*\*\`ectool\`\*\*: For Chromebooks, this utility needs to be present and accessible (often part of developer mode or specific packages).

\#\# Dependencies

\* \*\*tkinter\*\*: Standard Python library, usually included. On Linux, may require \`python3-tk\` package (\`sudo apt-get install python3-tk\`).  
\* \*\*psutil\*\* (Optional): For enhanced system information in the diagnostics tab. Install with \`pip3 install psutil\` or \`sudo apt-get install python3-psutil\`.

\#\# Installation & Setup

1\.  \*\*Download/Clone:\*\*  
    \* Place all project files into a root directory (e.g., \`rgb\_controller\_final2\`).

2\.  \*\*Run Setup Script (Optional but Recommended):\*\*  
    \* Navigate into your project directory (e.g., \`cd rgb\_controller\_final2\`).  
    \* Run \`python3 setup.py\`. This script will:  
        \* Create the necessary \`gui\` subdirectory structure (\`core\`, \`utils\`, \`hardware\`, \`effects\`).  
        \* Create \`\_\_init\_\_.py\` files in these directories.  
        \* Check for basic dependencies.  
        \* Provide a file placement guide.

3\.  \*\*Organize Files:\*\*  
    \* Ensure all Python modules (\`.py\` files) are placed into their correct subdirectories within the \`gui\` folder as outlined by \`setup.py\` and the structure below.

4\.  \*\*Install Dependencies (if \`setup.py\` indicated any are missing):\*\*  
    \`\`\`bash  
    sudo apt-get install python3-tk \# For Tkinter on Debian/Ubuntu  
    pip3 install psutil \# For optional system info  
    \`\`\`

\#\# Directory Structure

Your project should be organized as follows (assuming the root folder is \`rgb\_controller\_final2\`):

rgb\_controller\_final2/  
├── main.py \# Main launcher for running the application as a package  
├── setup.py \# Utility script for directory setup and dependency checks  
├── README.md \# This file  
└── gui/ \# Main application package  
├── init.py \# Makes 'gui' a package  
├── controller.py \# Contains the main RGBControllerGUI class  
├── assets/ \# Optional: For icons, images  
│ └── icon.png \# Example icon  
├── core/  
│ ├── init.py  
│ ├── constants.py \# Application-wide constants, default settings  
│ ├── settings.py \# SettingsManager class  
│ ├── rgb\_color.py \# RGBColor class  
│ └── exceptions.py \# Custom exception classes  
├── utils/  
│ ├── init.py  
│ ├── decorators.py \# Decorators like @safe\_execute  
│ ├── safe\_subprocess.py \# For running external commands safely  
│ ├── system\_info.py \# System information utilities  
│ └── input\_validation.py \# Input validation functions/class  
├── hardware/  
│ ├── init.py  
│ └── controller.py \# HardwareController class  
└── effects/  
├── init.py  
├── library.py \# EffectLibrary class with effect logic  
└── manager.py \# EffectManager class for controlling effects  
\#\# Usage

1\.  \*\*Navigate to the directory \*containing\* your project folder.\*\*  
    For example, if your project is in \`\~/Downloads/rgb\_controller\_final2\`, navigate to \`\~/Downloads/\`.

2\.  \*\*Run with root privileges:\*\*  
    \`\`\`bash  
    sudo python3 \-m rgb\_controller\_final2  
    \`\`\`  
    (Replace \`rgb\_controller\_final2\` with your actual project folder name if different.)

    Alternatively, if you are \*inside\* the project folder (\`rgb\_controller\_final2/\`):  
    \`\`\`bash  
    sudo python3 .  
    \`\`\`

3\.  \*\*Using the Application:\*\*  
    \* \*\*Hardware Detection\*\*: The application will attempt to detect available RGB control methods on startup.  
    \* \*\*General Tab\*\*: Quick color selection, brightness, and effect speed controls.  
    \* \*\*Zone Colors Tab\*\*: Customize colors for individual keyboard zones. Apply static rainbow or gradient patterns.  
    \* \*\*Effects Tab\*\*: Select from various animated lighting effects. Preview available.  
    \* \*\*Settings Tab\*\*: Configure startup behavior, preferred control method, import/export settings, and create a desktop launcher.  
    \* \*\*Diagnostics Tab\*\*: View hardware status, system information, log locations, and run basic hardware tests.

\#\# Supported Effects (Examples)

The application includes a variety of effects, managed by the \`EffectManager\` and defined in \`EffectLibrary\`.

\* \*\*Static Patterns:\*\*  
    \* Static Color (All Zones / Per Zone)  
    \* Static Rainbow (Across Zones)  
    \* Static Gradient (Across Zones)  
\* \*\*Animated Effects:\*\*  
    \* Breathing (Single color or Rainbow)  
    \* Color Cycle (Smooth HSV transition)  
    \* Wave (Single color or Rainbow, moves across zones)  
    \* Pulse (Single color or Rainbow)  
    \* Zone Chase (Single color or Rainbow block moving across zones)  
    \* Starlight (Random twinkling "stars")  
    \* Scanner (Light bar moving back and forth)  
    \* Strobe (Flashing effect)  
    \* Ripple (Color ripples emanating from a point/zone)  
    \* Raindrop (Simulated raindrops)  
\* \*\*Hardware Demo (If supported by \`ectool\`):\*\*  
    \* The GUI may provide an option to trigger hardware-based demo modes if detected.

\#\# Hardware Support

\* \*\*\`ectool\` (Recommended for Chromebooks):\*\*  
    \* Utilizes the Chrome OS \`ectool\` utility.  
    \* Generally the most reliable method on supported devices.  
    \* Requires \`ectool\` to be available in the system's PATH (often requires developer mode).  
\* \*\*EC Direct (Advanced/Experimental):\*\*  
    \* Intended for direct Embedded Controller register access.  
    \* Highly hardware-specific and requires careful implementation.  
    \* This method is less developed in the current version.

\#\# Configuration

Settings are automatically saved and loaded. The default location is typically:  
\`\~/.config/rgb\_controller\_final2/settings.json\` (Path derived from \`APP\_NAME\` in \`constants.py\`)

Saved settings include:  
\* Brightness level  
\* Last used static color and zone colors  
\* Last active effect and its parameters (speed, color, rainbow mode)  
\* Gradient colors  
\* Control method preference  
\* Startup behavior (restore settings, auto-apply effect)

\#\# Troubleshooting

\* \*\*"Root privileges required" error:\*\* Ensure you are running the application with \`sudo\`.  
\* \*\*"Hardware not detected" / No control methods found:\*\*  
    \* Verify you are on a compatible Chromebook or system with RGB keyboard support.  
    \* For Chromebooks, ensure \`ectool\` is installed and working (may require developer mode).  
\* \*\*\`ectool\` command not found:\*\* If \`ectool\` is installed but not in the default PATH for sudo, you might need to adjust your system's secure path or call \`ectool\` with its full path.  
\* \*\*Import errors (e.g., \`ModuleNotFoundError\`):\*\*  
    \* Double-check that all Python files are organized correctly within the \`gui\` package structure as shown above.  
    \* Ensure you are running the application as a module (\`sudo python3 \-m your\_project\_folder\_name\`) from the directory \*containing\* your project folder, or using \`sudo python3 .\` from \*inside\* your project folder.  
\* \*\*Tkinter errors (e.g., "no display name" or "TclError"):\*\*  
    \* Ensure a display server (X11 or Wayland with Xwayland) is running.  
    \* Make sure \`python3-tk\` (or equivalent) is installed.  
    \* When running with \`sudo\`, GUI applications can sometimes have issues with display access. Try:  
        \`\`\`bash  
        sudo env DISPLAY=$DISPLAY XAUTHORITY=$XAUTHORITY python3 \-m your\_project\_folder\_name  
        \`\`\`

\#\# Logs

For detailed error information and operational messages:  
\* \*\*Console Output:\*\* Check the terminal where you launched the application.  
\* \*\*Startup Log File:\*\* \`rgb\_controller\_final2/rgb\_controller\_startup.log\` (or in \`\~/.cache/\` if project dir not writable).  
\* \*\*Main Application Log Files:\*\* Located in \`\~/.config/rgb\_controller\_final2/logs/\` (path derived from \`APP\_NAME\`).

\#\# Safety Features

\* \*\*Circuit Breaker Pattern:\*\* Implemented in \`HardwareController\` to prevent repeated calls to failing hardware commands.  
\* \*\*Safe Command Execution:\*\* \`gui/utils/safe\_subprocess.py\` is used for running external commands like \`ectool\`, reducing risks.  
\* \*\*Error Handling:\*\* The application aims for graceful degradation and provides error messages for common issues.  
\* \*\*Input Validation:\*\* User inputs for colors, numbers, etc., are validated.

\#\# Development

The application is designed to be modular:  
\* Add new animated effects as static methods in \`gui/effects/library.py\` and map them in \`gui/effects/manager.py\`.  
\* Extend hardware support or control methods in \`gui/hardware/controller.py\`.  
\* Modify GUI layout and interactions in \`gui/controller.py\`.  
\* Core logic, constants, and custom types are in \`gui/core/\`.  
\* Reusable helper functions and decorators are in \`gui/utils/\`.

\#\# License

This software is provided "as-is". Use it for educational and personal purposes. No guarantees or warranties are implied.

\#\# Disclaimer

This software interacts directly with system hardware components (via \`ectool\` or potentially direct EC access). Incorrect use or bugs could potentially lead to unexpected behavior on your system. \*\*Use at your own risk.\*\* It is always recommended to understand the commands being sent to your hardware. The developers are not responsible for any damage or issues that may arise from the use of this software.  
