+++
title = "Stack vs Heap: Go's Escape Analysis"
date = "2024-12-31"
draft = false
tags = ["go", "dotnet", "memory", "performance", "csharp"]
+++

In C#, you mostly don't think about where variables live. Value types go on the stack (usually). Reference types go on the heap (always). The runtime and JIT make optimisations. You trust the process.

In Go, you still mostly don't think about it—but for different reasons. Go decides where things live at compile time through something called escape analysis. And sometimes it makes choices that'll surprise you.

## The C# Mental Model

C#'s rules are pretty clear:

```csharp
void Example()
{
    int x = 42;           // stack - value type, local variable
    Point p = new(1, 2);  // stack - value type (assuming Point is a struct)
    
    var user = new User(); // heap - reference type, always
    var boxed = (object)x; // heap - boxing allocates
}
```

Value types on stack (unless boxed, captured in closures, or part of a heap object). Reference types on heap. Simple.

.NET has more tricks now—`stackalloc`, `Span<T>`, `ref struct`—but the basic model is straightforward.

## Go's Escape Analysis

Go doesn't have value types vs reference types in the C# sense. Structs can live on the stack or heap. The compiler decides based on whether the value "escapes" the function.

```go
func stackAllocation() {
    x := 42           // stack (probably)
    user := User{}    // stack (probably)
    process(&user)    // might change things...
}

func heapAllocation() *User {
    user := User{}    // heap - returned pointer escapes
    return &user
}
```

The key insight: **if a pointer to something outlives the function, it must be on the heap**. Go figures this out at compile time.

## Seeing Escape Analysis

You can ask the compiler what it's doing:

```bash
go build -gcflags="-m" ./...
```

Output looks like:

```
./main.go:10:2: moved to heap: user
./main.go:15:9: &Config{...} escapes to heap
./main.go:20:2: result does not escape
```

This is genuinely useful for performance work. You can see exactly what's allocating.

## What Makes Things Escape

### Returning Pointers

```go
func newUser() *User {
    u := User{Name: "Alice"}  // escapes - returned pointer
    return &u
}
```

The `&u` pointer is returned, so `u` must outlive the function. Heap.

### Storing in Interface Values

```go
func example() {
    var w io.Writer = &bytes.Buffer{}  // escapes - interface storage
}
```

Interface values often cause heap allocation because the compiler can't always prove the lifetime.

### Closures Capturing Variables

```go
func example() {
    x := 42
    f := func() {
        fmt.Println(x)  // x escapes - captured by closure
    }
    go f()
}
```

Closures that outlive the function (like goroutines) force captures to the heap.

### Too Large for Stack

```go
func example() {
    data := make([]byte, 10*1024*1024)  // 10MB - escapes due to size
}
```

Very large allocations go to the heap regardless of escape.

### Pointer Stored in Slice or Map

```go
func example() {
    users := make([]*User, 0)
    u := User{Name: "Alice"}
    users = append(users, &u)  // u escapes - pointer stored in slice
}
```

## What Stays on the Stack

### Local Variables Not Referenced

```go
func example() {
    x := 42          // stack
    y := x + 1       // stack
    fmt.Println(y)   // y's value copied to Println, y stays on stack
}
```

### Pointers That Don't Escape

```go
func process(u *User) {
    u.Name = "modified"  // u doesn't escape, caller's stack
}

func example() {
    user := User{}
    process(&user)  // user can stay on stack - &user doesn't escape process
}
```

The compiler traces through calls to see if pointers ultimately escape.

## Comparing to .NET

Here's where I get cynical: .NET's approach is more sophisticated and gives you more control.

### `stackalloc`

```csharp
Span<byte> buffer = stackalloc byte[1024];
// Guaranteed stack allocation, zero heap involvement
```

Go can't do this. You can't force stack allocation. The compiler decides.

### `ref struct`

```csharp
ref struct Parser 
{
    private Span<char> _buffer;
    // Can ONLY live on stack, compiler enforced
}
```

Go has no equivalent. You can't declare "this type must never be heap-allocated."

### `Span<T>` Without Allocation

```csharp
void Process(ReadOnlySpan<char> text)
{
    var slice = text[10..20];  // no allocation, just pointer arithmetic
}
```

Go slices are similar but the escape analysis is less predictable.

### What .NET Gets Right

The JIT can do escape analysis too, and it can make different decisions at runtime based on actual usage patterns. Go's compile-time analysis is conservative—it heap-allocates when unsure.

```csharp
// .NET JIT might stack-allocate this if it proves the object doesn't escape
var temp = new StringBuilder();
temp.Append("hello");
return temp.ToString();
// StringBuilder might be optimised away entirely
```

Go's compiler is good, but it doesn't have runtime profile-guided optimisation.

## The Practical Impact

Does this matter? Sometimes.

For most code—web handlers, CLI tools, data processing—the GC is fast enough that escape analysis is academic. Things allocate, they get collected, life goes on.

For hot paths processing millions of events per second, allocation pressure matters. And here's the uncomfortable truth: **Go gives you less control than C#**.

You can't say "put this on the stack." You can't create stack-only types. You can write code that the compiler *will* stack-allocate, but you're working with the compiler, not commanding it.

### Tricks That Help

**Sync.Pool for reusable objects:**

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

This doesn't avoid allocation—it reuses allocations. Different problem, similar goal.

**Passing values instead of pointers for small structs:**

```go
// This might heap-allocate due to interface
func process(r io.Reader) { ... }

// This won't heap-allocate
func processBytes(data []byte) { ... }
```

Sometimes avoiding interfaces avoids allocation. But you lose flexibility.

**Preallocating slices:**

```go
// Might grow and reallocate multiple times
results := make([]Result, 0)

// Single allocation if you know the size
results := make([]Result, 0, expectedSize)
```

## The Honest Take

I'll be blunt: if you're coming from .NET and you care deeply about allocation control, Go will frustrate you.

.NET gives you:
- `stackalloc` for explicit stack allocation
- `ref struct` for stack-only types
- `Span<T>` for zero-allocation slicing
- `ArrayPool<T>` for buffer reuse with a clean API
- Object pooling with sophisticated lifetime management
- JIT optimisations that can eliminate allocations entirely

Go gives you:
- Escape analysis that usually does the right thing
- `sync.Pool` for object reuse (but with interface{} boxing before 1.18)
- The ability to check what escapes with compiler flags
- A fast garbage collector that makes most of this not matter

**When Go's approach works:**
- You're building services with reasonable latency requirements
- You're not processing millions of messages per second per core
- You value simplicity over maximum control
- You're okay trading some performance for less complexity

**When you'll miss .NET:**
- Sub-millisecond latency requirements
- Zero-GC paths are necessary
- You need guaranteed stack allocation
- High-frequency trading, game engines, real-time systems

For 90% of software, Go's escape analysis is fine. The GC is good. You won't notice. For the other 10%, .NET genuinely has better tools.

## Checking Your Allocations

Profile before optimising:

```bash
# Run benchmarks with allocation stats
go test -bench=. -benchmem

# Trace allocations
go tool pprof -alloc_space profile.out

# See escape decisions
go build -gcflags="-m -m" ./...  # extra -m for more detail
```

Know what's actually allocating before you fight the compiler.

---

*Next up: slices in depth—they're not arrays, they're not List<T>, and the gotchas around capacity, length, and shared backing arrays will bite you eventually.*
