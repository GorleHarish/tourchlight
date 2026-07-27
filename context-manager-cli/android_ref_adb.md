# Android ADB Reference — Device, Logcat, APK Install
# Load when: ADB offline, device not found, unauthorized, APK install failed.
# ~200 tokens. Do NOT load other reference files in the same turn.

## Device not found / offline
adb kill-server && adb start-server
adb devices -l

# If "unauthorized" -> revoke USB debugging on device -> replug -> re-authorize
# If "offline"      -> unplug/replug, different USB cable (data, not charge-only)
# Developer Options -> USB Debugging must be ON
# macOS: System Preferences -> Privacy -> Full Disk Access -> add adb

## APK install failures
# INSTALL_FAILED_UPDATE_INCOMPATIBLE  -> adb uninstall com.your.package
# INSTALL_FAILED_VERSION_DOWNGRADE    -> uninstall or bump versionCode
# INSTALL_FAILED_INSUFFICIENT_STORAGE -> free device storage
# INSTALL_PARSE_FAILED_NO_CERTIFICATES -> use debug build: ./gradlew assembleDebug
# INSTALL_FAILED_CPU_ABI_INCOMPATIBLE  -> build universal APK or add correct ABI

## Essential logcat commands
adb logcat -c                                      # clear buffer
adb logcat *:E                                     # errors only
adb logcat -s "YourTag"                            # filter by tag
adb logcat --pid=$(adb shell pidof -s com.pkg)     # filter by app
adb logcat -d > crash.txt                          # dump to file

## Other useful commands
adb install -r app-debug.apk                       # reinstall keeping data
adb uninstall com.your.package
adb shell am force-stop com.pkg
adb shell am start -n com.pkg/.MainActivity
adb shell dumpsys activity                         # activity back-stack
adb reverse tcp:8080 tcp:8080                      # proxy localhost to device

## Wireless debugging (Android 11+)
# Settings -> Developer Options -> Wireless Debugging -> Pair device with code
adb pair <ip>:<port>
adb connect <ip>:<port>
