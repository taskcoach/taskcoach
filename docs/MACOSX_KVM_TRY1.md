# macOS VM Setup with OSX-KVM

This document covers setting up a macOS virtual machine on Linux using OSX-KVM for testing Task Coach.

## 1. Install dependencies

Required:
```bash
sudo apt install qemu-system-x86
sudo apt install virt-manager
sudo apt install git
sudo apt install wget
sudo apt install p7zip-full
sudo apt install dmg2img
```

Optional (specified in the official OSX-KVM instructions, but not required for this install):
```bash
sudo apt install qemu-system
sudo apt install uml-utilities
sudo apt install libguestfs-tools
sudo apt install make
```

## 2. Clone the repo

```bash
cd ~/Downloads
git clone --depth 1 --recursive https://github.com/kholia/OSX-KVM.git
```

## 3. Fetch macOS installer and convert

Reference: https://en.wikipedia.org/wiki/MacOS_version_history

```bash
cd ~/Downloads/OSX-KVM
./fetch-macOS-v2.py
# Select 7 for Sonoma (14)
dmg2img -i BaseSystem.dmg BaseSystem.img
```

## 4. Set up disk images

```bash
# Create the main disk
sudo qemu-img create -f qcow2 /var/lib/libvirt/images/macos-sonoma.qcow2 128G

# Copy installer and support files
sudo cp ~/Downloads/OSX-KVM/BaseSystem.img /var/lib/libvirt/images/
sudo cp ~/Downloads/OSX-KVM/OpenCore/OpenCore.qcow2 /var/lib/libvirt/images/
sudo cp ~/Downloads/OSX-KVM/OVMF_CODE.fd /var/lib/libvirt/images/
sudo cp ~/Downloads/OSX-KVM/OVMF_VARS-1920x1080.fd /var/lib/libvirt/images/OVMF_VARS.fd
```

## 4a. Update CryptexFixup for Sonoma

The OSX-KVM repository ships with CryptexFixup 1.0.1 which does not support Sonoma. Update to 1.0.2+ (1.0.2 added macOS 14 support):

```bash
# Download latest CryptexFixup
cd ~/Downloads
curl -L -o CryptexFixup-1.0.5-RELEASE.zip https://github.com/acidanthera/CryptexFixup/releases/download/1.0.5/CryptexFixup-1.0.5-RELEASE.zip
unzip CryptexFixup-1.0.5-RELEASE.zip

# Mount OpenCore image
sudo modprobe nbd max_part=8
sudo qemu-nbd --connect=/dev/nbd0 /var/lib/libvirt/images/OpenCore.qcow2
sudo mkdir -p /mnt/opencore
sudo mount /dev/nbd0p1 /mnt/opencore

# Replace CryptexFixup
sudo rm -rf /mnt/opencore/EFI/OC/Kexts/CryptexFixup.kext
sudo cp -r ~/Downloads/CryptexFixup.kext /mnt/opencore/EFI/OC/Kexts/

# Verify new version
cat /mnt/opencore/EFI/OC/Kexts/CryptexFixup.kext/Contents/Info.plist | grep -A1 CFBundleVersion

# Unmount
sudo umount /mnt/opencore
sudo qemu-nbd --disconnect /dev/nbd0
```

## 5. Create and edit libvirt XML config

**Option A: Use the pre-made XML file**

A ready-to-use XML configuration is provided in this repository: [macos-sonoma.xml](macos-sonoma.xml)

```bash
cp /path/to/taskcoach/docs/macos-sonoma.xml ~/Downloads/OSX-KVM/
```

**Option B: Generate from OSX-KVM template**

