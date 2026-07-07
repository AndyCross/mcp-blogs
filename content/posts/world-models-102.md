+++
title = "The World Model Equation Is a WHERE Clause"
date = "2026-07-07"
draft = false
tags = ["ai", "world-models", "typescript", "maths", "probability"]
series = ["understanding-world-models"]
math = true
+++

The [first code post](/posts/world-models-101/) in this series opened with a jab at explanations that lead with "a conditional probability, a subscript, a latent variable, and half the audience gone by paragraph three". I also promised the maths would eventually arrive, once it described something you'd already watched run. This post makes good on that: it takes exactly those three scary things, one at a time, and shows that you've been writing all of them in TypeScript for years under different names.

Here are the two equations the whole field rests on. First, what an LLM does:

$$P(x_{t+1} \mid x_{1:t})$$

And what a world model does:

$$P(s_{t+1} \mid s_t, a_t)$$

If your eyes just slid off those, you're just like me. By the end of this post you'll be able to read both aloud and mean it, and the only new idea along the way is a `filter` call.

## Subscripts are array indices

Start with the smallest scary thing. The subscript `t` is a loop counter. Mathematicians write \(x_t\) where we'd write `x[t]`: the item at position `t` in a sequence. Time, in these equations, is an array.

```typescript
const x = ["the", "cat", "sat", "on", "the"];

// x_t        -> x[t]
// x_{t+1}    -> x[t + 1]      the next one
// x_{1:t}    -> x.slice(0, t) everything up to now
```

(The one wrinkle: mathematicians count from 1 and we count from 0. This has caused more bugs than any other fact in this post, but it changes nothing conceptually.)

So \(x_{1:t}\) is "the whole history so far" and \(x_{t+1}\) is "whatever comes next". Similarly \(s_t\) is "the state now", \(a_t\) is "the action we take now", and \(s_{t+1}\) is "the state one tick later". No subscript in this series will ever do anything fancier than that.

## Conditional probability is a filter and a count

Now the big one: \(P(\textit{something} \mid \textit{something else})\). Read the bar as "given". \(P(s_{t+1} \mid s_t, a_t)\) reads as "the probability of each possible next state, given the state we're in and the action we're taking".

That sounds abstract until you compute one, so let's compute one. Take the thermostat logs from last time, with the temperature bucketed into `cold`, `mild` and `warm` to keep the example small:

```typescript
const log = [
  { state: "cold", action: "heaterOn", next: "mild" },
  { state: "cold", action: "heaterOn", next: "cold" },
  { state: "cold", action: "heaterOn", next: "mild" },
  { state: "cold", action: "heaterOn", next: "mild" },
  { state: "cold", action: "wait",     next: "cold" },
  { state: "mild", action: "heaterOn", next: "warm" },
  { state: "mild", action: "wait",     next: "cold" },
  { state: "mild", action: "wait",     next: "mild" },
];
```

To get \(P(s_{t+1} \mid s_t = \text{cold},\ a_t = \text{heaterOn})\), you keep only the rows where the condition held, then count what happened next:

```typescript
function pNext(log: Transition[], state: string, action: string) {
  const matches = log.filter(t => t.state === state && t.action === action);
  const dist = new Map<string, number>();
  for (const t of matches) {
    dist.set(t.next, (dist.get(t.next) ?? 0) + 1 / matches.length);
  }
  return dist;
}

pNext(log, "cold", "heaterOn");
// Map(2) { 'mild' => 0.75, 'cold' => 0.25 }
```

That `Map` is the left-hand side of the equation. "Given cold and heater on, it's 75% mild next and 25% still cold." The condition (everything right of the bar) became the `filter` predicate. The probability (everything left of it) came from counting the survivors. If you've ever written `SELECT next, COUNT(*) FROM log WHERE state = 'cold' AND action = 'heaterOn' GROUP BY next`, you have computed a conditional probability, and the notation is just that query with the SQL boiled off.

Notice the function returns a distribution rather than a single answer. Last time our `predict` returned exactly one next state, which quietly assumed the world is deterministic. Real rooms aren't: sometimes someone opens a window. The \(P\) is the honest version, giving every possible next state a weight.

## Why the LLM equation needs a giant neural network

Now re-read the LLM equation with the same eyes:

$$P(x_{t+1} \mid x_{1:t})$$

Same shape, so the same trick should work: filter for every place the condition held, count the continuations.

```typescript
// P(next word | "the cat sat on the")
const matches = corpus.filter(seq => startsWith(seq, ["the", "cat", "sat", "on", "the"]));
```

And it does work, for short histories. The problem is on the right of that bar. The world model conditions on two values, a state and an action, and however long you run the system, that condition stays two values wide. The LLM conditions on \(x_{1:t}\), the *entire history*, and \(t\) grows every step. By the time your history is a paragraph long, no corpus on Earth contains an exact match, `matches` is empty, and counting tells you nothing.

That gap between "the condition almost never recurs exactly" and "we still need an answer" is the entire reason LLMs are enormous. The neural network exists to generalise across histories that are similar rather than identical, because filtering for identical ones stopped working. Which reframes the thing I keep saying about statefulness: the world model's fixed-width condition is a design decision to keep the right-hand side of the bar small, and everything about carrying state forward flows from it.

## A latent variable is a private field

One scary thing left. In the world model equation, `s` is called a *latent* state, and latent just means hidden. The person it's hidden from is you: it never appears in your telemetry.

In the toy example I chose the state myself: three buckets, picked by hand, visible in every log row. Real systems can't do that. The observations coming off a real device might be forty sensor channels, and which summary of them matters for prediction is exactly the thing nobody knows how to write down. So the model is allowed to invent its own summary and keep it to itself:

```typescript
class WorldModel {
  #state: Float32Array;  // s_t lives here, and nowhere in your logs

  observe(o: Observation) {
    // fold the new reading into #state
  }

  act(a: Action): Distribution<Observation> {
    // predict what we'll see next, given #state and a
  }
}
```

The latent state is the `#state` field, an internal detail that never reaches the public API or the data you collect. You judge it entirely by whether the predictions coming out of `act` are any good. When researchers talk about a model "learning a representation", they mean learning what to keep in that private field. How that learning works without anyone ever seeing the field directly is a properly interesting question, and it's the next post.

## Reading them aloud

Back to the top, once more, with fluency.

$$P(x_{t+1} \mid x_{1:t})$$

"The probability of each possible next token, given the whole history so far." A filter on an ever-growing condition, approximated by a very large network because exact matches ran out.

$$P(s_{t+1} \mid s_t, a_t)$$

"The probability of each possible next state, given the current state and the chosen action." A filter on a condition that never grows: one private summary of the world, one thing you're about to do.

Two equations, one `filter` call, and the bar was a WHERE clause all along. When the notation gets heavier later in the series (it will, gently), every new symbol gets this same treatment: code first, then the shorthand for the code.
