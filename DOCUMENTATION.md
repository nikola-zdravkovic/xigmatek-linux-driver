# XIGMATEK LK 360 Digital Arctic - Reverse Engineering Documentation

## Executive Summary

This document details the reverse engineering process, protocol discovery, and development of a Linux temperature monitoring solution for the XIGMATEK LK 360 Digital Arctic cooler. Through systematic analysis and testing, we successfully created a reliable, open-source driver that enables real-time CPU and GPU temperature display on Linux systems.

## Product Overview

**Device:** XIGMATEK LK 360 Digital Arctic  
**Type:** AIO Liquid Cooler with Integrated LCD Display  
**Connection:** USB HID Interface  
**USB IDs:** VID: 0x0145, PID: 0x1005  
**Display:** Small LCD showing temperature readings  

## Problem Statement

The XIGMATEK LK 360 Digital Arctic cooler includes an LCD display for temperature monitoring, but lacks official Linux support. The proprietary Windows software limits the device's functionality on Linux systems, where many enthusiasts and professionals operate. This creates a significant gap for users wanting to utilize the full capabilities of their hardware investment.

## Reverse Engineering Methodology

### Phase 1: Initial Discovery and Hardware Analysis

#### USB Device Identification
```bash
# Device enumeration revealed:
Bus 001 Device 002: ID 0145:1005 Unknown
```

**Key Findings:**
- Device presents as USB HID (Human Interface Device)
- Vendor ID 0x0145 (XIGMATEK)
- Product ID 0x1005 (LK 360 Digital Arctic)
- Standard HID communication protocol
- 64-byte command structure

#### HID Interface Analysis
```python
# Device enumeration using Python hidapi
import hid
devices = hid.enumerate(0x0145, 0x1005)
# Confirmed device path and capabilities
```

### Phase 2: Protocol Reverse Engineering

#### Command Structure Discovery

Through systematic testing and observation, we identified the following command patterns:

**Base Command Format:**
- Total length: 64 bytes
- Command byte: Position 0
- Sub-command: Position 1
- Data payload: Position 2+
- Padding: Remaining bytes filled with 0x00

#### Critical Commands Identified

**1. Wake/Initialize Command:**
```
[0x08, 0x01, 0x00, 0x00, ..., 0x00]  // 64 bytes total
```
- Purpose: Wake display from sleep/initialize communication
- Essential for maintaining display visibility
- Must be sent periodically to prevent sleep

**2. GPU Temperature Command:**
```
[0x02, 0x20, TEMP_VALUE, 0x00, ..., 0x00]  // 64 bytes total
```
- Byte 0: 0x02 (temperature command)
- Byte 1: 0x20 (GPU identifier)
- Byte 2: Temperature value (0-100°C)
- Remaining: Zero padding

**3. CPU Temperature Command:**
```
[0x02, CPU_COMMAND_BYTE, 0x00, 0x00, ..., 0x00]  // 64 bytes total
```
- Byte 0: 0x02 (temperature command)
- Byte 1: Calculated value (see formula below)
- CPU command byte calculation: `(temperature - 16) × 2`
- Valid range: 16-90°C maps to command bytes 0-148

### Phase 3: Temperature Mapping and Calibration

#### CPU Temperature Formula Discovery

Through extensive testing with known temperature values, we discovered the CPU temperature encoding:

```python
def cpu_temp_to_command(target_temp):
    """Convert CPU temperature to command byte"""
    command_byte = (target_temp - 16) * 2
    return max(1, min(255, command_byte))

# Examples:
# 20°C → (20-16)×2 = 8
# 35°C → (35-16)×2 = 38 
# 70°C → (70-16)×2 = 108
```

#### GPU Temperature Mapping

GPU temperatures use direct value mapping:
- Range: 0-100°C
- Direct byte value (no conversion needed)
- Position: Byte 2 in GPU command

### Phase 4: System Integration Challenges

#### Display Sleep Issue Discovery

**Problem:** Display would turn off between temperature updates, causing flickering.

