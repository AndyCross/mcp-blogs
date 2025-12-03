+++
title = "The Invisible Models: Debugging 3D Rendering on iOS Physical Devices"
date = "2024-11-30"
draft = false
tags = ["react-native", "ios", "3d", "filament", "debugging"]
+++

I spent the better part of a day staring at a blank screen on an iPhone 11. The 3D scene worked perfectly on the iOS Simulator. It worked on Android. But on an actual iOS device? Nothing. Just an empty void where my models should have been.

No errors. No warnings. Filament (the rendering engine) happily reported "ready". The JavaScript console was clean. Everything was fine, except for the part where nothing was rendering.

This is the story of two silent killers in React Native 3D development—and how to avoid them.

## The Setup

I'm building a React Native app with 3D scenes using Filament, Google's physically-based rendering engine. The scene includes casetas (little booth models) and a grid overlay. Standard stuff. Works everywhere in development.

Then I deployed to a physical iPhone. Black screen.

## Issue One: GLTF External References

Here's the first culprit. My grid model was a GLTF file that looked like this:

```json
{
  "buffers": [{
    "uri": "holodeck_grid.bin",
    "byteLength": 2928
  }]
}
```

GLTF is a text-based format. It references external binary files for the actual geometry data. This is fine for web browsers, desktop apps, and apparently iOS Simulators. But on a physical iOS device? Silent failure.

### Why It Fails

During development, Metro (React Native's bundler) serves assets via HTTP:

```
http://192.168.x.x:8081/assets/?unstable_path=./assets/holodeck_grid.gltf
```

The GLTF file loads fine. But then Filament's native C++/Metal code tries to fetch that relative `holodeck_grid.bin` reference. And it can't.

The reasons are murky but likely involve:

1. **iOS App Transport Security** — Even with `NSAllowsArbitraryLoads: true`, native code doesn't necessarily inherit JavaScript's network permissions
2. **Aggressive Sandboxing** — iOS sandboxes native code more heavily than JS
3. **Path Resolution** — Filament's iOS implementation expects local `file://` paths, not HTTP URLs with relative references

The frustrating part? No error. Just... nothing.

### The Fix

Convert GLTF to GLB. GLB is the binary version of GLTF—everything packed into a single self-contained file. No external references, no path resolution issues.

```bash
npx @gltf-transform/cli copy holodeck_grid.gltf holodeck_grid.glb
```

I made the conversion, rebuilt, deployed... and still nothing.

## Issue Two: LINE Primitive Mode

This is where it gets properly strange.

After converting to GLB, my grid model still broke rendering. But worse—it broke *everything*. Adding this one model caused the entire scene to stop rendering. Other models that worked perfectly became invisible too.

What fresh hell was this?

### The Clue

I ran `gltf-transform inspect` on the GLB:

```
│ mode  │ LINES │
```

That's the problem. The grid was using LINE primitive mode—a wireframe representation drawn with individual line segments.

This is perfectly valid GLTF. It works on iOS Simulator. It works on Android. But on iOS physical devices with Metal? Something in Filament's Metal backend doesn't handle LINE primitives correctly.

And instead of failing gracefully on just that model, it poisons the entire rendering pipeline.

### The Silent Catastrophe

This is the insidious part. You add a wireframe grid to your scene—seems harmless. Testing on simulator: works. Testing on Android: works. Deploy to a real iPhone: *everything* disappears.

If you're methodical, you'll eventually bisect your way to the problem model. If you're not, you'll question your sanity.

## The Solution

The rules for iOS physical devices are simple:

1. **Use GLB, not GLTF** — No external references
2. **Use TRIANGULAR primitives only** — No LINE mode, no POINTS mode

If you need a grid, build it from thin triangular strips instead of lines. If you need wireframes, use tube geometry or outline shaders.

Here's the compatibility matrix I wish I'd found at the start:

| Format | iOS Physical | iOS Simulator | Android |
|--------|-------------|---------------|---------|
| GLTF (external refs) | ❌ | ✅ | ✅ |
| GLB (LINE mode) | ❌ | ✅ | ✅ |
| GLB (TRIANGLES) | ✅ | ✅ | ✅ |

## Debugging Checklist

If your 3D models vanish on iOS physical devices:

1. **Test on simulator first** — If it works there, you've hit one of these issues
2. **Test on Android** — If it works there too, it's definitely iOS-specific
3. **Check your file format** — GLTF with external refs? Convert to GLB
4. **Inspect the GLB** — Look for LINE or POINTS primitive modes
5. **Bisect your models** — Remove them one by one to find the culprit

The inspection command:

```bash
npx @gltf-transform/cli inspect model.glb
```

Look for the `mode` field in the output. If it says anything other than `TRIANGLES`, that's your problem.

## The Broader Lesson

This experience crystallised something I've been thinking about: **the simulator is a lie**.

Not entirely, obviously. It's incredibly useful for rapid iteration. But there's a class of bugs that only exist on physical hardware—especially where native code interacts with platform-specific graphics APIs. iOS's Metal implementation has quirks that simply don't manifest in the simulated environment.

The painful truth is that if you're doing anything involving native code and 3D rendering, you need a physical device in your testing loop. Not occasionally. Constantly.

## Why This Isn't Documented Anywhere

I searched extensively before figuring this out. The issues are *known* in the sense that individual developers have hit them. But they're not documented in any central place because:

1. The React Native + Filament combination is fairly niche
2. The failure is silent, making it hard to search for
3. The simulator-vs-device discrepancy means many developers never see the issue during development

So I'm documenting it here. Maybe it saves someone else a day of staring at a blank screen.

## The Code That Works

```typescript
// ❌ GLTF with external .bin reference — fails on iOS device
const grid = require('./holodeck_grid.gltf');

// ❌ GLB with LINE primitive mode — also fails on iOS device
const grid = require('./wireframe_grid.glb');

// ✅ GLB with triangle primitives — works everywhere
const caseta = require('./caseta.glb');
```

When creating 3D assets for React Native, default to GLB with triangular geometry. Your future self, debugging on a physical device at 11pm, will thank you.

---

*Discovered December 2024 while building a 3D navigation app with Filament on React Native. The iPhone 11 involved has been forgiven but not forgotten.*