```bash
cd ~/Downloads/OSX-KVM
rm -f macos-sonoma.xml
sed "s|/home/CHANGEME/OSX-KVM|/var/lib/libvirt/images|g" macOS-libvirt-Catalina.xml > macos-sonoma.xml
sed -i "s|<name>macOS</name>|<name>macos-sonoma</name>|g" macos-sonoma.xml
sed -i "s|<title>macOS</title>|<title>macos-sonoma</title>|g" macos-sonoma.xml
sed -i "s|mac_hdd_ng.img|macos-sonoma.qcow2|g" macos-sonoma.xml
sed -i "s|OpenCore/OpenCore.qcow2|OpenCore.qcow2|g" macos-sonoma.xml
sed -i "s|<vcpu placement='static'>4</vcpu>|<vcpu placement='static'>12</vcpu>|g" macos-sonoma.xml
sed -i "s|<memory unit='KiB'>4194304</memory>|<memory unit='KiB'>8388608</memory>|g" macos-sonoma.xml
sed -i "s|<currentMemory unit='KiB'>4194304</currentMemory>|<currentMemory unit='KiB'>8388608</currentMemory>|g" macos-sonoma.xml
sed -i 's|Penryn,kvm=on,vendor=GenuineIntel,+invtsc,vmware-cpuid-freq=on,+ssse3,+sse4.2,+popcnt,+avx,+aes,+xsave,+xsaveopt,check|Penryn,kvm=on,vendor=GenuineIntel,+invtsc,vmware-cpuid-freq=on,+ssse3,+sse4.2,+popcnt,+avx,+avx2,+aes,+xsave,+xsaveopt,+fma,+bmi1,+bmi2,check|g' macos-sonoma.xml
sed -i 's|interface type="bridge"|interface type="network"|g' macos-sonoma.xml
sed -i 's|source bridge="virbr0"|source network="default"|g' macos-sonoma.xml
```

Memory is set to 8GB (8388608 KiB). Minimum for Sonoma is 4GB, but 8GB is more comfortable for GUI testing.

CPU is updated with `+avx2,+fma,+bmi1,+bmi2` which are required for macOS Sonoma.

Network is changed to use libvirt's default NAT network.

Review the file to verify the changes:

```bash
nano ~/Downloads/OSX-KVM/macos-sonoma.xml
```

Validate the XML:

```bash
virt-xml-validate ~/Downloads/OSX-KVM/macos-sonoma.xml
```

## 6. Import and launch the VM

Copy the XML to libvirt and register the VM:

```bash
sudo cp ~/Downloads/OSX-KVM/macos-sonoma.xml /etc/libvirt/qemu/
sudo virsh define /etc/libvirt/qemu/macos-sonoma.xml
```

Then open virt-manager and start the `macos-sonoma` VM.

## 7. Install macOS

### Prepare the disk

1. At OpenCore boot screen, select **macOS Base System**
2. At the Recovery menu, select **Disk Utility**
3. In Disk Utility menu bar: **View → Show All Devices**
4. Select the QEMU HARDDISK (~128GB), not a partition under it
5. Click **Erase**:
   - Name: `Macintosh HD`
   - Format: `APFS`
   - Scheme: `GUID Partition Map`
6. Click **Erase**, then **Done**
7. Close Disk Utility (Disk Utility → Quit Disk Utility)

### Install

1. Select **Install macOS Sonoma**
2. Click **Continue**, agree to terms
3. Select **Macintosh HD** as the destination
4. Be patient — setup screens can be slow

## Post-install cleanup

Remove the installer image (no longer needed):
```bash
sudo rm /var/lib/libvirt/images/BaseSystem.img
```

## Troubleshooting

If the VM crashes early in boot, you may need the KVM MSR workaround:

```bash
sudo cp ~/Downloads/OSX-KVM/kvm.conf /etc/modprobe.d/kvm.conf
sudo modprobe -r kvm_intel
sudo modprobe kvm_intel
```

Shut down all VMs before running modprobe, or just reboot the system instead.

## Debugging boot issues

If Mac HD boot loops, boot into Recovery and open **Utilities → Terminal**. Run these from your Linux host to type commands into the VM (focus the VM window within 3 seconds).

### Test 1: Check panic logs and system info

