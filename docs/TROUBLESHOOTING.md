# Troubleshooting Guide

This guide covers common issues and their solutions when using the XIGMATEK Linux Driver.

## Quick Diagnostic Commands

```bash
# Check service status
sudo systemctl status xigmatek-monitor

# View recent logs
sudo journalctl -u xigmatek-monitor -n 20

# Test device connection
python3 scripts/test-device.py

# Check USB connection
lsusb | grep 0145:1005

# List HID devices
ls -la /dev/hidraw*
```

## Common Issues

### 1. Device Not Found

**Symptoms:**
- Service fails to start
- "Device not found" errors in logs
- `lsusb` doesn't show device

**Causes & Solutions:**

#### USB Connection Issues
```bash
# Check USB connection
lsusb | grep 0145:1005

# If not found:
# 1. Try different USB port (preferably USB 2.0)
# 2. Try different USB cable
# 3. Check device power (fans spinning?)
# 4. Restart computer with device connected
```

#### USB Power Management
```bash
# Disable USB autosuspend
echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="0145", ATTRS{idProduct}=="1005", ATTR{power/autosuspend}="-1"' | sudo tee -a /etc/udev/rules.d/99-xigmatek.rules

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

#### Module Loading Issues
```bash
# Ensure HID modules are loaded
sudo modprobe usbhid
sudo modprobe hid-generic

# Check if modules are loaded
lsmod | grep hid
```

### 2. Permission Denied

**Symptoms:**
- "Permission denied" when accessing device
- Service starts but fails to communicate
- Works as root but not as user

**Solutions:**

#### Check udev Rules
```bash
# Verify udev rule exists
cat /etc/udev/rules.d/99-xigmatek.rules

# Should contain:
# SUBSYSTEM=="hidraw", ATTRS{idVendor}=="0145", ATTRS{idProduct}=="1005", MODE="0666", GROUP="users"
```

#### Fix udev Rules
```bash
# Create/fix udev rule
sudo tee /etc/udev/rules.d/99-xigmatek.rules > /dev/null << 'EOF'
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="0145", ATTRS{idProduct}=="1005", MODE="0666", GROUP="users"
SUBSYSTEM=="usb", ATTRS{idVendor}=="0145", ATTRS{idProduct}=="1005", MODE="0666", GROUP="users"
EOF

# Reload and trigger
sudo udevadm control --reload-rules
sudo udevadm trigger

# Unplug and replug device, or reboot
```

#### Check Device Permissions
```bash
# Find the hidraw device
for dev in /dev/hidraw*; do
    if udevadm info -q property $dev | grep -q "ID_VENDOR_ID=0145"; then
        echo "XIGMATEK device: $dev"
        ls -la $dev
    fi
done

# Should show mode 666 (rw-rw-rw-)
```

### 3. Display Flickering

**Symptoms:**
- Display turns on/off repeatedly
- Temperature shows briefly then disappears
- Intermittent display updates

**Solutions:**

#### Check Update Interval
```bash
# Edit configuration
sudo nano /etc/xigmatek-monitor.conf

# Ensure fast updates:
{
    "update_interval": 1.0,
    "wake_every_update": true,
    "wake_interval": 1
}

# Restart service
sudo systemctl restart xigmatek-monitor
```

#### Try Faster Updates
```bash
# For severe flickering, try even faster:
{
    "update_interval": 0.5,
    "wake_every_update": true
}
```

#### Check USB Issues
```bash
# USB errors can cause flickering
sudo dmesg | grep -i usb | tail -20

# Look for disconnect/reconnect messages
```

### 4. Temperature Sensors Not Found

**Symptoms:**
- Display shows fallback temperatures (35°C/40°C)
- Logs show "sensor error" messages
- Real temperatures not detected

**Solutions:**

#### Install and Configure Sensors
```bash
# Install lm-sensors
sudo pacman -S lm_sensors    # Arch
sudo apt install lm-sensors # Ubuntu/Debian
sudo dnf install lm_sensors # Fedora

# Configure sensors
sudo sensors-detect --auto

# Test sensors
sensors
```

#### CPU Temperature Detection
```bash
# Check what sensors are available
sensors | grep -E "(Tctl|Tccd|Core|Package|Tdie)"

# For AMD CPUs, look for:
# - Tctl (control temp)
# - Tccd1 (CPU die temp)
# - Tdie (die temp)

# For Intel CPUs, look for:
# - Core 0, Core 1, etc.
# - Package id 0
```

#### GPU Temperature Detection
```bash
# For NVIDIA GPUs
nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits

# For AMD GPUs
sensors | grep -E "(edge|junction)"

# For Intel integrated graphics
sensors | grep -i intel
```

#### Manual Sensor Configuration
```bash
# Edit configuration to specify sensor offsets
sudo nano /etc/xigmatek-monitor.conf

# Add offsets if sensors read differently:
{
    "cpu_offset": -5,    # Subtract 5°C from CPU reading
    "gpu_offset": 2      # Add 2°C to GPU reading
}
```

### 5. Service Startup Issues

**Symptoms:**
- Service fails to start automatically
- Works manually but not on boot
- "Failed to start" errors

**Solutions:**

#### Check Service Status
```bash
# Detailed status
sudo systemctl status xigmatek-monitor -l

