# Task Coach - Your friendly task manager

![Task Coach](icon-ideas/splash-modernize/splash_new3a.jpg)

Task Coach is a free/libre/open task manager for keeping track of projects and todo lists.

It's over 20 years old, and development was stagnant in recent years. Here, the project is continued again and has been updated to Python3!

## Screenshots

![Task Coach main window with task list and editors](docs/images/App%20Screenshot%201.png)

![Task Coach with Task Edit Tabbed Window](docs/images/App%20Screenshot%202.png)

## Install

Download the package for your system from the [latest release](https://github.com/taskcoach/taskcoach/releases):

| Platform | Package |
|----------|---------|
| [Windows](#windows) | `TaskCoach-2.0.3.1-windows-x64-setup.exe` |
| [Windows (portable)](#windows) | `TaskCoach-2.0.3.1-windows-x64-portable.zip` |
| [macOS (Apple Silicon)](#macos) | `TaskCoach-2.0.3.1-macos-arm64.dmg` |
| [macOS (Intel)](#macos) | `TaskCoach-2.0.3.1-macos-intel.dmg` |
| [Debian 12 (Bookworm)](#linux) | `taskcoach_2.0.3.1_debian-12-bookworm.deb` |
| [Debian 13 (Trixie)](#linux) | `taskcoach_2.0.3.1_debian-13-trixie.deb` |
| [Ubuntu 22.04 (Jammy), Linux Mint 21](#linux) | `taskcoach_2.0.3.1_ubuntu-22.04-jammy.deb` |
| [Ubuntu 24.04 (Noble), Linux Mint 22](#linux) | `taskcoach_2.0.3.1_ubuntu-24.04-noble.deb` |
| [Fedora 43](#linux) | `taskcoach-2.0.3.1-fedora43.rpm` |
| [Arch Linux / Manjaro](#linux) | `taskcoach-2.0.3.1-arch.pkg.tar.zst` |
| [Any Linux (x86_64)](#linux) | `TaskCoach-2.0.3.1-x86_64.AppImage` |
| [Flatpak (any Linux)](README_INSTALL_LINUX.md#flatpak-any-linux) | `TaskCoach-2.0.3.1-x86_64.flatpak` |

### Windows

Run the installer. Windows warns that the app is not signed with a Microsoft certificate: click **More info**, then **Run anyway**.

For the portable version, extract the `.zip` and run `TaskCoach.bat`.

Step by step, with screenshots: [README_INSTALL_WINDOWS.md](README_INSTALL_WINDOWS.md).

### macOS

Open the `.dmg` (Apple Silicon for M1 and later, Intel for older Macs) and drag Task Coach to Applications. On first launch macOS blocks it because it is not notarized: open **System Settings → Privacy & Security** and click **Open Anyway** next to the Task Coach message.

Step by step, with screenshots: [README_INSTALL_MACOS.md](README_INSTALL_MACOS.md).

### Linux

Install the downloaded package:

```bash
sudo apt install ./taskcoach_2.0.3.1_debian-13-trixie.deb   # Debian, Ubuntu, Linux Mint
sudo dnf install ./taskcoach-2.0.3.1-fedora43.rpm           # Fedora
sudo pacman -U taskcoach-2.0.3.1-arch.pkg.tar.zst           # Arch Linux, Manjaro
```

Or make the AppImage executable (`chmod +x TaskCoach-2.0.3.1-x86_64.AppImage`) and open it: it runs without installing.

Uninstalling, the Flatpak, and the tray icon on GNOME: [README_INSTALL_LINUX.md](README_INSTALL_LINUX.md).

## Support

- Report bugs or request features at GitHub Issues: https://github.com/taskcoach/taskcoach/issues
- Ask for help or have other open discussion at https://github.com/orgs/taskcoach/discussions

## License

Task Coach is free software licensed under the [GNU General Public License v3](https://www.gnu.org/licenses/gpl-3.0.html).

Copyright (C) 2004-2026 Task Coach developers

## Developers

Running from source, tests, building the packages and the design documents: [developer documentation](docs/README.md).
