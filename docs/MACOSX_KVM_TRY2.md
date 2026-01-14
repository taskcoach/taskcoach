# macOS VM Setup with OSX-KVM (Try 2)

**Status:** Confirmed working (2026-01-13)

Fresh attempt following official OSX-KVM documentation exactly.

**Key differences from Try 1:**
- Use `./OpenCore-Boot.sh` script directly (not libvirt)
- Use Ventura (13) instead of Sonoma - more stable, no cryptex issues
- Keep all files in `~/OSX-KVM` directory
- Only move to libvirt after successful installation

Reference: https://github.com/kholia/OSX-KVM

---

## 1. Clean up previous attempt

```bash
# Stop and remove old VM
sudo virsh destroy macos-sonoma 2>/dev/null
sudo virsh undefine macos-sonoma 2>/dev/null

# Remove old disk images
sudo rm -f /var/lib/libvirt/images/macos-sonoma.qcow2
sudo rm -f /var/lib/libvirt/images/OpenCore.qcow2
sudo rm -f /var/lib/libvirt/images/BaseSystem.img
sudo rm -f /var/lib/libvirt/images/OVMF_*.fd

# Remove old OSX-KVM clone
rm -rf ~/OSX-KVM

echo "=== Cleanup complete ==="
```

## 2. Install dependencies

```bash
sudo apt install -y qemu-system-x86 git dmg2img virt-manager
```

## 3. Clone fresh OSX-KVM

```bash
cd ~
git clone --depth 1 --recursive https://github.com/kholia/OSX-KVM.git
cd ~/OSX-KVM
```

## 4. Configure KVM MSR handling

```bash
# Enable MSR ignore (required for macOS)
echo 1 | sudo tee /sys/module/kvm/parameters/ignore_msrs

# Make permanent (Intel CPU)
sudo cp ~/OSX-KVM/kvm.conf /etc/modprobe.d/kvm.conf

# Reload KVM module
sudo modprobe -r kvm_intel 2>/dev/null
sudo modprobe kvm_intel

# Verify
cat /sys/module/kvm/parameters/ignore_msrs
# Should show: Y
```

## 5. Add user to KVM group

```bash
sudo usermod -aG kvm $(whoami)
newgrp kvm
```

## 6. Download macOS Ventura

Reference: https://en.wikipedia.org/wiki/MacOS_version_history#Releases

```bash
cd ~/OSX-KVM
./fetch-macOS-v2.py
# Select option 6 for Ventura (13)
```

## 7. Convert DMG to IMG

```bash
cd ~/OSX-KVM
dmg2img -i BaseSystem.dmg BaseSystem.img
```

## 8. Create virtual disk

```bash
cd ~/OSX-KVM
qemu-img create -f qcow2 mac_hdd_ng.img 128G
```

## 9. Run the installer

```bash
cd ~/OSX-KVM
./OpenCore-Boot.sh
```

A QEMU window will open with OpenCore boot menu.

### Install macOS:

1. Select **macOS Base System** from OpenCore menu
2. Wait for Recovery to load (can take a few minutes)
3. Open **Disk Utility**
4. **View > Show All Devices**
5. Select the QEMU HARDDISK (~128GB), click **Erase**:
   - Name: `Mac HD`
   - Format: `APFS`
   - Scheme: `GUID Partition Map`
6. Click **Erase**, then **Done**
7. Close Disk Utility
8. Select **Install macOS Ventura**
9. Follow the installer prompts
10. VM will reboot several times - each time select **macOS Installer** or **Mac HD** from OpenCore

## 10. First boot after install

After installation completes:

1. Select **Mac HD** from OpenCore menu
2. Complete the macOS setup wizard
3. You should reach the desktop

## 11. Move to libvirt/virt-manager

Only after successful installation via OpenCore-Boot.sh:

```bash
cd ~/OSX-KVM

# Remove old VM definitions from Try 1
sudo virsh undefine macos-sonoma 2>/dev/null
sudo virsh undefine macOS 2>/dev/null

# Copy files to standard libvirt location
sudo cp mac_hdd_ng.img /var/lib/libvirt/images/macos-ventura.qcow2
sudo cp OpenCore/OpenCore.qcow2 /var/lib/libvirt/images/
sudo cp OVMF_CODE.fd /var/lib/libvirt/images/
sudo cp OVMF_VARS-1920x1080.fd /var/lib/libvirt/images/OVMF_VARS.fd
sudo cp BaseSystem.img /var/lib/libvirt/images/

# Create libvirt XML config with new UUID
sed "s/CHANGEME/libvirt\/images/g" macOS-libvirt-Catalina.xml > macos-ventura.xml
sed -i "s|/home/libvirt/images/OSX-KVM|/var/lib/libvirt/images|g" macos-ventura.xml
sed -i "s|mac_hdd_ng.img|macos-ventura.qcow2|g" macos-ventura.xml
sed -i "s|OpenCore/OpenCore.qcow2|OpenCore.qcow2|g" macos-ventura.xml
sed -i "s|<name>macOS</name>|<name>macos-ventura</name>|g" macos-ventura.xml
sed -i "s|<title>macOS</title>|<title>macos-ventura</title>|g" macos-ventura.xml
sed -i "s|<uuid>.*</uuid>|<uuid>$(uuidgen)</uuid>|g" macos-ventura.xml

# Validate and define VM
virt-xml-validate macos-ventura.xml
sudo virsh define macos-ventura.xml

echo "=== Done. Open virt-manager and start macos-ventura ==="
```

## 12. Install Firefox (recommended)

Safari has rendering issues in VMs without GPU acceleration. Install Firefox instead.

Since copy/paste doesn't work, use xdotool from the Linux host to type into the VM:

1. Open Safari in the macOS VM
2. Run this script from Linux terminal
3. Click on the VM window to focus it

```bash
sleep 5
xdotool type --delay 50 "https://download.mozilla.org/?product=firefox-latest&os=osx&lang=en-US"
sleep 1
xdotool key Return
```

Then drag Firefox to Applications.

## 13. Download and install Task Coach

1. Open Firefox in the macOS VM
2. Run this script from Linux terminal
3. Click on the VM window to focus it

```bash
sleep 5
xdotool type --delay 50 "https://github.com/taskcoach/taskcoach/releases"
sleep 1
xdotool key Return
```

Download the DMG for your architecture (x86_64 for Intel, arm64 for Apple Silicon).
Open the DMG and drag Task Coach to Applications.

