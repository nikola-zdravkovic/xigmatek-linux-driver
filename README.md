# XIGMATEK Linux Driver

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Arch Linux](https://img.shields.io/badge/Arch%20Linux-supported-blue)](https://archlinux.org/)
[![Ubuntu](https://img.shields.io/badge/Ubuntu-supported-orange)](https://ubuntu.com/)
[![Fedora](https://img.shields.io/badge/Fedora-supported-blue)](https://getfedora.org/)

> **Unofficial Linux driver for XIGMATEK LK 360 Digital Arctic AIO cooler with real-time temperature display**

![XIGMATEK Display Demo](https://via.placeholder.com/400x200/1a1a1a/00ff00?text=CPU%3A+65°C%0AGPU%3A+58°C)

## 🎯 Features

- ✅ **Real-time temperature monitoring** on LCD display
- ✅ **Multi-distribution support** (Arch, Ubuntu, Fedora, openSUSE)
- ✅ **Auto-detection** of CPU and GPU sensors
- ✅ **No flickering** - smooth display updates
- ✅ **Systemd integration** - starts automatically on boot
- ✅ **Robust error handling** - auto-reconnect on USB issues
- ✅ **Configurable** - offsets, update intervals, sensor sources

## 🚀 Quick Start

### One-Line Installation

```bash
# Download and run the setup script
curl -sSL https://raw.githubusercontent.com/nikola-zdravkovic/xigmatek-linux-driver/main/setup.sh | bash
```

### Manual Installation

```bash
# Clone the repository
git clone https://github.com/nikola-zdravkovic/xigmatek-linux-driver.git
cd xigmatek-linux-driver

# Run setup script
chmod +x setup.sh
./setup.sh
```

### Start the Service

```bash
# Start now
sudo systemctl start xigmatek-monitor

# Enable on boot
sudo systemctl enable xigmatek-monitor

# Check status
sudo systemctl status xigmatek-monitor
```

## 📋 Requirements

### Hardware
- XIGMATEK LK 360 Digital Arctic AIO cooler
- USB connection to motherboard
- Linux system with HID support

### Software
- **Python 3.8+**
- **hidapi** library
- **lm-sensors** (for temperature monitoring)
- **systemd** (for service management)

### Supported Distributions
| Distribution | Status | Package Manager |
|--------------|--------|----------------|
| Arch Linux   | ✅ Tested | pacman |
| Ubuntu 20.04+ | ✅ Tested | apt |
| Fedora 35+   | ✅ Tested | dnf |
| Debian 11+   | ✅ Tested | apt |
| openSUSE     | ✅ Tested | zypper |

## 🔧 Configuration

Edit `/etc/xigmatek-monitor.conf`:

```json
{
    "update_interval": 1.0,        // Update frequency (seconds)
    "cpu_offset": 0,               // CPU temperature offset (±°C)
    "gpu_offset": 0,               // GPU temperature offset (±°C)
    "min_temp": 20,                // Minimum display temperature
    "max_temp": 90,                // Maximum display temperature
    "fallback_cpu": 35,            // Fallback CPU temperature
    "fallback_gpu": 40,            // Fallback GPU temperature
    "wake_every_update": true,     // Prevent display sleep
    "wake_interval": 1             // Wake command frequency
}
```

After editing, restart the service:
```bash
sudo systemctl restart xigmatek-monitor
```

## 📊 Monitoring

### Check Service Status
```bash
# Service status
sudo systemctl status xigmatek-monitor

# Live logs
sudo journalctl -u xigmatek-monitor -f

# Log file
tail -f /var/log/xigmatek-monitor.log
```

### Manual Testing
```bash
# Test device connection
python3 scripts/test-device.py

# Manual temperature test
python3 scripts/manual-test.py

# Check for display flickering
python3 scripts/flicker-test.py
```

## 🐛 Troubleshooting

### Device Not Found
```bash
# Check USB connection
lsusb | grep 0145:1005

# Check HID devices
ls -la /dev/hidraw*

# Try different USB port
```

### Permission Issues
```bash
# Check udev rules
cat /etc/udev/rules.d/99-xigmatek.rules

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### Display Flickering
- Ensure `wake_every_update: true` in config
- Try faster update interval (`update_interval: 0.5`)
- Check logs for connection errors

See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for detailed solutions.

## 📚 Documentation

- [**Installation Guide**](INSTALL.md) - Detailed installation instructions
- [**Technical Documentation**](DOCUMENTATION.md) - Reverse engineering process
- [**Protocol Reference**](docs/PROTOCOL.md) - Communication protocol details
- [**Troubleshooting**](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [**Contributing**](docs/CONTRIBUTING.md) - How to contribute

## 🎮 Supported Hardware

### Confirmed Working
- **XIGMATEK LK 360 Digital Arctic** (VID: 0x0145, PID: 0x1005)

### Potentially Compatible
- Other XIGMATEK coolers with LCD displays
- Submit an issue if you test other models!

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

### Ways to Contribute
- 🐛 **Bug reports** - Found an issue? Let us know!
- 💡 **Feature requests** - Ideas for improvements
- 🔧 **Code contributions** - Fixes and enhancements
- 📚 **Documentation** - Improve guides and docs
- 🧪 **Testing** - Try on different systems

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This is an **unofficial, community-developed driver**. It is not affiliated with or endorsed by XIGMATEK. Use at your own risk.

- No warranty provided
- May void warranty (check with manufacturer)
- Backup any existing software before installation

## 🙏 Acknowledgments

- **XIGMATEK** - For creating awesome hardware
- **Linux Community** - For reverse engineering tools and knowledge
- **Contributors** - Everyone who helped test and improve this driver

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/nikola-zdravkovic/xigmatek-linux-driver/issues)
- **Discussions**: [GitHub Discussions](https://github.com/nikola-zdravkovic/xigmatek-linux-driver/discussions)
- **Email**: your-email@example.com

---

**⭐ If this project helped you, please give it a star! It helps others discover the project.**

## 🚧 Roadmap

- [ ] GUI configuration tool
- [ ] RGB lighting control
- [ ] Additional XIGMATEK device support
- [ ] Integration with monitoring software
- [ ] Custom display messages
- [ ] Temperature alerts and notifications

---

Made with ❤️ for the Linux community