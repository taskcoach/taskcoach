# Installing Task Coach on macOS

## Download

Download the DMG for your Mac from the [latest release](https://github.com/taskcoach/taskcoach/releases):

- **Apple Silicon** (M1/M2/M3/M4): `TaskCoach-<version>-macos-arm64.dmg`
- **Intel**: `TaskCoach-<version>-macos-intel.dmg`

Where `<version>` is the release version (e.g., `2.0.2.0`).

Not sure which Mac you have? Click the Apple menu → "About This Mac". Look for "Chip" (Apple Silicon) or "Processor" (Intel).

## Installation

1. Open the downloaded `.dmg` file
2. Drag "Task Coach" to the "Applications" folder
3. Eject the DMG (drag to trash or right-click → Eject)

## Security Warning

On first launch, macOS will block the app because it's not notarized by Apple. This is normal for open-source software - Apple charges $99/year for a developer account required for notarization.

### Video Walkthrough

![macOS Gatekeeper bypass walkthrough](docs/images/macOS%20-%20Security%20Warning%20-%20Screen%20Recording.gif)

### Step 1: See the initial warning

![macOS cannot open warning](docs/images/macOS%20-%20Security%20Warning%201.png)

When you first try to open Task Coach, macOS shows: "Task Coach cannot be opened because it is from an unidentified developer." Click **OK**.

### Step 2: Open Privacy & Security settings

![Privacy & Security settings](docs/images/macOS%20-%20Security%20Warning%202.png)

1. Open **System Settings** (from Apple menu or Spotlight)
2. Click **Privacy & Security** in the sidebar
3. Scroll down to the **Security** section
4. You'll see: "Task Coach was blocked from use because it is not from an identified developer"
5. Click **Open Anyway**

### Step 3: Confirm opening

![Final confirmation dialog](docs/images/macOS%20-%20Security%20Warning%203.png)

macOS shows a final confirmation: "macOS cannot verify the developer of Task Coach. Are you sure you want to open it?"

Click **Open** to launch Task Coach.

After this one-time approval, Task Coach will open normally in the future.

## Launching Task Coach

After the initial setup, launch Task Coach from:

- Applications folder
- Launchpad
- Spotlight (Cmd+Space, type "Task Coach")
- Dock (if you added it)

## Uninstalling

To uninstall Task Coach:

1. Quit Task Coach if it's running
2. Open Applications folder
3. Drag "Task Coach" to the Trash
4. Empty Trash

Your task files (`.tsk`) are stored separately and won't be deleted.

## Troubleshooting

### "Task Coach is damaged and can't be opened"

This can happen if macOS quarantine flags get corrupted. Fix it by running this in Terminal:

```bash
xattr -cr /Applications/Task\ Coach.app
```

Then try opening again.

### App won't open after security approval

Try these steps:

1. Move Task Coach out of Applications, then back in
2. Restart your Mac
3. Re-download the DMG and reinstall

### Wrong architecture (Intel app on Apple Silicon)

If you accidentally installed the Intel version on an Apple Silicon Mac, it may work via Rosetta 2, but you'll get better performance with the native arm64 version. Download the correct DMG and reinstall.

## Why the Security Warning?

Task Coach is open-source software that isn't notarized with Apple. Notarization requires:

1. A paid Apple Developer account ($99/year)
2. Submitting the app to Apple's automated security checks

This is impractical for volunteer-maintained open-source projects.

If you want to verify your download:

- **Check the SHA256 hash** - Compare the hash on the [release page](https://github.com/taskcoach/taskcoach/releases) with your downloaded file using `shasum -a 256 <filename>` in Terminal
- **Review the source code** - The complete source is available on [GitHub](https://github.com/taskcoach/taskcoach)
