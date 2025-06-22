#!/bin/bash
# Universal XIGMATEK Temperature Monitor Setup Script
# Supports: Arch Linux, Ubuntu/Debian, Fedora/RHEL, openSUSE

set -e  # Exit on any error

echo "🚀 XIGMATEK Temperature Monitor Setup (Universal)"
echo "================================================="

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "❌ Don't run this script as root!"
   echo "Run as your regular user, we'll use sudo when needed"
   exit 1
fi

# Detect Linux distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        VERSION=$VERSION_ID
    elif type lsb_release >/dev/null 2>&1; then
        DISTRO=$(lsb_release -si | tr '[:upper:]' '[:lower:]')
    elif [ -f /etc/redhat-release ]; then
        DISTRO="rhel"
    else
        DISTRO="unknown"
    fi
    
    echo "🐧 Detected OS: $DISTRO"
}

# Install packages based on distribution
install_packages() {
    echo "📦 Installing system packages..."
    
    case $DISTRO in
        "arch"|"manjaro")
            echo "Using pacman (Arch Linux)..."
            sudo pacman -Sy --needed --noconfirm python python-pip lm_sensors python-hidapi
            ;;
        "ubuntu"|"debian"|"linuxmint"|"pop")
            echo "Using apt (Debian/Ubuntu)..."
            sudo apt update
            sudo apt install -y lm-sensors python3 python3-pip python3-hid udev
            ;;
        "fedora"|"rhel"|"centos"|"rocky"|"almalinux")
            echo "Using dnf/yum (Fedora/RHEL)..."
            if command -v dnf &> /dev/null; then
                sudo dnf install -y lm_sensors python3 python3-pip python3-hidapi
            else
                sudo yum install -y lm_sensors python3 python3-pip
                install_hidapi_pip=true
            fi
            ;;
        "opensuse"|"sles")
            echo "Using zypper (openSUSE)..."
            sudo zypper install -y sensors python3 python3-pip
            install_hidapi_pip=true
            ;;
        *)
            echo "⚠️  Unknown distribution: $DISTRO"
            echo "Attempting generic installation..."
            install_hidapi_pip=true
            ;;
    esac
}

# Install hidapi via pip if not available in system packages
install_hidapi_fallback() {
    if [ "$install_hidapi_pip" = true ] || ! python3 -c "import hid" 2>/dev/null; then
        echo "🐍 Installing hidapi via pip..."
        
        # Check if we're in an externally managed environment (like Arch with PEP 668)
        if python3 -m pip install --help 2>&1 | grep -q "externally-managed-environment"; then
            echo "📦 Detected externally managed Python environment"
            echo "Creating virtual environment..."
            
            # Create system-wide venv
            sudo mkdir -p /opt/xigmatek
            sudo python3 -m venv /opt/xigmatek/venv
            sudo /opt/xigmatek/venv/bin/pip install hidapi
            
            # Create wrapper script
            sudo tee /usr/local/bin/xigmatek-python > /dev/null << 'EOF'
#!/bin/bash
exec /opt/xigmatek/venv/bin/python "$@"
EOF
            sudo chmod +x /usr/local/bin/xigmatek-python
            PYTHON_CMD="/usr/local/bin/xigmatek-python"
        else
            # Traditional pip install
            if pip3 install --user hidapi 2>/dev/null; then
                echo "✓ hidapi installed via pip --user"
            else
                sudo pip3 install hidapi
                echo "✓ hidapi installed via sudo pip"
            fi
            PYTHON_CMD="python3"
        fi
    else
        echo "✓ hidapi already available"
        PYTHON_CMD="python3"
    fi
}

# Check if Python 3 is installed
check_python() {
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python 3 is not installed!"
        case $DISTRO in
            "arch"|"manjaro")
                echo "Install with: sudo pacman -S python"
                ;;
            "ubuntu"|"debian"|"linuxmint"|"pop")
                echo "Install with: sudo apt install python3"
                ;;
            "fedora"|"rhel"|"centos"|"rocky"|"almalinux")
                echo "Install with: sudo dnf install python3"
                ;;
            *)
                echo "Install Python 3 using your package manager"
                ;;
        esac
        exit 1
    fi
    echo "✓ Python 3 found"
}

# Configure sensors
setup_sensors() {
    echo "🌡️  Setting up sensors..."
    if ! sensors &> /dev/null; then
        echo "Configuring sensors (this may take a moment)..."
        sudo sensors-detect --auto
    else
        echo "✓ Sensors already configured"
    fi
}

# Create the main service script
create_service_script() {
    echo "📋 Creating service script..."
    
    sudo tee /usr/local/bin/xigmatek-monitor.py > /dev/null << EOF
#!$PYTHON_CMD
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
            "update_interval": 1.0,
            "cpu_offset": 0,
            "gpu_offset": 0,
            "min_temp": 20,
            "max_temp": 90,
            "fallback_cpu": 35,
            "fallback_gpu": 40,
            "enable_logging": True,
            "wake_every_update": True,
            "wake_interval": 1
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
                for line in result.stdout.split('\\n'):
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
                for line in result.stdout.split('\\n'):
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
                for line in result.stdout.split('\\n'):
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
                    (update_count - last_wake) >= self.config.get('wake_interval', 1)
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
                
                if update_count % 60 == 0:  # Log every 60 updates (1 minute with 1s interval)
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
EOF

    sudo chmod +x /usr/local/bin/xigmatek-monitor.py
}

