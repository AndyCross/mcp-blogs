+++
title = "Compute Isn't the Constraint"
date = "2026-06-17"
draft = false
tags = ["ai", "uk", "sovereignty", "geopolitics", "research", "talent"]
series = ["european-ai-sovereignty"]
+++

After [When the API Gets Switched Off](/posts/when-the-api-gets-switched-off/) went up, Bram De Buyser, an old friend, wrote back and put his finger on a line of thought I'd neglected. The frontier-lab ambition got one paragraph and a vague nod to "a serious compute commitment", and that nod is where the strategy is thinnest. His point, roughly:

> The Sovereign AI fund is primarily about compute access, but labs like Anthropic, OpenAI and Mistral aren't pumping out better models just because of compute access. They're putting in core research the others don't have yet, and that requires research staff and experimenting, not just training or inference compute. If the UK wants to compete on the frontier, it needs to come up with the actual frontier, not just train models based on papers from 2022 that the big labs already consider obsolete.

He's right, and once I pulled the numbers it looked worse than that one paragraph let on. The £500m fund is solving for the input that stopped being scarce a while ago.

## What the Fund Actually Buys

Look at how the money is structured rather than how it's described. The headline is a £500m sovereign AI fund and £400m for AI chips. The first tranche of backed companies (Cosine, Cursive, Odyssey, Doubleword, Prima Mente and the rest) gets access to the AIRR supercomputing network plus some direct equity, and there's a £282m carve-out to build proprietary UK datasets. Strip the press release and it's three things: compute hours, a bit of venture capital, and training data.

Every one of those is an input you can buy at market price. None of them is the thing that separates a frontier lab from a competent engineering team. You can hand a British startup a slice of a supercomputer and a clean dataset and what you get back is a well-trained model built from ideas that are already public. That's the trap, and the data on open models shows exactly how deep it is.

## The Reimplementation Treadmill

Published research lags the real frontier, and you can measure the gap. Epoch's Capabilities Index puts the best open-weight models about three to four months behind the closed frontier on a composite measure. On public benchmarks the gap is four to six months, which flatters the open models because those benchmarks leak into training sets. On private, unreleased benchmarks (the ones you can't optimise against) the lag stretches to eight to ten months. And if you measure by raw training compute deployed, it's fifteen to sixteen months. Meta's Llama 3.1 405B took roughly sixteen months to match the benchmark performance of the *first* GPT-4.

A team that reads papers and reimplements is structurally a generation behind and stays there, because the target moves at the speed of the unpublished work they aren't doing. The frontier labs publish the trick the quarter after it stops being their edge. So a fund that buys compute so domestic teams can train on the public literature is, by construction, financing the efficient replication of yesterday's breakthroughs. You become a very capable taker of technology. You do not become a maker of it.

This is the third term I left implicit last time. "Testing isn't building" had a sibling. Testing, building and researching are three different sports. Testing is evaluating and red-teaming someone else's model, which Britain does as well as anyone through AISI. Building is hosting and fine-tuning open weights on your own soil, which is the achievable operational win I keep banging on about and which protects you from the next export order. Researching is generating the architecture and the training recipe that define the next generation. The fund is aimed at building and calling it research.

## DeepSeek Did It for Pocket Change

Then there's DeepSeek-V3. Near-frontier performance on reasoning, coding and maths, trained for about $5.57m of GPU time, a rounding error inside a £500m fund. The capability came out of research, not cluster size: Multi-head Latent Attention to compress the KV cache, an auxiliary-loss-free mixture-of-experts routing scheme, an FP8 mixed-precision training framework that held numerically stable without rollbacks, and the DualPipe scheme that overlapped communication with computation to keep the GPUs near-saturated.

None of those came from hardware. They came from a team being clever about the maths, repeatedly, with the freedom to try things that might not work. DeepSeek was, by its own account, compute-constrained relative to the American labs, and got close to the frontier anyway. The lever was exactly the thing a compute fund doesn't fund. If anything, the lesson cuts the other way: hand a team unlimited retail GPU hours and you remove the pressure that produced MLA and DualPipe in the first place.

