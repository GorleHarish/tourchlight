# Android Emulator Reference — Setup, Acceleration, Performance
# Load when: emulator won't start, HAXM error, KVM disabled, slow/laggy emulator.
# ~200 tokens. Do NOT load other reference files in the same turn.

## Emulator won't start — by platform

# macOS (Apple Silicon M1/M2/M3)
# -> Use arm64-v8a system images ONLY in AVD Manager
# -> Do NOT use x86/x86_64 images — they require Rosetta and are slower
# -> Android Studio -> SDK Manager -> System Images -> ARM 64 v8a

# Windows
# -> Enable VT-x (Intel) or AMD-V in BIOS/UEFI
# -> Use Hyper-V OR Intel HAXM — never both simultaneously
# -> SDK Manager -> SDK Tools -> Intel x86 Emulator Accelerator (HAXM)

# Linux
sudo apt install qemu-kvm libvirt-daemon-system
sudo adduser $USER kvm
# Log out and log back in, then verify:
kvm-ok

## Emulator slow / laggy
# 1. AVD Manager -> Edit -> Graphics -> Hardware GLES 2.0  (not Software)
# 2. On Intel/AMD: use x86_64 system images (10-30x faster than ARM)
# 3. Allocate >=2 GB RAM in AVD settings
# 4. Enable snapshots — saves ~25s off each boot
# 5. Disable unused hardware (camera, sensors) in AVD Advanced settings

## Cold boot (when snapshot is corrupted)
# AVD Manager -> dropdown arrow -> Cold Boot Now

## Useful emulator flags
emulator -avd Pixel_6_API_33 -verbose           # startup diagnostics
emulator -avd Pixel_6_API_33 -no-snapshot-load  # force cold boot
emulator -avd Pixel_6_API_33 -gpu host          # force GPU acceleration

## Extended controls (in running emulator)
# Click (...) menu to simulate:
# GPS location, battery level, network speed, incoming calls, fingerprint