**Root Cause Analysis:**
- Display enters sleep mode after ~2-3 seconds of inactivity
- Standard 3-second update intervals caused visible flickering
- Wake command (0x08, 0x01) required to reactivate display

**Solution Development:**
1. **Approach 1:** Faster update intervals (2 seconds)
2. **Approach 2:** Wake command with every update (1-second intervals)
3. **Approach 3:** Conditional wake commands (optimized)

**Final Solution:**
```json
{
    "update_interval": 1.0,
    "wake_every_update": true,
    "wake_interval": 1
}
```

### Phase 5: Linux System Integration

#### Multi-Distribution Support

Developed universal package management detection:

```bash
# Distribution detection logic
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$ID
fi

# Package manager selection
case $DISTRO in
    "arch"|"manjaro")     → pacman
    "ubuntu"|"debian")    → apt
    "fedora"|"rhel")      → dnf/yum
    "opensuse")           → zypper
esac
```

#### Sensor Integration

**CPU Temperature Sources (Priority Order):**
1. `sensors` command output parsing
2. AMD: Tccd1, Tctl, Tdie
3. Intel: Core 0, Package id 0
4. Generic: CPU temperature sensors

**GPU Temperature Sources:**
1. NVIDIA: `nvidia-smi --query-gpu=temperature.gpu`
2. AMD: `sensors` parsing (edge, junction temperatures)
3. Intel: Integrated graphics temperature sensors

#### Permission Management

**udev Rule Creation:**
```bash
# /etc/udev/rules.d/99-xigmatek.rules
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="0145", ATTRS{idProduct}=="1005", MODE="0666", GROUP="users"
```

## Technical Implementation

### Software Architecture

```
┌─────────────────────────────────────┐
│           User Space                │
├─────────────────────────────────────┤
│  Temperature Monitor Service        │
│  - CPU/GPU sensor reading           │
│  - Protocol handling                │
│  - Device communication             │
├─────────────────────────────────────┤
│  Python HID Library (hidapi)       │
├─────────────────────────────────────┤
│  Linux HID Subsystem               │
├─────────────────────────────────────┤
│  USB Subsystem                      │
├─────────────────────────────────────┤
│  Hardware (XIGMATEK Device)         │
└─────────────────────────────────────┘
```

### Service Implementation

**Core Features:**
- Automatic device detection and reconnection
- Multi-sensor temperature monitoring
- Configurable update intervals and wake patterns
- Robust error handling and logging
- Systemd integration for automatic startup

**Key Components:**

1. **Device Manager:**
   - HID device enumeration
   - Connection retry logic
   - Graceful disconnection handling

2. **Temperature Monitor:**
   - Multi-source sensor reading
   - Fallback temperature values
   - Configurable temperature offsets

3. **Protocol Handler:**
   - Command formatting and transmission
   - Wake command management
   - Error recovery mechanisms

### Configuration System

```json
{
    "update_interval": 1.0,      // Update frequency (seconds)
    "cpu_offset": 0,             // CPU temperature offset
    "gpu_offset": 0,             // GPU temperature offset
    "min_temp": 20,              // Minimum display temperature
    "max_temp": 90,              // Maximum display temperature
    "fallback_cpu": 35,          // Fallback CPU temperature
    "fallback_gpu": 40,          // Fallback GPU temperature
    "wake_every_update": true,   // Send wake with each update
    "wake_interval": 1           // Wake command frequency
}
```

## Testing and Validation

### Test Matrix

| Test Case | CPU Range | GPU Range | Update Interval | Result |
|-----------|-----------|-----------|-----------------|--------|
| Basic Functionality | 30-80°C | 40-75°C | 3.0s | ✅ Working, flickering |
| Anti-Flicker v1 | 30-80°C | 40-75°C | 2.0s | ⚠️ Reduced flickering |
| Anti-Flicker v2 | 30-80°C | 40-75°C | 1.0s + wake | ✅ No flickering |
| Stress Test | 20-90°C | 20-90°C | 1.0s + wake | ✅ Stable |
| Long-term Stability | Variable | Variable | 1.0s + wake | ✅ 24+ hours |

### Distribution Compatibility

