+++
title = "select: Multiplexing Like a Pro"
date = "2025-01-01"
draft = false
tags = ["go", "dotnet", "concurrency", "channels", "csharp"]
+++

The `select` statement is where Go's channel system goes from "neat" to "powerful." It lets you wait on multiple channel operations simultaneously, handle timeouts, and do non-blocking checks—all with clean syntax.

C# doesn't have a direct equivalent. The closest is `Task.WhenAny`, but `select` is more flexible and more deeply integrated.

## Basic select

`select` waits on multiple channel operations and executes whichever is ready first:

```go
select {
case msg := <-ch1:
    fmt.Println("received from ch1:", msg)
case msg := <-ch2:
    fmt.Println("received from ch2:", msg)
}
```

If both channels have data, one is chosen randomly (fair scheduling). If neither has data, `select` blocks until one does.

## Timeouts

This is where `select` shines. Implementing a timeout:

```go
select {
case result := <-ch:
    fmt.Println("got result:", result)
case <-time.After(3 * time.Second):
    fmt.Println("timeout!")
}
```

`time.After` returns a channel that receives a value after the duration. If your main channel doesn't deliver in 3 seconds, the timeout case fires.

Compare to C#:

```csharp
var task = GetResultAsync();
var completed = await Task.WhenAny(task, Task.Delay(TimeSpan.FromSeconds(3)));

if (completed == task)
{
    var result = await task;
    Console.WriteLine($"got result: {result}");
}
else
{
    Console.WriteLine("timeout!");
}
```

More verbose, and the result handling is awkward.

## Non-Blocking Operations

Add a `default` case to make `select` non-blocking:

```go
select {
case msg := <-ch:
    fmt.Println("received:", msg)
default:
    fmt.Println("no message available")
}
```

If no channel is ready, `default` executes immediately. This is how you poll without blocking.

### Non-Blocking Send

```go
select {
case ch <- msg:
    fmt.Println("sent")
default:
    fmt.Println("channel full, dropping message")
}
```

Try to send; if the channel is full (or unbuffered with no receiver), execute default instead of blocking.

## Handling Multiple Sources

Real-world example: a worker that handles requests, ticks, and shutdown signals:

```go
func worker(requests <-chan Request, done <-chan struct{}) {
    ticker := time.NewTicker(time.Minute)
    defer ticker.Stop()

    for {
        select {
        case req := <-requests:
            handleRequest(req)
        case <-ticker.C:
            doPeriodicWork()
        case <-done:
            fmt.Println("shutting down")
            return
        }
    }
}
```

Three different event sources, one clean loop. In C#, you'd need `Task.WhenAny` with careful task management, or an Rx observable merge.

## The Empty select

A `select` with no cases blocks forever:

```go
select {}  // blocks forever
```

Useful for keeping a main function alive while goroutines do work:

```go
func main() {
    go server()
    select {}  // wait forever
}
```

Not common, but occasionally handy.

## Priority with Nested select

`select` chooses randomly among ready cases. If you need priority, nest them:

```go
for {
    // First, drain high priority
    select {
    case msg := <-highPriority:
        handle(msg)
        continue
    default:
    }
    
    // Then check both
    select {
    case msg := <-highPriority:
        handle(msg)
    case msg := <-lowPriority:
        handle(msg)
    }
}
```

The first `select` with `default` is non-blocking—it handles high-priority if available, otherwise falls through. This ensures high-priority messages are processed first.

## Cancellation Pattern

Using `select` with a done channel for cancellation:

```go
func doWork(done <-chan struct{}) error {
    for {
        select {
        case <-done:
            return errors.New("cancelled")
        default:
        }
        
        // Do a chunk of work
        if finished := processChunk(); finished {
            return nil
        }
    }
}
```

Check for cancellation at the top of each iteration. We'll see a better way with `context` later.

## Collecting Results with Timeout

Common pattern: gather results from multiple goroutines with an overall timeout:

```go
func fetchAll(urls []string, timeout time.Duration) []Result {
    results := make(chan Result, len(urls))
    
    for _, url := range urls {
        go func(u string) {
            resp, err := fetch(u)
            results <- Result{URL: u, Response: resp, Error: err}
        }(url)
    }
    
    var collected []Result
    deadline := time.After(timeout)
    
    for i := 0; i < len(urls); i++ {
        select {
        case r := <-results:
            collected = append(collected, r)
        case <-deadline:
            return collected  // return what we have
        }
    }
    
    return collected
}
```

We get as many results as complete before the timeout, then return whatever we have.

Compare to C#:

```csharp
async Task<List<Result>> FetchAll(string[] urls, TimeSpan timeout)
{
    var cts = new CancellationTokenSource(timeout);
    var tasks = urls.Select(url => FetchAsync(url, cts.Token));
    
    try
    {
        return (await Task.WhenAll(tasks)).ToList();
    }
    catch (OperationCanceledException)
    {
        // WhenAll throws if any task cancels - harder to get partial results
        return tasks
            .Where(t => t.IsCompletedSuccessfully)
            .Select(t => t.Result)
            .ToList();
    }
}
```

The C# version is more awkward for partial results because `Task.WhenAll` is all-or-nothing.

## select with Send and Receive

You can mix sends and receives in one select:

```go
select {
case ch1 <- value:
    fmt.Println("sent to ch1")
case msg := <-ch2:
    fmt.Println("received from ch2:", msg)
}
```

Whichever operation can proceed, does. Useful for bidirectional communication.

## The C# Comparison

| Go select | C# Equivalent | Notes |
|-----------|---------------|-------|
| `select` on multiple channels | `Task.WhenAny` | Less elegant syntax |
| Timeout with `time.After` | `Task.WhenAny` + `Task.Delay` | More verbose |
| Non-blocking with `default` | `Task.IsCompleted` check | Manual polling |
| Empty `select {}` | `Task.Delay(Timeout.Infinite)` | Rare in both |
| Priority handling | Manual with loops | No direct equivalent |

C# has `System.Threading.Channels` which gets closer:

```csharp
var reader = channel.Reader;
while (await reader.WaitToReadAsync())
{
    while (reader.TryRead(out var item))
    {
        Process(item);
    }
}
```

But multiplexing multiple channels still requires `Task.WhenAny` gymnastics.

## The Honest Take

`select` is one of Go's genuinely great features. It makes patterns that are awkward in other languages—timeouts, multiplexing, non-blocking checks—into one clean construct.

**What Go does better:**
- Clean syntax for multiplexing
- Timeouts are trivial
- Non-blocking operations with `default`
- Fair random selection among ready cases
- First-class language support

**What C# does better:**
- `Task.WhenAll` for collecting all results
- Better exception propagation
- Richer LINQ-style composition with Rx

**The verdict:**
If you're doing event-loop style programming—handling messages from multiple sources, implementing timeouts, coordinating shutdown—`select` is wonderful. It's one of those features you miss when you go back to languages without it.

---

*Next up: mutexes and WaitGroups—because sometimes shared memory with locks is simpler than channels.*
