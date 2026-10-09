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
import glob
import random
import datetime
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

# Product IDs seen under XIGMATEK's USB vendor ID 0x0145 and the protocol each one speaks.
#   "lk360": LK 360 Digital Arctic - separate wake / CPU / GPU commands (see docs/PROTOCOL.md)
#   "hwcx":  AK4 Digital ("HWCX USB Display") - challenge handshake, then one combined
#            64-byte status frame (see docs/PROTOCOL.md, "HWCX protocol")
SUPPORTED_DEVICES = {
    0x1005: ("lk360", "XIGMATEK LK 360 Digital Arctic"),
    0x1002: ("hwcx", "XIGMATEK AK4 Digital (HWCX USB Display)"),
}

# HWCX status-frame pages: bit (n-1) of the page byte shows page n.
HWCX_PAGE_CPU_C, HWCX_PAGE_CPU_F, HWCX_PAGE_CPU_LOAD, HWCX_PAGE_RAM, HWCX_PAGE_FAN = 1, 2, 3, 4, 5
HWCX_DISPLAY_OFF = 0x80


class XigmatekService:
    def __init__(self, config_path='/etc/xigmatek-monitor.conf'):
        self.device = None
        self.vendor_id = 0x0145
        self.product_id = 0x1005
        self.protocol = "lk360"
        self._cpu_stat = None
        self._temps = (None, None)
        self._temps_at = 0.0
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
            "wake_interval": 10,  # Send wake command every N updates
            "product_id": None,  # force a product ID (e.g. 4098 for 0x1002); default: auto-detect
            "hwcx_update_interval": 0.5,  # HWCX screens expect a frame about every 500 ms
            "hwcx_pages": [1, 3, 4],  # pages to rotate: 1 CPU C, 2 CPU F, 3 CPU load, 4 RAM, 5 fan
            "hwcx_fan": "auto"  # hwmon fan input to show (e.g. "fan2"), or "auto" = first spinning fan
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
            forced = self.config.get('product_id')
            for device_info in devices:
                pid = device_info['product_id']
                if device_info['vendor_id'] != self.vendor_id:
                    continue
                if (forced and pid == forced) or (not forced and pid in SUPPORTED_DEVICES):
                    self.product_id = pid
                    self.protocol, name = SUPPORTED_DEVICES.get(pid, ("lk360", "unknown model"))
                    logger.info(f"Found {name} (0x{self.vendor_id:04x}:0x{pid:04x}, "
                                f"{self.protocol} protocol): {device_info['path']}")
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
        if self.protocol == "hwcx":
            return self.hwcx_handshake()
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
    
    # ------------------------------------------------------------------ HWCX (AK4 Digital)
    @staticmethod
    def hwcx_checksums(pkt):
        """Byte 63 = XOR of (byte * index), byte 64 = sum of (byte * index), over the data bytes."""
        x = 0
        for i in range(60):
            x ^= (pkt[1 + i] * i) & 0xFF
        pkt[63] = x
        s = 0
        for i in range(63):
            s = (s + pkt[1 + i] * i) & 0xFF
        pkt[64] = s

    def hwcx_write(self, pkt):
        """Write one 65-byte report (report id 0x00 + 64 data bytes)."""
        return self.device.write(list(pkt)) > 0

    def hwcx_handshake(self, attempts=3):
        """The screen ignores status frames until this challenge (command 0x01) is answered.

        Packet (65 bytes, [0] = report id): random bytes, [1]=0x01, [2..4]=0, [5..6]=random word W,
        [11..12] = W ^ (((b7+b9)<<8) + b10 + b8), [63..64] = checksums.
        The screen replies with [5..6] = ((b9<<8)+b10) ^ (b6+b8+((b5+b7)<<8)).
        """
        for attempt in range(1, attempts + 1):
            try:
                pkt = bytearray(random.getrandbits(8) for _ in range(65))
                pkt[0] = 0x00
                pkt[1] = 0x01
                pkt[2] = pkt[3] = pkt[4] = 0x00
                w = random.getrandbits(16)
                pkt[5], pkt[6] = w >> 8, w & 0xFF
                a = (((pkt[7] + pkt[9]) << 8) + pkt[10] + pkt[8]) & 0xFFFF
                x = (w ^ a) & 0xFFFF
                pkt[11], pkt[12] = x >> 8, x & 0xFF
                self.hwcx_checksums(pkt)
                expected = (((pkt[9] << 8) + pkt[10]) ^ ((pkt[6] + pkt[8] + ((pkt[5] + pkt[7]) << 8)) & 0xFFFF)) & 0xFFFF
                self.hwcx_write(pkt)
                reply = self.device.read(65, 2000)
                if reply:
                    if len(reply) == 64:          # hidraw returns the data without the report id
                        reply = [0] + list(reply)
                    if ((reply[5] << 8) | reply[6]) == expected:
                        logger.info("HWCX handshake OK")
                        return True
                    logger.warning(f"HWCX handshake: unexpected reply (attempt {attempt})")
                else:
                    logger.warning(f"HWCX handshake: no reply (attempt {attempt})")
            except Exception as e:
                logger.warning(f"HWCX handshake error (attempt {attempt}): {e}")
            time.sleep(0.5)
        logger.error("HWCX handshake failed - the screen will ignore updates")
        return False

    def hwcx_page_mask(self):
        mask = 0
        for page in self.config.get('hwcx_pages', [1, 3, 4]):
            if 1 <= int(page) <= 7:
                mask |= 1 << (int(page) - 1)
        return mask & 0x7F          # bit 7 (0x80) switches the display off

    def hwcx_cpu_load(self):
        with open('/proc/stat') as f:
            fields = [int(v) for v in f.readline().split()[1:]]
        idle, total = fields[3] + fields[4], sum(fields)
        prev, self._cpu_stat = self._cpu_stat, (idle, total)
        if not prev or total == prev[1]:
            return 0
        return max(0, min(100, round(100 * ((total - prev[1]) - (idle - prev[0])) / (total - prev[1]))))

    @staticmethod
    def hwcx_cpu_mhz():
        vals = []
        for p in glob.glob('/sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq'):
            try:
                vals.append(int(open(p).read()))
            except (OSError, ValueError):
                pass
        return max(vals) // 1000 if vals else 0

    @staticmethod
    def hwcx_ram_percent():
        mem = {}
        with open('/proc/meminfo') as f:
            for line in f:
                key, val = line.split(':', 1)
                mem[key] = int(val.split()[0])
        return round(100 * (mem['MemTotal'] - mem['MemAvailable']) / mem['MemTotal'])

    def hwcx_fan_rpm(self):
        wanted = self.config.get('hwcx_fan', 'auto')
        for hw in sorted(glob.glob('/sys/class/hwmon/hwmon*')):
            inputs = sorted(glob.glob(f'{hw}/fan*_input'))
            for path in inputs:
                if wanted != 'auto' and os.path.basename(path) != f'{wanted}_input':
                    continue
                try:
                    rpm = int(open(path).read())
                except (OSError, ValueError):
                    continue
                if rpm or wanted != 'auto':
                    return rpm
        return 0

    def hwcx_temperatures(self):
        """CPU/GPU temperatures, refreshed every 2 s (sensors / nvidia-smi are slow)."""
        if time.time() - self._temps_at > 2:
            self._temps = (self.get_cpu_temperature(), self.get_gpu_temperature())
            self._temps_at = time.time()
        return self._temps

    def hwcx_frame(self):
        """One status frame (command 0x02). Offsets are data offsets ([0] of the data = 0x02)."""
        cpu_t, gpu_t = self.hwcx_temperatures()
        now = datetime.datetime.now()
        mhz, fan = self.hwcx_cpu_mhz(), self.hwcx_fan_rpm()
        d = bytearray(64)
        d[0] = 0x02
        d[1] = max(0, min(255, cpu_t))
        d[2] = max(0, min(255, gpu_t))
        d[3], d[4], d[5], d[6] = now.hour, now.minute, now.second, now.microsecond // 10000
        d[7], d[8], d[9], d[10] = now.year // 100, now.year % 100, now.month, now.day
        d[11] = (now.weekday() + 1) % 7          # 0 = Sunday
        d[12] = self.hwcx_cpu_load()
        d[13], d[14] = (mhz >> 8) & 0xFF, mhz & 0xFF
        d[19] = self.hwcx_ram_percent()
        d[24], d[25] = (fan >> 8) & 0xFF, fan & 0xFF
        d[48] = self.hwcx_page_mask()
        return bytes([0x00]) + bytes(d)

    def hwcx_monitor_loop(self):
        logger.info(f"Starting HWCX status updates (pages mask 0x{self.hwcx_page_mask():02x})...")
        interval = float(self.config.get('hwcx_update_interval', 0.5))
        errors, count = 0, 0
        while not self.stop_event.is_set():
            try:
                if self.hwcx_write(self.hwcx_frame()):
                    errors = 0
                    count += 1
                    if count % 120 == 0:
                        cpu_t, gpu_t = self._temps
                        logger.info(f"Update #{count}: CPU={cpu_t}°C, GPU={gpu_t}°C")
                else:
                    errors += 1
            except Exception as e:
                errors += 1
                logger.warning(f"HWCX write failed ({e})")
            if errors >= 5:
                logger.error("Too many errors, reconnecting...")
                try:
                    self.device.close()
                except Exception:
                    pass
                if self.connect_device() and self.initialize_display():
                    errors = 0
                else:
                    self.stop_event.wait(10)
            self.stop_event.wait(interval)

    def monitor_loop(self):
        """Main monitoring loop"""
        if self.protocol == "hwcx":
            return self.hwcx_monitor_loop()
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