```bash
sleep 3
xdotool type --delay 50 "ls /Volumes/"
sleep 1
xdotool key Return
sleep 3
xdotool type --delay 50 "ls '/Volumes/Mac HD/Library/Logs/DiagnosticReports/'"
sleep 1
xdotool key Return
sleep 3
xdotool type --delay 50 "cat '/Volumes/Mac HD/Library/Logs/DiagnosticReports/'*.panic"
sleep 1
xdotool key Return
sleep 3
xdotool type --delay 50 "log show --predicate 'process == \"kernel\"' --last 5m | tail -100"
sleep 1
xdotool key Return
sleep 5
xdotool type --delay 50 "log show --predicate 'eventMessage contains \"shutdown\"' --last 1h"
sleep 1
xdotool key Return
sleep 5
xdotool type --delay 50 "nvram -p"
sleep 1
xdotool key Return
sleep 3
xdotool type --delay 50 "system_profiler SPHardwareDataType"
sleep 1
xdotool key Return
sleep 3
xdotool type --delay 50 "sysctl -a | grep cpu"
sleep 1
xdotool key Return
sleep 3
xdotool type --delay 50 "diskutil list"
sleep 1
xdotool key Return
```

### Test 2: Check CPU configuration (run on Linux host)

Test 1 revealed the VM uses Penryn CPU which lacks AVX2. Sonoma requires AVX2.

```bash
grep -i cpu /etc/libvirt/qemu/macos-sonoma.xml
grep avx2 /proc/cpuinfo
```

Fix: Change CPU model to include AVX2 flags (already done in section 5 sed commands).

### Test 3: Verify guest sees AVX2

Boot into Recovery terminal and run from Linux host:

```bash
sleep 3
xdotool type --delay 50 "sysctl -a | grep avx"
sleep 1
xdotool key Return
```

Should show:
```
hw.optional.avx2_0: 1
hw.optional.avx1_0: 1
```

If AVX2 shows 0, the CPU flags aren't being passed through.

### Test 4: Fix Sonoma 14.4+ boot loop (SecureBootModel)

For macOS Sonoma 14.4 and later, SecureBootModel must be disabled in OpenCore's config.plist. The config is inside OpenCore.qcow2.

From Linux host (VM must be shut down):

```bash
# Install required tools
sudo apt install qemu-utils

# Load nbd module
sudo modprobe nbd max_part=8

# Connect the qcow2 image
sudo qemu-nbd --connect=/dev/nbd0 /var/lib/libvirt/images/OpenCore.qcow2

# Create mount point and mount
sudo mkdir -p /mnt/opencore
sudo mount /dev/nbd0p1 /mnt/opencore

# Set SecureBootModel to Disabled
sudo sed -i '/<key>SecureBootModel<\/key>/{ n; s/<string>.*<\/string>/<string>Disabled<\/string>/; }' /mnt/opencore/EFI/OC/config.plist

# Verify the change
grep -A1 "SecureBootModel" /mnt/opencore/EFI/OC/config.plist

# Unmount and disconnect
sudo umount /mnt/opencore
sudo qemu-nbd --disconnect /dev/nbd0
```

Or manually edit the config:

```bash
sudo nano /mnt/opencore/EFI/OC/config.plist
```

Find `SecureBootModel` and change the value on the next line to `Disabled`.

Then reset NVRAM twice from OpenCore menu and try booting Mac HD again.

### Test 5: Enable verbose kernel logging to serial console

Mount OpenCore and check config.plist boot-args:

```bash
sudo modprobe nbd max_part=8
sudo qemu-nbd --connect=/dev/nbd0 /var/lib/libvirt/images/OpenCore.qcow2
sudo mkdir -p /mnt/opencore
sudo mount /dev/nbd0p1 /mnt/opencore
grep -A1 "boot-args" /mnt/opencore/EFI/OC/config.plist
```

The boot-args should include `-v` for verbose. If not:

```bash
sudo nano /mnt/opencore/EFI/OC/config.plist
```

