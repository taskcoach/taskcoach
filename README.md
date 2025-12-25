# Task Coach - Your friendly task manager

Task Coach is a simple open source todo manager to keep track of personal tasks and todo lists.

## Quick Start

Download the package for your system from the [latest release](https://github.com/taskcoach/taskcoach/releases):

| Platform | Package |
|----------|---------|
| Debian 12 (Bookworm) | `taskcoach_2.0.0.75_debian-12-bookworm.deb` |
| Debian 13 (Trixie) | `taskcoach_2.0.0.75_debian-13-trixie.deb` |
| Debian Sid | `taskcoach_2.0.0.75_debian-sid.deb` |
| Ubuntu 22.04 (Jammy) | `taskcoach_2.0.0.75_ubuntu-22.04-jammy.deb` |
| Ubuntu 24.04 (Noble) | `taskcoach_2.0.0.75_ubuntu-24.04-noble.deb` |
| Linux Mint | Use Ubuntu `.deb` (Mint is Ubuntu-based) |
| Arch Linux / Manjaro | `taskcoach-2.0.0.75-arch.pkg.tar.zst` |
| Fedora 39/40 | `taskcoach-2.0.0.75-fedora39.noarch.rpm` |
| Any Linux (x86_64) | `TaskCoach-2.0.0.75-x86_64.AppImage` |

**Example: Install on Debian/Ubuntu**

```bash
cd ~/Downloads
wget https://github.com/taskcoach/taskcoach/releases/latest/download/taskcoach_2.0.0.75_debian-13-trixie.deb
sudo apt install ./taskcoach_2.0.0.75_debian-13-trixie.deb
taskcoach.py
```

Or launch from **Applications → Office → Task Coach**.

To uninstall:
```bash
sudo apt remove taskcoach
sudo apt autoremove  # optional: remove unused dependencies
```

**Example: Install on Arch Linux / Manjaro**

```bash
cd ~/Downloads
wget https://github.com/taskcoach/taskcoach/releases/latest/download/taskcoach-2.0.0.75-arch.pkg.tar.zst
sudo pacman -U taskcoach-2.0.0.75-arch.pkg.tar.zst
taskcoach.py
```

To uninstall:
```bash
sudo pacman -R taskcoach
sudo pacman -Qdtq | sudo pacman -Rs -  # optional: remove orphaned dependencies
```

**Example: Install on Fedora**

```bash
cd ~/Downloads
wget https://github.com/taskcoach/taskcoach/releases/latest/download/taskcoach-2.0.0.75-fedora40.noarch.rpm
sudo dnf install ./taskcoach-2.0.0.75-fedora40.noarch.rpm
taskcoach.py
```

To uninstall:
```bash
sudo dnf remove taskcoach
sudo dnf autoremove  # optional: remove unused dependencies
```

**Or run the AppImage (any Linux, no install needed)**

```bash
cd ~/Downloads
wget https://github.com/taskcoach/taskcoach/releases/latest/download/TaskCoach-2.0.0.75-x86_64.AppImage
chmod +x TaskCoach-2.0.0.75-x86_64.AppImage
./TaskCoach-2.0.0.75-x86_64.AppImage
```

To remove: simply delete the AppImage file.

## Running from Source

For development or if you prefer running from git:

```bash
git clone --depth 1 https://github.com/taskcoach/taskcoach.git
cd taskcoach
./setup.sh
./taskcoach-run.sh
```

See [docs/DEBIAN_BOOKWORM_SETUP.md](docs/DEBIAN_BOOKWORM_SETUP.md) for detailed setup options, troubleshooting, and platform-specific instructions.

## Testing

Quick sanity check to verify the installation:

```bash
./test_taskcoach.sh
```

This tests Python version, dependencies, module imports, and wxPython patch status.

## License

Task Coach is free software licensed under the [GNU General Public License v3](https://www.gnu.org/licenses/gpl-3.0.html).

Copyright (C) 2004-2016 Task Coach developers

## Architecture Overview

Task Coach is a desktop application developed in Python using wxPython for its GUI. It follows the Model-View-Controller pattern with three main layers:

- **Domain layer**: Classes for tasks, categories, effort, notes and other domain objects
- **GUI layer**: Viewers, controllers, dialogs, menus and other GUI components
- **Persistence layer**: Loading/saving domain objects to XML files (.tsk) and exporting to various formats

## Source Code Overview

Key packages:

| Package | Description |
|---------|-------------|
| `domain` | Domain objects (tasks, categories, effort, notes) |
| `gui` | Viewers, dialogs, and UI components |
| `command` | Undo/redo-capable user actions (Command pattern) |
| `config` | User settings and TaskCoach.ini handling |
| `persistence` | .tsk file format (XML) and export functionality |
| `i18n` | Internationalization and translations |
| `widgets` | Adapted wxPython widgets |

## Documentation

- [DEBIAN_BOOKWORM_SETUP.md](docs/DEBIAN_BOOKWORM_SETUP.md) - Detailed installation and setup
- [PACKAGING.md](docs/PACKAGING.md) - Building .deb packages
- [CRITICAL_WXPYTHON_PATCH.md](docs/CRITICAL_WXPYTHON_PATCH.md) - wxPython compatibility patch details

## Support

- GitHub Issues: https://github.com/taskcoach/taskcoach/issues
