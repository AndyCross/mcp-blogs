+++
title = "There Are No Emotions in Runtime Software"
date = "2026-01-13"
draft = false
tags = ["ai", "software-engineering", "philosophy", "hot-takes"]
+++

I read a piece this morning arguing that you shouldn't trust software you didn't "suffer" for. The premise being that personal struggle—the late nights, the debugging sessions, the moments of quiet desperation—somehow imbue code with trustworthiness. That suffering is the price of admission to understanding.

It's a romantic notion. I understand the appeal. But it's also, I think, deeply wrong.

## Suffering Is Not a Unit of Measurement

Here's the thing about suffering: it's wildly subjective. What destroys one developer is another's Tuesday afternoon. I've watched juniors spend three days on something I could solve in an hour—not because I'm smarter, but because I've already suffered through that particular flavour of hell a decade ago. Does their code become more trustworthy because they bled for it? Does mine become suspect because it didn't cost me enough?

The argument, taken to its logical conclusion, suggests that experts—people who've accumulated enough scar tissue to navigate problems efficiently—are somehow less invested in their work. That proficiency breeds detachment.

This is the opposite of what I've observed over 25 years. The people who really understand systems tend to care more, not less. They've seen enough failures to respect the blast radius. They've cleaned up enough messes to value doing it right the first time. Expertise doesn't breed complacency; it cultivates a kind of paranoid professionalism.

## Nobody Holds the Whole Thing Anymore

The article hints at something real though: concern about accountability when AI writes code. The "accountability black hole." And I get it—there's genuine anxiety here about losing the thread.

But here's a truth that predates AI by decades: nobody holds the whole system in their head anymore. Nobody has for a long time.

If you're working on anything of consequence, the codebase has already exceeded human cognitive capacity. You rely on team members, documentation, tests, monitoring. You build systems specifically because they're too complex for one mind. Microservices, CQRS, event sourcing—these aren't just architectural patterns, they're admission that we've given up on any single person understanding everything.

I've lost count of the times I've opened old code, thought "what kind of incompetent wrote this garbage," checked git blame, and found my own name staring back at me. Past-me had his reasons. Present-me has forgotten them. The code still runs. The suffering I endured writing it confers no special understanding today.

If you genuinely believe your particular module is so precious that only your suffering-certified brain can be trusted with it, I have news for you: you're working on something too small to matter, or you've fundamentally misunderstood how modern software gets built.

## You're Using AI Wrong

The accountability critique assumes a particular mode of AI usage: fire and forget. Generate code, deploy it, move on. This is indeed terrifying. It's also not how anyone serious is actually working.

AI should be pilot and navigator. I prompt, it suggests, I read, I question, I refine. It's a conversation, not a command. The accountability stays exactly where it always was: with the human who reviewed, tested, and shipped the code.

Using AI without oversight isn't sophisticated modern development. It's a toddler with a power tool. We don't blame the circular saw when someone cuts off their fingers whilst not paying attention.

The "suffering" model of trustworthiness mistakes the pain of the journey for the quality of the destination. But they're different things. Completely different things.

## The Projection Problem

And here's where it gets uncomfortable.

We keep anthropomorphising software. We talk about code we "trust" and systems we "understand." We project our emotional journey onto the artefact. But runtime software doesn't care about your suffering. It doesn't reward your dedication. It doesn't even know you exist.

Software is logic and state and memory allocation. It executes instructions. There's no gratitude for late nights. No loyalty for those who "really understand" it. The code that cost you six months of suffering and the code that an AI generated in thirty seconds—if they produce identical bytecode, they behave identically. The universe doesn't attach bonus points for human anguish.

Why do we keep projecting emotions onto something so fundamentally indifferent?

Maybe it's comforting. Maybe we need to believe that our struggle mattered, that the countless hours conferred something beyond mere functionality. That our relationship with the codebase is reciprocal somehow.

It isn't. It never was.

The software will run exactly the same whether you suffered for it or not. Whether you love it or hate it. Whether you remember how it works or have completely forgotten. It doesn't care. It can't care. It's not that kind of thing.

## The Real Question

The article frames this as an AI problem, but it's actually an older question: what do we owe ourselves in the process of building things?

If suffering confers no special quality to the output, why endure it? If AI can reduce the pain, why refuse the anaesthetic?

Perhaps there's value in the suffering itself—lessons learned, patterns recognised, taste developed. I believe there is. My $7 plugin post made the point that 25 years of experience was the enabling factor, not an incidental cost. But that's different from claiming the suffering transfers to the artefact.

The suffering changes *you*. It doesn't change the code.

And the code—cold, logical, indifferent—runs exactly the same either way.

---

*There's something almost liberating in accepting this. The pressure to have "earned" your understanding, to have paid appropriate dues, dissolves. What matters is whether the software works. Whether it's tested. Whether it's maintained. The emotional provenance is trivia.*

*Your runtime doesn't have feelings. Stop pretending it does.*

** I dont know whether I should link the original. Check medium for similar topics though **