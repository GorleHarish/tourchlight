"""
AndroidTroubleshootSkill — auto-loaded by Torchlight at startup.

Diagnoses and suggests fixes for the most common Android development problems.
Now PROJECT-AWARE: pass `project_dir` and the skill will scan your actual
build.gradle / proguard-rules.pro / AndroidManifest.xml before giving advice,
marking steps that are already implemented so the agent doesn't repeat them.

Categories:
  - Gradle build failures (sync, compilation, dependency conflicts)
  - ADB / device connectivity issues
  - Runtime crashes (ANR, OOM, NullPointerException patterns)
  - Emulator performance / boot failures
  - ProGuard / R8 obfuscation issues
  - Manifest merge conflicts
  - Resource & layout issues
  - Signing & keystore problems

Usage by the agent:
    ANDROID_TROUBLESHOOT(error="<paste error/logcat here>")
    ANDROID_TROUBLESHOOT(error="...", context="build|runtime|adb|emulator|proguard|manifest|signing")
    ANDROID_TROUBLESHOOT(error="...", project_dir="/path/to/android/project")
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from context_manager.skills.base import BaseSkill, SkillResult


# ─────────────────────────────────────────────────────────────────────────────
# Project scanner — reads real files and returns a flat dict of detected facts
# ─────────────────────────────────────────────────────────────────────────────

class ProjectSnapshot:
    """
    Lightweight scan of an Android project directory.

    Reads (if present):
      - app/build.gradle or app/build.gradle.kts
      - build.gradle (root)
      - settings.gradle / settings.gradle.kts
      - gradle.properties
      - app/proguard-rules.pro
      - app/src/main/AndroidManifest.xml
      - gradle/wrapper/gradle-wrapper.properties

    Stores results as a set of string "signals" and a raw text blob per file
    so that _check_already_done() can do quick membership tests.
    """

    def __init__(self, project_dir: str):
        self.root   = Path(project_dir).resolve()
        self.found  = False          # True if at least one Android file was detected
        self.texts: Dict[str, str] = {}   # filename → lowercased content
        self.signals: set[str]     = set()  # high-level detected facts

        self._scan()

    # ── File discovery ────────────────────────────────────────────────────────

    def _candidates(self) -> List[Tuple[str, Path]]:
        """Return (label, path) pairs for every file we want to read."""
        r = self.root
        return [
            ("app_gradle",      r / "app" / "build.gradle"),
            ("app_gradle",      r / "app" / "build.gradle.kts"),
            ("root_gradle",     r / "build.gradle"),
            ("root_gradle",     r / "build.gradle.kts"),
            ("settings",        r / "settings.gradle"),
            ("settings",        r / "settings.gradle.kts"),
            ("gradle_props",    r / "gradle.properties"),
            ("proguard",        r / "app" / "proguard-rules.pro"),
            ("manifest",        r / "app" / "src" / "main" / "AndroidManifest.xml"),
            ("wrapper",         r / "gradle" / "wrapper" / "gradle-wrapper.properties"),
            ("local_props",     r / "local.properties"),
        ]

    def _scan(self) -> None:
        merged: Dict[str, str] = {}

        for label, path in self._candidates():
            if path.exists():
                try:
                    text = path.read_text(encoding="utf-8", errors="replace").lower()
                    # Merge multiple files that share the same label (e.g. build.gradle + build.gradle.kts)
                    merged[label] = merged.get(label, "") + "\n" + text
                    self.found = True
                except OSError:
                    pass

        self.texts = merged
        if self.found:
            self._extract_signals()

    def _extract_signals(self) -> None:
        """Derive named boolean facts from the file contents."""
        app  = self.texts.get("app_gradle", "")
        root = self.texts.get("root_gradle", "")
        sett = self.texts.get("settings", "")
        prop = self.texts.get("gradle_props", "")
        pg   = self.texts.get("proguard", "")
        mf   = self.texts.get("manifest", "")
        wrap = self.texts.get("wrapper", "")
        lp   = self.texts.get("local_props", "")
        all_gradle = app + root + sett

        def sig(name: str, *patterns: str) -> None:
            for p in patterns:
                if re.search(p, all_gradle + pg + mf + prop + lp):
                    self.signals.add(name)
                    return

        # ── Dependencies already present ──────────────────────────────────────
        sig("has_leakcanary",    r"leakcanary")
        sig("has_glide",         r"com\.github\.bumptech\.glide|glide")
        sig("has_coil",          r"io\.coil-kt|coil")
        sig("has_picasso",       r"com\.squareup\.picasso")
        sig("has_retrofit",      r"com\.squareup\.retrofit2|retrofit2")
        sig("has_okhttp",        r"com\.squareup\.okhttp3|okhttp")
        sig("has_room",          r"androidx\.room|room-runtime")
        sig("has_hilt",          r"com\.google\.dagger.*hilt|hilt-android")
        sig("has_koin",          r"io\.insert-koin|koin-android")
        sig("has_coroutines",    r"kotlinx-coroutines|coroutines-android")
        sig("has_rxjava",        r"io\.reactivex|rxjava|rxandroid")
        sig("has_multidex",      r"multidex")
        sig("has_firebase",      r"com\.google\.firebase|firebase-bom")
        sig("has_crashlytics",   r"firebase-crashlytics")
        sig("has_workmanager",   r"androidx\.work|work-runtime")
        sig("has_navigation",    r"androidx\.navigation|navigation-fragment")
        sig("has_compose",       r"androidx\.compose|jetpack compose|compose-ui")

        # ── Build config ──────────────────────────────────────────────────────
        sig("minify_enabled",    r"minifyenabled\s*=?\s*true")
        sig("multidex_enabled",  r"multidexenabled\s*=?\s*true")
        sig("buildconfig_enabled", r"buildconfig\s*=\s*true")
        sig("has_proguard_file", r"proguardrules\.pro|proguard-rules\.pro")
        sig("signing_configured", r"signingconfig|storepassword|keyalias")
        sig("signing_env_vars",  r"system\.getenv|process\.env")
        sig("signing_local_props", r"localproperties\[|local\.properties")
        sig("vector_support",    r"vectordrawables\.usesupportlibrary\s*=\s*true")

        # ── gradle.properties flags ───────────────────────────────────────────
        if re.search(r"kotlin\.stdlib\.default\.dependency\s*=\s*false", prop):
            self.signals.add("kotlin_stdlib_dedup")
        if re.search(r"https\.proxy|http\.proxy", prop):
            self.signals.add("proxy_configured")
        if re.search(r"org\.gradle\.jvmargs", prop):
            self.signals.add("gradle_jvm_args")

        # ── ProGuard rules already written ────────────────────────────────────
        if re.search(r"-keepattributes sourcefile,linenumbertable", pg):
            self.signals.add("pg_keep_attributes")
        if re.search(r"-dontwarn", pg):
            self.signals.add("pg_dontwarn_present")
        if re.search(r"-keep class", pg):
            self.signals.add("pg_keep_class")
        if re.search(r"@keep", all_gradle + pg):
            self.signals.add("pg_at_keep")

        # ── Manifest ──────────────────────────────────────────────────────────
        if re.search(r"tools:replace", mf):
            self.signals.add("manifest_tools_replace")
        if re.search(r"tools:node", mf):
            self.signals.add("manifest_tools_node")
        if re.search(r"android:debuggable", mf):
            self.signals.add("manifest_debuggable")

        # ── Repository blocks ─────────────────────────────────────────────────
        if re.search(r"google\(\)", all_gradle + sett):
            self.signals.add("repo_google")
        if re.search(r"mavencentral\(\)", all_gradle + sett):
            self.signals.add("repo_maven_central")
        if re.search(r"dependencyresolutionmanagement", sett):
            self.signals.add("new_repo_style")   # AGP 7+ style

        # ── Wrapper / AGP version ─────────────────────────────────────────────
        m = re.search(r"gradle-(\d+\.\d+)", wrap)
        if m:
            self.signals.add(f"gradle_{m.group(1)}")
        m = re.search(r"com\.android\.tools\.build:gradle:(\d+)", all_gradle)
        if m:
            self.signals.add(f"agp_{m.group(1)}")

    # ── Public helpers ────────────────────────────────────────────────────────

    def has(self, *signal_names: str) -> bool:
        """True if ANY of the given signals are present."""
        return bool(self.signals.intersection(signal_names))

    def grep(self, pattern: str, *labels: str) -> bool:
        """True if pattern found in any of the named file labels."""
        for label in labels:
            if re.search(pattern, self.texts.get(label, "")):
                return True
        return False

    def summary(self) -> str:
        if not self.found:
            return "  (no Android project files found at the given path)"
        lines = ["  Detected in project:"]
        groups = {
            "Image loading":   ["has_glide", "has_coil", "has_picasso"],
            "Networking":      ["has_retrofit", "has_okhttp"],
            "Async":           ["has_coroutines", "has_rxjava"],
            "DI":              ["has_hilt", "has_koin"],
            "Database":        ["has_room"],
            "Firebase":        ["has_firebase", "has_crashlytics"],
            "Memory leaks":    ["has_leakcanary"],
            "Compose":         ["has_compose"],
            "WorkManager":     ["has_workmanager"],
            "Navigation":      ["has_navigation"],
            "Multidex":        ["has_multidex", "multidex_enabled"],
            "Minification":    ["minify_enabled"],
            "ProGuard":        ["has_proguard_file", "pg_keep_attributes", "pg_dontwarn_present"],
            "Signing":         ["signing_configured", "signing_env_vars"],
        }
        found_groups = []
        for group, sigs in groups.items():
            if any(s in self.signals for s in sigs):
                found_groups.append(group)
        if found_groups:
            lines.append("  " + ", ".join(found_groups))
        else:
            lines.append("  (no major libraries detected)")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Step annotation helpers
# ─────────────────────────────────────────────────────────────────────────────

_DONE  = "✅ ALREADY DONE —"
_CHECK = "🔍 VERIFY —"
_TODO  = "  "   # plain indent for steps not yet done


def _tag_step(step: str, done: bool, check: bool = False) -> str:
    """Prefix a step string with its status tag."""
    if done:
        return f"{_DONE} {step}"
    if check:
        return f"{_CHECK} {step}"
    return step


# ─────────────────────────────────────────────────────────────────────────────
# Diagnosis rules — now project-snapshot-aware
# ─────────────────────────────────────────────────────────────────────────────
# Each rule is a function that accepts (error_lower, snap) and returns
# Optional[Tuple[title, annotated_steps, doc_link]].
# Returning None means the pattern didn't match.

def _rule_dep_resolution(lower: str, snap: ProjectSnapshot):
    if not re.search(r"could not resolve|failed to resolve|dependency.*not found|unresolved reference.*implementation", lower):
        return None
    steps = [
        "1. Run `./gradlew --refresh-dependencies` to force re-download.",
        _tag_step(
            "2. Check `repositories` block — `google()` and `mavenCentral()` must be present.",
            done=snap.has("repo_google", "repo_maven_central"),
            check=not snap.found,
        ),
        _tag_step(
            "3. For AGP 7+, `repositories` goes in `settings.gradle`, not root `build.gradle`.",
            done=snap.has("new_repo_style"),
        ),
        _tag_step(
            "4. If behind a corporate proxy, configure `gradle.properties` with proxy settings.",
            done=snap.has("proxy_configured"),
        ),
        "5. Check for typos in the artifact coordinate (`group:artifact:version`).",
        "6. For SNAPSHOT versions add the Sonatype snapshots repository.",
    ]
    return ("Gradle Dependency Resolution Failure", steps, "https://docs.gradle.org/current/userguide/dependency_resolution.html")


def _rule_duplicate_class(lower: str, snap: ProjectSnapshot):
    if not re.search(r"duplicate class|already defined|class.*is defined multiple times", lower):
        return None
    steps = [
        "1. Find the conflict: `./gradlew app:dependencies | grep <ClassName>`",
        "2. Exclude from one dep:\n   ```groovy\n   implementation('com.example:lib:1.0') { exclude group: 'com.conflicting', module: 'module' }\n   ```",
        _tag_step(
            "3. Kotlin stdlib duplicate → add `kotlin.stdlib.default.dependency=false` to `gradle.properties`.",
            done=snap.has("kotlin_stdlib_dedup"),
        ),
        "4. Check for accidental `api` vs `implementation` leakage.",
    ]
    return ("Duplicate Class Conflict", steps, "https://developer.android.com/studio/build/dependencies#duplicate_classes")


def _rule_compile_error(lower: str, snap: ProjectSnapshot):
    if not re.search(r"execution failed for task.*mergejava|java.*compile.*error|error: cannot find symbol", lower):
        return None
    steps = [
        "1. Read the FIRST error only — subsequent errors are cascades.",
        "2. Run `./gradlew compileDebugJavaSources --stacktrace` for the full trace.",
        "3. `cannot find symbol` → missing import, wrong package, or annotation processor (`kapt`/`ksp`) not configured.",
        "4. Ensure `kotlin-android` plugin is applied in `build.gradle`.",
        "5. `./gradlew clean` then rebuild.",
    ]
    return ("Java/Kotlin Compilation Error", steps, "https://developer.android.com/studio/build/configure-apk-splits")


def _rule_gradle_dsl(lower: str, snap: ProjectSnapshot):
    if not re.search(r"build\.gradle.*could not find method|unresolved reference.*buildconfig|classpath.*not found", lower):
        return None
    steps = [
        "1. Verify AGP ↔ Gradle wrapper version compatibility: https://developer.android.com/studio/releases/gradle-plugin#updating-plugin",
        _tag_step(
            "2. After AGP 7+ upgrade, `repositories` moves to `settings.gradle`.",
            done=snap.has("new_repo_style"),
        ),
        _tag_step(
            "3. `BuildConfig` not found → add `buildFeatures { buildConfig = true }` in `build.gradle`.",
            done=snap.has("buildconfig_enabled"),
        ),
        "4. Sync Gradle after every `build.gradle` change.",
    ]
    return ("Gradle Build Script Error (DSL / Plugin)", steps, "https://developer.android.com/studio/releases/gradle-plugin")


def _rule_proguard(lower: str, snap: ProjectSnapshot):
    if not re.search(r"minification enabled.*could not find|r8|proguard.*warning.*can't find referenced class", lower):
        return None
    steps = [
        _tag_step(
            "1. Add `-dontwarn com.missing.ClassName` to `proguard-rules.pro`.",
            done=snap.has("pg_dontwarn_present"),
            check=snap.found and not snap.has("pg_dontwarn_present"),
        ),
        _tag_step(
            "2. Add `-keep` rules for reflection-heavy libs (Gson, Retrofit, Room).",
            done=snap.has("pg_keep_class"),
            check=snap.found and not snap.has("pg_keep_class"),
        ),
        "3. Check if the library ships consumer ProGuard rules via `consumerProguardFiles`.",
        "4. Add `-printusage usage.txt` to see what R8 removes.",
        _tag_step(
            "5. Temporarily disable minification (`minifyEnabled false`) to isolate the crash.",
            check=snap.has("minify_enabled"),
        ),
    ]
    return ("ProGuard / R8 Missing Class Warning", steps, "https://developer.android.com/studio/build/shrink-code")


def _rule_manifest(lower: str, snap: ProjectSnapshot):
    if not re.search(r"manifest merger failed|attribute.*already present|uses-sdk.*minsdkversion", lower):
        return None
    steps = [
        "1. Run `./gradlew processDebugManifest --info` and look for the merge error.",
        _tag_step(
            "2. Use `tools:replace` in your manifest to override library attributes.",
            done=snap.has("manifest_tools_replace"),
        ),
        _tag_step(
            "3. Use `tools:node` to remove or replace elements from library manifests.",
            done=snap.has("manifest_tools_node"),
        ),
        "4. Check `app/build/outputs/logs/manifest-merger-debug-report.txt`.",
    ]
    return ("Manifest Merge Conflict", steps, "https://developer.android.com/studio/build/manage-manifests")


def _rule_adb_offline(lower: str, snap: ProjectSnapshot):
    if not re.search(r"adb.*device not found|no devices.*attached|adb.*offline|cannot connect to daemon", lower):
        return None
    steps = [
        "1. `adb kill-server && adb start-server` — restart the ADB daemon.",
        "2. Unplug and replug the USB cable; accept the 'Allow USB Debugging' prompt on device.",
        "3. Verify USB debugging is ON: Settings → Developer Options → USB Debugging.",
        "4. Try a different USB cable (data cable, not charge-only).",
        "5. `adb devices -l` — if `unauthorized`, revoke and re-authorize.",
        "6. macOS: check System Preferences → Privacy → Full Disk Access for `adb`.",
        "7. Wireless debugging (Android 11+): Settings → Developer Options → Wireless Debugging.",
    ]
    return ("ADB Device Not Found / Offline", steps, "https://developer.android.com/tools/adb")


def _rule_apk_install(lower: str, snap: ProjectSnapshot):
    if not re.search(r"installation failed|apk.*install.*failed|pkg: error", lower):
        return None
    steps = [
        "1. `INSTALL_FAILED_UPDATE_INCOMPATIBLE` → `adb uninstall com.your.package` first.",
        "2. `INSTALL_FAILED_INSUFFICIENT_STORAGE` → free device storage.",
        "3. `INSTALL_FAILED_VERSION_DOWNGRADE` → uninstall or increment `versionCode`.",
        "4. `INSTALL_PARSE_FAILED_NO_CERTIFICATES` → use debug signing: `./gradlew assembleDebug`.",
        "5. `INSTALL_FAILED_CPU_ABI_INCOMPATIBLE` → build universal APK or add correct ABI.",
    ]
    return ("APK Installation Failure", steps, "https://developer.android.com/tools/adb#pm")


def _rule_npe(lower: str, snap: ProjectSnapshot):
    if not re.search(r"java\.lang\.nullpointerexception|kotlin\.nullpointerexception|npe at", lower):
        return None
    steps = [
        "1. Read the stack trace — the TOP line after the exception type is the crash site.",
        "2. In Kotlin, prefer `?.let { }` or `?: return` over `!!`.",
        "3. Views are null if accessed before `setContentView()` or after `onDestroyView()`.",
        "4. For Fragments: access views only in/after `onViewCreated()`.",
        "5. LiveData null → observe on `viewLifecycleOwner`, not `this`.",
        "6. Enable Android Studio's Null Safety inspections (Analyze → Inspect Code).",
    ]
    return ("NullPointerException (NPE)", steps, "https://developer.android.com/kotlin/common-patterns#null-safety")


def _rule_oom(lower: str, snap: ProjectSnapshot):
    if not re.search(r"outofmemoryerror|oom|failed to allocate.*bytes|gc overhead limit exceeded", lower):
        return None
    image_lib = snap.has("has_glide", "has_coil", "has_picasso")
    leak_lib  = snap.has("has_leakcanary")
    steps = [
        _tag_step(
            "1. For image OOM: use Glide or Coil — never load full-size Bitmaps manually.",
            done=image_lib,
            check=snap.found and not image_lib,
        ),
        _tag_step(
            "2. Check for memory leaks with LeakCanary (`debugImplementation 'com.squareup.leakcanary:leakcanary-android:2.x'`).",
            done=leak_lib,
            check=snap.found and not leak_lib,
        ),
        "3. Profile with Android Studio Memory Profiler (Run → Profile 'app').",
        "4. Avoid storing `Context` or `Activity` refs in long-lived objects (use `ApplicationContext`).",
        "5. Last resort: increase heap in `build.gradle`: `dexOptions { javaMaxHeapSize '4g' }`",
        "6. OOM in native code → check NDK JNI references for leaks.",
    ]
    return ("OutOfMemoryError (OOM)", steps, "https://developer.android.com/topic/performance/memory")


def _rule_anr(lower: str, snap: ProjectSnapshot):
    if not re.search(r"anr|application not responding|inputdispatching timed out", lower):
        return None
    has_async = snap.has("has_coroutines", "has_rxjava")
    steps = [
        "1. Never do I/O, database queries, or network calls on the main thread.",
        _tag_step(
            "2. Use Coroutines: `viewModelScope.launch(Dispatchers.IO) { /* heavy work */ }`.",
            done=has_async,
            check=snap.found and not has_async,
        ),
        "3. Pull ANR trace: `adb pull /data/anr/traces.txt` (root) or filter Logcat by `ANR`.",
        "4. StrictMode catches main-thread violations in debug builds.",
        _tag_step(
            "5. For BroadcastReceivers: do heavy work in WorkManager, not `onReceive()`.",
            done=snap.has("has_workmanager"),
            check=snap.found and not snap.has("has_workmanager"),
        ),
    ]
    return ("ANR — Application Not Responding", steps, "https://developer.android.com/topic/performance/vitals/anr")


def _rule_class_not_found(lower: str, snap: ProjectSnapshot):
    if not re.search(r"classnotfoundexception|classcastexception.*activity|could not find class", lower):
        return None
    multidex_ok = snap.has("has_multidex", "multidex_enabled")
    steps = [
        _tag_step(
            "1. After enabling minification → add a `-keep` rule in `proguard-rules.pro`.",
            done=snap.has("pg_keep_class"),
            check=snap.has("minify_enabled") and not snap.has("pg_keep_class"),
        ),
        "2. `ClassCastException` on Activity/Fragment → check class name in `AndroidManifest.xml`.",
        _tag_step(
            "3. `minSdkVersion < 21` → enable multidex: `multiDexEnabled true` + `androidx.multidex` dep.",
            done=multidex_ok,
            check=snap.found and not multidex_ok,
        ),
        "4. Check the class isn't in a Dynamic Feature Module not yet downloaded.",
    ]
    return ("ClassNotFoundException / ClassCastException", steps, "https://developer.android.com/studio/build/multidex")


def _rule_network_main_thread(lower: str, snap: ProjectSnapshot):
    if not re.search(r"network.*on main thread|networkonmainthreadexception", lower):
        return None
    has_async = snap.has("has_coroutines", "has_rxjava", "has_retrofit")
    steps = [
        _tag_step(
            "1. All network calls must be off the main thread. Use Coroutines (`Dispatchers.IO`) or Retrofit with enqueue().",
            done=has_async,
            check=snap.found and not has_async,
        ),
        "2. Never use `StrictMode.allowThreadDiskReads()` — it masks the problem.",
        _tag_step(
            "3. If using Retrofit, ensure a coroutine/RxJava CallAdapter is configured.",
            done=snap.has("has_retrofit") and has_async,
        ),
    ]
    return ("NetworkOnMainThreadException", steps, "https://developer.android.com/guide/background")


def _rule_emulator_start(lower: str, snap: ProjectSnapshot):
    if not re.search(r"emulator.*failed to start|hax.*is not working|kvm.*not enabled|hw.*acceleration", lower):
        return None
    steps = [
        "1. macOS (Apple Silicon): Use ARM64 system images in AVD Manager.",
        "2. Windows: Enable Hyper-V OR Intel HAXM in BIOS — not both.",
        "3. Linux: `sudo apt install qemu-kvm libvirt-daemon-system && sudo adduser $USER kvm`",
        "4. Verify HAXM: Android Studio → SDK Manager → SDK Tools → Intel x86 Emulator Accelerator.",
        "5. Reduce emulator RAM in AVD settings if host RAM < 8 GB.",
        "6. Use a physical device as a faster alternative during development.",
    ]
    return ("Emulator Won't Start / Hardware Acceleration Disabled", steps, "https://developer.android.com/studio/run/emulator-acceleration")


def _rule_emulator_slow(lower: str, snap: ProjectSnapshot):
    if not re.search(r"emulator.*slow|emulator.*lag|rendering.*software", lower):
        return None
    steps = [
        "1. AVD settings → Graphics → Hardware GLES 2.0.",
        "2. Allocate more RAM and VM Heap in AVD Manager.",
        "3. Use x86_64 system images (10–30× faster than ARM on Intel/AMD hosts).",
        "4. Disable unused emulator features (camera, sensors).",
        "5. Consider a physical device or Firebase Test Lab.",
    ]
    return ("Emulator Slow / Laggy", steps, "https://developer.android.com/studio/run/emulator")


def _rule_signing(lower: str, snap: ProjectSnapshot):
    if not re.search(r"keystore.*not found|signing.*failed|invalid keystore|wrong password|jks", lower):
        return None
    env_ok   = snap.has("signing_env_vars", "signing_local_props")
    sign_ok  = snap.has("signing_configured")
    steps = [
        _tag_step(
            "1. Verify keystore path in `build.gradle` signingConfigs.",
            done=sign_ok,
            check=snap.found and not sign_ok,
        ),
        "2. Check `storePassword`, `keyAlias`, `keyPassword` are correct (case-sensitive).",
        "3. Inspect keystore: `keytool -list -v -keystore your.jks`",
        _tag_step(
            "4. Never commit passwords to git — use environment variables or `local.properties`.",
            done=env_ok,
            check=sign_ok and not env_ok,
        ),
        "5. Generate new debug keystore: `keytool -genkeypair -v -keystore ~/.android/debug.keystore -alias androiddebugkey -keyalg RSA -keysize 2048 -validity 10000`",
    ]
    return ("Keystore / Signing Error", steps, "https://developer.android.com/studio/publish/app-signing")


def _rule_missing_resource(lower: str, snap: ProjectSnapshot):
    if not re.search(r"resource.*not found|cannot find.*@drawable|no resource found.*@string|aapt.*error", lower):
        return None
    steps = [
        "1. `./gradlew clean assembleDebug`.",
        "2. Resource names must be lowercase with underscores — no hyphens.",
        "3. Verify resource is in the correct folder (`res/drawable`, `res/layout`, `res/values`).",
        "4. `@string` not found → check `res/values/strings.xml` for the key.",
        _tag_step(
            "5. Vector drawables on API < 21 → set `vectorDrawables.useSupportLibrary = true`.",
            done=snap.has("vector_support"),
        ),
    ]
    return ("Missing Resource / AAPT Error", steps, "https://developer.android.com/guide/topics/resources/providing-resources")


def _rule_inflate(lower: str, snap: ProjectSnapshot):
    if not re.search(r"inflate.*exception|binary.*xml.*inflate|layoutinflater.*exception", lower):
        return None
    steps = [
        "1. The real cause is BELOW the InflateException in the stack trace — scroll down.",
        "2. Common causes: missing font file, bad custom view constructor, invalid XML attribute.",
        "3. Custom View must use `@JvmOverloads constructor(ctx, attrs?, defStyle?)` or implement all three constructors.",
        "4. For missing fonts: verify font file is in `res/font/` and referenced correctly.",
    ]
    return ("Layout Inflation Error", steps, "https://developer.android.com/reference/android/view/LayoutInflater")


# All rules in priority order
_ALL_RULES = [
    _rule_dep_resolution,
    _rule_duplicate_class,
    _rule_compile_error,
    _rule_gradle_dsl,
    _rule_proguard,
    _rule_manifest,
    _rule_adb_offline,
    _rule_apk_install,
    _rule_npe,
    _rule_oom,
    _rule_anr,
    _rule_class_not_found,
    _rule_network_main_thread,
    _rule_emulator_start,
    _rule_emulator_slow,
    _rule_signing,
    _rule_missing_resource,
    _rule_inflate,
]


# ─────────────────────────────────────────────────────────────────────────────
# Context-based tip sets (unchanged from v1)
# ─────────────────────────────────────────────────────────────────────────────

_CONTEXT_TIPS: Dict[str, str] = {
    "build": (
        "**General Build Troubleshooting Checklist**\n"
        "1. `./gradlew clean` — clears stale cache.\n"
        "2. File → Invalidate Caches & Restart in Android Studio.\n"
        "3. Delete `.gradle/` and `.idea/` folders, then re-sync.\n"
        "4. Check AGP ↔ Gradle wrapper version compatibility table.\n"
        "5. Run `./gradlew --stacktrace` for the full error origin.\n"
        "6. Check `$ANDROID_HOME`: `echo $ANDROID_HOME`."
    ),
    "runtime": (
        "**General Runtime Debug Checklist**\n"
        "1. Filter Logcat by package name and level ERROR.\n"
        "2. Enable 'Don't keep activities' in Developer Options.\n"
        "3. Use Android Studio Debugger: breakpoints, watchpoints, evaluate expression.\n"
        "4. Profile with CPU/Memory/Network profilers (Run → Profile 'app').\n"
        "5. `adb logcat -d > crash.txt` to dump the full log."
    ),
    "adb": (
        "**ADB Quick Commands**\n"
        "`adb devices -l`             — list connected devices\n"
        "`adb logcat -c`              — clear logcat buffer\n"
        "`adb logcat *:E`             — show errors only\n"
        "`adb shell dumpsys activity` — activity back-stack\n"
        "`adb shell am force-stop com.your.pkg` — force-stop app\n"
        "`adb reverse tcp:8080 tcp:8080` — reverse-proxy localhost to device"
    ),
    "emulator": (
        "**Emulator Tips**\n"
        "- Use Pixel 6 API 33 or newer Google Play images for accurate testing.\n"
        "- Cold boot: AVD Manager → ▼ → Cold Boot Now.\n"
        "- Snapshots save 20-30 s off boot time.\n"
        "- Extended controls (⋮): simulate GPS, battery, network, calls.\n"
        "- `emulator -avd Pixel_6 -verbose` for startup diagnostics."
    ),
    "proguard": (
        "**ProGuard / R8 Checklist**\n"
        "1. Always test release builds — `./gradlew assembleRelease`.\n"
        "2. Use `-keepattributes SourceFile,LineNumberTable` to preserve stack traces.\n"
        "3. Map file: `app/build/outputs/mapping/release/mapping.txt`.\n"
        "4. Firebase Crashlytics auto-uploads mapping files if configured.\n"
        "5. Use `@Keep` annotation to preserve individual classes/methods."
    ),
    "manifest": (
        "**Manifest Merge Checklist**\n"
        "1. View merged manifest: Android Studio → app/manifests → Merged tab.\n"
        "2. `tools:node=\"remove\"` — remove a library element.\n"
        "3. `tools:node=\"merge\"` — default merge strategy.\n"
        "4. `tools:node=\"replace\"` — your manifest wins completely."
    ),
    "signing": (
        "**Signing Best Practices**\n"
        "1. Enroll in Google Play App Signing — Google manages your release key.\n"
        "2. Keep a separate upload key for Google Play.\n"
        "3. Store passwords in CI environment variables, not source code.\n"
        "4. Back up your keystore — losing it means you can't update your app.\n"
        "5. SHA fingerprint: `keytool -list -v -keystore debug.keystore`"
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# Main diagnosis function
# ─────────────────────────────────────────────────────────────────────────────

def _diagnose(error_text: str, context: Optional[str], snap: ProjectSnapshot) -> str:
    lower = error_text.lower()
    matched = []

    for rule_fn in _ALL_RULES:
        result = rule_fn(lower, snap)
        if result is not None:
            matched.append(result)

    lines: List[str] = []

    # Show project snapshot summary when a project was scanned
    if snap.found:
        lines.append(f"📁 Project scanned: {snap.root}")
        lines.append(snap.summary())
        lines.append(f"   Signals: {', '.join(sorted(snap.signals)) or 'none'}")
        lines.append("")
        lines.append("Legend:  ✅ ALREADY DONE  |  🔍 VERIFY  |  (no prefix) = TODO")
        lines.append("")

    # Context-based tips
    if context and context.lower() in _CONTEXT_TIPS:
        lines.append(_CONTEXT_TIPS[context.lower()])
        lines.append("")

    if not matched and not error_text.strip():
        lines.append(
            "No error text provided. Pass your Logcat output, Gradle error, or ADB message "
            "as the `error` argument.\n"
            "Optional: `context` = build | runtime | adb | emulator | proguard | manifest | signing\n"
            "Optional: `project_dir` = path to your Android project root"
        )
        return "\n".join(lines)

    if not matched:
        lines.append(
            "⚠️  No specific rule matched. General debugging steps:\n\n"
            "1. Copy the FIRST error line — subsequent lines are cascades.\n"
            "2. Search the exact exception class on Stack Overflow / Android Issue Tracker.\n"
            "3. Run `./gradlew <task> --stacktrace --info` for full trace.\n"
            "4. Check Android Studio Event Log (View → Tool Windows → Event Log).\n\n"
            f"**Raw error received:**\n```\n{error_text[:800]}\n```"
        )
        return "\n".join(lines)

    lines.append(f"🔍 Found {len(matched)} matching issue(s):\n")

    for i, (title, steps, link) in enumerate(matched, 1):
        lines.append("─" * 60)
        lines.append(f"**Issue {i}: {title}**")
        lines.append(f"📖 Docs: {link}\n")
        lines.append("**Fix steps:**")
        for step in steps:
            lines.append(step)
        lines.append("")

    if len(matched) > 1:
        lines.append("💡 Multiple patterns matched. Start from Issue 1 — resolving it often clears the others.")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Skill class
# ─────────────────────────────────────────────────────────────────────────────

class AndroidTroubleshootSkill(BaseSkill):
    """
    Project-aware Android development error diagnosis.

    Scans build.gradle, proguard-rules.pro, AndroidManifest.xml, and
    gradle.properties to detect what's already implemented, then annotates
    each fix step as ✅ ALREADY DONE, 🔍 VERIFY, or plain TODO — so the
    agent never suggests things you've already set up.
    """

    name        = "ANDROID_TROUBLESHOOT"
    description = (
        "Diagnose and fix Android development errors — Gradle build failures, "
        "ADB/device issues, runtime crashes (NPE, OOM, ANR, ClassNotFound), "
        "ProGuard/R8, Manifest merge conflicts, Emulator problems, "
        "signing/keystore errors, layout inflation failures. "
        "Pass the error text from Logcat, Gradle output, or ADB directly. "
        "Also accepts project_dir to scan the actual project and skip steps already done."
    )
    icon = "🤖"

    async def execute(self, input_data: Dict[str, Any]) -> SkillResult:
        error       = str(input_data.get("error",       input_data.get("arg", "")))
        context     = input_data.get("context",     None)
        project_dir = input_data.get("project_dir", input_data.get("cwd", None))

        # Build project snapshot (fast — only file reads, no network)
        if project_dir:
            snap = ProjectSnapshot(project_dir)
        else:
            snap = ProjectSnapshot.__new__(ProjectSnapshot)
            snap.root    = Path(".")
            snap.found   = False
            snap.texts   = {}
            snap.signals = set()

        diagnosis = _diagnose(error, context, snap)
        return SkillResult(success=True, output=diagnosis)

    def get_prompt(self) -> str:
        # KEEP THIS ONE LINE — injected into every LLM message on 8k+ models.
        # Every extra token here costs conversation space on M1-class hardware.
        return f"{self.icon} **{self.name}**(error, context?, project_dir?) — diagnose Android errors"
