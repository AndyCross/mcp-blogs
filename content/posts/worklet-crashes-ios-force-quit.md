+++
title = "The Force-Quit Crash: When Worklets Outlive Your App"
date = "2024-12-07"
draft = false
tags = ["react-native", "ios", "expo", "worklets", "reanimated", "filament", "debugging"]
+++

Got a crash report from TestFlight this week. The user's feedback was two words: "Hard exit."

That's all I had to go on. No steps to reproduce, no description of what they were doing. Just a crash log with `SIGABRT` and a stack trace pointing at... everything and nothing.

Turns out, the user had force-quit the app from the iOS app switcher. Swiped up, gone. And my app crashed *while dying*.

This is the story of a race condition that only happens when users kill your app, why your beautifully animated 3D scenes are secretly time bombs, and how the "obvious" fix actually made things worse.

**Update (December 2024):** After the initial fix, I got *another* crash—this time from just opening the app switcher, not even force-quitting. The rabbit hole went deeper. See [Part 2: The App Switcher Crash](#part-2-the-app-switcher-crash) below.

## The Crash Log

Here's what I was staring at:

```
Exception Type:  EXC_CRASH (SIGABRT)
Termination Reason: SIGNAL 6 Abort trap: 6

Thread 1 Crashed:
  facebook::react::ObjCTurboModule::performVoidMethodInvocation
  objc_exception_rethrow
  std::__terminate
```

Helpful, right? A TurboModule was trying to invoke something. An Objective-C exception got rethrown. Then everything died.

But look at Thread 10, which was happily running at the time:

```
  RNWorklet::JsiWorklet::evaluteJavascriptInWorkletRuntime
  RNWorklet::WorkletInvoker::call
  margelo::NSThreadDispatcher
```

Worklets. Running on their own thread. Trying to do... something.

## The Setup

I'm building a React Native app with react-native-filament for 3D rendering. Filament uses react-native-worklets-core under the hood to run render callbacks on a separate thread. Every frame, a worklet executes to update the camera position, handle animations, that sort of thing.

The code looks something like this:

```typescript
useRenderCallback(() => {
  'worklet';
  
  // Update camera position based on shared values
  const angle = panOffsetX.value + autoOrbitAngle;
  camera.lookAt([camX, camY, camZ], [targetX, targetY, targetZ], [0, 1, 0]);
}, [camera, panOffsetX, /* ... */]);
```

This runs 60 times per second. It's beautiful. It's smooth. And it's completely unaware that the app might be dying.

## What Actually Happens

When a user force-quits from the app switcher, iOS doesn't give you much warning. The app transitions briefly to an `inactive` state, then gets terminated.

Here's the race:

1. User swipes up to force-quit
2. iOS starts tearing down the React Native bridge
3. Worklet thread is mid-execution
4. Worklet tries to access a shared value or call a native method
5. The bridge it's calling into is being invalidated
6. Objective-C exception
7. Nobody catches it
8. `SIGABRT`

The worklet doesn't know the app is dying. It's just doing its job, updating the camera, reading shared values. But those shared values are backed by native code that's being torn down.

## The Frustrating Part

This crash doesn't happen during development. It doesn't happen in the simulator. It happens when a real user, on a real device, decides they're done with your app and swipes it away.

You can't reproduce it by pressing the home button. You can't reproduce it by switching apps. Only the force-quit gesture triggers the race condition reliably.

## The Fix

Two parts: native-side cleanup and JS-side defensive programming.

### Native Side: AppDelegate

In a bare React Native project, you'd add this to `AppDelegate.swift`:

```swift
public override func applicationWillTerminate(_ application: UIApplication) {
    NotificationCenter.default.post(
        name: NSNotification.Name("RCTBridgeWillInvalidateNotification"),
        object: self
    )
    super.applicationWillTerminate(application)
}
```

This notification tells the React Native bridge to start cleanup, which should cancel pending worklet operations before they can cause trouble.

But if you're using Expo, you can't just edit AppDelegate. It gets regenerated on every `expo prebuild`. So...

### The Expo Config Plugin

I built a plugin that injects this cleanup code during prebuild:

```json
{
  "expo": {
    "plugins": ["expo-plugin-worklet-cleanup"]
  }
}
```

That's it. Run `npx expo prebuild --clean` and the cleanup handler gets added automatically.

### JS Side: Defensive Worklets

The native fix helps, but race conditions are slippery. Belt and braces. Add an `isSceneActive` shared value that you set to `false` on unmount:

```typescript
const isSceneActive = useSharedValue(true);

useEffect(() => {
  return () => {
    isSceneActive.value = false;
  };
}, []);

useRenderCallback(() => {
  'worklet';
  
  // Bail out if scene is being torn down
  if (!isSceneActive.value) return;
  
  // ... rest of render logic
}, [isSceneActive, /* ... */]);
```

Also, stop rendering when the app goes inactive. **But be careful:** don't unmount native views, just skip rendering. (I learned this the hard way—see [Part 2](#part-2-the-app-switcher-crash).)

```typescript
const [isAppActive, setIsAppActive] = useState(true);
const isAppActiveShared = useSharedValue(true);

useEffect(() => {
  const subscription = AppState.addEventListener('change', (state) => {
    const active = state === 'active';
    setIsAppActive(active);
    isAppActiveShared.value = active;
  });
  return () => subscription.remove();
}, []);

// In render callback - skip work but don't unmount
useRenderCallback(() => {
  'worklet';
  if (!isAppActiveShared.value) return;  // Skip, don't crash
  // ... render logic
});
```

The `inactive` state happens briefly during force-quit. If you stop rendering at that point, the worklet thread has nothing to do, and the race condition becomes much less likely.

> ⚠️ **Important:** Don't conditionally unmount `<FilamentView>` based on `isAppActive`. This triggers native cleanup which can race with Hermes teardown. See [Part 2](#part-2-the-app-switcher-crash) for why.

## Who's Affected

Anyone using worklet-based libraries:

- **react-native-worklets-core** — the underlying runtime
- **react-native-reanimated** — animations
- **react-native-filament** — 3D rendering
- **react-native-skia** — 2D graphics
- **vision-camera** — frame processors

If you're using any of these and haven't seen this crash, you've been lucky. Or your users are polite and use the home button instead of force-quitting.

## The Plugin

I've open-sourced the Expo plugin. It's on npm:

```bash
npm install expo-plugin-worklet-cleanup
```

Add it to your `app.json`:

```json
{
  "expo": {
    "plugins": ["expo-plugin-worklet-cleanup"]
  }
}
```

Rebuild with `npx expo prebuild --clean`, and the cleanup handler gets added automatically.

- **npm**: [npmjs.com/package/expo-plugin-worklet-cleanup](https://www.npmjs.com/package/expo-plugin-worklet-cleanup)
- **GitHub**: [github.com/AndyCross/expo-plugin-worklet-cleanup](https://github.com/AndyCross/expo-plugin-worklet-cleanup)

MIT licensed, because these kinds of fixes should just exist.

> **Note:** This section describes v1.0.0 of the plugin. After discovering additional crash scenarios, I released v2.0.0 with improved lifecycle handling. See [Part 2](#part-2-the-app-switcher-crash) below for the full story.

## The Broader Lesson

This bug is a perfect example of why crash reporting from real users matters. I never would have found this in development. The force-quit gesture is something users do constantly but developers almost never do—we're always hot-reloading or stopping from the CLI.

It's also a reminder that threads don't respect your app lifecycle. When you spin up background work—worklets, timers, network requests—you're making a promise that you'll clean up after yourself. Native frameworks expect it. When you don't, things get ugly.

## Will This Fix It Completely?

Probably not 100%. Race conditions are fundamentally about timing, and there's always a window where the stars align wrong. But these changes should reduce the crash rate significantly.

If you're still seeing crashes after implementing both the native cleanup and the JS-side guards, you're hitting edge cases in the worklet libraries themselves. At that point, it's worth opening an issue on react-native-worklets-core or react-native-reanimated with your crash log.

But start with the plugin. It's the lowest-effort fix for the most common case.

---

## Part 2: The App Switcher Crash

A week after deploying the fix above, I got another crash. Different signature this time:

```
Exception Type:  EXC_BAD_ACCESS (SIGSEGV)
Exception Codes: KERN_INVALID_ADDRESS at 0x000000000000000c

Thread 1 Crashed:
  convertNSExceptionToJSError
  facebook::react::ObjCTurboModule::performVoidMethodInvocation
  
Thread 14:
  filament::FRenderer::terminate
  filament::FEngine::destroy
  margelo::EngineImpl::~EngineImpl
```

The smoking gun: `0x000000000000000c`. That's 12 bytes offset from null—classic "accessing a field on a nil object."

And Thread 14? That's Filament cleaning up. `FEngine::destroy()`. The 3D renderer was shutting down.

But here's the kicker: **the user didn't force-quit**. They just opened the app switcher.

### The Real Problem

My "fix" from Part 1 included this pattern:

```typescript
if (!isAppActive) {
  return <View style={styles.placeholder} />;
}

return <FilamentView>{/* ... */}</FilamentView>;
```

When the app goes inactive (app switcher opens), we stop rendering the FilamentView. Seems reasonable, right? Save battery, prevent worklet crashes.

**Wrong.** This was the actual cause of the crash.

When `isAppActive` becomes `false`, React unmounts `<FilamentView>`. Unmounting triggers Filament's native cleanup—`FEngine::destroy()`, `FRenderer::terminate()`. That cleanup throws an `NSException`. React Native tries to convert that exception to a JavaScript error. But Hermes (the JS runtime) is already being torn down, or the conversion is happening on the wrong thread.

Null pointer. Crash.

### Why applicationWillTerminate Wasn't Enough

Remember the fix from Part 1? Adding `applicationWillTerminate` to post a cleanup notification?

```swift
public override func applicationWillTerminate(_ application: UIApplication) {
    NotificationCenter.default.post(
        name: NSNotification.Name("RCTBridgeWillInvalidateNotification"),
        object: self
    )
    // ...
}
```

Here's the thing: **`applicationWillTerminate` is not reliably called on iOS 13+**.

When users swipe away apps in the app switcher, iOS often just kills the process without calling it. The scene-based lifecycle in iOS 13+ changed the rules, and `applicationWillTerminate` became more of a "nice to have" than a guarantee.

So my cleanup notification was never being posted for the most common case.

### The Actual Fix

Two changes were needed:

#### 1. Don't Unmount—Just Pause

The key insight: **keep native 3D views mounted, but skip rendering in the worklet**.

```typescript
// DON'T do this - unmounting triggers native cleanup
if (!isAppActive) {
  return <View style={styles.placeholder} />;
}
return <FilamentScene>{/* ... */}</FilamentScene>;

// DO this instead - always mount, but skip rendering
return (
  <View style={styles.container}>
    <FilamentScene>
      <SceneContent isAppActive={isAppActiveShared} />
    </FilamentScene>
    {/* Overlay when paused - scene stays mounted underneath */}
    {!isAppActive && (
      <View style={StyleSheet.absoluteFill}>
        <Text>Paused</Text>
      </View>
    )}
  </View>
);
```

And in the render callback:

```typescript
const isAppActiveShared = useSharedValue(true);

useEffect(() => {
  const subscription = AppState.addEventListener('change', (state) => {
    isAppActiveShared.value = state === 'active';
  });
  return () => subscription.remove();
}, []);

useRenderCallback(() => {
  'worklet';
  
  // Skip rendering when backgrounded - no CPU work, no cleanup triggered
  if (!isAppActive.value) return;
  
  // ... rest of render logic
});
```

This way:
- Native Filament resources stay allocated (no cleanup race)
- We're not wasting CPU rendering frames nobody sees
- The scene can resume instantly when the app returns to foreground

#### 2. Add Background Notification to the Plugin

Since `applicationWillTerminate` isn't reliable, the plugin now also adds `applicationDidEnterBackground`:

```swift
public override func applicationDidEnterBackground(_ application: UIApplication) {
    NotificationCenter.default.post(
        name: NSNotification.Name("RNAppDidEnterBackground"),
        object: self
    )
    super.applicationDidEnterBackground(application)
}
```

This notification **is** reliably called. Native modules can listen for it to prepare for potential termination—pause operations, flush caches, whatever they need.

### Plugin v2.0.0

The updated plugin is now on npm:

```bash
npm install expo-plugin-worklet-cleanup@^2.0.0
```

It adds both handlers:

| Method | Notification | When | Reliability |
|--------|-------------|------|-------------|
| `applicationDidEnterBackground` | `RNAppDidEnterBackground` | App enters background | ✅ Always |
| `applicationWillTerminate` | `RCTBridgeWillInvalidateNotification` | App terminating | ⚠️ Not reliable |

### The Meta-Lesson

The first fix (unmounting on background) was the "obvious" solution. It made intuitive sense: if the app is inactive, stop doing stuff. But it was actually *causing* crashes, not preventing them.

Native resources and React component lifecycle don't mix cleanly. When you unmount a component that owns native resources, you trigger cleanup code. That cleanup code runs on native threads, potentially racing with other teardown operations.

The counterintuitive solution: keep things mounted, but inert. Let the native resources live, but don't feed them work. When the app truly terminates, iOS will reclaim everything anyway.

### Summary

| Problem | Wrong Fix | Right Fix |
|---------|-----------|-----------|
| Worklet crashes on force-quit | — | Bail out early with `isSceneActive` guard |
| Cleanup crashes on background | Unmount the FilamentScene | Keep mounted, skip rendering |
| `applicationWillTerminate` not called | — | Also use `applicationDidEnterBackground` |

---

*Updated December 2024 after discovering that my "fix" was actually the cause of a second, different crash. The phrase "don't unmount, just pause" is now burned into my memory.*