Find `boot-args` and ensure it contains: `-v keepsyms=1`

Unmount:
```bash
sudo umount /mnt/opencore
sudo qemu-nbd --disconnect /dev/nbd0
```

Then watch serial console while booting (VM must be shut down first):

```bash
sudo virsh start macos-sonoma
sudo virsh console macos-sonoma
```

### Test 6: Try Skylake-Client CPU model

If boot loop persists, the Penryn CPU model may be the issue. Change to Skylake-Client-noTSX-IBRS in the `qemu:commandline` section:

Edit `~/Downloads/OSX-KVM/macos-sonoma.xml`:

```bash
sed -i 's|Penryn,kvm=on,vendor=GenuineIntel,+invtsc,vmware-cpuid-freq=on,+ssse3,+sse4.2,+popcnt,+avx,+avx2,+aes,+xsave,+xsaveopt,+fma,+bmi1,+bmi2,check|Skylake-Client-noTSX-IBRS,kvm=on,vendor=GenuineIntel,+invtsc,vmware-cpuid-freq=on,+avx,+avx2,+aes,+xsave,+xsaveopt,+fma,+bmi1,+bmi2,check|g' ~/Downloads/OSX-KVM/macos-sonoma.xml
```

Redefine VM:
```bash
sudo virsh undefine macos-sonoma
sudo cp ~/Downloads/OSX-KVM/macos-sonoma.xml /etc/libvirt/qemu/
sudo virsh define /etc/libvirt/qemu/macos-sonoma.xml
```

Then try booting Mac HD again.

**Result:** Tested, no difference - still kernel panic with CryptexFixup error.

### Test 7: Enable kernel serial output

If serial console shows `HANDOFF TO XNU` then reboots with no kernel messages, add `serial=3` to boot-args:

```bash
sudo modprobe nbd max_part=8
sudo qemu-nbd --connect=/dev/nbd0 /var/lib/libvirt/images/OpenCore.qcow2
sudo mkdir -p /mnt/opencore
sudo mount /dev/nbd0p1 /mnt/opencore

# Add serial=3 to boot-args
sudo sed -i 's|<string>-v keepsyms=1|<string>-v keepsyms=1 serial=3|' /mnt/opencore/EFI/OC/config.plist

# Verify
grep -A1 "boot-args" /mnt/opencore/EFI/OC/config.plist

sudo umount /mnt/opencore
sudo qemu-nbd --disconnect /dev/nbd0
```

Then watch serial console again:
```bash
sudo virsh start macos-sonoma
sudo virsh console macos-sonoma
```

Select Mac HD in virt-manager. The kernel should now output messages to serial before crashing.

**Result:** Kernel panic - CryptexFixup disabled by Lilu, causing libSystem.B.dylib not found.

### Test 8: Fix CryptexFixup being disabled

The kernel panic shows CryptexFixup is disabled by Lilu, preventing the OS cryptex from mounting. This causes libSystem.B.dylib to be missing.

Check CryptexFixup and Lilu versions in OpenCore:

```bash
sudo modprobe nbd max_part=8
sudo qemu-nbd --connect=/dev/nbd0 /var/lib/libvirt/images/OpenCore.qcow2
sudo mkdir -p /mnt/opencore
sudo mount /dev/nbd0p1 /mnt/opencore

# List kexts
ls -la /mnt/opencore/EFI/OC/Kexts/

# Check CryptexFixup version (in Info.plist)
cat /mnt/opencore/EFI/OC/Kexts/CryptexFixup.kext/Contents/Info.plist | grep -A1 CFBundleVersion

# Check Lilu version
cat /mnt/opencore/EFI/OC/Kexts/Lilu.kext/Contents/Info.plist | grep -A1 CFBundleVersion

# Check if CryptexFixup is enabled in config.plist
grep -B5 -A10 "CryptexFixup" /mnt/opencore/EFI/OC/config.plist
```

