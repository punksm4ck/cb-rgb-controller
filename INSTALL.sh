#!/bin/bash
# OSIRIS RGB Controller - Enterprise Installer

echo "Initializing OSIRIS RGB Installation..."

# 1. Dependency Check
sudo apt update
sudo apt install python3-pip python3-tk -y

# 2. Install Hardware Hooking Library
sudo pip3 install keyboard --break-system-packages

# 3. Setup Directories
mkdir -p ~/Pictures/Icons
cp ./gui/assets/icon.png ~/Pictures/Icons/RGB.png 2>/dev/null

# 4. Create Desktop Launcher
cat << 'DL' > ~/.local/share/applications/osiris-rgb.desktop
[Desktop Entry]
Version=1.0
Type=Application
Name=OSIRIS RGB Control
Comment=Master Per-Key RGB Controller
Exec=$(pwd)/open_rgb_controller.sh
Icon=/home/tsann/Pictures/Icons/RGB.png
Terminal=false
Categories=Utility;System;
DL

chmod +x ~/.local/share/applications/osiris-rgb.desktop
cp ~/.local/share/applications/osiris-rgb.desktop ~/Desktop/
chmod +x ~/Desktop/osiris-rgb.desktop

echo "Installation Complete. Launch from Applications menu or Desktop."
