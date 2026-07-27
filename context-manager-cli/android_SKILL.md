---
name: android-troubleshoot
description: >
  Use for ANY Android development problem: Gradle/build failures, ADB/device issues,
  runtime crashes (NPE, OOM, ANR), ProGuard/R8, Manifest conflicts, emulator problems,
  signing errors, layout inflation, or any Logcat/Android Studio error. Trigger even if
  the user hasn't pasted an error yet. Always pass project_dir when the workspace is known.
---

# Android Troubleshoot — Routing Layer

## Step 1 — Call the tool

ANDROID_TROUBLESHOOT(error="<paste error>", project_dir="<workspace root>")

Optional context hint: build | runtime | adb | emulator | proguard | manifest | signing

## Step 2 — Read ONE reference file only if deeper guidance is needed

Error matches Gradle/AGP/deps/ProGuard/R8/Manifest  ->  references/build.md
Error matches NPE/OOM/ANR/ClassNotFound/Inflate      ->  references/runtime.md
Error matches ADB/device/APK install                 ->  references/adb.md
Error matches emulator start/slow/acceleration        ->  references/emulator.md
Error matches keystore/signing/jks                   ->  references/signing.md

Load only the one matching file. Do not preload others.
Each file is under 120 lines (~350 tokens) for 4k-8k context on Mac M1 Pro.
