# Installing Task Coach on Windows

## Download

Download the installer from the [latest release](https://github.com/taskcoach/taskcoach/releases):

- **Installer**: `TaskCoach-<version>-windows-x64-setup.exe` - Standard installation
- **Portable**: `TaskCoach-<version>-windows-x64-portable.zip` - No installation required

Where `<version>` is the release version (e.g., `2.0.1.20`).

## Security Warning

When you run the installer, Windows SmartScreen will show a security warning because the app is not signed with a Microsoft certificate. This is normal for open-source software that doesn't pay for code signing.

### Video Walkthrough

![Windows SmartScreen bypass walkthrough](docs/images/MS%20Windows%20Install%20-%20Security%20Warning%20-%20Screen%20Recording.gif)

### Step 1: Click "More info"

![Windows SmartScreen initial warning](docs/images/MS%20Windows%20Install%20-%20Security%20Warning%20-%20Screenshot%201.png)

Windows shows "Windows protected your PC" with only a "Don't run" button visible.

### Step 2: Click "Run anyway"

![Windows SmartScreen with Run anyway option](docs/images/MS%20Windows%20Install%20-%20Security%20Warning%20-%20Screenshot%202.png)

After clicking "More info", Windows shows the app name and publisher, and reveals the "Run anyway" button. Click it to proceed with installation.

## Installation

After accepting the security warning, follow the installer prompts:

1. Choose installation directory (default: `C:\Program Files\TaskCoach`)
2. Choose Start Menu folder
3. Optionally create a desktop shortcut
4. Click Install

## Portable Version

For the portable version:

1. Extract the `.zip` to any folder
2. Run `TaskCoach.bat` from the extracted folder (or `TaskCoach.vbs` for silent launch without a console window)
3. Your data is stored in the same folder, making it easy to move between computers

## Launching Task Coach

After installation, launch Task Coach from:

- Start Menu → Task Coach
- Desktop shortcut (if created)
- Search for "Task Coach" in the Start Menu

## Uninstalling

To uninstall Task Coach:

1. Open Settings → Apps → Installed apps
2. Find "Task Coach" in the list
3. Click the three dots menu and select "Uninstall"

Or use the uninstaller in Start Menu → Task Coach → Uninstall.

## Troubleshooting

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

## Why the Security Warning?

Task Coach is open-source software distributed without a paid code signing certificate. Microsoft charges hundreds of dollars per year for Extended Validation (EV) certificates, which is impractical for volunteer-maintained projects.

If you want to verify your download:

- **Check the SHA256 hash** - Compare the hash on the [release page](https://github.com/taskcoach/taskcoach/releases) with your downloaded file using `certutil -hashfile <filename> SHA256`
- **Review the source code** - The complete source is available on [GitHub](https://github.com/taskcoach/taskcoach)
- **Scan the file** - Upload to [VirusTotal](https://www.virustotal.com) or use your antivirus software
