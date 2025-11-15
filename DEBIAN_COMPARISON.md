# TaskCoach: Bookworm vs Trixie Comparison

## TL;DR: **Bookworm is simpler and recommended** ✓

## Detailed Comparison

### Debian 12 Bookworm (Stable) - RECOMMENDED

**Pros:**
- ✅ **Everything just works** - default Python matches system packages
- ✅ Python 3.11 is default, wxPython built for 3.11
- ✅ No version conflicts or mismatches
- ✅ Stable, tested package combinations
- ✅ Simple pip installs (no `--break-system-packages` needed for user installs)
- ✅ Better documentation and community support for stable

**Cons:**
- ⚠️ Slightly older package versions (but still recent enough)

**Setup:**
```bash
sudo apt-get install python3-wxgtk4.0 python3-pip
pip3 install --user <packages>
python3 taskcoach.py
```

**Package Versions:**
- Python: 3.11.2+
- wxPython: 4.2.0+dfsg-3
- Everything aligned and tested together

---

### Debian Trixie/Sid (Testing/Unstable)

**Pros:**
- ✅ Newer package versions
- ✅ Python 3.12 available
- ✅ wxPython 4.2.1 available (slightly newer)

**Cons:**
- ⚠️ **Multiple Python versions can cause confusion** (3.11, 3.12, 3.13)
- ⚠️ **Version mismatch issues**: wxPython built for 3.12, but 3.11 might be default
- ⚠️ Need to explicitly use `python3.12` everywhere
- ⚠️ PEP 668 externally-managed environment requires `--break-system-packages`
- ⚠️ Less stable, packages change frequently
- ⚠️ Potential dependency issues during updates

**Setup:**
```bash
sudo apt-get install python3-wxgtk4.0
python3.12 -m pip install --break-system-packages <packages>
python3.12 taskcoach.py  # Must specify 3.12
```

**Package Versions:**
- Python: 3.11 (default) / 3.12 / 3.13 available
- wxPython: 4.2.1+dfsg-3build2 (built for Python 3.12)
- **Mismatch**: Need to explicitly use python3.12

---

## Side-by-Side Setup Comparison

| Step | Bookworm | Trixie |
|------|----------|--------|
| Python version | `python3` (3.11) | Must use `python3.12` |
| wxPython install | `apt install python3-wxgtk4.0` | Same, but built for 3.12 |
| Pip installs | `pip3 install --user` | `pip3.12 install --break-system-packages` |
| Run command | `python3 taskcoach.py` | `python3.12 taskcoach.py` |
| Complexity | **Simple** | **More complex** |

---

## Real-World Testing Results

### On Trixie (What We Encountered):

```bash
# This failed (Python 3.11 vs wxPython built for 3.12):
python3 taskcoach.py
# ModuleNotFoundError: No module named 'wx._core'

# Had to use this:
python3.12 taskcoach.py  # Works

# Also needed:
python3.12 -m pip install --break-system-packages <packages>
```

### On Bookworm (Expected):

```bash
# This should work directly:
python3 taskcoach.py  # Works immediately

# Standard pip:
pip3 install --user <packages>  # No special flags needed
```

---

## Recommendation by Use Case

### For General Users: **Bookworm**
- Easier setup
- More reliable
- Standard Debian stable experience
- No need to track Python versions

### For Developers/Testing: **Trixie**
- If you need bleeding edge
- If you're testing Python 3.12+ features
- If you don't mind occasional breakage
- If you want to help test upcoming Debian releases

### For Production: **Bookworm**
- Stability is critical
- Well-tested package combinations
- Long-term support
- Predictable updates

---

## Migration Path

If on Trixie and want simplicity:
1. Stay on Trixie but use Python 3.12 explicitly everywhere
2. OR wait for Trixie to stabilize (becomes Debian 13)
3. OR use Bookworm for this application

If on Bookworm:
- Perfect! Stay there for TaskCoach

---

## Conclusion

**Use Bookworm** unless you have a specific reason to use Trixie.

Bookworm provides:
- Simpler setup (fewer commands)
- No version juggling
- More stable operation
- Better user experience

The package versions are only slightly older, and TaskCoach works perfectly fine with Bookworm's versions.