## The Talent Runs Uphill

The American lead at the frontier is imported, and that should worry anyone designing the fund. US universities educate around 24% of the world's elite AI researchers but US institutions employ 59% of them, with an 80% retention rate and a net inflow of more than 1,600 top researchers. The pipeline that feeds it is foreign: roughly 64% of new AI PhDs in North America are international students, and about 82% of those stay after graduating.

China is the cautionary tale. It educates 38% of the global elite pool, the largest share of anyone, and employs 11% of them. Net flow: minus 1,248. Something like 72% of China-educated top researchers end up working in the United States. Vast domestic investment in infrastructure has not stopped the people from leaving for where the best work is.

The UK's position is precarious in a specific way. Retention is a respectable 65% and net flow is positive but tiny, plus 92. Elite production is 4% of the global total. So the absolute numbers are small and the gravitational pull is enormous. In 2025, private AI investment in the US hit $285.9bn, against $12.4bn in China and $4.7bn for the whole of Europe's generative AI sector. A fund that finances a domestic lab is, in that field, building a training ground whose best researchers can be hired away by firms with compensation budgets it cannot come close to matching. You risk running a state-subsidised feeder academy for Silicon Valley.

## We Already Outsourced Our Frontier

It's tempting to think the UK at least has a frontier research culture to build on, because DeepMind is in London. The citation data says otherwise. In 2022 the UK contributed 16 papers to the 100 most-cited AI papers globally. Eleven of those 16, just under 69%, were DeepMind's. The concentration has been rising, not falling.

That isn't a broad sovereign research base. It's one extremely good laboratory, owned by Google, that happens to sit on British soil. If Google consolidates that work into California, or DeepMind's priorities shift, the UK's claim to frontier research thins out to almost nothing overnight. Which is the same dependency the original post was about, one layer up the stack. We worried about renting the model. We're also renting the research culture that makes models, and we don't fully own the building it sits in.

## The Clock Started Years Ago

There has been a tendency in recent years to romanticise Britain's ability to privateer its way to global competition. The Brexiteers and their toy story are the prime exemplar, though the instinct runs wider than them. It is fundamentally unrealistic. The investment that actually builds capability is patient and dull, and even within the EU it dwarfs anything Britain commits. Sophia Antipolis, the technology park the French have been growing above Antibes since 1969, is half a century of steady public money in a single place. The UK has never matched that, and a £500m fund announced alongside a supercomputer does not begin to. Agility is not a substitute for scale, and pretending otherwise is the toy story all over again.

No fund can price the part that matters most here. A frontier researcher is a ten-year artefact. The transformer paper landed in 2017, and the people who can now extend that line of work rather than reimplement it were already in graduate school when it did. The ones running labs today were doing their doctorates around the time DeepMind was founded in 2010. You don't hire that capability into existence, you grow it, and the growing takes the better part of a decade. Money committed in 2026 buys a cohort that matures around 2034. The reimplementation-lag numbers measure where the published frontier sits this month. They say nothing about the fact that the people who set it started a very long time before this month.

The cheap moment to build a sovereign research base was the early 2010s, when the field was small, the salaries were academic, and the talent hadn't been bid up by a hundred billion dollars of American capital. Hire a frontier-relevant researcher in 2015 and you paid a university professor's wage. Try for the equivalent now and you're bidding against the $285.9bn that went into US private AI last year, for a person who is one of a few hundred in the world and knows exactly what they're worth. The window when this was affordable closed somewhere around the point GPT-3 made the commercial case obvious, and it isn't reopening at a price the Treasury will like.

So the honest framing isn't "how do we win the frontier with £500m." It's that we're a decade late to a race that compounds, and the gap widens while we build. Every year the UK didn't fund long-horizon research, the labs that did were quietly accumulating people, institutional memory, and the web of who-trained-whom that no cheque shortcuts. That's not an argument for doing nothing. It's an argument for being honest about what the money can still buy, because a fund that pretends the lead time is zero will spend it on the photogenic thing and miss the achievable one.

