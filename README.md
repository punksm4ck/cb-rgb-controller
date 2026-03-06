# OSIRIS RGB Controller (v6.1.0)

A high-performance, reverse-engineered RGB control suite for Acer Chromebook Plus devices (Osiris/Starmie) running Kubuntu/Ubuntu.
NOTE: This was created, debugged, and tested ONLY on the Acer Chromebook Plus 516 GE OSIRIS machine, which features a "4-zone RGB-backlit keyboard" - it has not been tested on any other machine or with any other RGB keyboard, other than the one that is built-in to this Acer.
Use with caution on other devices, as while it may work, it also may not.

BIGGER NOTE: By default, the keyboard controller GUI is set to use ECTOOL, which is compiled in this build, but it also has the ECDirect option, which was been tested on this machine only
Even if you have this exact machine, using ECDirect as the control method can be risky to your hardware, and while it was been setup and tested to work, it is generally recommended to leave the setting on ECTOOL for best results.

## Features
- **Total-Matrix Engine:** 11-column per-key mapping for maximum hardware brightness.
- **Reactive Engine:** Real-time matrix-isolated reactive typing.
- **Splash Screen:** Borderless 4-second enterprise splash on startup.
- **KDE Integration:** Custom desktop launchers and application menu icons.

## Quick Install
\`\`\`bash
git clone https://github.com/punksm4ck/cb-rgb-controller.git
cd cb-rgb-controller
chmod +x INSTALL.sh
./INSTALL.sh
\`\`\`

## Usage
Run via the Desktop icon or:
\`\`\`bash
./open_rgb_controller.sh
\`\`\`
*Note: Sudo privileges are required for global keyboard hooking.*
