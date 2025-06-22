#!/usr/bin/env python3
"""
XIGMATEK Anti-Flicker Testing Script
Tests different update patterns to prevent display flickering and sleep
"""

import hid
import time
import sys
import threading

def print_header():
    """Print script header"""
    print("💫 XIGMATEK Anti-Flicker Testing Tool")
    print("=" * 45)
    print("Testing different update patterns to prevent display sleep/flicker")
    print("")

def connect_device():
    """Connect to XIGMATEK device"""
    try:
        device = hid.device()
        device.open(0x0145, 0x1005)
        print("✅ Connected to XIGMATEK device")
        return device
    except PermissionError:
        print("❌ Permission denied! Run as root or fix udev rules")
        return None
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return None

def send_temperatures_with_wake(device, cpu_temp, gpu_temp):
    """Send temperatures with wake command"""
    try:
        # Wake command
        wake_cmd = [0x08, 0x01] + [0x00] * 62
        device.write(wake_cmd)
        time.sleep(0.1)
        
        # GPU temperature
        gpu_cmd = [0x02, 0x20, gpu_temp] + [0x00] * 61
        device.write(gpu_cmd)
        time.sleep(0.1)
        
        # CPU temperature
        cpu_cmd_byte = (cpu_temp - 16) * 2
        cpu_cmd = [0x02, cpu_cmd_byte, 0x00] + [0x00] * 61
        device.write(cpu_cmd)
        
        return True
    except Exception as e:
        print(f"❌ Error sending with wake: {e}")
        return False

def send_temperatures_no_wake(device, cpu_temp, gpu_temp):
    """Send temperatures without wake command"""
    try:
        # GPU temperature
        gpu_cmd = [0x02, 0x20, gpu_temp] + [0x00] * 61
        device.write(gpu_cmd)
        time.sleep(0.1)
        
        # CPU temperature
        cpu_cmd_byte = (cpu_temp - 16) * 2
        cpu_cmd = [0x02, cpu_cmd_byte, 0x00] + [0x00] * 61
        device.write(cpu_cmd)
        
        return True
    except Exception as e:
        print(f"❌ Error sending without wake: {e}")
        return False

def test_no_updates(device, duration=10):
    """Test what happens with no updates (baseline)"""
    print(f"\n🔍 Test 1: No Updates for {duration} seconds")
    print("   Purpose: Observe display sleep behavior without any commands")
    print("   Expected: Display should turn off after 2-3 seconds")
    
    # Initialize display
    send_temperatures_with_wake(device, 50, 45)
    print("   ✅ Initial temperatures set (CPU: 50°C, GPU: 45°C)")
    
    input("   👀 Watch the display and press Enter when it turns off...")
    print("   ✅ Test complete")
    return True

def test_slow_updates(device, interval=5, duration=30):
    """Test slow updates (likely to cause flickering)"""
    print(f"\n🔍 Test 2: Slow Updates ({interval}s interval for {duration}s)")
    print("   Purpose: Test update pattern that should cause flickering")
    print("   Expected: Display flickers or turns off between updates")
    
    start_time = time.time()
    update_count = 0
    
    print("   👀 Watch for display flickering...")
    
    while time.time() - start_time < duration:
        cpu_temp = 50 + update_count % 10  # Vary temperature
        gpu_temp = 45 + update_count % 8
        
        send_temperatures_with_wake(device, cpu_temp, gpu_temp)
        update_count += 1
        print(f"   Update {update_count}: CPU {cpu_temp}°C, GPU {gpu_temp}°C")
        
        time.sleep(interval)
    
    print(f"   ✅ Slow update test complete ({update_count} updates)")
    return True

