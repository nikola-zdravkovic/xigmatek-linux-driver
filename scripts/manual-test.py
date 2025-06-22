#!/usr/bin/env python3
"""
XIGMATEK Manual Testing Script
Interactive testing tool for manual device testing and protocol exploration
"""

import hid
import time
import math
import sys
import subprocess

def print_header():
    """Print script header"""
    print("🔧 XIGMATEK Manual Testing Tool")
    print("=" * 40)
    print("Interactive testing for device communication and protocol exploration")
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

def send_wake_command(device):
    """Send wake command to device"""
    try:
        wake_cmd = [0x08, 0x01] + [0x00] * 62
        device.write(wake_cmd)
        print("✅ Wake command sent")
        return True
    except Exception as e:
        print(f"❌ Wake command failed: {e}")
        return False

def send_gpu_temperature(device, temp):
    """Send GPU temperature to device"""
    try:
        temp = max(0, min(100, int(temp)))
        gpu_cmd = [0x02, 0x20, temp] + [0x00] * 61
        device.write(gpu_cmd)
        print(f"✅ GPU temperature set to {temp}°C")
        return True
    except Exception as e:
        print(f"❌ GPU command failed: {e}")
        return False

def send_cpu_temperature(device, temp):
    """Send CPU temperature to device"""
    try:
        temp = max(16, min(90, int(temp)))
        cmd_byte = (temp - 16) * 2
        cmd_byte = max(1, min(255, cmd_byte))
        cpu_cmd = [0x02, cmd_byte, 0x00] + [0x00] * 61
        device.write(cpu_cmd)
        print(f"✅ CPU temperature set to {temp}°C (command byte: {cmd_byte})")
        return True
    except Exception as e:
        print(f"❌ CPU command failed: {e}")
        return False

def send_custom_command(device, cmd_array):
    """Send custom command to device"""
    try:
        # Ensure command is 64 bytes
        while len(cmd_array) < 64:
            cmd_array.append(0x00)
        cmd_array = cmd_array[:64]
        
        device.write(cmd_array)
        print(f"✅ Custom command sent: {cmd_array[:8]}...")
        return True
    except Exception as e:
        print(f"❌ Custom command failed: {e}")
        return False

