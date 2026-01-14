# macOS Support Documentation

This document covers macOS-specific implementation details, version requirements, and platform considerations for Task Coach.

## Table of Contents

- [Supported Versions](#supported-versions)
- [Intel vs Apple Silicon](#intel-vs-apple-silicon)
- [Apple's Intel Transition Timeline](#apples-intel-transition-timeline)
- [Native macOS Features](#native-macos-features)
- [Idle Time Detection](#idle-time-detection)
- [Power Management](#power-management)
- [Darwin Version Mapping](#darwin-version-mapping)
- [Code Signing and Notarization](#code-signing-and-notarization)
- [Troubleshooting](#troubleshooting)
- [References](#references)

---

## Supported Versions

| macOS Version | Codename | Status |
|---------------|----------|--------|
| macOS 13 | Ventura | **Minimum supported** |
| macOS 14 | Sonoma | Supported |
| macOS 15 | Sequoia | Supported |
| macOS 16 | Tahoe | Supported (expected) |

**Minimum requirement:** macOS 13 (Ventura), released October 2022.

Older versions (Monterey and earlier) are not supported. The `LSMinimumSystemVersion` in the app bundle is set to `13.0`.

---

## Intel vs Apple Silicon

Task Coach builds for both Mac architectures:

| Architecture | CPU | Target Macs | GitHub Runner |
|--------------|-----|-------------|---------------|
| x86_64 | Intel | Intel Macs (2006-2020) | `macos-15-intel` |
| arm64 | Apple Silicon | M1/M2/M3/M4 Macs (2020+) | `macos-latest` |

### Why Both Architectures?

Apple transitioned from Intel to ARM-based Apple Silicon starting in November 2020. The architectures are binary-incompatible:

- **Native ARM64 code** won't run on Intel Macs
- **Intel code** runs on Apple Silicon only via Rosetta 2 emulation (performance penalty)

Building native binaries for both ensures optimal performance on all supported Macs.

### Universal Binaries (Alternative)

An alternative approach is building a Universal Binary (fat binary) containing both architectures in a single .app. This increases file size but simplifies distribution. Task Coach currently uses separate builds.

---

## Apple's Intel Transition Timeline

Apple announced their transition from Intel to Apple Silicon at WWDC 2020, with the transition completing in 2022 (last Intel Mac sold).

### Official Support Timeline

| macOS Version | Year | Intel Mac Support |
|---------------|------|-------------------|
| macOS 14 Sonoma | 2023 | Many Intel models supported |
| macOS 15 Sequoia | 2024 | Reduced Intel support |
| **macOS 16 Tahoe** | **2025** | **Last version with Intel support** |
| macOS 17 | 2026 | **Apple Silicon only** |

### macOS 16 Tahoe - Final Intel Support

At WWDC 2025 (June 9, 2025), Apple announced that macOS Tahoe will be the **last macOS version supporting Intel Macs**.

Only four Intel Mac models are supported by macOS 16 Tahoe:
- Mac Pro (2019)
- MacBook Pro (16-inch, 2019)
- MacBook Pro (13-inch, 2020, four Thunderbolt 3 ports)
- iMac (2020)

All Intel MacBook Air and Mac mini models are no longer supported as of Tahoe.

### Rosetta 2 Future

Apple has announced Rosetta 2 plans:
- **macOS 16 (2025):** Full Rosetta support
- **macOS 17 (2026):** Full Rosetta support
- **macOS 18+ (2027+):** Reduced Rosetta - only for legacy gaming titles

### Security Updates for Intel Macs

Intel Macs will continue to receive security updates for approximately three years after their last supported macOS version, following Apple's standard policy.

### Recommendation for Task Coach

Given the timeline:
- **2025-2026:** Keep both Intel and ARM64 builds
- **2027+:** Consider dropping Intel builds (reassess based on user base)

---

## Native macOS Features

Task Coach uses pure Python implementations for macOS-specific features via `ctypes`:

| Feature | Implementation | Framework |
|---------|----------------|-----------|
| Idle detection | `ctypes` | IOKit |
| Power management | Base class (no-op) | — |
| Date formatting | Python `strftime` | — |
| Text-to-speech | Subprocess | `say` command |
| Thunderbird paths | Python | `~/Library/Thunderbird` |

### Historical Note

Task Coach previously included native C extensions (`_idle.so`, `_powermgt.so`) for macOS. These were removed in January 2026 because:
1. They used Python 2 API (`Py_InitModule3`) incompatible with Python 3
2. They were compiled only for Intel (ia32/ia64), not ARM64
3. Pure Python ctypes implementations provide the same functionality

See [PYTHON3_MIGRATION_5.md](PYTHON3_MIGRATION_5.md#macos-native-extensions-cleanup) for details.

---

## Idle Time Detection

Task Coach detects user idle time for effort tracking features. On macOS, this is implemented using IOKit via ctypes.

### Implementation

```python
# taskcoachlib/powermgt/idle.py - MacIdleQuery class

from ctypes import cdll, c_void_p, c_uint32, c_int32, c_int64, byref

class MacIdleQuery:
    def __init__(self):
        # Load macOS frameworks
        self._iokit = cdll.LoadLibrary(
            '/System/Library/Frameworks/IOKit.framework/IOKit'
        )
        self._cf = cdll.LoadLibrary(
            '/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation'
        )

    def getIdleSeconds(self):
        # Query IOHIDSystem for HIDIdleTime property
        hid_service = self._iokit.IOServiceGetMatchingService(
            0,  # kIOMasterPortDefault
            self._iokit.IOServiceMatching(b"IOHIDSystem")
        )
        idle_time_ref = self._iokit.IORegistryEntryCreateCFProperty(
            hid_service, self._idle_key, None, 0
        )
        # Value is in nanoseconds, convert to seconds
        return idle_ns.value / 1_000_000_000
```

### IOKit APIs Used

| Function | Purpose |
|----------|---------|
| `IOServiceMatching` | Create matching dictionary for IOHIDSystem |
| `IOServiceGetMatchingService` | Get the HID system service |
| `IORegistryEntryCreateCFProperty` | Get HIDIdleTime property |
| `IOObjectRelease` | Release service reference |

---

## Power Management

Power state notifications (sleep/wake) on macOS require registering callbacks with `IORegisterForSystemPower` and running a `CFRunLoop`. This is complex to implement in pure Python.

**Current implementation:** Falls back to base class (no-op). The application relies on:
- Standard wxPython events (`EVT_POWER_SUSPENDED`, `EVT_POWER_RESUME`) where available
- Idle detection resuming naturally after wake

This is acceptable because idle detection is the primary use case for effort tracking.

---

## Darwin Version Mapping

macOS version detection uses the Darwin kernel version via `platform.release()`:

| Darwin Version | macOS Version | Codename | Year |
|----------------|---------------|----------|------|
| 20 | 11 | Big Sur | 2020 |
| 21 | 12 | Monterey | 2021 |
| 22 | 13 | Ventura | 2022 |
| 23 | 14 | Sonoma | 2023 |
| 24 | 15 | Sequoia | 2024 |
| 25 | 16 | Tahoe | 2025 |

### Version Check Code

```python
# taskcoachlib/operating_system.py

def _platformVersion():
    return tuple(map(int, platform.release().split(".")))

def isMacOsSonoma_OrNewer():
    """Check if running on macOS 14 (Sonoma) or newer."""
    if isMac():
        return _platformVersion() >= (23,)  # Darwin 23 = macOS 14
    return False
```

### Reference

For complete version history: [macOS version history - Wikipedia](https://en.wikipedia.org/wiki/MacOS_version_history#Releases)

---

## Code Signing and Notarization

### Current Status

Task Coach macOS builds are **unsigned**. This means:
- Users see "unidentified developer" warning on first launch
- Users must right-click → Open, or use `xattr` to clear quarantine

### Bypassing Gatekeeper

For unsigned apps downloaded from the internet:

```bash
# Clear quarantine attribute
xattr -cr "/Applications/Task Coach.app"

# Or via System Preferences:
# Security & Privacy → General → "Open Anyway"
```

### Requirements for Signed Distribution

To distribute signed/notarized apps, you need:

1. **Apple Developer Program membership** ($99/year)
2. **Developer ID Application certificate**
3. **Notarization** through Apple's notary service
4. **Stapling** the notarization ticket to the app/DMG

### Future Work

To add signing to GitHub Actions:
1. Export Developer ID certificate as .p12
2. Store certificate and password in GitHub Secrets
3. Add signing step to workflow using `codesign`
4. Add notarization step using `xcrun notarytool`

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| "App is damaged and can't be opened" | Gatekeeper quarantine | Run `xattr -cr "/Applications/Task Coach.app"` |
| "unidentified developer" warning | Unsigned app | Right-click → Open, or clear quarantine |
| App won't launch on Intel Mac | ARM64-only binary | Use Intel build (`-intel.dmg`) |
| App slow on Apple Silicon | Running Intel binary via Rosetta | Use ARM64 build (`-arm64.dmg`) |
| Idle detection returns 0 | IOKit access issue | Check Console.app for errors |

---

## References

### Apple Documentation
- [Mac computers with Apple silicon - Apple Support](https://support.apple.com/en-us/116943)
- [IOKit Framework Reference](https://developer.apple.com/documentation/iokit)
- [Notarizing macOS Software Before Distribution](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)

### Version History
- [macOS version history - Wikipedia](https://en.wikipedia.org/wiki/MacOS_version_history#Releases)
- [Apple will end support for Intel Macs - 9to5Mac](https://9to5mac.com/2025/06/09/apple-will-end-support-for-intel-macs/)
- [macOS Tahoe - Wikipedia](https://en.wikipedia.org/wiki/macOS_Tahoe)

### Task Coach Documentation
- [PYTHON3_MIGRATION_5.md](PYTHON3_MIGRATION_5.md#macos-native-extensions-cleanup) - Native extension removal details
- [PACKAGING.md](PACKAGING.md#macos-packaging) - Build workflow overview
