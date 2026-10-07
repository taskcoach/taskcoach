# Installing Task Coach on Linux

## Table of Contents

- [Download](#download)
- [Debian, Ubuntu and Linux Mint](#debian-ubuntu-and-linux-mint)
- [Fedora](#fedora)
- [Arch Linux and Manjaro](#arch-linux-and-manjaro)
- [AppImage (any Linux)](#appimage-any-linux)
- [Flatpak (any Linux)](#flatpak-any-linux)
- [Launching Task Coach](#launching-task-coach)
- [Tray Icon](#tray-icon)

## Download

Download the package for your system from the
[latest release](https://github.com/taskcoach/taskcoach/releases):

| System | Package |
|--------|---------|
| Debian 12 (Bookworm) | `taskcoach_<version>_debian-12-bookworm.deb` |
| Debian 13 (Trixie) | `taskcoach_<version>_debian-13-trixie.deb` |
| Ubuntu 22.04 (Jammy), Linux Mint 21 | `taskcoach_<version>_ubuntu-22.04-jammy.deb` |
| Ubuntu 24.04 (Noble), Linux Mint 22 | `taskcoach_<version>_ubuntu-24.04-noble.deb` |
| Fedora 43 | `taskcoach-<version>-fedora43.rpm` |
| Arch Linux, Manjaro | `taskcoach-<version>-arch.pkg.tar.zst` |
| Any Linux (x86_64) | `TaskCoach-<version>-x86_64.AppImage` |
| Any Linux with Flatpak | `TaskCoach-<version>-x86_64.flatpak` |

Where `<version>` is the release version (e.g., `2.0.3.1`). The
commands below download into `~/Downloads`.

## Debian, Ubuntu and Linux Mint

Use the `.deb` of your release; Linux Mint uses Ubuntu's (Mint 22 is
based on Ubuntu 24.04, Mint 21 on 22.04). For Debian 13:

```bash
cd ~/Downloads
wget https://github.com/taskcoach/taskcoach/releases/latest/download/taskcoach_<version>_debian-13-trixie.deb
sudo apt install ./taskcoach_<version>_debian-13-trixie.deb
```

`apt` installs the dependencies too. To uninstall:

```bash
sudo apt remove taskcoach
sudo apt autoremove  # optional: remove unused dependencies
```

## Fedora

```bash
cd ~/Downloads
wget https://github.com/taskcoach/taskcoach/releases/latest/download/taskcoach-<version>-fedora43.rpm
sudo dnf install ./taskcoach-<version>-fedora43.rpm
```

To uninstall:

```bash
sudo dnf remove taskcoach
sudo dnf autoremove  # optional: remove unused dependencies
```

## Arch Linux and Manjaro

```bash
cd ~/Downloads
wget https://github.com/taskcoach/taskcoach/releases/latest/download/taskcoach-<version>-arch.pkg.tar.zst
sudo pacman -U taskcoach-<version>-arch.pkg.tar.zst
```

To uninstall:

```bash
sudo pacman -R taskcoach
sudo pacman -Qdtq | sudo pacman -Rs -  # optional: remove orphaned dependencies
```

## AppImage (any Linux)

Runs without installing:

```bash
cd ~/Downloads
wget https://github.com/taskcoach/taskcoach/releases/latest/download/TaskCoach-<version>-x86_64.AppImage
chmod +x TaskCoach-<version>-x86_64.AppImage
./TaskCoach-<version>-x86_64.AppImage
```

Or open the file from your file manager once it is executable. To
remove it, delete the file.

## Flatpak (any Linux)

A single-file Flatpak bundle. It needs `flatpak` installed; the first
install pulls the GNOME runtime from Flathub.

```bash
cd ~/Downloads
wget https://github.com/taskcoach/taskcoach/releases/latest/download/TaskCoach-<version>-x86_64.flatpak
flatpak install ./TaskCoach-<version>-x86_64.flatpak
flatpak run io.github.taskcoach.TaskCoach
```

To uninstall:

```bash
flatpak uninstall io.github.taskcoach.TaskCoach
```

## Launching Task Coach

Once installed, Task Coach is in your applications menu (Office >
Task Coach). From a terminal, the command is `taskcoach.py`; for the
Flatpak, `flatpak run io.github.taskcoach.TaskCoach`.

## Tray Icon

Installed from a package or the Flatpak, Task Coach shows an icon in
the system tray on every desktop (KDE, XFCE, MATE, LXQt, LXDE,
Cinnamon), on X11 and Wayland: the packages install what it needs,
and the Flatpak brings its own. The AppImage shows none where the
desktop needs AppIndicator for it (GNOME, KDE on Wayland).

GNOME Shell has no tray of its own: install the
[AppIndicator Support](https://extensions.gnome.org/extension/615/appindicator-support/)
extension to see the icon. Ubuntu has it already.
