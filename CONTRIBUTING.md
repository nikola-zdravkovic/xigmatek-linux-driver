# Contributing to XIGMATEK Linux Driver

Thank you for your interest in contributing! This project welcomes contributions from everyone.

## Ways to Contribute

### 🐛 Bug Reports
- Found a bug? Report it!
- Check existing issues first
- Include detailed information

### 💡 Feature Requests
- Ideas for new features
- Improvements to existing functionality
- Better hardware support

### 🔧 Code Contributions
- Bug fixes
- New features
- Performance improvements
- Code cleanup

### 📚 Documentation
- Improve installation guides
- Add troubleshooting tips
- Update README
- Translate documentation

### 🧪 Testing
- Test on different distributions
- Test with different hardware
- Report compatibility

## Getting Started

### Prerequisites
- Linux system with XIGMATEK hardware (preferred)
- Git and GitHub account
- Python 3.8+ development environment
- Familiarity with USB/HID protocols (for advanced contributions)

### Development Setup

1. **Fork the repository**
   ```bash
   # On GitHub, click "Fork" button
   git clone https://github.com/nikola-zdravkovic/xigmatek-linux-driver.git
   cd xigmatek-linux-driver
   ```

2. **Create development environment**
   ```bash
   # Install development dependencies
   pip3 install --user hidapi pytest black flake8
   
   # Install system dependencies
   sudo pacman -S python-hidapi lm_sensors  # Arch
   # or
   sudo apt install python3-hid lm-sensors  # Ubuntu/Debian
   ```

3. **Set up pre-commit hooks (optional)**
   ```bash
   pip3 install --user pre-commit
   pre-commit install
   ```

## Development Guidelines

### Code Style
- **Python**: Follow PEP 8
- **Line length**: 88 characters (Black default)
- **Imports**: Group standard library, third-party, local imports
- **Comments**: Clear, concise explanations

### Code Formatting
```bash
# Format code with Black
black src/xigmatek-monitor.py

# Check style with flake8
flake8 src/xigmatek-monitor.py --max-line-length=88
```

### Testing
```bash
# Run device tests (requires hardware)
python3 scripts/test-device.py

# Test service functionality
sudo python3 src/xigmatek-monitor.py --test

# Test installation script
./setup.sh
```

## Contribution Process

### 1. Create an Issue (Optional but Recommended)
- Describe the problem or feature
- Get feedback before starting work
- Avoid duplicate efforts

### 2. Create a Branch
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 3. Make Changes
- Keep commits small and focused
- Write clear commit messages
- Test your changes

### 4. Commit Guidelines
```bash
# Good commit messages:
git commit -m "Fix display flickering on fast updates"
git commit -m "Add support for custom temperature offsets"
git commit -m "Update documentation for Fedora installation"

# Use imperative mood ("Fix" not "Fixed" or "Fixes")
# Explain what the commit does, not what you did
```

### 5. Push and Create Pull Request
```bash
git push origin feature/your-feature-name
# Then create PR on GitHub
```

## Pull Request Guidelines

### PR Description
Include:
- **What**: What does this change do?
- **Why**: Why is this change needed?
- **How**: How does it work?
- **Testing**: How was it tested?

### PR Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement

## Testing
- [ ] Tested on hardware
- [ ] Unit tests pass
- [ ] Integration tests pass

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or clearly documented)
```

### Review Process
1. **Automated checks** must pass
2. **Manual review** by maintainers
3. **Testing** on real hardware (when possible)
4. **Discussion** and feedback
5. **Merge** when approved

## Reporting Issues

### Bug Reports
Use this template:

```markdown
**Description**
Clear description of the bug

**Environment**
- Distribution: Arch Linux
- Kernel version: 6.5.0
- Python version: 3.11
- Driver version: 1.0.0

**Hardware**
- XIGMATEK model: LK 360 Digital Arctic
- USB connection: Direct to motherboard
- Other coolers: None

**Steps to Reproduce**
1. Install driver
2. Start service
3. Observe display

**Expected Behavior**
Display should show temperatures

**Actual Behavior**
Display flickers constantly

**Logs**
```
Include relevant log output
```

**Additional Context**
Any other relevant information
```

### Feature Requests
```markdown
**Feature Description**
Clear description of desired feature

**Use Case**
Why would this be useful?

**Possible Implementation**
Ideas for how it could work

**Alternatives**
Other solutions you've considered
```

## Development Areas

### Priority Areas
1. **Hardware Support**
   - Support for additional XIGMATEK models
   - RGB lighting control
   - Fan curve integration

2. **Software Features**
   - GUI configuration tool
   - Integration with monitoring software
   - Custom display messages
   - Temperature alerts

3. **Stability**
   - Better error handling
   - Recovery mechanisms
   - Performance optimization

4. **Platform Support**
   - Additional Linux distributions
   - Different init systems
   - Embedded systems

### Getting Started Ideas
Good first contributions:
- Fix typos in documentation
- Add distribution-specific installation notes
- Test on different systems
- Improve error messages
- Add configuration validation

## Communication

### Channels
- **GitHub Issues**: Bug reports, feature requests
- **GitHub Discussions**: General questions, ideas
- **Pull Requests**: Code review, technical discussion

### Community Guidelines
- **Be respectful** and constructive
- **Help others** when you can
- **Search existing issues** before creating new ones
- **Stay on topic** in discussions
- **Follow the code of conduct**

## Code of Conduct

### Our Standards
- **Welcoming**: Inclusive environment for all contributors
- **Respectful**: Professional and courteous communication
- **Collaborative**: Working together toward common goals
- **Constructive**: Helpful feedback and suggestions

### Unacceptable Behavior
- Harassment or discrimination
- Trolling or inflammatory comments
- Personal attacks
- Off-topic discussions

## Recognition

### Contributors
All contributors are recognized in:
- README.md contributors section
- Release notes
- GitHub contributors page

### Types of Recognition
- **Code contributors**: Listed with GitHub profiles
- **Documentation**: Acknowledged in docs
- **Testing**: Mentioned in compatibility notes
- **Ideas**: Credited for feature suggestions

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

- **General questions**: GitHub Discussions
- **Bug reports**: GitHub Issues
- **Security issues**: Email maintainers directly
- **Code review**: Pull request comments

Thank you for contributing to making XIGMATEK hardware work better on Linux! 🚀