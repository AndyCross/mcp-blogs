+++
title = "Your Time Series Is Already Training Data"
date = "2026-07-05"
draft = false
tags = ["ai", "world-models", "iot", "energy", "agents"]
series = ["understanding-world-models"]
+++

At [Unimo](https://getunimo.com) we spend our days watching telemetry from energy hardware. Temperatures, states of charge, power flows, a reading every few seconds from devices sitting in buildings we'll never visit. Alongside the readings sits a second stream that gets far less attention: the commands. Turn this on. Back that off. Hold here.

For years I thought of those two streams as operations data. You keep them so you can draw dashboards, catch faults, and win arguments about what actually happened last Tuesday. Then I started reading about world models, and it slowly dawned on me that we'd been sitting on something else entirely. Interleave the two streams and you get a long record of *the world was like this, we did that, and here is what happened next*. That record is exactly what a world model is trained on. We hadn't been keeping logs. We'd been keeping lessons.

This post is the code-free version of that idea. There's a companion piece with TypeScript in it for those who want one, but nothing here needs it.

## A model of what happens next

A world model is a piece of software that answers one question: if things are like this, and I do that, what happens next?

You already own one. It's in your head, and you use it constantly. Your living room is at 14 degrees, it's 5 degrees outside, and you turn the heating on. You know roughly what follows: the room creeps up towards 15, then 16, faster at first, slower as it goes. You know that if you'd left the heating off, the room would drift down towards the outside temperature instead. Nobody gave you the equations for heat loss through a Victorian wall. You've simply lived through the experiment a few hundred times, and your brain fitted a model to the results.

That model earns its keep because it lets you try things without doing them. Before you programme the heating to come on at six, you run the plan forward in your imagination: on at six, warm by seven, that works. You test the future in your head and only then commit to it in the world. A world model gives software the same ability. Propose an action, roll it forward inside the model, look at where you'd end up, and only then touch the actual hardware.

## The raw material

To learn a model like that, you need experience, and experience has a specific shape. Each unit of it is a before, an action, and an after. The room was at 14 with the heater off. We turned the heater on. A minute later the room was at 14.6 with the heater running. That's one lesson. A battery was at 40 per cent, solar was producing 3 kilowatts, we told the battery to charge, and ten minutes later it was at 46 per cent. Another lesson.

Machine learning people call this supervised learning, which usually implies an expensive human labelling everything by hand. Here nobody labels anything. The world does it for you, because the answer to "what happens next?" arrives automatically one timestep later. You act, and the next sensor reading marks your homework.

Now look again at what a fleet of connected devices produces all day. Sensor readings, timestamped. Commands, timestamped. Join them up and you have millions of these before-action-after lessons, stretching back years, covering winters and heatwaves and that one week the firmware misbehaved. Anyone running a thermostat fleet, a battery estate, a pump network or a factory floor has been accumulating world-model training data since the day they switched on logging. Most of them, like me until recently, think of it as a dashboard feed.

## What the chatbots can't do

The obvious question is whether the AI everyone already uses does this. Large language models are also "what comes next" machines, after all. They predict the next word, given all the words so far, and they're astonishingly good at it.

Two things separate them from world models, and the first is the one I'd underline.

An LLM has no memory of its own. Every time you call one, you send it the entire conversation from the beginning, it reads the whole lot, produces some words, and forgets you existed. The continuity you experience in a chat is an illusion maintained by your app, which stores the transcript and resends it every turn. As conversations grow, the model's grip on the early parts weakens. Anyone who has built on these systems has watched one confidently misremember something from forty turns ago.

A world model keeps its own state. It carries a compact summary of the situation forward in time, folding in each new observation and each action as they happen. Ask it about the consequences of something that happened five hundred steps ago and it doesn't need to re-read five hundred steps of history, because everything that still matters is already baked into its current picture of the world.

The second difference is how actions are treated. To an LLM, an action is just more text in the transcript, no different in kind from a description of an action in a novel. A world model takes the action as a distinct input, and learning what actions *do* is its entire training objective.

The difference shows up when you ask "what if?". Ask a chatbot what happens if you turn the heater on and you'll get a fluent, plausible story about the room warming up, assembled from the millions of similar stories in its training data. Ask a world model and it runs your specific room forward: this temperature, this weather, this radiator. For writing an essay about heating, the story is fine. For deciding whether to actually switch several hundred real devices, I'd rather have the simulation.

## Why I'm writing this series

World models have moved from reinforcement-learning research into systems you can actually download and run, and most of the writing about them opens with dense notation. That's a shame, because the core idea is close to common sense, and the people best placed to use it (people who operate real things that log real data) are exactly the ones the notation drives away.

So this series builds the ideas up gently. The [next post](/posts/world-models-101/) shows the whole concept working in about forty lines of TypeScript, and later ones get into how these models learn from data, what the open-source options look like, and what all of this means for those of us with hardware in the field. If code isn't your thing, skim those parts. The ideas survive the journey without it.

If you operate devices and you're logging what they see alongside what you tell them to do, you're further ahead than you think. The training data problem, the one that stalls most machine-learning ambitions before they start, is one you solved years ago without noticing.
