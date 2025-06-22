#!/usr/bin/env python3
"""
XIGMATEK Device Detection and Testing Script
Tests device connection, basic functionality, and compatibility
"""

import hid
import time
import subprocess
import sys

def print_header():
    """Print script header"""
    print("🔍 XIGMATEK Device Detection & Test")
    print("=" * 40)

def check_usb_connection():
    """Check if device appears in USB devices"""
    print("📡 Checking USB connection...")
    try:
        result = subprocess.run(['lsusb'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            xigmatek_found = False
            
            for line in lines:
                if '0145:1005' in line:
                    print(f"✅ Found XIGMATEK device: {line}")
                    xigmatek_found = True
                    break
            
            if not xigmatek_found:
                print("❌ XIGMATEK device not found in USB devices")
                print("💡 Check:")
                print("   - Device is plugged in")
                print("   - USB cable is working")
                print("   - Device is powered on")
                return False
            return True
        else:
            print("❌ Failed to run lsusb command")
            return False
    except Exception as e:
        print(f"❌ Error checking USB: {e}")
        return False

def check_hid_devices():
    """Check HID device enumeration"""
    print("\n🔌 Checking HID devices...")
    try:
        devices = hid.enumerate()
        xigmatek_devices = []
        
        for device in devices:
            if device['vendor_id'] == 0x0145 and device['product_id'] == 0x1005:
                xigmatek_devices.append(device)
        
        if xigmatek_devices:
            print(f"✅ Found {len(xigmatek_devices)} XIGMATEK HID device(s)")
            for i, device in enumerate(xigmatek_devices):
                print(f"   Device {i+1}:")
                print(f"     Path: {device['path']}")
                print(f"     Manufacturer: {device['manufacturer_string']}")
                print(f"     Product: {device['product_string']}")
                print(f"     Serial: {device['serial_number']}")
            return True
        else:
            print("❌ No XIGMATEK devices found in HID enumeration")
            return False
    except Exception as e:
        print(f"❌ Error enumerating HID devices: {e}")
        return False

def test_device_connection():
    """Test actual device connection"""
    print("\n🔗 Testing device connection...")
    try:
        device = hid.device()
        device.open(0x0145, 0x1005)
        print("✅ Successfully opened device connection")
        
        # Test basic write operation
        test_cmd = [0x08, 0x01] + [0x00] * 62
        device.write(test_cmd)
        print("✅ Successfully sent test command")
        
        device.close()
        print("✅ Device connection test passed")
        return True
        
    except PermissionError:
        print("❌ Permission denied!")
        print("💡 Solutions:")
        print("   - Run as root: sudo python3 test-device.py")
        print("   - Fix udev rules: check /etc/udev/rules.d/99-xigmatek.rules")
        print("   - Add user to appropriate group")
        return False
    except Exception as e:
        print(f"❌ Device connection failed: {e}")
        return False

def test_temperature_commands():
    """Test temperature command functionality"""
    print("\n🌡️  Testing temperature commands...")
    try:
        device = hid.device()
        device.open(0x0145, 0x1005)
        
        # Initialize display
        wake_cmd = [0x08, 0x01] + [0x00] * 62
        device.write(wake_cmd)
        time.sleep(0.5)
        print("✅ Display initialization sent")
        
        # Test GPU temperature command
        gpu_cmd = [0x02, 0x20, 50] + [0x00] * 61  # 50°C
        device.write(gpu_cmd)
        time.sleep(0.1)
        print("✅ GPU temperature command (50°C) sent")
        
        # Test CPU temperature command
        cpu_cmd_byte = (65 - 16) * 2  # 65°C
        cpu_cmd = [0x02, cpu_cmd_byte, 0x00] + [0x00] * 61
        device.write(cpu_cmd)
        time.sleep(0.1)
        print("✅ CPU temperature command (65°C) sent")
        
        device.close()
        print("✅ Temperature command test passed")
        print("💡 Check your display - it should show CPU: 65°C, GPU: 50°C")
        return True
        
    except Exception as e:
        print(f"❌ Temperature command test failed: {e}")
        return False

def test_sensor_availability():
    """Test system sensor availability"""
    print("\n🌡️  Testing sensor availability...")
    
    # Test sensors command
    try:
        result = subprocess.run(['sensors'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            output = result.stdout
            cpu_sensors = []
            gpu_sensors = []
            
            # Look for CPU sensors
            cpu_patterns = ['Tccd1:', 'Tctl:', 'Core 0:', 'Package id 0:', 'Tdie:']
            for line in output.split('\n'):
                for pattern in cpu_patterns:
                    if pattern in line and '+' in line:
                        temp_str = line.split('+')[1].split('°')[0].strip()
                        cpu_sensors.append(f"{pattern} {temp_str}°C")
                        break
            
            # Look for GPU sensors (NVIDIA)
            try:
                nvidia_result = subprocess.run(
                    ['nvidia-smi', '--query-gpu=temperature.gpu', '--format=csv,noheader,nounits'],
                    capture_output=True, text=True, timeout=5
                )
                if nvidia_result.returncode == 0:
                    gpu_temp = nvidia_result.stdout.strip()
                    gpu_sensors.append(f"NVIDIA GPU: {gpu_temp}°C")
            except:
                pass
            
            # Look for AMD GPU sensors
            for line in output.split('\n'):
                if ('edge:' in line or 'junction:' in line) and '+' in line:
                    temp_str = line.split('+')[1].split('°')[0].strip()
                    gpu_sensors.append(f"AMD GPU: {temp_str}°C")
            
            print(f"✅ Sensors command available")
            if cpu_sensors:
                print(f"✅ Found {len(cpu_sensors)} CPU sensor(s):")
                for sensor in cpu_sensors[:3]:  # Show first 3
                    print(f"   - {sensor}")
            else:
                print("⚠️  No CPU sensors detected")
            
            if gpu_sensors:
                print(f"✅ Found {len(gpu_sensors)} GPU sensor(s):")
                for sensor in gpu_sensors:
                    print(f"   - {sensor}")
            else:
                print("⚠️  No GPU sensors detected")
            
            return True
        else:
            print("❌ Sensors command failed")
            print("💡 Install lm-sensors: sudo pacman -S lm_sensors")
            return False
    except FileNotFoundError:
        print("❌ 'sensors' command not found")
        print("💡 Install lm-sensors package")
        return False
    except Exception as e:
        print(f"❌ Sensor test error: {e}")
        return False

def check_permissions():
    """Check device permissions"""
    print("\n🔐 Checking device permissions...")
    try:
        # Check if udev rule exists
        udev_rule_path = "/etc/udev/rules.d/99-xigmatek.rules"
        try:
            with open(udev_rule_path, 'r') as f:
                rule_content = f.read()
                if '0145' in rule_content and '1005' in rule_content:
                    print("✅ udev rule found and appears correct")
                else:
                    print("⚠️  udev rule exists but may be incorrect")
        except FileNotFoundError:
            print("❌ udev rule not found")
            print("💡 Create udev rule:")
            print('   sudo bash -c \'echo "SUBSYSTEM==\\"hidraw\\", ATTRS{idVendor}==\\"0145\\", ATTRS{idProduct}==\\"1005\\", MODE=\\"0666\\", GROUP=\\"users\\"" > /etc/udev/rules.d/99-xigmatek.rules\'')
            print("   sudo udevadm control --reload-rules")
            print("   sudo udevadm trigger")
        
        # Check hidraw devices
        try:
            result = subprocess.run(['ls', '-la', '/dev/hidraw*'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ HID raw devices found:")
                for line in result.stdout.strip().split('\n')[:3]:  # Show first 3
                    print(f"   {line}")
            else:
                print("❌ No /dev/hidraw* devices found")
        except Exception as e:
            print(f"⚠️  Could not check /dev/hidraw*: {e}")
        
        return True
    except Exception as e:
        print(f"❌ Permission check error: {e}")
        return False

def run_full_test():
    """Run complete test suite"""
    print_header()
    
    tests = [
        ("USB Connection", check_usb_connection),
        ("HID Enumeration", check_hid_devices),
        ("Device Connection", test_device_connection),
        ("Temperature Commands", test_temperature_commands),
        ("System Sensors", test_sensor_availability),
        ("Permissions", check_permissions),
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        try:
            results[test_name] = test_func()
        except KeyboardInterrupt:
            print(f"\n❌ Test interrupted by user")
            results[test_name] = False
            break
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 TEST SUMMARY")
    print(f"{'='*50}")
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<20} {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your system is ready for XIGMATEK monitoring.")
        print("💡 Next steps:")
        print("   - Run the setup script: ./setup.sh")
        print("   - Start the service: sudo systemctl start xigmatek-monitor")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please address the issues above.")
        print("💡 Common solutions:")
        print("   - Run as root: sudo python3 test-device.py")
        print("   - Install missing packages")
        print("   - Check USB connection")
        print("   - Create udev rules")
    
    return passed == total

def main():
    """Main function"""
    if len(sys.argv) > 1:
        if sys.argv[1] == '--quick':
            print_header()
            success = test_device_connection()
            sys.exit(0 if success else 1)
        elif sys.argv[1] == '--sensors-only':
            print_header()
            success = test_sensor_availability()
            sys.exit(0 if success else 1)
    
    success = run_full_test()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()