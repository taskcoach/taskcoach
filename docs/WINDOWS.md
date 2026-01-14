# Windows Packaging for Task Coach

- **Windows:** [Inno Setup](https://jrsoftware.org/isinfo.php) | [Python Embeddable Package](https://www.python.org/downloads/windows/) | [Thonny](https://github.com/thonny/thonny) (reference implementation)
- **Project files:** [`build-windows.yml`](../.github/workflows/build-windows.yml)

Windows builds use Python's embeddable distribution + Inno Setup (same approach as Thonny).

## Available Builds

| Build | Python | Arch | Target |
|-------|--------|------|--------|
| `TaskCoach-X.Y.Z-windows-x64-setup.exe` | 3.11 | 64-bit | Most users |
| `TaskCoach-X.Y.Z-windows-x64-portable.zip` | 3.11 | 64-bit | Portable |

**32-bit builds (disabled):** The following builds are commented out in the workflow since no current users require them. To reactivate, uncomment the x86 matrix entry in `.github/workflows/build-windows.yml`:

| Build | Python | Arch | Target |
|-------|--------|------|--------|
| `TaskCoach-X.Y.Z-windows-x86-py39-setup.exe` | 3.9 | 32-bit | VMs, older systems |
| `TaskCoach-X.Y.Z-windows-x86-py39-portable.zip` | 3.9 | 32-bit | Portable, compatibility |

## Windows Packaging Options

### Executable Generators (Python → EXE)

| Tool | GitHub Actions | Pros | Cons | Example Projects |
|------|:--------------:|------|------|------------------|
| **[PyInstaller](https://pyinstaller.org/)** | ✅ | Most popular, good library support | Can hang on GitHub Actions, large output | [Pyfa](https://github.com/pyfa-org/Pyfa) (wxPython, AppVeyor) |
| **[Nuitka](https://nuitka.net/)** | ✅ | Compiles to C, 2-3x faster, obfuscated | Long compile times, 2x larger output | [Nuitka-Action](https://github.com/Nuitka/Nuitka-Action) (official) |
| **[cx_Freeze](https://cx-freeze.readthedocs.io/)** | ✅ | Cross-platform, simple | Doesn't auto-detect imports, no obfuscation | — |
| **[Briefcase](https://beeware.org/briefcase/)** | ✅ | Good docs, native packaging, uses WiX 5 | Newer, fewer examples | [BeeWare CI Guide](https://briefcase.beeware.org/en/latest/how-to/ci.html) |
| **[PyOxidizer](https://pyoxidizer.readthedocs.io/)** | ✅ | Single-file, embeds Python, WiX integration | More complex setup | [doc2dash](https://github.com/hynek/doc2dash) |
| **Python Embed** | ✅ | No compilation, reliable, exact Python version | Requires separate installer tool | [Thonny](https://github.com/thonny/thonny), **Task Coach** |

### Installer Builders (EXE → Installer)

| Tool | Output | GitHub Actions | Pre-installed | Example Projects |
|------|--------|:--------------:|:-------------:|------------------|
| **[Inno Setup](https://jrsoftware.org/isinfo.php)** | `.exe` | ✅ | windows-2022, windows-2025 | [Thonny](https://github.com/thonny/thonny), [Pyfa](https://github.com/pyfa-org/Pyfa), **Task Coach** |
| **[WiX Toolset](https://wixtoolset.org/)** | `.msi` | ✅ | windows-2022, windows-2025 | [Briefcase](https://github.com/beeware/briefcase) apps |
| **[NSIS](https://nsis.sourceforge.net/)** | `.exe` | ⚠️ | windows-2022 only | [Mu Editor](https://github.com/mu-editor/mu) (via pynsist) |
| **[pynsist](https://pynsist.readthedocs.io/)** | `.exe` | ✅ | Uses NSIS | [Mu Editor](https://github.com/mu-editor/mu) |

### GitHub Runner Pre-installed Tools

| Tool | windows-2022 | windows-2025 | Action if Missing |
|------|:------------:|:------------:|-------------------|
| Inno Setup 6.6.1 | ✅ | ✅ | [Inno-Setup-Action](https://github.com/Minionguyjpro/Inno-Setup-Action) |
| WiX Toolset 3.14.1 | ✅ | ✅ | — |
| NSIS 3.10 | ✅ | ❌ | [nsis-install](https://github.com/marketplace/actions/install-nsis-compiler) |

## Why Python Embed + Inno Setup?

| Method | Status | Notes |
|--------|--------|-------|
| PyInstaller | ⚠️ | Can hang at "Looking for dynamic libraries" on GitHub Actions |
| cx_Freeze | ❌ | Produced executables that failed to run |
| Nuitka | ✅ | Viable alternative, longer build times |
| Briefcase | ✅ | Viable alternative, produces MSI instead of EXE |
| **Python Embed + Inno Setup** | ✅ **Current** | Reliable, proper installer, file associations, fast builds |

## Reference Implementations

| Project | Exe Generator | Installer | CI Platform | Notes |
|---------|---------------|-----------|-------------|-------|
| [Thonny](https://github.com/thonny/thonny) | Python Embed | Inno Setup | GitHub Actions | 64-bit and 32-bit, same approach as Task Coach |
| [Pyfa](https://github.com/pyfa-org/Pyfa) | PyInstaller | Inno Setup | AppVeyor | wxPython app, EVE Online fitting tool |
| [Mu Editor](https://github.com/mu-editor/mu) | PUP | pynsist/NSIS | GitHub Actions | Python IDE for beginners |
| [doc2dash](https://github.com/hynek/doc2dash) | PyOxidizer | WiX | GitHub Actions | Documentation tool |

## Key Configuration for Python Embeddable Package

The Python embeddable package requires careful configuration to work with pip-installed packages like wxPython and pywin32.

### 1. The `._pth` File (Critical)

The `pythonXX._pth` file controls `sys.path`. The order matters - `import site` must come **AFTER** all paths:

```
python311.zip
.
Lib\site-packages
..
import site
```

**Why?** `import site` triggers `site.main()` which looks for `.pth` files in directories already in `sys.path`. If `import site` comes before `Lib\site-packages`, packages like pywin32 that use `.pth` files for DLL path setup won't work.

### 2. Create the DLLs Folder

Create an empty `DLLs` folder in the Python directory. Without this, Python can't locate some modules and imports fail with "FileNotFoundError".

### 3. Copy pywin32 DLLs

pywin32's `pywin32_bootstrap` mechanism (via `.pth` file) doesn't reliably work with embeddable Python. Copy DLLs directly to the Python directory:

```powershell
Copy-Item "Lib\site-packages\pywin32_system32\*.dll" -Destination "python\" -Force
```

This copies `pywintypesXX.dll` and `pythoncomXX.dll` where they'll be found.

### 4. Bundle VC++ Runtime DLLs

wxPython requires Visual C++ Runtime DLLs that are **NOT** included in Windows by default:
- `msvcp140.dll`
- `vcruntime140.dll`
- `vcruntime140_1.dll`

Copy these from the build system (GitHub Actions runner has them in `C:\Windows\System32\`) to the Python directory:

```powershell
Copy-Item "C:\Windows\System32\msvcp140.dll" -Destination "python\"
Copy-Item "C:\Windows\System32\vcruntime140.dll" -Destination "python\"
Copy-Item "C:\Windows\System32\vcruntime140_1.dll" -Destination "python\"
```

**Note:** The Python embeddable package includes `vcruntime140.dll` but NOT `msvcp140.dll`. wxPython (built with C++) requires `msvcp140.dll`.

### Runtime DLL Setup in Application

In `taskcoach.py`, additional DLL directory registration is needed for Python 3.8+:

```python
if sys.platform == 'win32':
    import site
    python_dir = os.path.dirname(os.path.abspath(sys.executable))
    site_packages = os.path.join(python_dir, 'Lib', 'site-packages')
    if os.path.isdir(site_packages):
        site.addsitedir(site_packages)  # Process .pth files

    if sys.version_info >= (3, 8) and hasattr(os, 'add_dll_directory'):
        # Register DLL directories for Python 3.8+
        for dll_dir in [os.path.join(site_packages, 'wx'),
                        os.path.join(site_packages, 'pywin32_system32'),
                        python_dir]:
            if os.path.isdir(dll_dir):
                os.add_dll_directory(dll_dir)
```

## Windows Exit/Shutdown Behavior

wxPython applications on Windows require special handling for clean shutdown, particularly when launched from a console vs from the Start Menu.

### python.exe vs pythonw.exe

| Executable | Subsystem | Console | Use Case |
|------------|-----------|---------|----------|
| `python.exe` | `IMAGE_SUBSYSTEM_WINDOWS_CUI` | Attached | Command line, debugging |
| `pythonw.exe` | `IMAGE_SUBSYSTEM_WINDOWS_GUI` | None | Start Menu, shortcuts |

When running with `python.exe`, the app inherits a console window. This creates complications during shutdown because:
1. The console has its own close handler that may conflict with wxPython's event loop
2. Writing to stdout/stderr after console cleanup causes access violations

### SetConsoleCtrlHandler - Don't Use It

**Important:** Do NOT use `SetConsoleCtrlHandler` in wxPython applications.

According to [Microsoft documentation](https://learn.microsoft.com/en-us/windows/console/setconsolectrlhandler):
> If a console application loads the gdi32.dll or user32.dll library, the HandlerRoutine function [...] isn't called for the CTRL_LOGOFF_EVENT and CTRL_SHUTDOWN_EVENT events.

wxPython loads both libraries, so `SetConsoleCtrlHandler` won't receive shutdown events and can cause zombie processes.

**Instead, use:**
- `wx.EVT_CLOSE` - Window close event
- `wx.EVT_END_SESSION` - System shutdown event (if needed)
- `wx.App.OnExit()` - Application cleanup

### Proper Shutdown Sequence

The shutdown must:
1. **Destroy the TaskBarIcon** - `RemoveIcon()` alone is not sufficient; must call `Destroy()`
2. **Stop all timers** - Timers firing during shutdown cause crashes
3. **Call ExitMainLoop()** - Force the event loop to exit
4. **Detach from console** - Call `FreeConsole()` and redirect stderr to `os.devnull`

See `taskcoachlib/application/application.py` `quitApplication()` method for the implementation.

### Power Management Events

Windows power events (suspend/resume) are handled using native wxPython events:
- `wx.EVT_POWER_SUSPENDED`
- `wx.EVT_POWER_RESUME`

Do NOT use WNDPROC subclassing or `ctypes` to handle `WM_POWERBROADCAST` - this can cause crashes during shutdown.

See `taskcoachlib/powermgt/win32.py` for the implementation.

## Testing in VMs

**32-bit vs 64-bit Windows:** Check `System Information > System Type`:
- "X86-based PC" = 32-bit Windows (32-bit builds currently disabled, see above)
- "x64-based PC" = 64-bit Windows (use x64 build)

**Common issue:** QEMU/KVM VMs may have 32-bit Windows installed even with 64-bit CPU passthrough. 64-bit apps fail with "not compatible with the version of Windows" error. Solution: reinstall with 64-bit Windows ISO, or reactivate 32-bit builds in the workflow.

**Windows 10 testing:** Installs without product key (watermark only, fully functional).
