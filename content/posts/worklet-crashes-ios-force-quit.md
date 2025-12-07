+++
title = "The Force-Quit Crash: When Worklets Outlive Your App"
date = "2024-12-07"
draft = false
tags = ["react-native", "ios", "expo", "worklets", "reanimated", "filament", "debugging"]
+++

Got a crash report from TestFlight this week. The user's feedback was two words: "Hard exit."

That's all I had to go on. No steps to reproduce, no description of what they were doing. Just a crash log with `SIGABRT` and a stack trace pointing at... everything and nothing.

Turns out, the user had force-quit the app from the iOS app switcher. Swiped up, gone. And my app crashed *while dying*.

This is the story of a race condition that only happens when users kill your app, and why your beautifully animated 3D scenes are secretly time bombs.

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

Also, stop rendering entirely when the app goes inactive:

```typescript
const [isAppActive, setIsAppActive] = useState(true);

useEffect(() => {
  const subscription = AppState.addEventListener('change', (state) => {
    setIsAppActive(state === 'active');
  });
  return () => subscription.remove();
}, []);

if (!isAppActive) {
  return <View style={styles.placeholder} />;
}

return <FilamentView>{/* ... */}</FilamentView>;
```

The `inactive` state happens briefly during force-quit. If you stop rendering at that point, the worklet thread has nothing to do, and the race condition becomes much less likely.

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

## The Broader Lesson

This bug is a perfect example of why crash reporting from real users matters. I never would have found this in development. The force-quit gesture is something users do constantly but developers almost never do—we're always hot-reloading or stopping from the CLI.

It's also a reminder that threads don't respect your app lifecycle. When you spin up background work—worklets, timers, network requests—you're making a promise that you'll clean up after yourself. Native frameworks expect it. When you don't, things get ugly.

## Will This Fix It Completely?

Probably not 100%. Race conditions are fundamentally about timing, and there's always a window where the stars align wrong. But these changes should reduce the crash rate significantly.

If you're still seeing crashes after implementing both the native cleanup and the JS-side guards, you're hitting edge cases in the worklet libraries themselves. At that point, it's worth opening an issue on react-native-worklets-core or react-native-reanimated with your crash log.

But start with the plugin. It's the lowest-effort fix for the most common case.

---

*Discovered December 2024 while wondering why TestFlight users kept sending crash reports with no context. The phrase "Hard exit" will haunt me.*
