+++
title = "Mutexes and WaitGroups: When Channels Aren't the Answer"
date = "2025-01-01"
draft = false
tags = ["go", "dotnet", "concurrency", "sync", "csharp"]
series = ["step-over-to-go"]
+++

Go's mantra is "share memory by communicating," but sometimes you just need a bloody mutex. The `sync` package has all the primitives you know from C#, and knowing when to use them vs channels is part of becoming proficient in Go.

## sync.Mutex

The classic lock:

```go
type Counter struct {
    mu    sync.Mutex
    value int
}

func (c *Counter) Increment() {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.value++
}

func (c *Counter) Value() int {
    c.mu.Lock()
    defer c.mu.Unlock()
    return c.value
}
```

In C#:

```csharp
public class Counter
{
    private readonly object _lock = new();
    private int _value;
    
    public void Increment()
    {
        lock (_lock) { _value++; }
    }
    
    public int Value
    {
        get { lock (_lock) { return _value; } }
    }
}
```

Pretty similar. Go doesn't have a `lock` keyword, so you explicitly call `Lock()` and `Unlock()`. The `defer` ensures unlock even if the code panics.

### RWMutex for Read-Heavy Workloads

When you have many readers and few writers:

```go
type Cache struct {
    mu    sync.RWMutex
    items map[string]string
}

func (c *Cache) Get(key string) (string, bool) {
    c.mu.RLock()         // read lock - multiple readers allowed
    defer c.mu.RUnlock()
    val, ok := c.items[key]
    return val, ok
}

func (c *Cache) Set(key, value string) {
    c.mu.Lock()          // write lock - exclusive
    defer c.mu.Unlock()
    c.items[key] = value
}
```

Equivalent to `ReaderWriterLockSlim` in C#.

## sync.WaitGroup

This is what you reach for when you need to wait for multiple goroutines to complete:

```go
func main() {
    var wg sync.WaitGroup
    
    for i := 0; i < 5; i++ {
        wg.Add(1)
        go func(n int) {
            defer wg.Done()
            doWork(n)
        }(i)
    }
    
    wg.Wait()  // blocks until all Done() calls
    fmt.Println("all done")
}
```

In C#:

```csharp
var tasks = Enumerable.Range(0, 5)
    .Select(n => Task.Run(() => DoWork(n)))
    .ToArray();

await Task.WhenAll(tasks);
Console.WriteLine("all done");
```

C#'s version is more concise. Go's is more explicit about the counting.

### Common WaitGroup Mistakes

```go
// WRONG: Add inside goroutine - race condition
for i := 0; i < 5; i++ {
    go func(n int) {
        wg.Add(1)  // too late! main might call Wait() first
        defer wg.Done()
        doWork(n)
    }(i)
}

// CORRECT: Add before starting goroutine
for i := 0; i < 5; i++ {
    wg.Add(1)
    go func(n int) {
        defer wg.Done()
        doWork(n)
    }(i)
}
```

Always `Add` before `go`, never inside the goroutine.

## sync.Once

Execute something exactly once, regardless of how many goroutines try:

```go
var (
    instance *Database
    once     sync.Once
)

func GetDatabase() *Database {
    once.Do(func() {
        instance = connectToDatabase()
    })
    return instance
}
```

C# equivalent with `Lazy<T>`:

```csharp
private static readonly Lazy<Database> _instance = 
    new(() => ConnectToDatabase());

public static Database GetDatabase() => _instance.Value;
```

Or with double-checked locking... which is why `Lazy<T>` exists.

## sync.Cond

Condition variables for signaling between goroutines:

```go
type Queue struct {
    items []int
    cond  *sync.Cond
}

func NewQueue() *Queue {
    return &Queue{
        cond: sync.NewCond(&sync.Mutex{}),
    }
}

func (q *Queue) Put(item int) {
    q.cond.L.Lock()
    defer q.cond.L.Unlock()
    
    q.items = append(q.items, item)
    q.cond.Signal()  // wake one waiting goroutine
}

func (q *Queue) Get() int {
    q.cond.L.Lock()
    defer q.cond.L.Unlock()
    
    for len(q.items) == 0 {
        q.cond.Wait()  // releases lock, waits, reacquires lock
    }
    
    item := q.items[0]
    q.items = q.items[1:]
    return item
}
```

Honestly? For this pattern, channels are cleaner:

