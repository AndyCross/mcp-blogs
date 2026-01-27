+++
title = "Channels: The sync You Didn't Know You Wanted"
date = "2025-01-01"
draft = false
tags = ["go", "dotnet", "concurrency", "channels", "csharp"]
series = ["step-over-to-go"]
+++

If goroutines are Go's lightweight threads, channels are how they talk to each other. Think `BlockingCollection<T>` meets message passing, with first-class language support.

The Go mantra is: **"Don't communicate by sharing memory; share memory by communicating."** Channels are how you do that.

## The Basics

A channel is a typed conduit for sending and receiving values:

```go
ch := make(chan int)  // unbuffered channel of ints

// Send (blocks until someone receives)
ch <- 42

// Receive (blocks until someone sends)
value := <-ch
```

The `<-` operator does both sending and receiving. The arrow points in the direction of data flow.

## Buffered vs Unbuffered

**Unbuffered channels** synchronise sender and receiver:

```go
ch := make(chan int)  // unbuffered

go func() {
    ch <- 1  // blocks here until main receives
    fmt.Println("sent")
}()

time.Sleep(time.Second)
fmt.Println(<-ch)  // "sent" prints after this line
```

The sender blocks until the receiver is ready. This creates a synchronisation point, a "handshake" between goroutines.

**Buffered channels** have capacity:

```go
ch := make(chan int, 3)  // buffer of 3

ch <- 1  // doesn't block
ch <- 2  // doesn't block
ch <- 3  // doesn't block
ch <- 4  // NOW it blocks - buffer full
```

Sends only block when the buffer is full. Receives only block when the buffer is empty.

## The C# Comparison: BlockingCollection

C#'s closest equivalent is `BlockingCollection<T>`:

```csharp
var collection = new BlockingCollection<int>(boundedCapacity: 3);

// Producer
Task.Run(() => {
    collection.Add(1);
    collection.Add(2);
    collection.CompleteAdding();
});

// Consumer
foreach (var item in collection.GetConsumingEnumerable())
{
    Console.WriteLine(item);
}
```

Go's version:

```go
ch := make(chan int, 3)

// Producer
go func() {
    ch <- 1
    ch <- 2
    close(ch)
}()

// Consumer
for item := range ch {
    fmt.Println(item)
}
```

Similar pattern, but channels are built into the language. No `using System.Collections.Concurrent`, no `GetConsumingEnumerable()`. Just `range` over the channel.

## Closing Channels

Closing a channel signals "no more values coming":

```go
ch := make(chan int)

go func() {
    ch <- 1
    ch <- 2
    close(ch)  // signal completion
}()

for v := range ch {
    fmt.Println(v)  // prints 1, then 2, then loop exits
}
```

Important rules:

