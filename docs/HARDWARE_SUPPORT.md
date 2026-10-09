# Hardware Support

This document details hardware compatibility, requirements, and testing status for the XIGMATEK Linux Driver.

## Supported Devices

### ✅ Confirmed Working

| Model | USB IDs | Display Type | Status | Notes |
|-------|---------|--------------|--------|-------|
| XIGMATEK LK 360 Digital Arctic | 0145:1005 | LCD | ✅ Fully Supported | Original development target |
| XIGMATEK AK4 Digital (air cooler) | 0145:1002 ("HWCX USB Display") | Digital | ✅ Supported | Different protocol (handshake + status frame), auto-detected — see PROTOCOL.md |

### 🔍 Potentially Compatible

| Model | USB IDs | Display Type | Status | Notes |
|-------|---------|--------------|--------|-------|
| XIGMATEK LK 240 Digital Arctic | Unknown | LCD | 🔍 Needs Testing | Likely same protocol |
| XIGMATEK Aurora Arctic 240 | Unknown | LCD | 🔍 Needs Testing | May use similar commands |
| XIGMATEK Aurora Arctic 360 | Unknown | LCD | 🔍 Needs Testing | May use similar commands |

**Want to help test?** If you have other XIGMATEK coolers with displays, please [create an issue](../../issues/new) with your device information!

## System Requirements

### Minimum Requirements

**Hardware:**
- USB 2.0 or 3.0 port
- 512MB RAM (for Python process)
- 50MB disk space
- x86_64 or ARM64 processor

**Software:**
- Linux kernel 3.0+ with HID support
- Python 3.8+
- systemd (recommended) or other init system
- USB and HID kernel modules

### Recommended Requirements

**Hardware:**
- USB 2.0 port (more stable than USB 3.0 for some devices)
- 1GB+ RAM
- SSD storage (faster service startup)

**Software:**
- Recent Linux kernel (5.0+)
- Python 3.10+
- systemd 245+
- lm-sensors configured

## Distribution Compatibility

### ✅ Fully Tested

| Distribution | Version | Package Manager | Status | Notes |
|--------------|---------|----------------|---------|-------|
| Arch Linux | Current | pacman | ✅ Tested | Primary development platform |
| Manjaro | 21.0+ | pacman | ✅ Tested | Based on Arch |
| Ubuntu | 20.04+ | apt | ✅ Tested | LTS and current releases |
| Pop!_OS | 20.04+ | apt | ✅ Tested | Ubuntu-based |
| Linux Mint | 20+ | apt | ✅ Tested | Ubuntu-based |
| Debian | 11+ | apt | ✅ Tested | Stable and testing |
| Fedora | 35+ | dnf | ✅ Tested | Current releases |
| openSUSE Tumbleweed | Current | zypper | ✅ Tested | Rolling release |

### 🔶 Should Work (Untested)

| Distribution | Version | Package Manager | Status | Notes |
|--------------|---------|----------------|---------|-------|
| CentOS Stream | 8+ | dnf | 🔶 Untested | RHEL-based |
| Rocky Linux | 8+ | dnf | 🔶 Untested | RHEL-based |
| AlmaLinux | 8+ | dnf | 🔶 Untested | RHEL-based |
| openSUSE Leap | 15.4+ | zypper | 🔶 Untested | Stable release |
| EndeavourOS | Current | pacman | 🔶 Untested | Arch-based |
| Garuda Linux | Current | pacman | 🔶 Untested | Arch-based |

### ❓ Unknown Compatibility

| Distribution | Status | Notes |
|--------------|--------|-------|
| NixOS | ❓ Unknown | Different package management |
| Gentoo | ❓ Unknown | Source-based, should work |
| Void Linux | ❓ Unknown | Different init system |
| Alpine Linux | ❓ Unknown | musl libc, different package manager |

**Help expand compatibility!** Test on your distribution and report results.

## CPU Sensor Compatibility

### ✅ Fully Supported

#### AMD Processors
- **Ryzen 1000-7000 series** (all variants)
- **Threadripper 1000-7000 series**
- **EPYC** (server processors)

