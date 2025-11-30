# TaskCoach on Debian Trixie - Known Issues & Planning

This document tracks known problems with TaskCoach on Debian Trixie (testing) and plans for fixes.

## Current Status

✅ **TaskCoach works on Trixie** with Python 3.12
⚠️ **Additional complexity** compared to Bookworm

## Known Issues

### 1. Multiple Python Versions Confusion

**Problem:**
- Trixie has Python 3.11, 3.12, and 3.13 available
- System wxPython is built for Python 3.12
- Default `python3` might not be 3.12
- Users must explicitly use `python3.12` everywhere

**Impact:**
- Error: `ModuleNotFoundError: No module named 'wx._core'` when using wrong Python version
- Confusing for users who expect `python3` to work

**Potential Solutions:**
- [ ] Detect Python version mismatch in taskcoach-run.sh and warn user
- [ ] Auto-select correct Python version in launcher script
- [ ] Add version detection to setup_bookworm.sh (rename to setup.sh?)
- [ ] Document Trixie-specific setup clearly

**Status:** Documented workaround exists (use python3.12 explicitly)

---

### 2. PEP 668 Requires --break-system-packages

**Problem:**
- `pip install --user` blocked by PEP 668
- Users must use `--break-system-packages` flag
- This is potentially dangerous if used incorrectly

**Impact:**
- Confusing error messages for users
- Risk of breaking system Python if misused

**Current Solution:**
- Use virtual environment with `--system-site-packages`
- Works on both Bookworm and Trixie

**Status:** ✅ Solved with venv approach

---

### 3. Package Version Mismatches

**Problem:**
- Trixie packages change frequently during testing cycle
- wxPython version might not match other dependencies
- System package updates can break working setups

**Impact:**
- Unreliable setup - works today, breaks tomorrow
- Hard to support users on constantly changing platform

**Potential Solutions:**
- [ ] Pin package versions in documentation
- [ ] Add version checks to setup script
- [ ] Recommend Bookworm for production use

**Status:** Monitoring - no specific issues yet, but risk exists

---

### 4. Setup Script Only Targets Bookworm

**Problem:**
- `setup_bookworm.sh` is named for Bookworm only
- Script doesn't detect or handle Trixie-specific requirements
- No Trixie-specific setup automation

**Impact:**
- Manual setup required for Trixie users
- Higher chance of user error

**Potential Solutions:**
- [ ] Rename to `setup_debian.sh`
- [ ] Add distro/version detection
- [ ] Auto-handle Python version selection on Trixie
- [ ] Create separate `setup_trixie.sh` if needed

**Status:** Planning phase

---

### 5. Documentation Focused on Bookworm

**Problem:**
- Main documentation (DEBIAN_BOOKWORM_SETUP.md) targets Bookworm
- Trixie setup buried in comparison document
- No clear Trixie quickstart

**Impact:**
- Trixie users might not find correct instructions
- Confusion about which Python version to use

**Potential Solutions:**
- [x] Create DEBIAN_TRIXIE_PLANNING.md (this file)
- [ ] Add Trixie section to main setup guide
- [ ] Create DEBIAN_TRIXIE_SETUP.md if complexity warrants it

**Status:** In progress

---

## Trixie-Specific Setup (Current Working Method)

```bash
# 1. Install system packages (built for Python 3.12)
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv python3-wxgtk4.0 \
    python3-six python3-lxml python3-numpy \
    python3-dateutil python3-chardet python3-keyring \
    python3-pyparsing python3-pyxdg

# 2. Create virtual environment with system packages
cd /path/to/taskcoach
python3.12 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install desktop3 lockfile gntp distro pypubsub 'watchdog>=3.0.0'
deactivate

# 3. Run TaskCoach
./taskcoach-run.sh
```

**Note:** The launcher script may need to be updated to use `python3.12` explicitly on Trixie.

---

## Testing Needed

- [ ] Test on clean Trixie installation
- [ ] Verify all Python versions (3.11, 3.12, 3.13) behavior
- [ ] Test with different default Python versions
- [ ] Verify package version compatibility
- [ ] Test after Trixie package updates

---

## Recommendations

### For Users:
- **Use Bookworm** for production/stable TaskCoach usage
- **Use Trixie** only if you need bleeding edge or are testing
- **Always use python3.12** explicitly on Trixie

### For Developers:
- Focus testing on Bookworm (stable target)
- Test Trixie changes before they become Debian 13 stable
- Automate Python version detection
- Consider supporting both Bookworm and future Debian 13

---

## Future Work

### Short Term:
1. Add Trixie detection to setup script
2. Auto-select correct Python version
3. Add clear warnings when Python version mismatch detected

### Medium Term:
1. Create unified setup script for both Bookworm and Trixie
2. Add comprehensive Trixie testing to CI (if applicable)
3. Document migration path from Bookworm to future Debian 13

### Long Term:
1. Prepare for Debian 13 (when Trixie becomes stable)
2. Drop Bookworm support when Debian 13 is stable (years away)
3. Stay ahead of Python version changes

---

## Questions & Decisions Needed

1. **Should we support Trixie officially?**
   - Pro: Ready for Debian 13
   - Con: Maintenance burden, unstable target

2. **Should setup script detect distro?**
   - Pro: Better UX, fewer user errors
   - Con: More complexity

3. **Should we create separate Trixie documentation?**
   - Pro: Clear, specific instructions
   - Con: Documentation duplication

---

## Contributing

If you encounter Trixie-specific issues or have solutions, please:
1. Test the issue thoroughly
2. Document the problem and solution
3. Update this file
4. Submit improvements to the setup scripts

---

## See Also

- [DEBIAN_BOOKWORM_SETUP.md](DEBIAN_BOOKWORM_SETUP.md) - Main setup guide (recommended)
- [setup_bookworm.sh](setup_bookworm.sh) - Automated setup script
- [README.md](README.md) - General TaskCoach information