- Only senders should close channels (receivers don't know when senders are done)
- Sending on a closed channel panics
- Receiving from a closed channel returns the zero value immediately
- You can check if a channel is closed: `v, ok := <-ch` (ok is false if closed)

```go
v, ok := <-ch
if !ok {
    fmt.Println("channel closed")
}
```

## Common Patterns

### Fan-Out: One Producer, Many Consumers

```go
func worker(id int, jobs <-chan int, results chan<- int) {
    for job := range jobs {
        results <- job * 2  // process and send result
    }
}

func main() {
    jobs := make(chan int, 100)
    results := make(chan int, 100)

    // Start 3 workers
    for w := 1; w <= 3; w++ {
        go worker(w, jobs, results)
    }

    // Send jobs
    for j := 1; j <= 9; j++ {
        jobs <- j
    }
    close(jobs)

    // Collect results
    for r := 1; r <= 9; r++ {
        fmt.Println(<-results)
    }
}
```

Notice the channel direction syntax:
- `jobs <-chan int`: receive-only channel
- `results chan<- int`: send-only channel

This prevents workers from accidentally closing `jobs` or reading from `results`.

### Fan-In: Many Producers, One Consumer

```go
func producer(id int, ch chan<- string) {
    for i := 0; i < 3; i++ {
        ch <- fmt.Sprintf("producer %d: message %d", id, i)
    }
}

func main() {
    ch := make(chan string)

    go producer(1, ch)
    go producer(2, ch)
    go producer(3, ch)

    for i := 0; i < 9; i++ {
        fmt.Println(<-ch)
    }
}
```

Multiple producers send to one channel. The consumer receives interleaved messages.

### Pipeline: Chain of Transformations

```go
func generate(nums ...int) <-chan int {
    out := make(chan int)
    go func() {
        for _, n := range nums {
            out <- n
        }
        close(out)
    }()
    return out
}

func square(in <-chan int) <-chan int {
    out := make(chan int)
    go func() {
        for n := range in {
            out <- n * n
        }
        close(out)
    }()
    return out
}

func main() {
    // Pipeline: generate -> square -> print
    for n := range square(generate(1, 2, 3, 4)) {
        fmt.Println(n)  // 1, 4, 9, 16
    }
}
```

Each stage runs in its own goroutine. Data flows through channels. This is remarkably similar to LINQ or Rx, but with explicit concurrency.

## Getting Results from Multiple Goroutines

Remember the "fire and forget" problem with goroutines? Channels solve it:

```go
func fetchUser(id int, ch chan<- *User) {
    user, _ := getUser(id)  // simplified error handling
    ch <- user
}

func main() {
    ch := make(chan *User, 2)
    
    go fetchUser(1, ch)
    go fetchUser(2, ch)
    
    user1 := <-ch
    user2 := <-ch
    
    fmt.Println(user1, user2)
}
```

This is Go's answer to `Task.WhenAll`:

```csharp
// C#
var users = await Task.WhenAll(GetUserAsync(1), GetUserAsync(2));
```

Go's version is more verbose, but gives you control over how results are collected.

## Error Handling with Channels

Channels carry one type. If you need values and errors, use a struct:

```go
type Result struct {
    User  *User
    Error error
}

func fetchUser(id int, ch chan<- Result) {
    user, err := getUser(id)
    ch <- Result{User: user, Error: err}
}

func main() {
    ch := make(chan Result, 2)
    
    go fetchUser(1, ch)
    go fetchUser(2, ch)
    
    for i := 0; i < 2; i++ {
        result := <-ch
        if result.Error != nil {
            fmt.Println("error:", result.Error)
            continue
        }
        fmt.Println("user:", result.User)
    }
}
```

Clunkier than C#'s exception propagation through Tasks, but explicit.

## When Channels Are the Wrong Tool

Channels aren't always the answer:

- **Simple mutex protection**: If you just need to guard a shared variable, `sync.Mutex` is simpler
- **Reference counting**: Use `sync.WaitGroup`
- **One-time events**: Use `sync.Once`
- **Atomic counters**: Use `sync/atomic`

Go's proverb is "share memory by communicating," but sometimes sharing memory with a mutex is fine. We'll cover when in a later post.

## The Comparison

| Aspect | C# BlockingCollection | Go Channels |
|--------|----------------------|-------------|
| Syntax | Library type | Language primitive |
| Bounded | Yes (constructor) | Yes (make with size) |
| Direction typing | No | Yes (`<-chan`, `chan<-`) |
| Closing | `CompleteAdding()` | `close()` |
| Iteration | `GetConsumingEnumerable()` | `range` |
| Multiple consumers | Manual coordination | Built-in fair scheduling |
| Select/multiplex | No direct equivalent | `select` statement |

## The Honest Take

Channels are remarkably elegant. They're built into the language, they compose well, and they make producer-consumer patterns trivial.

**What Go does better:**
- First-class language support
- Direction typing prevents bugs
- `select` for multiplexing (next post)
- Clean iteration with `range`

**What C# does better:**
- Easier result collection with `Task.WhenAll`
- Exception propagation through task chains
- More familiar for developers from OOP backgrounds
- `Channel<T>` in .NET Core is actually quite nice

**The verdict:**
If you're doing producer-consumer, pipelines, or fan-out/fan-in patterns, channels are delightful. If you're doing request-response where you need a result back, they're more ceremony than `await`.

---

*Next up: the `select` statement. Multiplexing channels, handling timeouts, and non-blocking operations.*
