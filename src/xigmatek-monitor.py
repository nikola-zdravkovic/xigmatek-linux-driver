#!/usr/bin/env python3
"""
XIGMATEK Temperature Monitor Service
Universal Linux version with auto-detection and recovery
"""

import hid
import time
import threading
import subprocess
import sys
import signal
import logging
import json
import os
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/xigmatek-monitor.log')
    ]
)
logger = logging.getLogger(__name__)

class XigmatekService:
    def __init__(self, config_path='/etc/xigmatek-monitor.conf'):
        self.device = None
        self.vendor_id = 0x0145
        self.product_id = 0x1005
        self.stop_event = threading.Event()
        self.monitor_thread = None
        
        # Load configuration
        self.load_config(config_path)
        
    def load_config(self, config_path):
        """Load configuration from file"""
        default_config = {
            "update_interval": 2.0,  # Faster updates to prevent sleep
            "cpu_offset": 0,
            "gpu_offset": 0,
            "min_temp": 20,
            "max_temp": 90,
            "fallback_cpu": 35,
            "fallback_gpu": 40,
            "enable_logging": True,
            "wake_every_update": True,  # Send wake command with every update
            "wake_interval": 10  # Send wake command every N updates
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                # Merge with defaults
                self.config = {**default_config, **config}
            else:
                self.config = default_config
                logger.info(f"Using default configuration (no config file at {config_path})")
        except Exception as e:
            logger.warning(f"Error loading config: {e}, using defaults")
            self.config = default_config
    
    def find_device(self):
        """Find XIGMATEK device among all HID devices"""
        try:
            devices = hid.enumerate()
            for device_info in devices:
                if (device_info['vendor_id'] == self.vendor_id and 
                    device_info['product_id'] == self.product_id):
                    logger.info(f"Found XIGMATEK device: {device_info['path']}")
                    return True
            logger.warning("XIGMATEK device not found in HID enumeration")
            return False
        except Exception as e:
            logger.error(f"Error enumerating devices: {e}")
            return False
    
    def connect_device(self):
        """Connect to device with retry logic"""
        max_attempts = 10
        attempt = 0
        
        while attempt < max_attempts and not self.stop_event.is_set():
            try:
                # First check if device exists
                if not self.find_device():
                    logger.warning(f"Attempt {attempt + 1}: Device not found, retrying in 5s...")
                    self.stop_event.wait(5)
                    attempt += 1
                    continue
                
                # Try to connect
                self.device = hid.device()
                self.device.open(self.vendor_id, self.product_id)
                logger.info("✅ Connected to XIGMATEK device!")
                return True
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}: Connection failed: {e}")
                self.stop_event.wait(5)
                attempt += 1
        
        logger.error("Failed to connect after all attempts")
        return False
    
    def initialize_display(self):
        """Initialize the display"""
        try:
            wake_cmd = [0x08, 0x01] + [0x00] * 62
            self.device.write(wake_cmd)
            time.sleep(0.5)
            logger.info("Display initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize display: {e}")
            return False
    
    def send_command(self, cmd_array):
        """Send command to device"""
        try:
            while len(cmd_array) < 64:
                cmd_array.append(0x00)
            cmd_array = cmd_array[:64]
            self.device.write(cmd_array)
            return True
        except Exception as e:
            logger.error(f"Failed to send command: {e}")
            return False
    
    def get_cpu_temperature(self):
        """Get CPU temperature with multiple methods"""
        try:
            result = subprocess.run(['sensors'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    # Try different CPU sensor patterns
                    for pattern in ['Tccd1:', 'Tctl:', 'Core 0:', 'Package id 0:', 'Tdie:', 'CPU:']:
                        if pattern in line and '+' in line:
                            temp_str = line.split('+')[1].split('°')[0].strip()
                            temp = int(float(temp_str)) + self.config['cpu_offset']
                            return max(self.config['min_temp'], min(self.config['max_temp'], temp))
        except Exception as e:
            logger.debug(f"CPU sensor error: {e}")
        
        return self.config['fallback_cpu']
    
    def get_gpu_temperature(self):
        """Get GPU temperature with multiple methods"""
        # Try NVIDIA first
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=temperature.gpu', '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                temp = int(result.stdout.strip()) + self.config['gpu_offset']
                return max(self.config['min_temp'], min(self.config['max_temp'], temp))
        except:
            pass
        
        # Try AMD GPU via sensors
        try:
            result = subprocess.run(['sensors'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if ('edge:' in line or 'junction:' in line or 'GPU:' in line) and '+' in line:
                        temp_str = line.split('+')[1].split('°')[0].strip()
                        temp = int(float(temp_str)) + self.config['gpu_offset']
                        return max(self.config['min_temp'], min(self.config['max_temp'], temp))
        except:
            pass
        
        # Try intel GPU
        try:
            result = subprocess.run(['sensors'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'intel' in line.lower() and 'temp' in line.lower() and '+' in line:
                        temp_str = line.split('+')[1].split('°')[0].strip()
                        temp = int(float(temp_str)) + self.config['gpu_offset']
                        return max(self.config['min_temp'], min(self.config['max_temp'], temp))
        except:
            pass
        
        return self.config['fallback_gpu']
    
    def cpu_temp_to_command(self, target_temp):
        """Convert CPU temperature to command byte"""
        command_byte = (target_temp - 16) * 2
        return max(1, min(255, command_byte))
    
    def send_wake_command(self):
        """Send wake command to keep display active"""
        try:
            wake_cmd = [0x08, 0x01] + [0x00] * 62
            return self.send_command(wake_cmd)
        except Exception as e:
            logger.error(f"Failed to send wake command: {e}")
            return False
    
    def send_temperatures_with_wake(self, cpu_temp, gpu_temp):
        """Send both temperatures with wake command"""
        success = True
        
        try:
            # Send wake command first to ensure display is active
            if not self.send_wake_command():
                logger.warning("Wake command failed")
            
            time.sleep(0.1)
            
            # Send GPU temperature
            gpu_cmd = [0x02, 0x20, gpu_temp] + [0x00] * 61
            if not self.send_command(gpu_cmd):
                success = False
            
            time.sleep(0.1)
            
            # Send CPU temperature
            cpu_cmd_byte = self.cpu_temp_to_command(cpu_temp)
            cpu_cmd = [0x02, cpu_cmd_byte, 0] + [0x00] * 61
            if not self.send_command(cpu_cmd):
                success = False
            
        except Exception as e:
            logger.error(f"Error sending temperatures with wake: {e}")
            success = False
        
        return success
    
    def send_temperatures_fast(self, cpu_temp, gpu_temp):
        """Send both temperatures without wake command (faster)"""
        success = True
        
        try:
            # Send GPU temperature
            gpu_cmd = [0x02, 0x20, gpu_temp] + [0x00] * 61
            if not self.send_command(gpu_cmd):
                success = False
            
            time.sleep(0.05)  # Shorter delay
            
            # Send CPU temperature
            cpu_cmd_byte = self.cpu_temp_to_command(cpu_temp)
            cpu_cmd = [0x02, cpu_cmd_byte, 0] + [0x00] * 61
            if not self.send_command(cpu_cmd):
                success = False
            
        except Exception as e:
            logger.error(f"Error sending temperatures: {e}")
            success = False
        
        return success
    
    def send_temperatures(self, cpu_temp, gpu_temp):
        """Send both temperatures (legacy method)"""
        return self.send_temperatures_with_wake(cpu_temp, gpu_temp)
    
    def monitor_loop(self):
        """Main monitoring loop"""
        logger.info("Starting temperature monitoring...")
        consecutive_errors = 0
        update_count = 0
        last_wake = 0
        
        while not self.stop_event.is_set():
            try:
                # Get temperatures
                cpu_temp = self.get_cpu_temperature()
                gpu_temp = self.get_gpu_temperature()
                
                # Determine if we need to send wake command
                need_wake = (
                    self.config.get('wake_every_update', True) or 
                    (update_count - last_wake) >= self.config.get('wake_interval', 10)
                )
                
                # Send to display
                if need_wake:
                    # Send with wake command
                    if self.send_temperatures_with_wake(cpu_temp, gpu_temp):
                        consecutive_errors = 0
                        update_count += 1
                        last_wake = update_count
                    else:
                        consecutive_errors += 1
                        logger.warning(f"Send failed (error #{consecutive_errors})")
                else:
                    # Send without wake command
                    if self.send_temperatures_fast(cpu_temp, gpu_temp):
                        consecutive_errors = 0
                        update_count += 1
                    else:
                        consecutive_errors += 1
                        logger.warning(f"Send failed (error #{consecutive_errors})")
                
                if update_count % 20 == 0:  # Log every 20 updates
                    logger.info(f"Update #{update_count}: CPU={cpu_temp}°C, GPU={gpu_temp}°C")
                
                # If too many errors, try to reconnect
                if consecutive_errors >= 5:
                    logger.error("Too many errors, attempting reconnect...")
                    try:
                        self.device.close()
                    except:
                        pass
                    
                    if self.connect_device() and self.initialize_display():
                        consecutive_errors = 0
                        logger.info("Reconnected successfully")
                    else:
                        logger.error("Reconnection failed")
                        self.stop_event.wait(10)
                
                # Wait for next update
                self.stop_event.wait(self.config['update_interval'])
                
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                consecutive_errors += 1
                self.stop_event.wait(2)
    
    def start_service(self):
        """Start the service"""
        logger.info("🚀 Starting XIGMATEK Temperature Service")
        
        # Connect to device
        if not self.connect_device():
            logger.error("Cannot connect to device")
            return False
        
        # Initialize display
        if not self.initialize_display():
            logger.error("Cannot initialize display")
            return False
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self.monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info("✅ Service started successfully!")
        return True
    
    def stop_service(self):
        """Stop the service"""
        logger.info("Stopping service...")
        self.stop_event.set()
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        if self.device:
            try:
                self.device.close()
            except:
                pass
        
        logger.info("Service stopped")
    
    def run_forever(self):
        """Run as daemon"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}")
            self.stop_service()
            sys.exit(0)
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        if not self.start_service():
            sys.exit(1)
        
        try:
            # Keep running
            while not self.stop_event.is_set():
                self.stop_event.wait(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt")
        finally:
            self.stop_service()
    
    def test_mode(self):
        """Run test for 30 seconds"""
        logger.info("Running in test mode for 30 seconds...")
        if self.start_service():
            time.sleep(30)
            self.stop_service()
            logger.info("Test completed successfully")
            return True
        else:
            logger.error("Test failed")
            return False

def main():
    service = XigmatekService()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        if service.test_mode():
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        service.run_forever()

if __name__ == "__main__":
    main()