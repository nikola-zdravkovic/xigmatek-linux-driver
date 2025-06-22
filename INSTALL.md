# Installation Guide

## Prerequisites

### Hardware Requirements
- XIGMATEK LK 360 Digital Arctic AIO cooler
- USB connection between cooler and motherboard
- Linux system with USB and HID support

### Software Requirements
- Python 3.8 or newer
- Package manager (pacman, apt, dnf, zypper)
- Internet connection for downloading dependencies

## Installation Methods

### Method 1: Automatic Setup (Recommended)

The setup script automatically detects your Linux distribution and installs all dependencies:

```bash
# Download and run the setup script
curl -sSL https://raw.githubusercontent.com/nikola-zdravkovic/xigmatek-linux-driver/main/setup.sh | bash

# Or download first, then run
wget https://raw.githubusercontent.com/nikola-zdravkovic/xigmatek-linux-driver/main/setup.sh
chmod +x setup.sh
./setup.sh
```

The script will:
1. Detect your Linux distribution
2. Install required packages using your system's package manager
3. Install Python dependencies
4. Create system service files
5. Set up device permissions
6. Test the installation
7. Offer to start the service

### Method 2: Manual Installation

#### Step 1: Install System Dependencies

**Arch Linux / Manjaro:**
```bash
sudo pacman -Sy python python-pip lm_sensors python-hidapi
```

**Ubuntu / Debian:**
```bash
sudo apt update
sudo apt install python3 python3-pip lm-sensors python3-hid
```

**Fedora / RHEL / CentOS:**
```bash
sudo dnf install python3 python3-pip lm_sensors python3-hidapi
```

**openSUSE:**
```bash
sudo zypper install python3 python3-pip sensors
pip3 install --user hidapi
```

#### Step 2: Configure Sensors

```bash
# Auto-detect and configure hardware sensors
sudo sensors-detect --auto

# Test sensors
sensors
```

#### Step 3: Download the Driver

```bash
# Clone the repository
git clone https://github.com/nikola-zdravkovic/xigmatek-linux-driver.git
cd xigmatek-linux-driver

# Or download specific files manually
mkdir -p xigmatek-linux-driver/{src,config,scripts}
cd xigmatek-linux-driver
```

#### Step 4: Install Service Files

```bash
# Copy main service script
sudo cp src/xigmatek-monitor.py /usr/local/bin/
sudo chmod +x /usr/local/bin/xigmatek-monitor.py

# Copy configuration file
sudo cp config/xigmatek-monitor.conf /etc/

# Copy systemd service file
sudo cp config/xigmatek-monitor.service /etc/systemd/system/
```

#### Step 5: Set Up Device Permissions

```bash
# Create udev rule for device access
sudo tee /etc/udev/rules.d/99-xigmatek.rules > /dev/null << 'EOF'
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="0145", ATTRS{idProduct}=="1005", MODE="0666", GROUP="users"
EOF

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

#### Step 6: Initialize Service

```bash
# Create log file
sudo touch /var/log/xigmatek-monitor.log
sudo chmod 644 /var/log/xigmatek-monitor.log

# Reload systemd
sudo systemctl daemon-reload
```

## Post-Installation

### Start the Service

```bash
# Start the service now
sudo systemctl start xigmatek-monitor

# Enable automatic startup on boot
sudo systemctl enable xigmatek-monitor

# Check service status
sudo systemctl status xigmatek-monitor
```

### Verify Installation

```bash
# Test device connection
python3 scripts/test-device.py

# Check service logs
sudo journalctl -u xigmatek-monitor -f

# Verify temperature display
# Your XIGMATEK display should now show CPU and GPU temperatures
```

## Installation on Specific Distributions

### Arch Linux with External Python Management

If you encounter "externally-managed-environment" errors:

```bash
# The setup script will automatically create a virtual environment
# Or manually:
sudo mkdir -p /opt/xigmatek
sudo python3 -m venv /opt/xigmatek/venv
sudo /opt/xigmatek/venv/bin/pip install hidapi

# Update the service file to use the virtual environment
sudo sed -i 's|ExecStart=/usr/local/bin/xigmatek-monitor.py|ExecStart=/opt/xigmatek/venv/bin/python /usr/local/bin/xigmatek-monitor.py|' /etc/systemd/system/xigmatek-monitor.service
```

### Ubuntu with Snap Python

If using snap-installed Python:

```bash
# Install system Python instead
sudo apt install python3 python3-pip
# Then follow normal installation
```

### Fedora with Python Version Issues

```bash
# Ensure Python 3.8+
python3 --version

# If older version, enable newer Python
sudo dnf install python39
sudo alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1
```

## Troubleshooting Installation

### Common Issues

**Device not found:**
```bash
# Check USB connection
lsusb | grep 0145:1005

# Try different USB port
# Ensure device is powered on
```

**Permission denied:**
```bash
# Check udev rule was created
cat /etc/udev/rules.d/99-xigmatek.rules

# Force reload
sudo udevadm control --reload-rules
sudo udevadm trigger

# Reboot if needed
sudo reboot
```

**Python module not found:**
```bash
# Verify hidapi installation
python3 -c "import hid; print('✓ hidapi working')"

# If fails, reinstall
pip3 install --user hidapi --force-reinstall
```

**Service fails to start:**
```bash
# Check detailed logs
sudo journalctl -u xigmatek-monitor --no-pager

# Test script manually
sudo /usr/local/bin/xigmatek-monitor.py --test

# Check Python path
which python3
```

### Getting Help

If you encounter issues:

1. **Check logs:**
   ```bash
   sudo journalctl -u xigmatek-monitor -n 50
   ```

2. **Run test scripts:**
   ```bash
   python3 scripts/test-device.py
   ```

3. **Create an issue:**
   - Go to GitHub Issues
   - Include your distribution and version
   - Include log output
   - Describe what you were trying to do

## Uninstallation

If you need to remove the driver:

```bash
# Stop and disable service
sudo systemctl stop xigmatek-monitor
sudo systemctl disable xigmatek-monitor

# Remove files
sudo rm /usr/local/bin/xigmatek-monitor.py
sudo rm /etc/xigmatek-monitor.conf
sudo rm /etc/systemd/system/xigmatek-monitor.service
sudo rm /etc/udev/rules.d/99-xigmatek.rules
sudo rm /var/log/xigmatek-monitor.log

# Remove virtual environment (if created)
sudo rm -rf /opt/xigmatek

# Reload systemd and udev
sudo systemctl daemon-reload
sudo udevadm control --reload-rules

# Optional: Remove Python dependencies
pip3 uninstall hidapi
```

## Next Steps

After successful installation:

1. **Configure settings** in `/etc/xigmatek-monitor.conf`
2. **Monitor service status** with `systemctl status xigmatek-monitor`
3. **Check your display** for temperature readings
4. **Report any issues** on GitHub
5. **Star the repository** if it worked for you! ⭐