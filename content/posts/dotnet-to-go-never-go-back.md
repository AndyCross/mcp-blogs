+++
title = "What I'll Never Go Back For"
date = "2025-02-01"
draft = false
tags = ["go", "dotnet", "reflection", "csharp"]
+++

Last time I talked about what I miss from C#. Now let's flip it: what has Go given me that I'd genuinely struggle to give up?

Some of these I expected to like. Others surprised me. All of them have changed how I think about software.

## Fast Compilation

This sounds minor until you've lived it. `go build` takes seconds. For a large project, maybe 10-15 seconds. That's it.

Coming from .NET where build times can stretch into minutes for larger solutions, the fast feedback loop in Go is transformative. I run the compiler constantly. I try things. I iterate quickly.

When I go back to C# projects now, the build times feel painful in a way they didn't before.

## Single Binary Deployment

I keep coming back to this because it's so operationally clean.

```bash
scp myapp server:/usr/local/bin/
ssh server 'systemctl restart myapp'
```

No runtime installation. No SDK version matching. No framework compatibility. Just a file that runs.

Every time I deploy a .NET app and deal with runtime versions or container size, I miss Go's simplicity.

## Cross-Compilation

Building for Linux from my Mac:

```bash
GOOS=linux GOARCH=amd64 go build -o myapp
```

No Docker. No virtual machines. No cross-compiler toolchains. Just environment variables.

I now consider "can I easily build for all platforms?" when evaluating any tool. Go spoiled me.

## Explicit Error Handling

I know, I know—I literally wrote a post about `if err != nil` being tedious. But here's the thing: after months of it, I've come to appreciate the explicitness.

Every line that can fail is marked. Every error is handled (or explicitly ignored). No hidden control flow. When something goes wrong, the error path is obvious.

Going back to exception-based code, I find myself thinking "wait, which of these lines can throw?" The implicit nature of exceptions, which I never questioned before, now feels like hidden complexity.

## Goroutines and Channels

The concurrency model is genuinely excellent.

```go
go processRequest(req)
```

No `Task.Run`. No async/await colouring. No thread pool configuration. Just `go`.

And channels for communication:

```go
results := make(chan Result, 10)
go worker(results)
for r := range results {
    process(r)
}
```

The producer-consumer pattern in one elegant construct.

I can spin up thousands of goroutines without thinking. In .NET, creating thousands of Tasks has overhead and complexity that makes me hesitate.

## The `defer` Statement

Resource cleanup that reads top-to-bottom:

```go
file, err := os.Open(name)
if err != nil {
    return err
}
defer file.Close()  // cleanup declared right after acquisition

// Use file...
// Cleanup happens automatically when function returns
```

Compare to:

```csharp
using var file = File.OpenRead(name);
// or
try { } finally { file.Close(); }
```

`using` is fine, but `defer` is more flexible—it works for any cleanup, not just `IDisposable`.

## Implicit Interface Satisfaction

Defining an interface that existing types already implement:

```go
type Stringer interface {
    String() string
}
// fmt.Stringer already exists, many types implement it
// My new interface is satisfied by all of them, retroactively
```

No modifying the original types. No adapters. Just "if you have these methods, you implement this interface."

When I design APIs now, I think in terms of small interfaces that might already be satisfied. It's a different design philosophy, and I prefer it.

## gofmt: One True Format

No bikeshedding about formatting. Ever. `gofmt` decides, everyone uses it, discussions about tabs vs spaces simply don't happen.

The uniformity of Go codebases is remarkable. I can read anyone's code and it looks like my code, structurally. That matters for open source, for team collaboration, for just reading random code on GitHub.

I now find formatting debates in other languages exhausting. Just pick one and enforce it.

## Context Propagation

Every function that does I/O takes `context.Context`. Cancellation propagates automatically. Request-scoped values flow through the call chain.

```go
func HandleRequest(ctx context.Context, req Request) error {
    // ctx carries cancellation, deadlines, request ID, user info...
    return processWithDependencies(ctx, req)
}
```

This pervasive context threading seemed tedious at first. Now it's indispensable. I always have cancellation. I always have request context. I never have to wonder "how do I get the current request ID here?"

## Small Standard Library Surface

The Go standard library is focused. It does HTTP, JSON, SQL, crypto, and other fundamentals well. It doesn't try to do everything.

This forces you to understand what you're using. There's no kitchen-sink framework hiding complexity. You build with small, understandable pieces.

In .NET, the framework is vast. Great for discoverability, but you can go deep into features you don't understand. Go's smaller surface area means I actually know my tools.

## What This Means

These aren't just features I like—they've changed how I think about software development:

- **Feedback loops matter**: Fast compilation isn't a nice-to-have.
- **Deployment simplicity compounds**: Single binaries eliminate entire categories of problems.
- **Explicit beats implicit**: I'd rather see the error handling than have it hidden.
- **Concurrency should be easy**: If it's hard, people won't use it correctly.
- **Consistency beats preference**: Team standards > individual style.

Would I take a job writing C# again? Absolutely. It's a good language with a mature ecosystem.

Would I miss these Go features? Absolutely. Some of them every single day.

---

*Next time: six months in—a proper retrospective on whether this journey was worth it.*