# Check if enabled
sudo systemctl is-enabled xigmatek-monitor

# Enable if not enabled
sudo systemctl enable xigmatek-monitor
```

#### Check Dependencies
```bash
# Ensure Python and hidapi are available
python3 -c "import hid; print('✓ hidapi working')"

# Check script permissions
ls -la /usr/local/bin/xigmatek-monitor.py

# Should be executable (755 or 755)
```

#### Fix Service File
```bash
# Reload systemd configuration
sudo systemctl daemon-reload

# Check service file syntax
sudo systemd-analyze verify /etc/systemd/system/xigmatek-monitor.service
```

### 6. High CPU Usage

**Symptoms:**
- Python process using significant CPU
- System slowdown
- High frequency updates in logs

**Solutions:**

#### Optimize Update Interval
```bash
# Increase update interval (if no flickering)
sudo nano /etc/xigmatek-monitor.conf

{
    "update_interval": 2.0,
    "wake_every_update": false,
    "wake_interval": 10
}
```

#### Check for Reconnection Loops
```bash
# Look for repeated connection attempts
sudo journalctl -u xigmatek-monitor | grep -E "(connect|disconnect|error)"

# If many errors, check USB connection stability
```

### 7. Temperatures Not Updating

**Symptoms:**
- Display shows static temperatures
- Service running but temperatures don't change
- Logs show successful updates but display unchanged

**Solutions:**

#### Verify Sensor Changes
```bash
# Monitor sensors while running stress test
watch -n 1 sensors

# Run CPU stress test
stress --cpu 4 --timeout 60s

# Temperatures should increase
```

#### Check Temperature Ranges
```bash
# Verify temperature limits in config
sudo nano /etc/xigmatek-monitor.conf

{
    "min_temp": 20,
    "max_temp": 90
}

# Ensure actual temps are within range
```

#### Test Manual Updates
```bash
# Stop service
sudo systemctl stop xigmatek-monitor

# Run manually with verbose output
sudo /usr/local/bin/xigmatek-monitor.py --test

# Check if display updates during test
```

## Advanced Troubleshooting

### USB Traffic Analysis

```bash
# Install Wireshark
sudo pacman -S wireshark-qt    # Arch
sudo apt install wireshark    # Ubuntu

# Capture USB traffic (advanced users)
sudo wireshark
# Filter: usb.device_address == X && usb.idVendor == 0x0145
```

### Debug Mode

```bash
# Run with Python debugging
sudo python3 -u /usr/local/bin/xigmatek-monitor.py --test

# Enable verbose logging (edit script to add):
logging.basicConfig(level=logging.DEBUG)
```

### Hardware Testing

```bash
# Test on different USB ports
# USB 2.0 ports often more stable than USB 3.0

# Test with minimal USB devices connected
# Some devices can cause interference

# Try powered USB hub
# Can provide more stable power delivery
```

## Getting Help

### Before Reporting Issues

1. **Run the test script:**
   ```bash
   python3 scripts/test-device.py
   ```

2. **Collect logs:**
   ```bash
   sudo journalctl -u xigmatek-monitor -n 50 > xigmatek-logs.txt
   ```

3. **Check system info:**
   ```bash
   uname -a > system-info.txt
   lsusb >> system-info.txt
   python3 --version >> system-info.txt
   ```

### Reporting Issues

When creating a GitHub issue, include:

- **Distribution and version**
- **Hardware specifications**
- **Complete error messages**
- **Output from test script**
- **Service logs**
- **Steps to reproduce**

### Community Support

- **GitHub Issues**: Technical problems and bugs
- **GitHub Discussions**: General questions and ideas
- **Distribution Forums**: OS-specific issues

### Emergency Fixes

#### Completely Remove Driver
```bash
sudo systemctl stop xigmatek-monitor
sudo systemctl disable xigmatek-monitor
sudo rm /etc/systemd/system/xigmatek-monitor.service
sudo rm /usr/local/bin/xigmatek-monitor.py
sudo rm /etc/xigmatek-monitor.conf
sudo systemctl daemon-reload
```

#### Reset to Defaults
```bash
# Stop service
sudo systemctl stop xigmatek-monitor

# Reset configuration
sudo cp config/xigmatek-monitor.conf /etc/

# Restart service
sudo systemctl start xigmatek-monitor
```

## Prevention Tips

### Stable Setup
- Use USB 2.0 ports when possible
- Avoid USB hubs if experiencing issues
- Keep system and drivers updated
- Regular service log monitoring

### Monitoring Health
```bash
# Weekly health check
sudo systemctl status xigmatek-monitor
sudo journalctl -u xigmatek-monitor --since "1 week ago" | grep -i error

# Check for USB errors
sudo dmesg | grep -i usb | grep -i error
```

### Backup Configuration
```bash
# Backup working configuration
sudo cp /etc/xigmatek-monitor.conf ~/xigmatek-monitor.conf.backup

# Restore if needed
sudo cp ~/xigmatek-monitor.conf.backup /etc/xigmatek-monitor.conf
sudo systemctl restart xigmatek-monitor
```