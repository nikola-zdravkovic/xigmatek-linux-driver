# XIGMATEK LK 360 Digital Arctic - Protocol Documentation

## Overview

The XIGMATEK LK 360 Digital Arctic communicates via USB HID (Human Interface Device) protocol. This document details the command structure and communication patterns discovered through reverse engineering.

## Device Information

- **Vendor ID**: 0x0145 (XIGMATEK)
- **Product ID**: 0x1005 (LK 360 Digital Arctic)
- **Interface**: USB HID
- **Communication**: Write-only commands
- **Packet Size**: 64 bytes

## Command Structure

All commands follow a consistent 64-byte structure:

```
Byte 0    : Command Type
Byte 1    : Sub-command or Parameter
Byte 2    : Data Payload (if applicable)
Byte 3-63 : Zero padding (0x00)
```

## Command Reference

### 1. Wake/Initialize Command

**Purpose**: Wake display from sleep state and initialize communication

**Command**: `[0x08, 0x01, 0x00, 0x00, ..., 0x00]`

**Structure**:
- Byte 0: `0x08` (Wake command type)
- Byte 1: `0x01` (Initialize parameter)
- Bytes 2-63: Zero padding

**Usage**:
```python
wake_cmd = [0x08, 0x01] + [0x00] * 62
device.write(wake_cmd)
```

**Notes**:
- Must be sent periodically to prevent display sleep
- Display sleep timeout appears to be ~2-3 seconds
- Essential for maintaining display visibility

### 2. GPU Temperature Command

**Purpose**: Set GPU temperature display

**Command**: `[0x02, 0x20, TEMP, 0x00, ..., 0x00]`

**Structure**:
- Byte 0: `0x02` (Temperature command type)
- Byte 1: `0x20` (GPU identifier)
- Byte 2: Temperature value (0-100°C)
- Bytes 3-63: Zero padding

**Temperature Range**: 0-100°C (direct mapping)

**Usage**:
```python
def set_gpu_temperature(device, temperature):
    temp = max(0, min(100, temperature))  # Clamp to valid range
    gpu_cmd = [0x02, 0x20, temp] + [0x00] * 61
    device.write(gpu_cmd)
```

**Examples**:
```python
# Set GPU to 45°C
gpu_cmd = [0x02, 0x20, 45] + [0x00] * 61

# Set GPU to 72°C  
gpu_cmd = [0x02, 0x20, 72] + [0x00] * 61
```

### 3. CPU Temperature Command

**Purpose**: Set CPU temperature display

**Command**: `[0x02, CMD_BYTE, 0x00, 0x00, ..., 0x00]`

**Structure**:
- Byte 0: `0x02` (Temperature command type)
- Byte 1: Calculated command byte (see formula)
- Byte 2: `0x00` (Reserved)
- Bytes 3-63: Zero padding

**Command Byte Calculation**:
```
command_byte = (temperature_celsius - 16) × 2
```

**Valid Temperature Range**: 16-90°C

**Formula Details**:
- **Input**: Temperature in Celsius (16-90°C)
- **Output**: Command byte (0-148)
- **Clamping**: Values outside range are clamped to nearest valid value

**Usage**:
```python
def cpu_temp_to_command(temperature):
    """Convert CPU temperature to command byte"""
    command_byte = (temperature - 16) * 2
    return max(1, min(255, command_byte))

def set_cpu_temperature(device, temperature):
    cmd_byte = cpu_temp_to_command(temperature)
    cpu_cmd = [0x02, cmd_byte, 0x00] + [0x00] * 61
    device.write(cpu_cmd)
```

**Examples**:
```python
# 25°C → (25-16)×2 = 18 → [0x02, 18, 0x00, ...]
# 45°C → (45-16)×2 = 58 → [0x02, 58, 0x00, ...]  
# 70°C → (70-16)×2 = 108 → [0x02, 108, 0x00, ...]
```

## Communication Patterns

### Standard Update Sequence

1. **Send Wake Command** (prevents display sleep)
2. **Wait** 100ms
3. **Send GPU Temperature**
4. **Wait** 100ms  
5. **Send CPU Temperature**
6. **Wait** until next update cycle

```python
def update_temperatures(device, cpu_temp, gpu_temp):
    # Wake display
    wake_cmd = [0x08, 0x01] + [0x00] * 62
    device.write(wake_cmd)
    time.sleep(0.1)
    
    # Set GPU temperature
    gpu_cmd = [0x02, 0x20, gpu_temp] + [0x00] * 61
    device.write(gpu_cmd)
    time.sleep(0.1)
    
    # Set CPU temperature
    cpu_cmd_byte = cpu_temp_to_command(cpu_temp)
    cpu_cmd = [0x02, cpu_cmd_byte, 0x00] + [0x00] * 61
    device.write(cpu_cmd)
```

### Anti-Flicker Pattern

To prevent display flickering, use fast update intervals with wake commands:

```python
def continuous_monitoring(device):
    while True:
        # Get current temperatures
        cpu_temp = get_cpu_temperature()
        gpu_temp = get_gpu_temperature()
        
        # Update display
        update_temperatures(device, cpu_temp, gpu_temp)
        
        # Short interval prevents sleep
        time.sleep(1.0)  # 1-second updates
```

## Timing Requirements

### Critical Timing
- **Wake Command**: Must be sent before each temperature update sequence
- **Inter-command Delay**: 100ms minimum between commands
- **Update Frequency**: 1-2 seconds maximum to prevent display sleep
- **USB Write Timeout**: 5 seconds (for error handling)

### Display Sleep Behavior
- **Sleep Timeout**: ~2-3 seconds without commands
- **Wake Time**: <100ms after wake command
- **Visual Symptom**: Display turns off/flickers without proper timing

