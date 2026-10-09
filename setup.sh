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
# The driver lives in src/xigmatek-monitor.py. It used to be pasted into this script as a second
# copy, which meant fixes made in src/ never reached people who installed with setup.sh.
# Now the real file is installed: from the local checkout, or downloaded when run via curl | bash.
DRIVER_URL="${DRIVER_URL:-https://raw.githubusercontent.com/nikola-zdravkovic/xigmatek-linux-driver/main/src/xigmatek-monitor.py}"

create_service_script() {
    echo "📋 Creating service script..."

    local script_dir src tmp
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
    src="$script_dir/src/xigmatek-monitor.py"
    tmp="$(mktemp)"
    if [ -f "$src" ]; then
        cp "$src" "$tmp"
    elif ! curl -fsSL "$DRIVER_URL" -o "$tmp"; then
        echo "❌ Could not download the driver from $DRIVER_URL"
        rm -f "$tmp"
        exit 1
    fi
    # use the Python interpreter detected above
    sed -i "1s|^#!.*|#!$PYTHON_CMD|" "$tmp"
    sudo install -m 755 "$tmp" /usr/local/bin/xigmatek-monitor.py
    rm -f "$tmp"
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
# XIGMATEK AK4 Digital (HWCX USB Display)
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="0145", ATTRS{idProduct}=="1002", MODE="0666", GROUP="users"
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
    pids = [d['product_id'] for d in hid.enumerate(0x0145) if d['product_id'] in (0x1005, 0x1002)]
    if not pids:
        raise RuntimeError('no supported XIGMATEK device (0145:1005 or 0145:1002) found')
    device = hid.device()
    device.open(0x0145, pids[0])
    device.close()
    print(f'✓ Device connection test passed (0145:{pids[0]:04x})')
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