def test_fast_updates_with_wake(device, interval=1, duration=30):
    """Test fast updates with wake commands"""
    print(f"\n🔍 Test 3: Fast Updates with Wake ({interval}s interval for {duration}s)")
    print("   Purpose: Test anti-flicker pattern with wake commands")
    print("   Expected: Stable display, no flickering")
    
    start_time = time.time()
    update_count = 0
    
    print("   👀 Display should remain stable...")
    
    while time.time() - start_time < duration:
        cpu_temp = 55 + update_count % 15  # Vary temperature
        gpu_temp = 50 + update_count % 12
        
        send_temperatures_with_wake(device, cpu_temp, gpu_temp)
        update_count += 1
        
        if update_count % 10 == 0:
            print(f"   Update {update_count}: CPU {cpu_temp}°C, GPU {gpu_temp}°C")
        
        time.sleep(interval)
    
    print(f"   ✅ Fast update with wake test complete ({update_count} updates)")
    return True

def test_fast_updates_no_wake(device, interval=1, duration=30):
    """Test fast updates without wake commands"""
    print(f"\n🔍 Test 4: Fast Updates without Wake ({interval}s interval for {duration}s)")
    print("   Purpose: Test if fast updates alone prevent flickering")
    print("   Expected: May still flicker without wake commands")
    
    # Initial wake
    wake_cmd = [0x08, 0x01] + [0x00] * 62
    device.write(wake_cmd)
    time.sleep(0.5)
    
    start_time = time.time()
    update_count = 0
    
    print("   👀 Watch for display behavior without wake commands...")
    
    while time.time() - start_time < duration:
        cpu_temp = 60 + update_count % 10  # Vary temperature
        gpu_temp = 55 + update_count % 8
        
        send_temperatures_no_wake(device, cpu_temp, gpu_temp)
        update_count += 1
        
        if update_count % 10 == 0:
            print(f"   Update {update_count}: CPU {cpu_temp}°C, GPU {gpu_temp}°C")
        
        time.sleep(interval)
    
    print(f"   ✅ Fast update without wake test complete ({update_count} updates)")
    return True

def test_very_fast_updates(device, interval=0.5, duration=30):
    """Test very fast updates"""
    print(f"\n🔍 Test 5: Very Fast Updates ({interval}s interval for {duration}s)")
    print("   Purpose: Test optimal anti-flicker pattern")
    print("   Expected: Very stable display")
    
    start_time = time.time()
    update_count = 0
    
    print("   👀 Display should be very stable...")
    
    while time.time() - start_time < duration:
        cpu_temp = 40 + update_count % 20  # Vary temperature
        gpu_temp = 35 + update_count % 15
        
        send_temperatures_with_wake(device, cpu_temp, gpu_temp)
        update_count += 1
        
        if update_count % 20 == 0:
            print(f"   Update {update_count}: CPU {cpu_temp}°C, GPU {gpu_temp}°C")
        
        time.sleep(interval)
    
    print(f"   ✅ Very fast update test complete ({update_count} updates)")
    return True

def test_periodic_wake(device, update_interval=2, wake_interval=5, duration=60):
    """Test periodic wake commands with regular updates"""
    print(f"\n🔍 Test 6: Periodic Wake Pattern")
    print(f"   Update interval: {update_interval}s, Wake every: {wake_interval} updates")
    print(f"   Duration: {duration}s")
    print("   Purpose: Test optimized wake pattern for efficiency")
    print("   Expected: Stable display with less wake command overhead")
    
    start_time = time.time()
    update_count = 0
    
    print("   👀 Testing optimized wake pattern...")
    
    while time.time() - start_time < duration:
        cpu_temp = 45 + update_count % 25  # Vary temperature
        gpu_temp = 40 + update_count % 20
        
        # Send wake command every N updates
        if update_count % wake_interval == 0:
            wake_cmd = [0x08, 0x01] + [0x00] * 62
            device.write(wake_cmd)
            time.sleep(0.1)
            print(f"   💫 Wake command sent (update {update_count})")
        
        # Send temperatures
        send_temperatures_no_wake(device, cpu_temp, gpu_temp)
        update_count += 1
        
        if update_count % 10 == 0:
            print(f"   Update {update_count}: CPU {cpu_temp}°C, GPU {gpu_temp}°C")
        
        time.sleep(update_interval)
    
    print(f"   ✅ Periodic wake test complete ({update_count} updates)")
    return True

