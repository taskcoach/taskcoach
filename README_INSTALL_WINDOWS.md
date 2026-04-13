# Installing Task Coach on Windows

## Table of Contents

- [Download](#download)
- [Security Warning](#security-warning)
- [Installation](#installation)
- [Portable Version](#portable-version)
- [Launching Task Coach](#launching-task-coach)
- [Troubleshooting Logging](#troubleshooting-logging)
- [Uninstalling](#uninstalling)
- [Troubleshooting](#troubleshooting)
- [Why the Security Warning?](#why-the-security-warning)

## <a id="download"></a>Download

Download the installer from the [latest release](https://github.com/taskcoach/taskcoach/releases):

- **Installer**: `TaskCoach-<version>-windows-x64-setup.exe` - Standard installation
- **Portable**: `TaskCoach-<version>-windows-x64-portable.zip` - No installation required

Where `<version>` is the release version (e.g., `2.0.2.11`).

## <a id="security-warning"></a>Security Warning

When you run the installer, Windows SmartScreen will show a security warning because the app is not signed with a Microsoft certificate. This is normal for open-source software that doesn't pay for code signing. See [Why the Security Warning?](#why-the-security-warning) for details.

### Video Walkthrough

![Windows SmartScreen bypass walkthrough](docs/images/MS%20Windows%20Install%20-%20Security%20Warning%20-%20Screen%20Recording.gif)

### Step 1: Click "More info"

![Windows SmartScreen initial warning](docs/images/MS%20Windows%20Install%20-%20Security%20Warning%20-%20Screenshot%201.png)

Windows shows "Windows protected your PC" with only a "Don't run" button visible.

### Step 2: Click "Run anyway"

![Windows SmartScreen with Run anyway option](docs/images/MS%20Windows%20Install%20-%20Security%20Warning%20-%20Screenshot%202.png)

After clicking "More info", Windows shows the app name and publisher, and reveals the "Run anyway" button. Click it to proceed with installation.

## <a id="installation"></a>Installation

After accepting the security warning, follow the installer prompts:

1. Choose installation directory (default: `%LOCALAPPDATA%\Programs\Task Coach`)
2. Choose Start Menu folder
3. Optionally create a desktop shortcut
4. Click Install

## <a id="portable-version"></a>Portable Version

For the portable version:

1. Extract the `.zip` to any folder
2. Run `TaskCoach.bat` from the extracted folder (or `TaskCoach.vbs` for silent launch without a console window)
3. Your data is stored in the same folder, making it easy to move between computers

## <a id="launching-task-coach"></a>Launching Task Coach

After installation, launch Task Coach from:

- Start Menu → Task Coach
- Desktop shortcut (if created)
- Search for "Task Coach" in the Start Menu

## <a id="troubleshooting-logging"></a>Troubleshooting Logging

Task Coach normally launches without a console window, so diagnostic output is not visible. To see application output, open a Command Prompt and run `TaskCoach.bat`, which keeps the console window open showing all messages, warnings, and errors.

### Installed version

```cmd
cd "%LOCALAPPDATA%\Programs\Task Coach"
TaskCoach.bat
```

### Portable version

```cmd
cd "%USERPROFILE%\Downloads\TaskCoach"
TaskCoach.bat
```

Replace the path with wherever you extracted the portable zip.

## <a id="uninstalling"></a>Uninstalling

To uninstall Task Coach:

1. Open Settings → Apps → Installed apps
2. Find "Task Coach" in the list
3. Click the three dots menu and select "Uninstall"

Or use the uninstaller in Start Menu → Task Coach → Uninstall.

## <a id="troubleshooting"></a>Troubleshooting

### "Windows protected your PC" won't go away

If you don't see the "More info" link:

1. Right-click the installer file
2. Select "Properties"
3. Check "Unblock" at the bottom of the General tab
4. Click OK and try running again

### Antivirus blocking the installer

Some antivirus software may flag the installer. This is a false positive common with Python-based applications. You can:

1. Temporarily disable your antivirus
2. Add an exception for the Task Coach installer
3. Download again if your antivirus quarantined the file

## <a id="why-the-security-warning"></a>Why the Security Warning?

Task Coach is open-source software distributed without a paid code signing certificate. Microsoft charges hundreds of dollars per year for Extended Validation (EV) certificates, which is impractical for volunteer-maintained projects.

If you want to verify your download:

- **Check the SHA256 hash** - Compare the hash on the [release page](https://github.com/taskcoach/taskcoach/releases) with your downloaded file using `certutil -hashfile <filename> SHA256`
- **Review the source code** - The complete source is available on [GitHub](https://github.com/taskcoach/taskcoach)
- **Scan the file** - Use your favorite antivirus software to scan the downloaded file