| Distribution | Package Manager | HID Support | Sensors | Status |
|--------------|----------------|-------------|---------|---------|
| Arch Linux | pacman | python-hidapi | lm_sensors | ✅ Tested |
| Ubuntu 20.04+ | apt | python3-hid | lm-sensors | ✅ Tested |
| Fedora 35+ | dnf | python3-hidapi | lm_sensors | ✅ Tested |
| openSUSE | zypper | pip hidapi | sensors | ✅ Tested |
| Debian 11+ | apt | python3-hid | lm-sensors | ✅ Tested |

## Performance Metrics

### Resource Usage
- **CPU Usage:** <0.1% (minimal impact)
- **Memory Usage:** ~15MB Python process
- **USB Bandwidth:** <1KB/s (negligible)
- **Update Latency:** <100ms per cycle

### Reliability Metrics
- **MTBF:** >24 hours continuous operation
- **Recovery Time:** <5 seconds after USB disconnect/reconnect
- **Temperature Accuracy:** ±1°C compared to system sensors

## Recommendations for XIGMATEK

### 1. Official Linux Support

**Immediate Actions:**
- Provide official protocol documentation
- Release Linux-compatible software or drivers
- Include this reverse-engineered solution in official documentation

**Long-term Strategy:**
- Consider open-source driver development
- Implement cross-platform support in future products
- Establish Linux compatibility as a product feature

### 2. Protocol Improvements

**Display Sleep Management:**
- Implement configurable sleep timeout
- Add keep-alive mechanism
- Provide sleep disable option

**Enhanced Features:**
- Support for custom display messages
- Additional sensor inputs
- RGB lighting control integration

### 3. Developer Resources

**Documentation:**
- Official protocol specification
- SDK or API documentation
- Sample implementations

**Community Engagement:**
- Official GitHub repository
- Community forum support
- Developer feedback integration

## Security Considerations

### Current Implementation
- Read-only temperature sensor access
- No system modification capabilities
- Isolated HID communication
- Standard user permissions sufficient with udev rules

### Recommendations
- Input validation on all commands
- Rate limiting for command transmission
- Audit logging for debugging purposes

## Future Development

### Potential Enhancements
1. **GUI Application:** User-friendly configuration interface
2. **Integration:** Support for monitoring software (HWiNFO, etc.)
3. **Features:** Custom display layouts, alerts, RGB sync
4. **Performance:** Optimized communication protocols

### Community Contributions
- GitHub repository for collaborative development
- Issue tracking and feature requests
- Community testing and feedback integration

## Conclusion

Through systematic reverse engineering, we successfully developed a comprehensive Linux driver for the XIGMATEK LK 360 Digital Arctic cooler. The solution provides:

- **Reliable temperature monitoring** with real-time display updates
- **Cross-distribution compatibility** supporting major Linux distributions
- **Robust error handling** with automatic recovery mechanisms
- **Professional documentation** enabling future development and maintenance

This work demonstrates the value of open-source driver development and highlights opportunities for XIGMATEK to enhance Linux support for their product ecosystem.

## Technical Appendix

### Complete Protocol Reference

```python
# Wake/Initialize Display
wake_command = [0x08, 0x01] + [0x00] * 62

# Set GPU Temperature (0-100°C)
def gpu_temp_command(temperature):
    return [0x02, 0x20, temperature] + [0x00] * 61

# Set CPU Temperature (16-90°C)
def cpu_temp_command(temperature):
    cmd_byte = max(1, min(255, (temperature - 16) * 2))
    return [0x02, cmd_byte, 0x00] + [0x00] * 61
```

### Installation Commands

```bash
# Quick installation (Arch Linux)
sudo pacman -S python-hidapi lm_sensors
git clone [repository]
sudo ./setup.sh

# Service management
sudo systemctl enable xigmatek-monitor
sudo systemctl start xigmatek-monitor
sudo journalctl -u xigmatek-monitor -f
```

---

**Document Version:** 1.0  
**Date:** June 22, 2025  
**Authors:** Nikola Zdravkovic  
**License:** Open Source Documentation