## What I'd Spend It On

The fund isn't wasted. Operational sovereignty, hosting frozen open weights on UK soil under UK law, is real and worth paying for, and a chunk of this money buys it. But if the stated goal is to compete on the frontier, the allocation is pointed at the wrong constraint, and three changes would point it back.

Spend on research endowments, not compute vouchers. Long-horizon, non-commercial grants on the Bell Labs model, where the point is high-risk basic research with no deliverable next quarter. That's the only kind of money that produces an MLA or a DualPipe, and it's the kind venture equity and supercomputer time structurally can't.

Compete for the people directly. Elite researchers are mobile, so immigration policy and pay are the levers. National research chairs with packages built to go toe-to-toe with hyperscaler offers, fast-tracked visas, and the freedom to fail are worth more per pound than another rack of GPUs. The talent numbers say retention is the whole game, and we currently lose it on money.

Pick a niche and own it. Trying to match American brute-force scaling is a losing trade for a mid-tier nation. Hardware-efficient architectures, low-precision training, custom compilers, the DeepSeek style of doing more with less, is a defensible specialism, and it happens to be where research cleverness beats capital most reliably.

There's a people problem before any of that, mind. I've read through the grants and the funding actually on offer, and it's depressingly middle management. The whole apparatus has the energy of the Golgafrincham Ark Fleet Ship B, the one Douglas Adams loaded with the telephone sanitisers and the management consultants and fired off to colonise a planet while everyone who could actually do something stayed home. Plenty of delivery partners, governance frameworks and stakeholder workshops, not much sign of anyone who has shipped a model that mattered. It could be so much better than this. My business partner has worked inside funds like these before, and I'd hand him the cheque a thousand times over before I'd hand it to this lot.

None of the right answers are as photogenic as a supercomputer launch, which is presumably why a compute fund is what we got. But Bram was right. The frontier isn't a pile of chips you haven't bought yet. It's a few hundred people doing work nobody has published, and you don't get them by renting them a cluster. You get them by being the place that pays for the experiment that fails. Thanks, Bram.

---

## References

- **[When the API Gets Switched Off](/posts/when-the-api-gets-switched-off/)**. The post this one answers, on the Fable 5 shutdown and the limits of "build our own".
- **[Building AI Platforms Under European Sovereignty](/posts/european-ai-sovereignty/)**. The pragmatic/operational/strict sovereignty spectrum these arguments lean on.
- **[A Practical Guide to the European Sovereign Inference Stack](/posts/sovereign-inference-stack/)**. What hosting frozen open weights actually involves.
- **[Open models lag state-of-the-art closed models](https://epoch.ai/data-insights/open-closed-eci-gap)**, Epoch AI. The capability-lag figures.
- **[The Global AI Talent Tracker 3.0](https://archivemacropolo.org/interactive/digital-projects/the-global-ai-talent-tracker)**, MacroPolo. Elite researcher production, employment and retention flows.
- **[DeepSeek-V3 Technical Report](https://arxiv.org/html/2412.19437v1)**. MLA, DualPipe, FP8 training, and the training-cost numbers.
- **[UK's over-dependence on Google's DeepMind](https://www.verdict.co.uk/uks-over-dependence-on-googles-deepmind-harms-its-global-ai-competitiveness/)**, Verdict. The concentration of UK top-cited output in one corporate lab.
- **[The 2026 AI Index Report](https://hai.stanford.edu/ai-index/2026-ai-index-report)**, Stanford HAI. Publication shares and private investment figures.
- **[AI firms backed through the UK's Sovereign AI fund](https://www.gov.uk/government/news/ai-firms-pioneering-drug-discovery-cheaper-supercomputing-and-more-get-first-backing-through-uks-sovereign-ai)**, GOV.UK. How the first tranche of the fund is allocated.
