+++
title = "When the API Gets Switched Off"
date = "2026-06-14"
draft = false
tags = ["ai", "uk", "sovereignty", "geopolitics", "regulation"]
series = ["european-ai-sovereignty"]
+++

On 13 June, Anthropic disabled Claude Fable 5 and Mythos 5 for every customer outside the United States. Not deprecated, not rate-limited, but disabled. US national security authorities raised concerns days after the public release, and the company wrote that "the net effect of this order is that we must abruptly disable Fable 5 and Mythos 5 for all our customers to ensure compliance."

Fable 5 was only generally available for about three days before it got pulled, so it's not as though it was load-bearing in anyone's production stack. It was available in mine, in CrossMoore EngineCore, but sitting there as a capability while we learned how it behaved, not running anything that mattered. The shape of it is what counts though. No migration window, no deprecation notice. One evening the calls just came back as an error.

I've spent a fair amount of this year writing about [why jurisdiction is the real constraint on European AI](/posts/european-ai-sovereignty/), about the [UK-EU regulatory split](/posts/compliance-as-code-two-europes/), and about the [practical sovereign inference stack](/posts/sovereign-inference-stack/). The argument running through all of it was that a US-controlled API isn't infrastructure you own. It's infrastructure you rent from a landlord who answers to a government that isn't yours. The risk was always a bit abstract but it isn't abstract now. A foreign administration decided a model was a national security matter and the model went away the same day, for everyone outside its borders. Since Anthropic didn't have a measure in place to geo-restrict, it went for everyone. Howveer I suspect it'll be back for Americans pretty soon. 

The European Commission reached straight for the word "sovereignty". Its spokesman said the move "further underlined Europe's need for technological sovereignty," and the bloc had already spent the month unveiling measures to cut its dependence on America and Asia for things like AI. Brussels has been building toward that line for years. The UK has mostly been hoping it wouldn't have to.

## The Reflexive Answer

The obvious response is: this proves Britain needs its own AI. And it does. An economy that runs critical workflows on a tool a foreign capital can switch off overnight has handed someone else a kill switch and called it procurement. Wanting independence from that is just good sense. This week made the argument better than any white paper could.

The trouble is that "build our own" is a slogan, and the slogan hides roughly two orders of magnitude of difficulty. Because when you actually ask what a sovereign British model would stand on, the answer is: almost everything that matters was made somewhere else. This is going to be missed by the majority of people in this discussion, so I wanted to reiterate it. 

## What "Our Own" Stands On

Start at the bottom and work up.

The architecture is a transformer, published by Google researchers in 2017. Every frontier model on earth, sovereign or not, is a variation on someone else's eight-(plus)-year-old paper. The training recipes, the scaling laws, the RLHF techniques, the evaluation methods: this is a global research literature, and the centre of gravity is American, with a heavy Chinese contribution and a steady leak of talent in both directions.

The weights you'd realistically start from are open, and they're not British. Llama is Meta's. Qwen is Alibaba's. Mistral is the closest thing Europe has to a frontier-adjacent open lab, and it's French and Apache-licensed, which is rather good and still not the same as sovereign by origin. A UK team building "its own" model in any reasonable timeframe is fine-tuning or distilling from weights that were trained on compute it didn't own, on data it never saw.

The hardware is NVIDIA, fabricated by TSMC in Taiwan on lithography from ASML in the Netherlands. There's no British silicon path to frontier training, and there won't be one this decade. Even the strictest sovereign stack I've ever sketched ran on the same GPUs as everyone else, reserved months in advance, paying the same NVIDIA tax.

So the honest version of British AI independence is a balancing act. It's standing on a stack of foreign giants and trying to make sure that when one of them turns around, you don't fall off. That's a much less satisfying sentence than "build our own", and it's the true one.

## Testing Isn't Building

The model that got pulled was assessed by the UK's AI Security Institute, which found it could exploit defended systems 73% of the time, a result one of the academics involved called a step change in capability. A British government institution had the expertise to red-team a frontier model, characterise a genuinely dangerous capability, and produce a number that everyone then quoted in the coverage.

Britain is properly good at evaluation. AISI is a real institutional asset, the kind of thing most countries don't have and can't easily stand up. But evaluating a frontier model and producing one are different sports played by different teams. We can tell you, with rigour, exactly how capable and how dangerous someone else's model is. We can't currently make one at that frontier. The gap between knowing and building is the whole problem, and it doesn't close because we're annoyed about an API.

## What Sovereignty Can Actually Mean