def get_system_temperatures():
    """Get current system temperatures"""
    print("\n🌡️  Current System Temperatures:")
    
    # CPU Temperature
    try:
        result = subprocess.run(['sensors'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            cpu_temp = None
            gpu_temp = None
            
            for line in result.stdout.split('\n'):
                # CPU patterns
                for pattern in ['Tccd1:', 'Tctl:', 'Core 0:', 'Package id 0:', 'Tdie:']:
                    if pattern in line and '+' in line:
                        temp_str = line.split('+')[1].split('°')[0].strip()
                        cpu_temp = float(temp_str)
                        print(f"   CPU: {cpu_temp}°C ({pattern})")
                        break
                
                # GPU patterns (AMD)
                if ('edge:' in line or 'junction:' in line) and '+' in line:
                    temp_str = line.split('+')[1].split('°')[0].strip()
                    gpu_temp = float(temp_str)
                    print(f"   GPU: {gpu_temp}°C (AMD)")
            
            # NVIDIA GPU
            try:
                nvidia_result = subprocess.run(
                    ['nvidia-smi', '--query-gpu=temperature.gpu', '--format=csv,noheader,nounits'],
                    capture_output=True, text=True, timeout=5
                )
                if nvidia_result.returncode == 0:
                    gpu_temp = float(nvidia_result.stdout.strip())
                    print(f"   GPU: {gpu_temp}°C (NVIDIA)")
            except:
                pass
            
            return cpu_temp, gpu_temp
        else:
            print("   ❌ Could not read sensors")
            return None, None
    except Exception as e:
        print(f"   ❌ Sensor error: {e}")
        return None, None

def interactive_temperature_test(device):
    """Interactive temperature testing"""
    print("\n🎮 Interactive Temperature Testing")
    print("Commands: cpu <temp>, gpu <temp>, both <cpu> <gpu>, system, quit")
    
    while True:
        try:
            cmd = input("\n> ").strip().lower()
            
            if cmd == "quit" or cmd == "exit":
                break
            elif cmd == "system":
                cpu_temp, gpu_temp = get_system_temperatures()
                if cpu_temp is not None:
                    send_cpu_temperature(device, int(cpu_temp))
                if gpu_temp is not None:
                    send_gpu_temperature(device, int(gpu_temp))
            elif cmd.startswith("cpu "):
                try:
                    temp = int(cmd.split()[1])
                    send_wake_command(device)
                    time.sleep(0.1)
                    send_cpu_temperature(device, temp)
                except (IndexError, ValueError):
                    print("❌ Usage: cpu <temperature>")
            elif cmd.startswith("gpu "):
                try:
                    temp = int(cmd.split()[1])
                    send_wake_command(device)
                    time.sleep(0.1)
                    send_gpu_temperature(device, temp)
                except (IndexError, ValueError):
                    print("❌ Usage: gpu <temperature>")
            elif cmd.startswith("both "):
                try:
                    parts = cmd.split()
                    cpu_temp = int(parts[1])
                    gpu_temp = int(parts[2])
                    send_wake_command(device)
                    time.sleep(0.1)
                    send_gpu_temperature(device, gpu_temp)
                    time.sleep(0.1)
                    send_cpu_temperature(device, cpu_temp)
                except (IndexError, ValueError):
                    print("❌ Usage: both <cpu_temp> <gpu_temp>")
            elif cmd == "wake":
                send_wake_command(device)
            elif cmd == "help":
                print("Available commands:")
                print("  cpu <temp>      - Set CPU temperature (16-90°C)")
                print("  gpu <temp>      - Set GPU temperature (0-100°C)")
                print("  both <cpu> <gpu> - Set both temperatures")
                print("  system          - Use current system temperatures")
                print("  wake            - Send wake command")
                print("  help            - Show this help")
                print("  quit/exit       - Exit interactive mode")
            else:
                print("❌ Unknown command. Type 'help' for available commands.")
                
        except KeyboardInterrupt:
            print("\n👋 Exiting interactive mode...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

def protocol_exploration(device):
    """Protocol exploration mode for testing new commands"""
    print("\n🔬 Protocol Exploration Mode")
    print("Send custom commands to explore device protocol")
    print("Format: hex bytes separated by spaces (e.g., '08 01 00')")
    print("Commands: send <hex>, preset <name>, quit")
    
    presets = {
        "wake": [0x08, 0x01],
        "gpu50": [0x02, 0x20, 50],
        "cpu50": [0x02, 68, 0x00],  # (50-16)*2 = 68
        "test1": [0x01, 0x00, 0x00],
        "test2": [0x03, 0x00, 0x00],
        "test3": [0x04, 0x00, 0x00],
    }
    
    print(f"\nAvailable presets: {', '.join(presets.keys())}")
    
    while True:
        try:
            cmd = input("\n> ").strip().lower()
            
            if cmd == "quit" or cmd == "exit":
                break
            elif cmd.startswith("send "):
                try:
                    hex_str = cmd[5:]
                    hex_bytes = [int(x, 16) for x in hex_str.split()]
                    send_custom_command(device, hex_bytes)
                    print("💡 Check display for any changes")
                except ValueError:
                    print("❌ Invalid hex format. Use: send 08 01 00")
            elif cmd.startswith("preset "):
                preset_name = cmd.split()[1]
                if preset_name in presets:
                    send_custom_command(device, presets[preset_name].copy())
                    print(f"✅ Sent preset '{preset_name}'")
                else:
                    print(f"❌ Unknown preset. Available: {', '.join(presets.keys())}")
            elif cmd == "help":
                print("Protocol exploration commands:")
                print("  send <hex>      - Send custom command (e.g., 'send 08 01 00')")
                print("  preset <name>   - Send preset command")
                print(f"  Available presets: {', '.join(presets.keys())}")
                print("  help            - Show this help")
                print("  quit/exit       - Exit exploration mode")
            else:
                print("❌ Unknown command. Type 'help' for available commands.")
                
        except KeyboardInterrupt:
            print("\n👋 Exiting exploration mode...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

def stress_test(device):
    """Stress test with rapid temperature changes"""
    print("\n💪 Stress Test Mode")
    print("Testing rapid temperature changes and stability")
    
    try:
        duration = int(input("Test duration in seconds (default 60): ") or "60")
        interval = float(input("Update interval in seconds (default 0.5): ") or "0.5")
    except ValueError:
        duration = 60
        interval = 0.5
    
    print(f"\nRunning stress test for {duration} seconds with {interval}s intervals...")
    print("Press Ctrl+C to stop early")
    
    start_time = time.time()
    update_count = 0
    errors = 0
    
    try:
        while time.time() - start_time < duration:
            try:
                # Generate varying temperatures
                elapsed = time.time() - start_time
                cpu_temp = int(30 + 20 * abs(math.sin(elapsed * 0.1)))  # 30-50°C sine wave
                gpu_temp = int(35 + 15 * abs(math.cos(elapsed * 0.15)))  # 35-50°C cosine wave
                
                # Send wake command
                send_wake_command(device)
                time.sleep(0.05)
                
                # Send temperatures
                send_gpu_temperature(device, gpu_temp)
                time.sleep(0.05)
                send_cpu_temperature(device, cpu_temp)
                
                update_count += 1
                
                if update_count % 10 == 0:
                    print(f"Updates: {update_count}, CPU: {cpu_temp}°C, GPU: {gpu_temp}°C, Errors: {errors}")
                
                time.sleep(interval - 0.1)  # Account for command delays
                
            except Exception as e:
                errors += 1
                print(f"❌ Error #{errors}: {e}")
                time.sleep(interval)
    
    except KeyboardInterrupt:
        print("\n⏹️  Stress test stopped by user")
    
    elapsed = time.time() - start_time
    print(f"\n📊 Stress Test Results:")
    print(f"   Duration: {elapsed:.1f} seconds")
    print(f"   Updates: {update_count}")
    print(f"   Errors: {errors}")
    print(f"   Success rate: {((update_count - errors) / max(update_count, 1) * 100):.1f}%")
    print(f"   Updates/second: {update_count / elapsed:.1f}")

def main_menu(device):
    """Main menu for manual testing"""
    while True:
        print("\n🎯 XIGMATEK Manual Testing Menu")
        print("1. Interactive Temperature Testing")
        print("2. Protocol Exploration")
        print("3. Stress Test")
        print("4. System Temperature Check")
        print("5. Wake Command Test")
        print("6. Exit")
        
        try:
            choice = input("\nSelect option (1-6): ").strip()
            
            if choice == "1":
                interactive_temperature_test(device)
            elif choice == "2":
                protocol_exploration(device)
            elif choice == "3":
                stress_test(device)
            elif choice == "4":
                get_system_temperatures()
            elif choice == "5":
                send_wake_command(device)
                print("💡 Check if display turned on")
            elif choice == "6":
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice. Please select 1-6.")
                
        except KeyboardInterrupt:
            print("\n👋 Exiting...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

def main():
    """Main function"""
    print_header()
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--quick-test":
            device = connect_device()
            if device:
                send_wake_command(device)
                time.sleep(0.5)
                send_gpu_temperature(device, 45)
                time.sleep(0.1)
                send_cpu_temperature(device, 55)
                print("💡 Quick test complete. Check display for CPU: 55°C, GPU: 45°C")
                device.close()
            return
        elif sys.argv[1] == "--system-temps":
            device = connect_device()
            if device:
                cpu_temp, gpu_temp = get_system_temperatures()
                if cpu_temp or gpu_temp:
                    send_wake_command(device)
                    time.sleep(0.1)
                    if gpu_temp:
                        send_gpu_temperature(device, int(gpu_temp))
                        time.sleep(0.1)
                    if cpu_temp:
                        send_cpu_temperature(device, int(cpu_temp))
                    print("💡 System temperatures sent to display")
                device.close()
            return
    
    # Connect to device
    device = connect_device()
    if not device:
        print("\n❌ Cannot proceed without device connection")
        print("💡 Make sure:")
        print("   - Device is connected via USB")
        print("   - You have proper permissions (try sudo)")
        print("   - udev rules are configured")
        sys.exit(1)
    
    try:
        # Initial wake command
        send_wake_command(device)
        
        # Show main menu
        main_menu(device)
        
    finally:
        # Clean up
        try:
            device.close()
            print("✅ Device connection closed")
        except:
            pass

if __name__ == "__main__":
    main()