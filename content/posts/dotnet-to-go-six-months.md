+++
title = "Six Months In: Was It Worth It?"
date = "2025-06-28"
draft = false
tags = ["go", "dotnet", "retrospective", "career", "csharp"]
series = ["step-over-to-go"]
+++

Six months ago, I started this series with a simple goal: document learning Go as an experienced C# developer. Not a tutorial (there are plenty of those) but an honest account of the transition.

Now, with half a year of production Go code behind me, it's time for a retrospective. Was it worth it? Would I do it again? What would I tell past-me?

## The Learning Curve

**Weeks 1-2**: Syntax adjustment. Easy. Go is a small language.

**Weeks 3-4**: Fighting the language. Trying to write C# in Go. Wondering why there are no generics (there are now), no exceptions (by design), no classes (by design).

**Months 2-3**: Acceptance. Starting to see why Go makes its choices. Writing idiomatic code. Stopping fighting.

**Months 4-6**: Fluency. Thinking in Go. Actually preferring some of its approaches. Not reaching for C# patterns anymore.

The inflection point was around month two. That's when I stopped asking "why doesn't Go have X?" and started asking "how do Go developers solve this?"

## What I Got Right

**Starting with real projects**: I didn't do tutorials. I built things I needed. That forced me to solve actual problems, not artificial exercises.

**Reading the standard library**: Go's stdlib is readable and idiomatic. I learned more from reading `net/http` source than from any guide.

**Accepting the constraints**: Once I stopped resisting (no inheritance, explicit errors, no LINQ), I could appreciate the benefits.

**Keeping notes**: This blog series was originally just my notes. Writing forced me to understand things properly.

## What I Got Wrong

**Overusing channels**: Early on, I used channels for everything. Turns out, sometimes a mutex is simpler. "Share memory by communicating" isn't "always use channels."

**Fighting gofmt**: I tried to configure formatting. You can't. I wasted time before accepting the One True Format.

**Importing my architecture**: I tried to recreate C#-style layered architecture in Go. It felt wrong because it was wrong. Go projects structure differently.

**Ignoring the ecosystem**: I tried to stick to stdlib for too long. Libraries like `chi`, `sqlx`, and `zerolog` exist for good reasons. Use them.

## The Productivity Question

Here's the honest answer: I'm about as productive in Go as I was in C#.

- For HTTP services, similar productivity
- For CLI tools, Go is faster (single binary, fast compilation)
- For complex business logic with lots of types, C# might be faster (LINQ, pattern matching, rich type system)
- For deployment and operations, Go is significantly simpler

The productivity isn't dramatically different. What's different is *what kind* of work is easy.

## What I Build Now

Six months in, I naturally reach for Go when:

- Building microservices or APIs
- Writing CLI tools
- Creating Lambda functions
- Anything that needs cross-platform binaries
- Projects where deployment simplicity matters

I'd still use C# for:

- Complex domain modelling (richer type system)
- Windows-specific applications
- Teams that know .NET well
- Projects requiring mature ORMs or complex LINQ

## The Things I Still Miss

Even after six months:

- **LINQ**. Every time I write a for loop to filter a slice.
- **Pattern matching**. When I have complex type dispatch.
- **IDE refactoring**. Rider's tools are unmatched.
- **Rich generics**. Go's generics are adequate, not great.

These aren't dealbreakers. But they're real gaps that don't disappear with familiarity.

## The Things I Can't Give Up

Equally persistent:

- **Fast builds**. Going back to slow compilation feels painful.
- **Single binaries**. Deployment simplicity is addictive.
- **Explicit errors**. I now find exception-based code harder to reason about.
- **gofmt**. No formatting debates. Ever. Bliss.

## Would I Do It Again?

Yes. Without hesitation.

Not because Go is objectively better than C#. It isn't, not in all dimensions. But because:

1. **Learning a different paradigm expanded my thinking**. Go's constraints forced different solutions. Some of those solutions are better.

2. **Professional flexibility increased**. I can now take Go or C# roles. More options is good.

3. **It made me better at C# too**. Understanding Go's explicit error handling made me more careful in C#. Understanding Go's interface design influenced how I design C# interfaces.

4. **It was fun**. Learning something new after years of expertise is energising.

## Advice for C# Developers Considering Go

**Do it if:**
- You want to expand your thinking
- You're building services where deployment simplicity matters
- You're curious about different paradigms
- Your team or job requires it

**Don't expect:**
- Go to be better at everything
- The transition to be instant
- Your C# knowledge to transfer completely
- To never want C# features

**The mindset shift:**
- Go is simple, not primitive
- Constraints can be features
- Different isn't worse
- "Boring" code is often good code

## Six Months vs Day One

| Aspect | Day One | Six Months |
|--------|---------|------------|
| Error handling | Tedious | Appreciated |
| No inheritance | Limiting | Liberating |
| Small stdlib | Lacking | Focused |
| gofmt | Annoying | Essential |
| Deployment | Nice | Can't go back |
| Productivity | Lower | Equivalent |
| Enjoyment | Frustration | Comfort |

## The Final Word

Was it worth it?

For me, absolutely. The operational benefits alone (fast builds, single binaries, simple deployment) have saved more time than the learning curve cost. The expanded perspective has made me a better engineer.

But I want to be clear: this isn't a "Go is better than C#" conclusion. It's a "Go is *different* from C#, and understanding both makes you better" conclusion.

C# is an excellent language with a mature ecosystem. Go is an excellent language with different trade-offs. Knowing both lets you pick the right tool for each job.

If you've followed this series, I hope it's been useful. Not as a Go tutorial (there are better resources for that) but as an honest map of the terrain from someone who's walked it.

The learning curve is real. The frustrations are real. And so are the benefits.

Thanks for reading.

---

*This concludes the C# to Go series. All 48 posts are available in the archive. If you found it useful, I'd love to hear about your own transition experiences. Find me on the usual channels.*
