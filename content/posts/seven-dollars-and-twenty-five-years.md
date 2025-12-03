+++
title = "Seven Dollars and Twenty-Five Years: Building an Expo Plugin with AI"
date = "2024-12-03"
draft = false
tags = ["ai", "expo", "react-native", "android", "business"]
+++

I'm building an AI training tool for small language models that ultimately deploys on mobile. Nothing revolutionary there—it's a natural endpoint for a lot of the SLM work happening right now. But I hit a snag: Google Sign-In on Android.

Specifically, I needed native Google Sign-In using Android's modern Credential Manager API, with proper nonce support for Auth0 token exchange. Sounds niche, but it's actually a common requirement for any serious mobile auth flow.

## The Paywall Problem

Here's the thing: solutions exist. Expo has a vibrant plugin ecosystem. But the ones that solve this particular problem—native Credential Manager with nonce support—are almost all behind paywalls. Subscription services. Premium tiers. Enterprise plans.

I get it. People need to make money. But for a side project exploring SLM deployment, paying $20/month for an auth plugin feels wrong. Especially when the underlying Android APIs are well-documented and straightforward.

So I built my own.

## What the Plugin Does

The plugin adds native Google Sign-In to Android using the [Credential Manager API](https://developer.android.com/identity/sign-in/credential-manager). This is the modern replacement for the deprecated Google Sign-In SDK—it's what Google actually recommends now.

Key features:

- **One-Tap Experience**: That native bottom sheet UI users trust
- **Automatic Nonce Generation**: Required for secure token exchange with Auth0
- **Zero Runtime Config**: Works with Expo's managed workflow via config plugins
- **Just Android**: iOS gets Apple Sign-In via `expo-apple-authentication`—no need to reinvent that wheel

The usage is dead simple:

```typescript
import { signInWithGoogle, isGoogleSignInAvailable } from 'expo-plugin-google-signin';

async function handleSignIn() {
  if (!isGoogleSignInAvailable()) return;
  
  const result = await signInWithGoogle(WEB_CLIENT_ID);
  if (result) {
    // result.idToken contains the JWT with nonce
    // Exchange with Auth0 or your backend
  }
}
```

## How It Actually Works

The interesting bit is in the plugin mechanics. Expo config plugins let you modify native code at prebuild time—they're essentially code generators that run when you execute `npx expo prebuild`.

My plugin does three things:

**1. Adds Dependencies to build.gradle**

```groovy
implementation("androidx.credentials:credentials:1.3.0")
implementation("androidx.credentials:credentials-play-services-auth:1.3.0")
implementation("com.google.android.libraries.identity.googleid:googleid:1.1.1")
```

**2. Generates Kotlin Native Modules**

The plugin writes two Kotlin files directly into your app's package directory:

- `GoogleCredentialModule.kt` — The React Native bridge that calls Credential Manager
- `GoogleCredentialPackage.kt` — Registers the module with React Native

The module itself is straightforward—generate a nonce, build a `GetGoogleIdOption`, make the credential request, parse the response. About 140 lines of Kotlin.

**3. Registers the Package in MainApplication.kt**

The plugin patches `MainApplication.kt` to include the new package in the React Native initialization.

All of this happens at prebuild time. By the time you run `expo run:android`, the native code is already in place, looking exactly like you'd written it by hand.

## The Economics Question

Here's where it gets philosophical.

This plugin took me about 2 hours to build. The LLM token cost was around $7—mostly Claude helping me navigate the Credential Manager API and Expo's config plugin system.

But that's not the real cost, is it?

Those 2 hours were productive because I've spent 25 years learning how to guide these conversations. Knowing what questions to ask. Recognising when the AI is hallucinating versus when it's onto something. Understanding enough about Android's architecture to validate the generated code. Feeling when something is "right" even before running it.

So what's the equation?

```
$7 (tokens) + 2 hours (implementation time) + 25 years (accumulated context) = ?
```

I genuinely don't know how to calculate this. The $7 is measurable. The 2 hours has an opportunity cost. But the 25 years? That's harder. It's not like I was saving those years specifically for this moment. They were happening anyway—building other things, learning other lessons.

Maybe the equation is:

```
total_cost = token_cost + (hourly_rate × hours) + ???
```

Where `???` is some function of experience that I haven't figured out yet. Perhaps it's a multiplier on efficiency. Perhaps it's an enabling factor—without it, the other terms don't produce a result at all.

I suspect we need this equation. As AI tooling becomes more central to how we build software, we'll need better ways to value the human expertise that makes AI productive. The tokens are cheap. The time is measurable. But the decades of context that let you wield these tools effectively—that's the variable nobody's quantified yet.

## Try It Yourself

The plugin is MIT licensed and on npm:

```bash
npm install expo-plugin-google-signin
```

Add to your `app.json`:

```json
{
  "expo": {
    "plugins": [
      ["expo-plugin-google-signin", {
        "androidPackage": "com.yourcompany.yourapp"
      }]
    ]
  }
}
```

Then prebuild and run:

```bash
npx expo prebuild --clean
npx expo run:android
```

The [GitHub repo](https://github.com/AndyCross/expo-plugin-google-signin) has full documentation, including Auth0 integration guides and troubleshooting tips.

## The Broader Point

This isn't really about Google Sign-In. It's about the calculus of building versus buying in an AI-assisted world.

The paywalled solutions exist because someone invested their time and expertise to build them. That's legitimate. But the economics have shifted. When $7 and 2 hours can produce a working solution—if you have the right background—the threshold for "just build it" drops considerably.

The question is: who has that background? And what happens to the paywall business models when AI makes the "just build it" option increasingly viable?

What I do know is this: the 25 years weren't optional. Without them, the $7 buys you nothing but confident-sounding nonsense. The AI amplifies what you already have—it doesn't replace the judgement that comes from decades of getting things wrong in interesting ways.

We're going to need that equation. And when we figure it out, I suspect experience will be the dominant term.

---

*[expo-plugin-google-signin](https://github.com/AndyCross/expo-plugin-google-signin) is available on npm and GitHub. It's MIT licensed because I'd rather people use it than pay for something that should be straightforward.*

---

*A note for UK readers: yes, I'm aware that "nonce" has an entirely different and deeply unpleasant meaning in British English. In this context, it's strictly the cryptographic term—a number used once to prevent replay attacks. I didn't name it. Blame the security researchers.*