# Create directories
create_directories() {
    echo "📁 Creating directories..."
    sudo mkdir -p /usr/local/bin
    sudo mkdir -p /etc/systemd/system
    sudo mkdir -p /var/log
}

# Create configuration file
create_config() {
    echo "⚙️  Creating configuration file..."
    sudo tee /etc/xigmatek-monitor.conf > /dev/null << 'EOF'
{
    "update_interval": 1.0,
    "cpu_offset": 0,
    "gpu_offset": 0,
    "min_temp": 20,
    "max_temp": 90,
    "fallback_cpu": 35,
    "fallback_gpu": 40,
    "enable_logging": true,
    "wake_every_update": true,
    "wake_interval": 1
}
EOF
}

# Create systemd service file
create_systemd_service() {
    echo "🔧 Creating systemd service..."
    sudo tee /etc/systemd/system/xigmatek-monitor.service > /dev/null << 'EOF'
[Unit]
Description=XIGMATEK Temperature Monitor
After=multi-user.target
Wants=multi-user.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/xigmatek-monitor.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log

[Install]
WantedBy=multi-user.target
EOF
}

# Create udev rule
create_udev_rule() {
    echo "🔌 Creating udev rule..."
    sudo tee /etc/udev/rules.d/99-xigmatek.rules > /dev/null << 'EOF'
# XIGMATEK LK 360 Digital Arctic
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="0145", ATTRS{idProduct}=="1005", MODE="0666", GROUP="users"
EOF

    # Reload udev rules
    echo "🔄 Reloading udev rules..."
    sudo udevadm control --reload-rules
    sudo udevadm trigger
}

# Setup logging
setup_logging() {
    echo "📝 Setting up logging..."
    sudo touch /var/log/xigmatek-monitor.log
    sudo chmod 644 /var/log/xigmatek-monitor.log
}

# Test installation
test_installation() {
    echo "🧪 Testing installation..."
    
    # Test device connection
    echo "Testing device connection..."
    if $PYTHON_CMD -c "
import hid
try:
    device = hid.device()
    device.open(0x0145, 0x1005)
    device.close()
    print('✓ Device connection test passed')
except Exception as e:
    print(f'❌ Device connection test failed: {e}')
    exit(1)
"; then
    echo "✓ Device test passed"
else
    echo "❌ Device test failed!"
    echo "Make sure your XIGMATEK device is connected"
    echo "Try a different USB port or check the cable"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

    # Test the service script
    echo "Testing service script..."
    if sudo /usr/local/bin/xigmatek-monitor.py --test; then
        echo "✓ Service test passed"
    else
        echo "❌ Service test failed!"
        echo "Check the logs for details"
        read -p "Continue anyway? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Print final instructions
print_instructions() {
    echo ""
    echo "🎉 Installation completed successfully!"
    echo ""
    echo "Next steps:"
    echo "==========="
    echo "1. Start the service:"
    echo "   sudo systemctl start xigmatek-monitor"
    echo ""
    echo "2. Enable auto-start on boot:"
    echo "   sudo systemctl enable xigmatek-monitor"
    echo ""
    echo "3. Check service status:"
    echo "   sudo systemctl status xigmatek-monitor"
    echo ""
    echo "4. View logs:"
    echo "   sudo journalctl -u xigmatek-monitor -f"
    echo ""
    echo "5. Stop the service:"
    echo "   sudo systemctl stop xigmatek-monitor"
    echo ""
    echo "Configuration file: /etc/xigmatek-monitor.conf"
    echo "You can edit this file to adjust settings like temperature offsets"
    echo ""
    echo "Distribution detected: $DISTRO"
    echo "Python command used: $PYTHON_CMD"
    echo ""
    echo "🎯 Your XIGMATEK display will now show real CPU and GPU temperatures!"
}

# Main execution
main() {
    detect_distro
    check_python
    install_packages
    install_hidapi_fallback
    setup_sensors
    create_directories
    create_config
    create_service_script
    create_systemd_service
    create_udev_rule
    setup_logging
    
    # Reload systemd
    echo "🔄 Reloading systemd..."
    sudo systemctl daemon-reload
    
    test_installation
    print_instructions
    
    # Offer to start the service
    read -p "Start the service now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo systemctl start xigmatek-monitor
        sudo systemctl enable xigmatek-monitor
        echo "✓ Service started and enabled!"
        echo ""
        echo "Check status with: sudo systemctl status xigmatek-monitor"
        echo "View live logs with: sudo journalctl -u xigmatek-monitor -f"
    fi
    
    echo ""
    echo "Setup complete! 🚀"
}

# Set default values
install_hidapi_pip=false
PYTHON_CMD="python3"

# Run main function
main