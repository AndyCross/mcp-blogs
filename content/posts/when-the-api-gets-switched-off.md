+++
title = "When the API Gets Switched Off"
date = "2026-06-14"
draft = false
tags = ["ai", "uk", "sovereignty", "geopolitics", "regulation"]
series = ["european-ai-sovereignty"]
+++

On 13 June, Anthropic disabled Claude Fable 5 and Mythos 5 for every customer outside the United States. Not deprecated, not rate-limited. Disabled. US national security authorities raised concerns days after the public release, and the company wrote that "the net effect of this order is that we must abruptly disable Fable 5 and Mythos 5 for all our customers to ensure compliance."

Claude Fable 5 was only generally available for about three days before it was pulled, so it is not as though it was load-bearing in anyone's production stack. It was in mine, in CrossMoore EngineCore, but sitting there as a capability while we learned how it behaved, not running anything that mattered. The shape of it is what counts though. No migration window, no deprecation notice. One morning the calls just came back as an error.

I have spent a fair amount of this year writing about [why jurisdiction is the real constraint on European AI](/posts/european-ai-sovereignty/), about the [UK-EU regulatory split](/posts/compliance-as-code-two-europes/), and about the [practical sovereign inference stack](/posts/sovereign-inference-stack/). The argument running through all of it was that a US-controlled API is not infrastructure you own. It is infrastructure you rent from a landlord who answers to a government that is not yours. The risk was always a bit abstract. It is not abstract now. A foreign administration decided a model was a national security matter and the model went away the same week, for everyone outside its borders.

The European Commission reached straight for the word. Its spokesman said the move "further underlined Europe's need for technological sovereignty," and the bloc had already spent the month unveiling measures to cut its dependence on America and Asia for things like AI. Brussels has been building toward that line for years. The UK has mostly been hoping it would not have to.

## The reflexive answer is correct and useless

The obvious response is: this proves Britain needs its own AI. And it does. An economy that runs critical workflows on a tool a foreign capital can switch off overnight has handed someone else a kill switch and called it procurement. Wanting independence from that is not paranoia. It is just reading the news.

The trouble is that "build our own" is a slogan, and the slogan hides roughly two orders of magnitude of difficulty. Because when you actually ask what a sovereign British model would stand on, the answer is: almost everything that matters was made somewhere else.

## What "our own" is actually built on

Start at the bottom and work up.

The architecture is a transformer, published by Google researchers in 2017. Every frontier model on earth, sovereign or not, is a variation on someone else's eight-year-old paper. The training recipes, the scaling laws, the RLHF techniques, the evaluation methods: this is a global research literature, and the centre of gravity is American, with a heavy Chinese contribution and a steady leak of talent in both directions.

The weights you would realistically start from are open, and they are not British. Llama is Meta's. Qwen is Alibaba's. Mistral is the closest thing Europe has to a frontier-adjacent open lab, and it is French and Apache-licensed, which is wonderful and still not the same as sovereign by origin. A UK team building "its own" model in any reasonable timeframe is fine-tuning or distilling from weights that were trained on compute it did not own, on data it never saw.

The hardware is NVIDIA, fabricated by TSMC in Taiwan on lithography from ASML in the Netherlands. There is no British silicon path to frontier training, and there will not be one this decade. Even the strictest sovereign stack I have ever sketched ran on the same GPUs as everyone else, reserved months in advance, paying the same NVIDIA tax.

So the honest version of British AI independence is not a clean break. It is standing on a stack of foreign giants and trying to make sure that when one of them turns around, you do not fall off. That is a much less satisfying sentence than "build our own," and it is the true one.

## The UK knows how to test these models. That is not the same as building them

Here is the part of the story that should sting a little.

The model that got pulled was assessed by the UK's AI Security Institute, which found it could exploit defended systems 73% of the time, a result one of the academics involved called a step change in capability. Read that again. A British government institution had the expertise to red-team a frontier model, characterise a genuinely dangerous capability, and produce a number that people quoted in the coverage.

Britain is properly good at evaluation. AISI is a real institutional asset, the kind of thing most countries do not have and cannot easily stand up. But evaluating a frontier model and producing one are different sports played by different teams. We can tell you, with rigour, exactly how capable and how dangerous someone else's model is. We cannot currently make one at that frontier. The gap between knowing and building is the whole problem, and it does not close because we are annoyed about an API.

## What sovereignty can actually mean here

This is where the series spectrum earns its keep. Sovereignty was never a binary you achieve. It is a degree of resilience you buy, and there are tiers.

The achievable British win, the one available this year rather than this decade, is operational. Take open weights you are allowed to run. Freeze them. Host them on UK soil, on infrastructure under UK law, with keys you hold and logs that cannot be subpoenaed out from under you. You did not control the training and you should be honest that you did not. But the artefact is yours to run, and nobody in Washington can reach into your data centre and disable it on a Tuesday. A frozen Llama or Mistral checkpoint serving inference in London is not at the frontier. It is also not going to vanish because of an export order.

That is the trade the Fable 5 episode actually surfaces. The frontier capability you rent can be revoked. The merely-very-good capability you host cannot. For most real workloads, the second one was always the better deal, and a lot of organisations are about to discover they over-bought on capability and under-bought on control.

The frontier-lab ambition is worth having too. A British equivalent of Mistral, with public money behind it and a serious compute commitment, is a sensible national project. I just want us to hold two thoughts at once: it is worth starting, and it will not save you from next month's export order. The thing that saves you from next month's export order is a stack you can run without asking permission, today, on foundations you did not lay.

## The cheap lesson

Anthropic, for what it is worth, sounds as blindsided as its customers. The company said the authorities never identified a specific concern, that the demonstrated "jailbreak" turned up a handful of already-known minor vulnerabilities, and that other public models find the same ones without any bypass. It is suing the Pentagon over a separate "supply chain risk" designation, the first ever handed to a US company. None of which mattered to the customer outside the US, because the customer outside the US still woke up to a disabled model. The merits of the order are a fight between Anthropic and its own government. The dependency was yours.

That is the cheap version of this lesson, and we should take it gratefully. Nobody's hospital triage system went dark. Nobody's fraud pipeline fell over in production. We got a warning shot, loudly, with names attached, and the worst most people suffered was a scramble and a bad week.

The expensive version of the lesson is the one where the switched-off model was load-bearing and the warning never came. Standing on the shoulders of giants is how all of this gets built, and there is no shame in it. The only rule is that you keep checking you can still stand when the giant decides to turn around. Last week it turned around. It is worth finding out now, while it is cheap, exactly how far you would have fallen.

---

## References

- **[Building AI Platforms Under European Sovereignty](/posts/european-ai-sovereignty/)**. The spectrum from pragmatic to strict sovereignty that this post leans on.
- **[Architecting for Two Europes with Compliance-as-Code](/posts/compliance-as-code-two-europes/)**. The UK-EU regulatory split in practice.
- **[A Practical Guide to the European Sovereign Inference Stack](/posts/sovereign-inference-stack/)**. What hosting frozen open weights on European soil actually involves, including the NVIDIA tax.
- **[AI Security Institute](https://www.aisi.gov.uk/)**, UK Government. The body that assessed the model's exploit capability.
- **[Attention Is All You Need](https://arxiv.org/abs/1706.03762)** (Vaswani et al., 2017). The transformer paper every frontier model still descends from.