def interactive_test(device):
    """Interactive flicker testing"""
    print("\n🎮 Interactive Flicker Testing")
    print("Commands: interval <seconds>, wake <on/off>, test <duration>, quit")
    
    current_interval = 1.0
    wake_enabled = True
    
    print(f"Current settings: interval={current_interval}s, wake={wake_enabled}")
    
    # Start background update thread
    stop_updates = threading.Event()
    update_count = 0
    
    def update_loop():
        nonlocal update_count
        while not stop_updates.is_set():
            cpu_temp = 50 + (update_count % 20)
            gpu_temp = 45 + (update_count % 15)
            
            if wake_enabled:
                send_temperatures_with_wake(device, cpu_temp, gpu_temp)
            else:
                send_temperatures_no_wake(device, cpu_temp, gpu_temp)
            
            update_count += 1
            stop_updates.wait(current_interval)
    
    update_thread = threading.Thread(target=update_loop, daemon=True)
    update_thread.start()
    
    try:
        while True:
            cmd = input(f"\n[{update_count} updates] > ").strip().lower()
            
            if cmd == "quit" or cmd == "exit":
                break
            elif cmd.startswith("interval "):
                try:
                    current_interval = float(cmd.split()[1])
                    print(f"✅ Update interval set to {current_interval}s")
                except (IndexError, ValueError):
                    print("❌ Usage: interval <seconds>")
            elif cmd.startswith("wake "):
                wake_setting = cmd.split()[1].lower()
                if wake_setting in ["on", "true", "1"]:
                    wake_enabled = True
                    print("✅ Wake commands enabled")
                elif wake_setting in ["off", "false", "0"]:
                    wake_enabled = False
                    print("✅ Wake commands disabled")
                else:
                    print("❌ Usage: wake <on/off>")
            elif cmd.startswith("test "):
                try:
                    test_duration = float(cmd.split()[1])
                    print(f"✅ Running test for {test_duration} seconds...")
                    time.sleep(test_duration)
                    print("✅ Test complete")
                except (IndexError, ValueError):
                    print("❌ Usage: test <duration>")
            elif cmd == "status":
                print(f"Status: {update_count} updates, interval={current_interval}s, wake={wake_enabled}")
            elif cmd == "help":
                print("Commands:")
                print("  interval <seconds> - Set update interval")
                print("  wake <on/off> - Enable/disable wake commands")
                print("  test <duration> - Run test for specified duration")
                print("  status - Show current settings")
                print("  help - Show this help")
                print("  quit/exit - Exit interactive mode")
            else:
                print("❌ Unknown command. Type 'help' for available commands.")
    
    except KeyboardInterrupt:
        print("\n🛑 Interactive mode interrupted")
    finally:
        stop_updates.set()
        update_thread.join(timeout=1)
        print("✅ Interactive mode stopped")

def main():
    """Main function"""
    print_header()
    
    device = connect_device()
    if not device:
        sys.exit(1)
    
    print("\n🔧 Available Tests:")
    print("1. No updates (baseline)")
    print("2. Slow updates (likely to flicker)")
    print("3. Fast updates with wake")
    print("4. Fast updates without wake")
    print("5. Very fast updates")
    print("6. Periodic wake pattern")
    print("7. Interactive mode")
    print("8. Run all tests")
    
    try:
        choice = input("\nSelect test (1-8): ").strip()
        
        if choice == "1":
            test_no_updates(device)
        elif choice == "2":
            test_slow_updates(device)
        elif choice == "3":
            test_fast_updates_with_wake(device)
        elif choice == "4":
            test_fast_updates_no_wake(device)
        elif choice == "5":
            test_very_fast_updates(device)
        elif choice == "6":
            test_periodic_wake(device)
        elif choice == "7":
            interactive_test(device)
        elif choice == "8":
            print("\n🚀 Running all tests...")
            test_no_updates(device)
            test_slow_updates(device)
            test_fast_updates_with_wake(device)
            test_fast_updates_no_wake(device)
            test_very_fast_updates(device)
            test_periodic_wake(device)
            print("\n✅ All tests completed!")
        else:
            print("❌ Invalid choice")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n🛑 Testing interrupted by user")
    finally:
        device.close()
        print("✅ Device disconnected")

if __name__ == "__main__":
    main() 