CryptexFixup 1.0.2+ is required for Sonoma (1.0.2 added macOS 14 support). If outdated, download latest from:
- https://github.com/acidanthera/CryptexFixup/releases
- https://github.com/acidanthera/Lilu/releases

Replace the kexts:
```bash
# Backup old kexts
sudo mv /mnt/opencore/EFI/OC/Kexts/CryptexFixup.kext /mnt/opencore/EFI/OC/Kexts/CryptexFixup.kext.bak
sudo mv /mnt/opencore/EFI/OC/Kexts/Lilu.kext /mnt/opencore/EFI/OC/Kexts/Lilu.kext.bak

# Extract and copy new kexts (after downloading)
cd ~/Downloads
curl -L -o CryptexFixup-1.0.5-RELEASE.zip https://github.com/acidanthera/CryptexFixup/releases/download/1.0.5/CryptexFixup-1.0.5-RELEASE.zip
unzip CryptexFixup-1.0.5-RELEASE.zip
sudo cp -r CryptexFixup.kext /mnt/opencore/EFI/OC/Kexts/

# Verify config.plist has CryptexFixup enabled with correct MinKernel
grep -B5 -A10 "CryptexFixup" /mnt/opencore/EFI/OC/config.plist
```

In config.plist under Kernel → Add, ensure CryptexFixup entry has:
- `Enabled` = `true`
- `MinKernel` = empty or `23.0.0` (for Sonoma)
- `MaxKernel` = empty

Unmount:
```bash
sudo umount /mnt/opencore
sudo qemu-nbd --disconnect /dev/nbd0
```

Reset NVRAM from OpenCore menu and try booting Mac HD again.

### Test 9: Update Lilu and force CryptexFixup to load

**Result from Test 8:** Kernel gets further (Darwin 23.6.0 boots, AHCI disks detected) but still panics with:
```
Lilu       api: @ automatically disabling CryptexFixup (101) on an unsupported operating system
CryptexFixup      init: @ parent said we should not continue 4
...
panic: initproc failed to start -- Library not loaded: /usr/lib/libSystem.B.dylib
```

The error code 101 means Lilu is refusing to load CryptexFixup because it doesn't recognize the OS version. This is likely because:
1. Lilu version is too old to recognize macOS 14.6+
2. Boot-args are needed to force loading

**Fix: Update Lilu to latest and add force boot-args**

```bash
# Mount OpenCore
sudo modprobe nbd max_part=8
sudo qemu-nbd --disconnect /dev/nbd0 2>/dev/null; sudo qemu-nbd --connect=/dev/nbd0 /var/lib/libvirt/images/OpenCore.qcow2
sudo mkdir -p /mnt/opencore
sudo umount /mnt/opencore 2>/dev/null; sudo mount /dev/nbd0p1 /mnt/opencore

# Show current Lilu version
echo "=== Current Lilu version ===" && grep -A1 CFBundleVersion /mnt/opencore/EFI/OC/Kexts/Lilu.kext/Contents/Info.plist

# Download and install latest Lilu
cd ~/Downloads
curl -L -o Lilu-1.7.1-RELEASE.zip https://github.com/acidanthera/Lilu/releases/download/1.7.1/Lilu-1.7.1-RELEASE.zip
unzip -o Lilu-1.7.1-RELEASE.zip
sudo rm -rf /mnt/opencore/EFI/OC/Kexts/Lilu.kext.bak
sudo mv /mnt/opencore/EFI/OC/Kexts/Lilu.kext /mnt/opencore/EFI/OC/Kexts/Lilu.kext.bak
sudo cp -r Lilu.kext /mnt/opencore/EFI/OC/Kexts/

# Show new Lilu version
echo "=== New Lilu version ===" && grep -A1 CFBundleVersion /mnt/opencore/EFI/OC/Kexts/Lilu.kext/Contents/Info.plist

# Show current boot-args
echo "=== Current boot-args ===" && grep -A1 "boot-args" /mnt/opencore/EFI/OC/config.plist

# Add -liluforce and -lilubetaall to boot-args (handles both cases: with or without existing args)
sudo sed -i '/<key>boot-args<\/key>/{ n; s|<string>\([^<]*\)</string>|<string>\1 -liluforce -lilubetaall</string>|; }' /mnt/opencore/EFI/OC/config.plist

# Show updated boot-args
echo "=== Updated boot-args ===" && grep -A1 "boot-args" /mnt/opencore/EFI/OC/config.plist

# Unmount
sudo umount /mnt/opencore
sudo qemu-nbd --disconnect /dev/nbd0

echo "=== Done. Reset NVRAM twice from OpenCore menu, then boot Mac HD ==="
```