**Sensor Sources:**
- `Tctl` (Control temperature)
- `Tccd1` (Core Complex Die temperature)
- `Tdie` (Die temperature)

**Example Output:**
```
k10temp-pci-00c3
Adapter: PCI adapter
Tctl:         +45.0°C  <- Used by driver
Tccd1:        +42.5°C  <- Alternative source
```

#### Intel Processors
- **Core 8th-13th generation** (Coffee Lake to Raptor Lake)
- **Xeon** (server processors)
- **Core 6th-7th generation** (Skylake, Kaby Lake)

**Sensor Sources:**
- `Core 0, Core 1, ...` (Per-core temperatures)
- `Package id 0` (Package temperature)

**Example Output:**
```
coretemp-isa-0000
Adapter: ISA adapter
Package id 0:  +42.0°C  <- Used by driver
Core 0:        +40.0°C  <- Alternative source
Core 1:        +41.0°C
```

### 🔶 Partially Supported

#### Older AMD Processors
- **FX series** (limited sensor support)
- **Athlon** (basic temperature reading)
- **A-series APUs** (may require configuration)

#### Older Intel Processors
- **Core 2nd-5th generation** (Sandy Bridge to Broadwell)
- **Core 1st generation** (Nehalem) - limited

### ❌ Not Supported

- **Very old processors** without digital thermal sensors
- **Embedded processors** with limited sensor access
- **Some ARM processors** (architecture limitation)

## GPU Sensor Compatibility

### ✅ Fully Supported

#### NVIDIA GPUs
- **RTX 40 series** (Ada Lovelace)
- **RTX 30 series** (Ampere)
- **RTX 20 series** (Turing)
- **GTX 16 series** (Turing)
- **GTX 10 series** (Pascal)
- **Quadro** (professional cards)
- **Tesla** (data center cards)

**Requirements:**
- NVIDIA proprietary driver
- `nvidia-smi` utility

**Example Detection:**
```bash
nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits
65
```

#### AMD GPUs
- **RX 7000 series** (RDNA 3)
- **RX 6000 series** (RDNA 2)
- **RX 5000 series** (RDNA)
- **RX Vega series**
- **RX 500/400 series** (Polaris)
- **Radeon Pro** (professional cards)

**Requirements:**
- Mesa or AMDGPU driver
- `sensors` command with AMDGPU support

**Example Detection:**
```
amdgpu-pci-0300
Adapter: PCI adapter
vddgfx:        +0.81 V
fan1:         1200 RPM
edge:         +45.0°C  <- Used by driver
junction:     +52.0°C  <- Alternative source
```

### 🔶 Partially Supported

#### Intel Integrated Graphics
- **Iris Xe** (11th+ gen)
- **UHD Graphics** (8th-11th gen)
- **HD Graphics** (older generations)

**Note:** Temperature sensors may not be available on all models.

#### Older NVIDIA GPUs
- **GTX 900 series** and older
- May require legacy drivers
- Limited sensor access

#### Older AMD GPUs
- **R9/R7 series** and older
- May have limited sensor support
- Requires legacy drivers

### ❌ Not Supported

- **Very old GPUs** without digital thermal sensors
- **Some integrated graphics** without temperature sensors
- **Matrox, PowerVR,** and other uncommon GPUs

## Motherboard and USB Compatibility

### ✅ Recommended USB Configurations

**USB Port Types:**
- **USB 2.0 ports** (most stable)
- **USB 3.0/3.1/3.2** (usually works fine)
- **Direct motherboard ports** (preferred over hubs)

**Motherboard Chipsets:**
- **AMD**: B450, B550, B650, X470, X570, X670
- **Intel**: B460, B560, B660, Z490, Z590, Z690, Z790
- **Most modern chipsets** with standard USB controllers

### 🔶 May Have Issues

**USB Configurations:**
- **USB hubs** (can cause power/timing issues)
- **USB-C to USB-A adapters** (potential compatibility issues)
- **Very old USB controllers** (pre-2010)

