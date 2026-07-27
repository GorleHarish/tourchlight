# Android Build Reference — Gradle, AGP, Dependencies, ProGuard, Manifest
# Load this file when the error matches: Gradle sync, dependency resolution,
# duplicate class, AGP/DSL errors, ProGuard/R8, or Manifest merge conflicts.
# ~350 tokens. Do NOT load other reference files in the same turn.

## Quick triage
# Read the FIRST error line only — the rest are cascades.
# ./gradlew <task> --stacktrace --info 2>&1 | head -60

## Gradle sync failures
./gradlew --refresh-dependencies        # force re-download
./gradlew clean
# Nuclear: rm -rf ~/.gradle/caches/ .gradle/

# AGP <-> Gradle wrapper compatibility (must match):
# AGP 8.x -> Gradle 8.0+, Java 17
# AGP 7.4 -> Gradle 7.5+, Java 11
# AGP 7.0-7.3 -> Gradle 7.0+, Java 11

## Repository block (AGP 7+ style — goes in settings.gradle, NOT root build.gradle)
# settings.gradle
dependencyResolutionManagement {
    repositories { google(); mavenCentral() }
}

## Dependency resolution failure
# Find what pulls in a conflict:
./gradlew app:dependencies --configuration debugRuntimeClasspath | grep -A5 "bad-lib"

# Exclude a transitive dep:
# implementation('com.lib:artifact:1.0') { exclude group: 'x', module: 'y' }

# Kotlin stdlib duplicate -> gradle.properties:
# kotlin.stdlib.default.dependency=false

## Duplicate class
# Force a specific version:
# configurations.all { resolutionStrategy { force 'com.x:y:1.2.3' } }

## BuildConfig not found (AGP 8+)
# app/build.gradle:
# android { buildFeatures { buildConfig = true } }

## ProGuard / R8 class missing
# proguard-rules.pro:
# -dontwarn com.missing.ClassName
# -keep class com.yourpkg.model.** { *; }
# -keepattributes SourceFile,LineNumberTable
# -printusage usage.txt   <- shows what R8 removes

# Temporarily disable to isolate crash: minifyEnabled false
# Mapping file: app/build/outputs/mapping/release/mapping.txt

## Manifest merge conflict
# View merged result: Android Studio -> app/manifests -> Merged tab
# Run: ./gradlew processDebugManifest --info

# Override a library attribute:
# <application tools:replace="android:theme" android:theme="@style/App">
# Remove a library element:
# <activity android:name="com.lib.X" tools:node="remove"/>
# Override minSdkVersion conflict:
# <uses-sdk tools:overrideLibrary="com.conflicting.lib"/>
