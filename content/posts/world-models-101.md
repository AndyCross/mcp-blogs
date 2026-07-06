+++
title = "A World Model in Forty Lines of TypeScript"
date = "2026-07-06"
draft = false
tags = ["ai", "world-models", "typescript", "iot", "agents"]
series = ["understanding-world-models"]
+++

Every explanation of world models I've read starts the same way. A conditional probability, a subscript, a latent variable, and half the audience gone by paragraph three. Which is a shame, because the core idea fits in a few lines of code and most working programmers already have the intuition. They've just never had it pointed at.

So this series starts with TypeScript. We'll get to the equations eventually, but only once they're describing something you've already watched run. (If you'd rather have today's ideas with no code at all, the [previous post](/posts/world-models-001/) covers the same ground in prose.)

## The whole idea, in code

A world model answers one question: **if the world looks like this, and I do that, what happens next?**

State in, action in, predicted next state out. Here's the smallest honest version I can write, using a domain I spend a lot of my life in: a room with a heater.

```typescript
type State = {
  roomTemp: number;     // °C
  outsideTemp: number;  // °C
  heaterOn: boolean;
};

type Action = "turnHeaterOn" | "turnHeaterOff" | "wait";

function predict(state: State, action: Action): State {
  const heaterOn =
    action === "turnHeaterOn" ? true :
    action === "turnHeaterOff" ? false :
    state.heaterOn;

  // Heat leaks towards outside; the heater pushes back.
  const leak = (state.outsideTemp - state.roomTemp) * 0.1;
  const heat = heaterOn ? 1.5 : 0;

  return {
    roomTemp: state.roomTemp + leak + heat,
    outsideTemp: state.outsideTemp,
    heaterOn,
  };
}
```

`predict` is a world model. A hand-written, embarrassingly simple one, but structurally the real thing: it takes a state and an action and returns the next state. The fancy research systems (DreamerV3, LeCun's JEPA work, NVIDIA's Cosmos line) are this same function signature with the body learned from data instead of typed by me, and with `State` replaced by something the model invents for itself. We'll unpack both of those moves later in the series. The shape doesn't change.

And once you have that function, you get the properly useful trick for free: you can run the future without touching the present.

```typescript
function rollout(start: State, actions: Action[]): State[] {
  const trajectory = [start];
  for (const action of actions) {
    trajectory.push(predict(trajectory[trajectory.length - 1], action));
  }
  return trajectory;
}

const cold: State = { roomTemp: 14, outsideTemp: 5, heaterOn: false };

// What happens if I turn the heater on and leave it?
rollout(cold, ["turnHeaterOn", "wait", "wait", "wait"])
  .map(s => s.roomTemp.toFixed(1));
// [ '14.0', '14.6', '15.1', '15.6', '16.1' ]
```

No heater was harmed. We asked "what if?" four steps deep and got an answer in microseconds. Planning, in the world-model sense, is exactly this: propose a few candidate action sequences, roll each one forward inside the model, pick the future you like best, then execute only the first action for real.

## Action-result pairs are the raw material

My `predict` function encodes physics I made up. A real world model learns its `predict` from logged experience, and the unit of experience is the **action-result pair**: I was in state `s`, I did action `a`, I ended up in state `s'`.

```typescript
type Transition = {
  state: State;
  action: Action;
  nextState: State;
};

const experience: Transition[] = [
  {
    state: { roomTemp: 14.0, outsideTemp: 5, heaterOn: false },
    action: "turnHeaterOn",
    nextState: { roomTemp: 14.6, outsideTemp: 5, heaterOn: true },
  },
  {
    state: { roomTemp: 14.6, outsideTemp: 5, heaterOn: true },
    action: "wait",
    nextState: { roomTemp: 15.1, outsideTemp: 5, heaterOn: true },
  },
  // ...thousands more
];
```

Training a world model means fitting a function to this table: given the first two columns, predict the third. Which is just supervised learning with free labels, because the world hands you the answer one timestep later. Nobody annotates anything.

If you run devices in the field, look at that `Transition` type again. It's a telemetry log with the actuator commands joined on. Every thermostat, pump controller and battery system that's been logging sensor readings alongside its control decisions has been accumulating world-model training data for years. This is a big part of why I care: at [Unimo](https://getunimo.com) we live in exactly this stream of readings and commands from energy hardware, which is the realisation the [previous post](/posts/world-models-001/) was built around. The boring operational log is also the training set.

## So how is this different from an LLM?

An LLM is also a next-thing predictor, so it's fair to ask what's actually new here. Two things, and the first is the one I think matters most.

**Statefulness.** An LLM has no memory of its own. Every API call, you hand it the entire conversation and it recomputes everything from scratch, predicts some tokens, and forgets you existed. The "state" of your chat lives in your database, not in the model. It's a pure function over a context window, and when the conversation outgrows the window, the model's grip on what's true starts to slip. Anyone who's built an agent that gradually forgets what it did twenty steps ago has felt this.

A world model is stateful by construction. It carries a compact internal state forward from step to step, updating it as actions happen and observations arrive. Ask it about step 500 and it doesn't need to rummage through 500 steps of history, because everything that still matters is already folded into the current state.

**Actions are first-class.** For an LLM, an action is just more text. A tool call is tokens out, a tool result is tokens in, and the model must infer from prose what its action did. A world model takes the action as an explicit, typed input (the `a` in `predict(s, a)`) and is trained specifically on what actions *do*. Cause and effect is the whole curriculum rather than something absorbed second-hand from prose about other people's causes and effects.

Side by side:

| | LLM | World model |
|---|---|---|
| Predicts | next token | next state |
| Given | a context window of text | current state + an action |
| State between calls | none, resent every time | persistent, carried forward |
| "What if?" | narrates a plausible story | rolls the trajectory forward |
| Learns from | mostly static text | logged action-result pairs |

Ask an LLM what happens if you turn the heater on and it will tell you a *story* about the room warming up, and it will be a good story, statistically resembling the millions of similar stories in its training data. Ask a world model and it *runs* it, the same way our `rollout` did. For chatting, the story is fine. For deciding whether to actually flip a relay on hardware you're responsible for, I want the simulation.

To be fair to LLMs, they do pick up something world-model-ish internally. Interpretability work has found neurons in Llama-family models tracking space and time surprisingly well. But those representations are passive and rebuilt from scratch on every call. Having read a lot about rooms is not the same as tracking the temperature of this one.

## Where this series goes

This post is deliberately the shallow end. My `predict` cheats in ways that stop mattering only in toy problems: the state is three fields I chose by hand, the dynamics are made up, and nothing is learned. Real systems have to *invent* their own state representation from messy high-dimensional observations, learn the transition function from logs, and avoid some entertaining failure modes while doing it (there's one called representation collapse, where the model discovers it can score perfectly by declaring every state identical, which is the ML equivalent of a student answering every question with "no change").

Roughly where we're headed:

1. **The [code-free introduction](/posts/world-models-001/) and this post.** State, actions, rollouts. The function signature.
2. **Learning `predict` from data.** Replacing my hand-written physics with a fitted model, still in TypeScript, still no notation.
3. **Latent states.** What happens when the state is a sensor array or camera frame and the model has to compress it itself. This is where the field gets interesting and where the maths finally earns its keep.
4. **The open-source landscape.** DreamerV3, JEPA and friends, what you can run on your own hardware, and why that matters more than it first appears.
5. **World models and physical devices.** Where the action-result firehose from real hardware meets all of the above.

If you take one thing from today, take the function signature. An LLM completes your text. A world model, given where you are and what you're about to do, tells you where you'll be. Everything else in this series is elaboration on that difference.