```go
ch := make(chan int)
ch <- item      // put
item := <-ch    // get
```

`sync.Cond` exists for complex scenarios where channels don't fit, but I rarely use it.

## sync.Pool

Object pool for reducing allocations:

```go
var bufferPool = sync.Pool{
    New: func() interface{} {
        return make([]byte, 4096)
    },
}

func process() {
    buf := bufferPool.Get().([]byte)
    defer bufferPool.Put(buf)
    
    // use buf...
}
```

C# has `ArrayPool<T>`:

```csharp
var buffer = ArrayPool<byte>.Shared.Rent(4096);
try
{
    // use buffer...
}
finally
{
    ArrayPool<byte>.Shared.Return(buffer);
}
```

Similar idea. Pool objects to avoid allocation pressure.

## sync/atomic

For simple counters and flags, atomics are faster than mutexes:

```go
var counter int64

func Increment() {
    atomic.AddInt64(&counter, 1)
}

func Value() int64 {
    return atomic.LoadInt64(&counter)
}
```

C#:

```csharp
private long _counter;

public void Increment() => Interlocked.Increment(ref _counter);
public long Value => Interlocked.Read(ref _counter);
```

Same primitives, different names.

## Channels vs Mutexes: When to Choose

**Use channels when:**
- Passing ownership of data between goroutines
- Coordinating multiple goroutines
- Building pipelines
- Signaling events

**Use mutexes when:**
- Protecting simple shared state (counters, caches)
- The "critical section" is obvious
- You don't need to transfer data, just guard it
- Performance matters and channels add overhead

**The rule of thumb:**
If you're passing data, use channels. If you're guarding data, use mutexes.

```go
// Channel: transferring data ownership
workQueue := make(chan Job)
go worker(workQueue)
workQueue <- newJob  // worker now "owns" this job

// Mutex: guarding shared state
type Metrics struct {
    mu     sync.Mutex
    counts map[string]int
}

func (m *Metrics) Inc(key string) {
    m.mu.Lock()
    m.counts[key]++
    m.mu.Unlock()
}
```

## The map Concurrency Problem

Maps are not concurrency-safe in Go:

```go
m := make(map[string]int)

go func() { m["a"] = 1 }()
go func() { m["b"] = 2 }()
// RACE CONDITION - might corrupt the map or panic
```

You need either:

**Option 1: Mutex**
```go
type SafeMap struct {
    mu sync.RWMutex
    m  map[string]int
}
```

**Option 2: sync.Map**
```go
var m sync.Map
m.Store("key", value)
val, ok := m.Load("key")
```

`sync.Map` is optimised for specific patterns (keys written once, read many times). For general use, a mutex-protected map is often simpler.

## The Comparison

| C# | Go | Notes |
|-----|-----|-------|
| `lock` | `sync.Mutex` | Manual Lock/Unlock |
| `ReaderWriterLockSlim` | `sync.RWMutex` | Same concept |
| `Task.WhenAll` | `sync.WaitGroup` | Go is more verbose |
| `Lazy<T>` | `sync.Once` | Same purpose |
| `Monitor.Wait/Pulse` | `sync.Cond` | Rarely needed |
| `ConcurrentDictionary` | `sync.Map` | Different optimisations |
| `ArrayPool<T>` | `sync.Pool` | Similar |
| `Interlocked` | `sync/atomic` | Same primitives |

## The Honest Take

Go's sync package is perfectly adequate. Nothing here will surprise a C# developer who knows their threading primitives.

**What Go does well:**
- Clean, minimal API
- `defer` makes unlock reliable
- WaitGroup is explicit about what you're waiting for

**What C# does better:**
- `lock` keyword is more concise than Lock/Unlock
- `Task.WhenAll` is cleaner than WaitGroup
- `ConcurrentDictionary` has more features than `sync.Map`
- Overall better tooling for concurrency debugging

**The verdict:**
These primitives work fine. You'll miss `lock` syntax occasionally. You'll miss `Task.WhenAll`'s elegance frequently. But you'll be productive.

The more interesting question is channels vs mutexes. Go developers sometimes over-use channels when a mutex would be simpler. Don't cargo-cult "share by communicating" when a simple lock does the job.

---

*Next up: context.Context. Go's answer to CancellationToken, and arguably one of the most important patterns in Go.*