## Error Handling

### Common Error Conditions

1. **Device Disconnected**
   ```python
   try:
       device.write(command)
   except OSError as e:
       # Device likely disconnected
       reconnect_device()
   ```

2. **Invalid Temperature Range**
   ```python
   def safe_cpu_temp(temp):
       return max(16, min(90, temp))
   
   def safe_gpu_temp(temp):
       return max(0, min(100, temp))
   ```

3. **Command Timeout**
   ```python
   import signal
   
   def timeout_handler(signum, frame):
       raise TimeoutError("Command timeout")
   
   signal.signal(signal.SIGALRM, timeout_handler)
   signal.alarm(5)  # 5-second timeout
   try:
       device.write(command)
   finally:
       signal.alarm(0)
   ```

## Device Detection

### USB Enumeration
```python
import hid

def find_xigmatek_device():
    """Find XIGMATEK device among all HID devices"""
    devices = hid.enumerate()
    for device_info in devices:
        if (device_info['vendor_id'] == 0x0145 and 
            device_info['product_id'] == 0x1005):
            return device_info['path']
    return None

def connect_device():
    """Connect to XIGMATEK device"""
    device = hid.device()
    device.open(0x0145, 0x1005)
    return device
```

### Linux-Specific Detection
```bash
# Check USB devices
lsusb | grep "0145:1005"

# Check HID devices
ls -la /dev/hidraw*

# Check device permissions
udevadm info -a -p $(udevadm info -q path -n /dev/hidraw0)
```

## Advanced Usage

### Optimized Update Loop
```python
class XigmatekController:
    def __init__(self):
        self.device = None
        self.last_wake = 0
        self.wake_interval = 10  # Wake every 10 updates
        
    def update_with_smart_wake(self, cpu_temp, gpu_temp, update_count):
        """Update temperatures with intelligent wake management"""
        
        # Send wake command periodically
        if update_count % self.wake_interval == 0:
            wake_cmd = [0x08, 0x01] + [0x00] * 62
            self.device.write(wake_cmd)
            time.sleep(0.1)
        
        # Send temperatures
        gpu_cmd = [0x02, 0x20, gpu_temp] + [0x00] * 61
        self.device.write(gpu_cmd)
        time.sleep(0.05)  # Shorter delay for efficiency
        
        cpu_cmd_byte = cpu_temp_to_command(cpu_temp)
        cpu_cmd = [0x02, cpu_cmd_byte, 0x00] + [0x00] * 61
        self.device.write(cpu_cmd)
```

### Batch Commands
```python
def send_command_batch(device, commands):
    """Send multiple commands with proper timing"""
    for i, cmd in enumerate(commands):
        device.write(cmd)
        if i < len(commands) - 1:  # Don't delay after last command
            time.sleep(0.1)
```

## Reverse Engineering Notes

### Discovery Process
1. **USB Traffic Analysis**: Used Wireshark to capture Windows software communication
2. **Pattern Recognition**: Identified repeating command structures
3. **Temperature Correlation**: Compared commands with known temperature values
4. **Timing Analysis**: Determined sleep behavior and wake requirements

### Command Byte Investigation
The CPU temperature formula was discovered through systematic testing:

```python
# Test data collected:
# Temp 20°C → Command byte 8  → (20-16)×2 = 8  ✓
# Temp 25°C → Command byte 18 → (25-16)×2 = 18 ✓
# Temp 30°C → Command byte 28 → (30-16)×2 = 28 ✓
# Formula confirmed: (temp - 16) × 2
```

### Sleep Behavior Analysis
- Tested various update intervals
- Observed visual flickering patterns
- Determined optimal wake command frequency
- Confirmed 1-second updates prevent sleep

## Protocol Limitations

### Known Constraints
- **Write-only**: No read commands discovered
- **Temperature only**: No other sensor data support
- **Fixed format**: No custom display messages
- **No feedback**: No acknowledgment from device

### Potential Extensions
- **RGB Control**: Additional command types may exist
- **Fan Control**: Possible integration with cooling curves
- **Custom Messages**: Text display capabilities unknown
- **Sensor Reading**: Device may support temperature feedback

## Security Considerations

### Protocol Security
- **No authentication**: Commands sent without verification
- **No encryption**: All data transmitted in plain text
- **Limited attack surface**: Write-only, temperature data only
- **Local access required**: USB connection necessary

### Recommendations
- **Input validation**: Always validate temperature ranges
- **Rate limiting**: Prevent command flooding
- **Error handling**: Graceful failure on malformed data
- **Permission management**: Use appropriate udev rules

## Future Protocol Investigation

### Areas for Further Research
1. **Additional Commands**:
   - RGB lighting control
   - Fan speed control
   - Display brightness
   - Custom text messages

2. **Read Commands**:
   - Device status
   - Actual sensor readings
   - Firmware version
   - Error states

3. **Advanced Features**:
   - Temperature alarms
   - Historical data
   - Configuration persistence
   - Multiple sensor support

### Research Tools
```bash
# USB traffic capture
sudo wireshark

# HID command testing
sudo python3 -c "
import hid
device = hid.device()
device.open(0x0145, 0x1005)
# Test commands here
device.close()
"

# Protocol analysis
hexdump -C captured_data.bin
```

## Conclusion

The XIGMATEK LK 360 Digital Arctic uses a simple but effective HID protocol for temperature display. The key discoveries enabling reliable Linux support are:

1. **Command structure**: 64-byte HID commands with specific byte layouts
2. **Temperature encoding**: Different formulas for CPU and GPU temperatures
3. **Wake management**: Critical for preventing display flickering
4. **Timing requirements**: Proper delays and update frequencies

This protocol documentation enables full Linux compatibility and provides a foundation for future enhancements and additional device support.