**Run the VM and watch serial console:**

```bash
# Start the VM
sudo virsh start macos-sonoma

# Connect to serial console (Ctrl+] to exit)
sudo virsh console macos-sonoma
```

In virt-manager GUI:
1. Select "Reset NVRAM" from OpenCore menu (do this twice)
2. Select "Mac HD" to boot

### Test 10: Force CryptexFixup to run with AVX2

**Result from Test 9:** Lilu now force-enabled, but CryptexFixup is skipping:
```
Lilu    config: @ force enabling due to force flag
CryptexFixup crypt_fix: @ system natively support AVX2.0, skipping
```

The cryptex grafts successfully but libSystem.B.dylib still not found. CryptexFixup detects native AVX2 and assumes the system can handle cryptexes natively - but VMs still need the fix. Force it with `-crypt_force_avx`.

```bash
# Mount OpenCore
sudo modprobe nbd max_part=8
sudo qemu-nbd --disconnect /dev/nbd0 2>/dev/null; sudo qemu-nbd --connect=/dev/nbd0 /var/lib/libvirt/images/OpenCore.qcow2
sudo mkdir -p /mnt/opencore
sudo umount /mnt/opencore 2>/dev/null; sudo mount /dev/nbd0p1 /mnt/opencore

# Show current boot-args
echo "=== Current boot-args ===" && grep -A1 "boot-args" /mnt/opencore/EFI/OC/config.plist | head -2

# Add -crypt_force_avx to boot-args
sudo sed -i 's|-liluforce -lilubetaall|-liluforce -lilubetaall -crypt_force_avx|' /mnt/opencore/EFI/OC/config.plist

# Show updated boot-args
echo "=== Updated boot-args ===" && grep -A1 "boot-args" /mnt/opencore/EFI/OC/config.plist | head -2

# Unmount
sudo umount /mnt/opencore
sudo qemu-nbd --disconnect /dev/nbd0

echo "=== Done. Boot Mac HD (no NVRAM reset needed) ==="
```

**Run the VM:**

```bash
sudo virsh start macos-sonoma
sudo virsh console macos-sonoma
```

### Test 10 Result: CryptexFixup patch not working

**Result:** CryptexFixup now forcing patch:
```
CryptexFixup crypt_fix: @ system natively support AVX2.0, but forcing AVX patch upon user request
```

But still panics with same error - cryptex grafts but libSystem.B.dylib not accessible.

**Root cause:** CryptexFixup 1.0.5 (released Sep 2023) is not compatible with this macOS 14.6 build (Nov 2025). The patch mechanism has changed in newer macOS versions.

**Options:**

1. **Try older macOS version** - macOS 14.0-14.3 or macOS 13 Ventura may work with current kexts
2. **Wait for updated CryptexFixup** - Check acidanthera/CryptexFixup for newer releases
3. **Try OpenCore Legacy Patcher (OCLP)** - May have more up-to-date patches
4. **Use different virtualization** - VMware Fusion or Parallels may have better compatibility

### Alternative: Try macOS Ventura (13) instead

macOS 13 Ventura has better hackintosh/VM support and may work with current OpenCore/kexts.

```bash
cd ~/Downloads/OSX-KVM
./fetch-macOS-v2.py
# Select option 6 for Ventura (13)
```

Then repeat the setup process with a new disk image.