This is where the [sovereignty spectrum](/posts/european-ai-sovereignty/) from earlier in this series pays off. Sovereignty was never a binary you achieve. It's a degree of resilience you buy, and there are tiers: pragmatic, operational, strict.

The achievable British win, the one available this year rather than this decade, is operational. Take open weights you're allowed to run. Freeze them. Host them on UK soil, on infrastructure under UK law, with keys you hold and logs that can't be subpoenaed out from under you. You didn't control the training and you should be honest that you didn't. But the artefact is yours to run, and nobody in Washington can reach into your data centre and disable it on a Tuesday. A frozen Llama or Mistral checkpoint serving inference in London isn't at the frontier. It's also not going to vanish because of an export order.

That's the trade the Fable 5 episode actually surfaces. The frontier capability you rent can be revoked. The merely-very-good capability you host can't. For most real workloads, the second one was always the better deal, and a lot of organisations are about to discover they over-bought on capability and under-bought on control.

The frontier-lab ambition is worth having too. A British equivalent of Mistral, with public money behind it and a serious compute commitment, is a sensible national project. I just want us to hold two thoughts at once: it's worth starting, and it won't save you from next month's export order. The thing that saves you from next month's export order is a stack you can run without asking permission, today, on foundations you didn't lay.

## Ask for the Carve-Out Anyway

None of that happens this quarter. Operational resilience takes months, a British frontier lab takes years, and right now we're a long way back. So the sensible thing to do in the meanwhile is exactly what the government appears to be doing: get on the phone and ask for a carve-out. The weekend reporting has Downing Street lobbying Washington to put Britain on whatever approved-countries list replaces the blanket ban, and pushing for a surgical regime rather than a switch that takes everyone out at once. That's the right call. When you're this far behind, losing frontier access for a few months is a real cost, and refusing to ask for it back on principle would be daft.

Be honest about what a carve-out is, though. It's permission. Being on someone's approved list is still being at their whim, and the list can be shortened as easily as it was drawn up. A carve-out gets you back in the room. It doesn't get you the keys. So do both. Ask for the access today, and build the stack that turns the next ban into an inconvenience rather than an outage.

And the gap is the reason the carve-out matters. Last week the government announced £400m for AI chips from British firms and a £500m sovereign AI fund for start-ups. Both welcome, both real money. Both also small. NVIDIA is worth around $5tn, and its biggest customers spend hundreds of billions between them on its hardware every year. Nine hundred million pounds is a deposit, not a frontier programme. It buys a start, and a start needs time to compound. The carve-out is how you buy that time. You don't turn down the antibiotics because you'd rather have built a better immune system. You take the course, and then you go and build the immune system.

## The Cheap Lesson

Anthropic, for what it's worth, sounds as blindsided as its customers. The company said the authorities never identified a specific concern, that the demonstrated "jailbreak" turned up a handful of already-known minor vulnerabilities, and that other public models find the same ones without any bypass. It's suing the Pentagon over a separate "supply chain risk" designation, the first ever handed to a US company. None of which mattered to the customer outside the US, because the customer outside the US still woke up to a disabled model. The merits of the order are a fight between Anthropic and its own government. The dependency was yours.

That's the cheap version of this lesson, and we should take it gratefully. Nobody's hospital triage system went dark. Nobody's fraud pipeline fell over in production. We got a warning shot, loudly, with names attached, and the worst most people suffered was a scramble and a bad week.

The expensive version is the one where the switched-off model was load-bearing and the warning never came. Standing on the shoulders of giants is how all of this gets built, and there's no shame in it. The only rule is that you keep checking you can still stand when the giant decides to turn around. Last week it turned around. Worth finding out now, while it's cheap, exactly how far you'd have fallen.

---

## References

- **[Building AI Platforms Under European Sovereignty](/posts/european-ai-sovereignty/)**. The spectrum from pragmatic to strict sovereignty that this post leans on.
- **[Architecting for Two Europes with Compliance-as-Code](/posts/compliance-as-code-two-europes/)**. The UK-EU regulatory split in practice.
- **[A Practical Guide to the European Sovereign Inference Stack](/posts/sovereign-inference-stack/)**. What hosting frozen open weights on European soil actually involves, including the NVIDIA tax.
- **[AI Security Institute](https://www.aisi.gov.uk/)**, UK Government. The body that assessed the model's exploit capability.
- **[Attention Is All You Need](https://arxiv.org/abs/1706.03762)** (Vaswani et al., 2017). The transformer paper every frontier model still descends from.
