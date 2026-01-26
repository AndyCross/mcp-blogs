+++
title = "Async/Await vs Goroutines: A Mindset Shift"
date = "2025-01-01"
draft = false
tags = ["go", "dotnet", "concurrency", "async", "csharp"]
+++

Here's the thing about Go's concurrency model: it's going to feel backwards. You've spent years learning that async operations need `async` keywords, `await` expressions, `Task<T>` return types, and careful thought about which thread you're on.

Go throws all of that out. Any function can be concurrent. There's no special syntax. No coloured functions. No async/await virus spreading through your codebase.

It feels wrong until suddenly it doesn't.

## The C# Model: Async All the Way Down

In C#, concurrency is opt-in and explicit:

```csharp
public async Task<User> GetUserAsync(int id)
{
    var response = await _httpClient.GetAsync($"/users/{id}");
    var json = await response.Content.ReadAsStringAsync();
    return JsonSerializer.Deserialize<User>(json);
}

public async Task ProcessUsersAsync()
{
    var user1 = await GetUserAsync(1);
    var user2 = await GetUserAsync(2);
    // Sequential - second waits for first
}
```

Want parallel execution?

```csharp
public async Task ProcessUsersAsync()
{
    var task1 = GetUserAsync(1);
    var task2 = GetUserAsync(2);
    var users = await Task.WhenAll(task1, task2);
    // Parallel - both run concurrently
}
```

This model is explicit, type-safe, and viral. Once you have an async function, everything that calls it tends to become async too.

## The Go Model: Just... Go

Go's approach is simpler:

```go
func GetUser(id int) (*User, error) {
    resp, err := http.Get(fmt.Sprintf("/users/%d", id))
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    
    var user User
    if err := json.NewDecoder(resp.Body).Decode(&user); err != nil {
        return nil, err
    }
    return &user, nil
}
```

Notice: no async keyword. No special return type. It's just a function.

Want to run it concurrently? Add the `go` keyword:

```go
go GetUser(1)  // runs in background, returns immediately
go GetUser(2)  // also runs in background
```

That's it. Any function can be spawned as a goroutine. No syntax changes to the function itself.

## What's a Goroutine?

A goroutine is a lightweight thread managed by Go's runtime. Think of it as a Task that's:

- **Cheaper**: Goroutines start with ~2KB stack (vs ~1MB for OS threads)
- **Multiplexed**: Go's scheduler runs thousands of goroutines on a few OS threads
- **Implicit**: No `Task.Run()` ceremony, just `go f()`

```go
func main() {
    for i := 0; i < 10000; i++ {
        go func(n int) {
            fmt.Println(n)
        }(i)
    }
    time.Sleep(time.Second)  // wait for goroutines (crude, we'll fix this)
}
```

Spawning 10,000 goroutines is fine. Spawning 10,000 OS threads would kill your machine.

## The Problem: Getting Results Back

Here's where things get interesting. When you `go` a function, you can't get its return value:

```go
result := go GetUser(1)  // DOESN'T WORK - go doesn't return anything
```

The `go` keyword fires and forgets. If you need results, you need **channels**, which we'll cover properly in the next post. For now, here's a taste:

```go
func main() {
    results := make(chan *User, 2)
    
    go func() {
        user, _ := GetUser(1)
        results <- user
    }()
    
    go func() {
        user, _ := GetUser(2)
        results <- user
    }()
    
    user1 := <-results
    user2 := <-results
    fmt.Println(user1, user2)
}
```

More verbose than `Task.WhenAll`? Yes. More flexible? Also yes. But we're getting ahead of ourselves.

## No Coloured Functions

This is the big philosophical difference. In C#, functions are "coloured":

- **Red functions** (`async`): Can use `await`, return `Task<T>`
- **Blue functions** (sync): Can't use `await`, return `T` directly
- Red can call blue, but blue calling red is awkward

This leads to the "async all the way down" pattern. One async function at the bottom of your call stack, and suddenly everything above it needs to be async too.

Go doesn't have coloured functions. Every function is the same colour:

```go
// These are identical in signature
func DoSyncThing() error { ... }
func DoAsyncThing() error { ... }  // might internally use goroutines

// Caller doesn't know or care
err := DoSyncThing()
err = DoAsyncThing()
```

The caller decides whether to run something concurrently:

```go
DoSyncThing()      // blocking
go DoSyncThing()   // concurrent

DoAsyncThing()     // blocking (waits for internal goroutines)
go DoAsyncThing()  // concurrent
```

## Blocking Is Fine

In C#, blocking an async operation is a code smell:

```csharp
// DON'T DO THIS - can deadlock, wastes threads
var result = GetUserAsync(1).Result;
```

In Go, blocking is the default and it's fine:

```go
// Totally normal
user, err := GetUser(1)
```

Why? Because Go's scheduler is cooperative. When a goroutine blocks on I/O, the scheduler runs other goroutines on the same OS thread. You're not tying up a thread pool thread. You're just pausing one goroutine.

This is why Go doesn't need async/await. Blocking calls don't waste resources because the runtime handles the multiplexing.

## When This Feels Better

**Simple concurrent operations:**

```go
// Go
go sendEmail(user)
go updateAnalytics(event)
go notifySlack(message)
// All three run concurrently, fire-and-forget
```

```csharp
// C# equivalent
_ = Task.Run(() => SendEmailAsync(user));
_ = Task.Run(() => UpdateAnalyticsAsync(event));
_ = Task.Run(() => NotifySlackAsync(message));
// More ceremony, and those discards feel wrong
```

**CPU-bound parallelism:**

```go
// Go
for _, item := range items {
    go process(item)
}
```

```csharp
// C#
Parallel.ForEach(items, item => Process(item));
// Or
await Task.WhenAll(items.Select(item => ProcessAsync(item)));
```

Both work, but Go's is more uniform: same syntax for I/O-bound and CPU-bound concurrency.

## When C# Feels Better

**Structured async flow:**

```csharp
var user = await GetUserAsync(id);
var orders = await GetOrdersAsync(user.Id);
var summary = await BuildSummaryAsync(user, orders);
return summary;
```

This sequential async flow is clean in C#. In Go, you'd write the same thing without any special syntax. Fine, but you don't get the visual markers of "this is I/O."

**Parallel with results:**

```csharp
var tasks = ids.Select(id => GetUserAsync(id));
var users = await Task.WhenAll(tasks);
```

Go requires more scaffolding for this pattern (channels, WaitGroups). We'll cover it, but it's more code.

**Cancellation:**

C#'s `CancellationToken` integrates beautifully with async/await. Go's `context.Context` is similar but more manual. We'll cover this in a later post.

## The Mental Shift

Here's what took me time to internalise:

1. **Functions don't need to declare their concurrency potential**. Any function can be `go`'d.

2. **Blocking is fine**. The scheduler handles it. Stop feeling guilty about synchronous calls.

3. **Concurrency is at the call site, not the definition**. You decide whether to wait or fire-and-forget when you call, not when you write the function.

4. **Communication replaces shared state**. Instead of returning values, goroutines send results through channels.

5. **No thread pool to configure**. GOMAXPROCS controls parallelism. The scheduler does the rest.

## The Comparison

| Aspect | C# async/await | Go goroutines |
|--------|---------------|---------------|
| Syntax | `async`/`await` keywords | `go` keyword |
| Return values | `Task<T>` | Channels |
| Function colouring | Yes (async vs sync) | No |
| Blocking | Discouraged | Normal |
| Cancellation | `CancellationToken` | `context.Context` |
| Thread model | Thread pool | M:N scheduling |
| Overhead | ~300 bytes per Task | ~2KB per goroutine |
| Debugging | Excellent tooling | Good, improving |

## The Honest Take

Go's concurrency model is simpler to start with and scales well. The lack of function colouring is genuinely liberating. No more "async virus" infecting your codebase.

But C#'s model is more explicit about what's happening. When you see `await`, you know there's a potential suspension point. In Go, any function call might block. That's fine, but less visible.

**What Go does better:**
- No function colouring
- Lightweight goroutines (spawn thousands easily)
- Blocking is natural, not wasteful
- Uniform syntax for all concurrency

**What C# does better:**
- Explicit suspension points
- `Task.WhenAll` for collecting results
- Better tooling and debugging
- Clearer error propagation in async flows

Neither is objectively better. They're different philosophies. Go says "concurrency should be easy, let the runtime handle scheduling." C# says "concurrency should be explicit, let the developer see what's happening."

---

*Next up: channels. Go's answer to BlockingCollection, and the primary way goroutines communicate.*
