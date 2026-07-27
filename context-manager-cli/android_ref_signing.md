# Android Signing Reference — Keystore, Certificates, Google Play
# Load when: keystore not found, signing failed, wrong password, jks error.
# ~200 tokens. Do NOT load other reference files in the same turn.

## Inspect a keystore
keytool -list -v -keystore your.keystore
keytool -list -v -keystore ~/.android/debug.keystore -alias androiddebugkey \
  -storepass android -keypass android

## Common errors
# "Keystore file not found" -> check path in signingConfigs (relative to module dir)
# "Wrong password"          -> storePassword/keyPassword are case-sensitive
# "Invalid keystore format" -> file may be corrupted; restore from backup

## Secure signing config (never commit passwords to git)
# app/build.gradle:
android {
    signingConfigs {
        release {
            storeFile     file(System.getenv("KEYSTORE_PATH") ?: localProperties["KEYSTORE_PATH"])
            storePassword System.getenv("KEYSTORE_PASS")  ?: localProperties["KEYSTORE_PASS"]
            keyAlias      System.getenv("KEY_ALIAS")      ?: localProperties["KEY_ALIAS"]
            keyPassword   System.getenv("KEY_PASS")       ?: localProperties["KEY_PASS"]
        }
    }
    buildTypes { release { signingConfig signingConfigs.release } }
}

## Generate a new debug keystore (if lost)
keytool -genkeypair -v \
  -keystore ~/.android/debug.keystore \
  -alias androiddebugkey \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -storepass android -keypass android

## Google Play App Signing (recommended)
# Enroll: Play Console -> App -> Setup -> App signing
# Google manages the release key; you upload with a separate upload key
# SHA-1/SHA-256 shown in Play Console -> App signing page

## SHA fingerprint for Firebase / Google APIs
keytool -list -v -keystore ~/.android/debug.keystore \
  -alias androiddebugkey -storepass android -keypass android | grep SHA
