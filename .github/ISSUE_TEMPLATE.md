---
name: Bug Report
about: Create a bug report to help us improve
title: '[BUG] '
labels: bug
assignees: ''
---

## Bug Description
**Clear and concise description of the bug**

## Environment
**System Information:**
- Distribution: [e.g., Arch Linux, Ubuntu 22.04]
- Kernel version: [e.g., 6.5.0]
- Python version: [e.g., 3.11.2]
- Driver version: [e.g., 1.0.0]

**Hardware Information:**
- XIGMATEK model: [e.g., LK 360 Digital Arctic]
- CPU: [e.g., AMD Ryzen 5 5600X]
- GPU: [e.g., NVIDIA RTX 3070]
- Motherboard: [e.g., ASUS B550-F]
- USB connection: [Direct to motherboard/USB hub]

## Steps to Reproduce
1. [First step]
2. [Second step]
3. [And so on...]

## Expected Behavior
**What you expected to happen**

## Actual Behavior
**What actually happened**

## Logs
**Include relevant log output:**

```bash
# Service logs
sudo journalctl -u xigmatek-monitor -n 50

# Test output
python3 scripts/test-device.py
```

**Log output:**
```
[Paste log output here]
```

## Configuration
**Your configuration file (`/etc/xigmatek-monitor.conf`):**
```json
{
    "update_interval": 1.0,
    "cpu_offset": 0,
    "gpu_offset": 0
}
```

## Additional Context
**Any other relevant information, screenshots, or context**

## Troubleshooting Steps Tried
- [ ] Restarted the service
- [ ] Checked USB connection
- [ ] Ran test script
- [ ] Checked logs
- [ ] Tried different USB port
- [ ] Rebooted system

---

**For maintainers:**
- [ ] Bug confirmed
- [ ] Reproduction steps verified
- [ ] Fix identified
- [ ] Tests added
- [ ] Documentation updated