**Motherboard Issues:**
- **Some MSI boards** with aggressive USB power management
- **Some ASUS boards** with problematic USB drivers
- **Budget motherboards** with poor USB power delivery

### ❌ Known Incompatible

- **USB 1.1 ports** (too slow)
- **Some Thunderbolt docks** (compatibility issues)
- **Virtual machines** (USB passthrough complications)

## BIOS/UEFI Settings

### Recommended Settings

```
USB Configuration:
├── USB 2.0 Support: Enabled
├── USB 3.0 Support: Enabled
├── Legacy USB Support: Enabled
├── USB Power Management: Disabled
└── XHCI Hand-off: Enabled

Power Management:
├── USB Standby Power: Enabled
├── ErP Ready: Disabled
└── Deep Sleep: Disabled
```

### Settings to Avoid

- **USB Selective Suspend** (can cause disconnections)
- **Aggressive power management** (may disable device)
- **Fast boot** (can skip USB initialization)

## Testing New Hardware

### Before Testing

1. **Check USB IDs:**
   ```bash
   lsusb | grep -i xigmatek
   # Look for vendor ID (0145) and product ID
   ```

2. **Verify HID interface:**
   ```bash
   ls -la /dev/hidraw*
   udevadm info -a -p $(udevadm info -q path -n /dev/hidraw0)
   ```

3. **Test basic connection:**
   ```bash
   python3 scripts/test-device.py
   ```

### Testing Process

1. **Device Detection:**
   - Run `lsusb` and `hid.enumerate()`
   - Document USB IDs and device path
   - Test basic HID communication

2. **Protocol Testing:**
   - Try standard wake command: `[0x08, 0x01, ...]`
   - Test temperature commands
   - Monitor display response

3. **Compatibility Testing:**
   - Test temperature ranges
   - Check display behavior
   - Verify anti-flicker settings

4. **Report Results:**
   - Create GitHub issue with findings
   - Include device model and USB IDs
   - Document any protocol differences

### Compatibility Test Script

```python
#!/usr/bin/env python3
"""Test new XIGMATEK device compatibility"""

import hid

def test_new_device(vendor_id, product_id):
    try:
        # Test connection
        device = hid.device()
        device.open(vendor_id, product_id)
        
        # Test wake command
        wake_cmd = [0x08, 0x01] + [0x00] * 62
        device.write(wake_cmd)
        
        # Test temperature commands
        gpu_cmd = [0x02, 0x20, 50] + [0x00] * 61
        device.write(gpu_cmd)
        
        cpu_cmd = [0x02, 68, 0x00] + [0x00] * 61  # 50°C
        device.write(cpu_cmd)
        
        device.close()
        return True
    except Exception as e:
        print(f"Test failed: {e}")
        return False

# Test with your device IDs
if test_new_device(0x0145, 0x1005):
    print("✅ Device compatible!")
else:
    print("❌ Device incompatible or needs different protocol")
```

## Reporting Hardware Issues

### Information to Include

**Device Information:**
- Exact model name and number
- USB vendor and product IDs
- Purchase date and region
- Any included software version

**System Information:**
- Linux distribution and version
- Kernel version
- Motherboard model
- USB controller type

**Test Results:**
- Output from test scripts
- Error messages and logs
- Photos/videos of device behavior
- Comparison with Windows software (if available)

### Creating Hardware Reports

1. **Use the issue template**
2. **Tag as "hardware-support"**
3. **Include all test output**
4. **Mention if willing to test further**

## Contributing Hardware Support

### Ways to Help

1. **Test existing devices** on new distributions
2. **Test new XIGMATEK models** for compatibility
3. **Submit compatibility reports** for untested systems
4. **Help debug issues** with problematic hardware
5. **Update documentation** with new findings

### Hardware Donation

If you have incompatible or untested XIGMATEK devices and are willing to help with development, please reach out through GitHub issues. Developer access to hardware significantly speeds up compatibility development.

---

**Last Updated:** June 2025  
**Contributors:** Nikola Zdravkovic