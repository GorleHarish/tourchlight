# Android Runtime Reference — Crashes, ANR, OOM, Lifecycle
# Load this file when the error matches: NPE, OOM, ANR, ClassNotFoundException,
# NetworkOnMainThreadException, or InflateException.
# ~350 tokens. Do NOT load other reference files in the same turn.

## Reading a stack trace
# FATAL EXCEPTION: main
# java.lang.NullPointerException        <- exception TYPE — read this
#   at com.example.MyClass.foo(X.kt:42) <- YOUR code — go here
#   at android.app.Activity...          <- framework — ignore

## NullPointerException (NPE)
# Common causes and fixes:
# View null -> only access views in/after onViewCreated() (Fragment) or after setContentView()
# LiveData null -> observe on viewLifecycleOwner, not `this`
# !! operator -> replace with ?.let {} or ?: return
# Intent extra missing -> intent.getStringExtra("key") ?: "default"
# Context null in Fragment -> requireContext() (throws if detached, which is correct)

## OutOfMemoryError (OOM)
# Images — always use Glide or Coil:
# Glide.with(ctx).load(url).into(imageView)
# implementation 'com.github.bumptech.glide:glide:4.x'

# Detect leaks:
# debugImplementation 'com.squareup.leakcanary:leakcanary-android:2.12'

# Avoid storing Activity/Context in long-lived objects — use applicationContext
# Profile: Run -> Profile app -> Memory tab

## ANR (Application Not Responding — blocks main thread > 5s)
# WRONG: val data = networkCall()  // on main thread
# RIGHT:
# viewModelScope.launch(Dispatchers.IO) {
#     val data = networkCall()
#     withContext(Dispatchers.Main) { updateUi(data) }
# }

# Get ANR trace: adb pull /data/anr/traces.txt
# StrictMode catches violations in debug:
# StrictMode.setThreadPolicy(StrictMode.ThreadPolicy.Builder().detectAll().penaltyLog().build())

## ClassNotFoundException / ClassCastException
# After enabling minification -> add -keep rule in proguard-rules.pro
# minSdkVersion < 21 -> enable multidex:
#   multiDexEnabled true
#   implementation 'androidx.multidex:multidex:2.0.1'

## NetworkOnMainThreadException
# All network calls must be off the main thread.
# Use: Retrofit suspend fun, OkHttp enqueue(), or Dispatchers.IO coroutine
# Never use StrictMode.allowThreadDiskReads() — it masks the bug

## Layout InflateException
# Real cause is BELOW the InflateException — scroll down in logcat
# Custom View must use @JvmOverloads:
# class MyView @JvmOverloads constructor(
#     ctx: Context, attrs: AttributeSet? = null, defStyle: Int = 0
# ) : View(ctx, attrs, defStyle)
