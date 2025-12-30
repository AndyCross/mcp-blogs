+++
title = "Benchmarks and Profiling Out of the Box"
date = "2025-01-03"
draft = false
tags = ["go", "dotnet", "testing", "performance", "benchmarks", "csharp"]
+++

Here's something that surprised me: Go has built-in benchmarking. No BenchmarkDotNet to install. No configuration. Write a function, run `go test -bench`, get numbers.

And profiling? Also built in. CPU profiles, memory profiles, blocking profiles—all from the standard toolchain.

Coming from .NET where you install BenchmarkDotNet for proper benchmarks and a separate profiler for profiling, Go's integrated approach is refreshing.

## Writing Benchmarks

Benchmark functions start with `Benchmark` and take `*testing.B`:

```go
func BenchmarkAdd(b *testing.B) {
    for i := 0; i < b.N; i++ {
        Add(2, 3)
    }
}
```

That `b.N` is key. The framework controls it, running your code enough times to get stable measurements.

Run with:

```bash
go test -bench=.                    # all benchmarks
go test -bench=BenchmarkAdd         # specific benchmark
go test -bench=. -benchtime=5s      # run for 5 seconds
go test -bench=. -count=10          # run 10 times
```

Output:

```
BenchmarkAdd-8    1000000000    0.3192 ns/op
```

Translation: on 8 cores, ran 1 billion iterations, each took ~0.32 nanoseconds.

## Comparing to BenchmarkDotNet

In C#, you'd write:

```csharp
[Benchmark]
public int Add() => Math.Add(2, 3);
```

Then run the benchmark project. BenchmarkDotNet gives you beautiful output, statistical analysis, memory diagnostics, multiple runtimes...

Go's benchmarks are simpler. Less analysis, less ceremony, faster feedback.

## Benchmarking with Setup

Don't include setup in the measured loop:

```go
func BenchmarkParse(b *testing.B) {
    data := loadTestData()  // setup, not measured
    
    b.ResetTimer()  // start timing from here
    
    for i := 0; i < b.N; i++ {
        Parse(data)
    }
}
```

`b.ResetTimer()` excludes setup time from measurements.

## Memory Benchmarks

Track allocations:

```bash
go test -bench=. -benchmem
```

Output:

```
BenchmarkParse-8    50000    32145 ns/op    4096 B/op    12 allocs/op
```

Now you see: 4096 bytes allocated per operation, 12 separate allocations.

You can also report memory in code:

```go
func BenchmarkAllocations(b *testing.B) {
    b.ReportAllocs()
    for i := 0; i < b.N; i++ {
        _ = make([]byte, 1024)
    }
}
```

## Benchmark Comparison

Compare different implementations:

```go
func BenchmarkConcatPlus(b *testing.B) {
    for i := 0; i < b.N; i++ {
        s := "hello" + " " + "world"
        _ = s
    }
}

func BenchmarkConcatBuilder(b *testing.B) {
    for i := 0; i < b.N; i++ {
        var sb strings.Builder
        sb.WriteString("hello")
        sb.WriteString(" ")
        sb.WriteString("world")
        _ = sb.String()
    }
}
```

Run both:

```bash
go test -bench=BenchmarkConcat
```

Use `benchstat` for statistical comparison:

```bash
go install golang.org/x/perf/cmd/benchstat@latest

go test -bench=. -count=10 > old.txt
# make changes
go test -bench=. -count=10 > new.txt

benchstat old.txt new.txt
```

Output shows whether changes are statistically significant.

## Sub-Benchmarks

Test different sizes:

```go
func BenchmarkSort(b *testing.B) {
    sizes := []int{10, 100, 1000, 10000}
    
    for _, size := range sizes {
        b.Run(fmt.Sprintf("size=%d", size), func(b *testing.B) {
            data := generateData(size)
            b.ResetTimer()
            
            for i := 0; i < b.N; i++ {
                sort.Ints(data)
            }
        })
    }
}
```

Output:

```
BenchmarkSort/size=10-8       5000000     234 ns/op
BenchmarkSort/size=100-8       500000    3456 ns/op
BenchmarkSort/size=1000-8       30000   45678 ns/op
BenchmarkSort/size=10000-8       2000  678901 ns/op
```

## CPU Profiling

Generate a CPU profile:

```bash
go test -bench=. -cpuprofile=cpu.prof
```

Analyse with pprof:

```bash
go tool pprof cpu.prof
```

Interactive commands:

```
(pprof) top           # hottest functions
(pprof) top --cum     # including callees
(pprof) list FuncName # source annotation
(pprof) web           # open graph in browser
```

Or the web UI:

```bash
go tool pprof -http=:8080 cpu.prof
```

Opens a browser with flame graphs, call graphs, source annotations.

## Memory Profiling

Generate memory profiles:

```bash
go test -bench=. -memprofile=mem.prof
```

Analyse:

```bash
go tool pprof mem.prof
(pprof) top           # biggest allocators
(pprof) list FuncName # source with allocation sizes
```

Two views:

```bash
go tool pprof -alloc_space mem.prof  # total bytes allocated
go tool pprof -inuse_space mem.prof  # bytes in use at snapshot
```

## Runtime Profiling

For running applications (not benchmarks):

```go
import (
    "net/http"
    _ "net/http/pprof"  // side-effect import
)

func main() {
    go func() {
        http.ListenAndServe("localhost:6060", nil)
    }()
    
    // your application
}
```

Now you can:

```bash
go tool pprof http://localhost:6060/debug/pprof/profile?seconds=30
go tool pprof http://localhost:6060/debug/pprof/heap
go tool pprof http://localhost:6060/debug/pprof/goroutine
```

Profile a live application without restarting.

## The Comparison

| Feature | BenchmarkDotNet | Go Benchmarks |
|---------|-----------------|---------------|
| Setup | NuGet + project | Built-in |
| Statistical analysis | Extensive | Basic (use benchstat) |
| Memory tracking | Detailed | Good |
| Profiling integration | Separate tools | Built-in |
| Output format | Beautiful | Functional |
| Multiple runtimes | Yes | No (just Go) |
| Configuration | Attributes | Code |

## Practical Tips

### Avoid Compiler Optimisation

The compiler might optimise away unused results:

```go
// BAD: compiler might skip the work
func BenchmarkBad(b *testing.B) {
    for i := 0; i < b.N; i++ {
        Add(2, 3)  // result unused, might be optimised away
    }
}

// GOOD: use the result
var result int

func BenchmarkGood(b *testing.B) {
    var r int
    for i := 0; i < b.N; i++ {
        r = Add(2, 3)
    }
    result = r  // prevent optimisation
}
```

### Benchmark What Matters

Don't benchmark trivial operations:

```go
// Pointless: measures loop overhead more than Add
func BenchmarkTrivial(b *testing.B) {
    for i := 0; i < b.N; i++ {
        _ = 2 + 3
    }
}
```

Benchmark real workloads with realistic data sizes.

### Profile Before Optimising

Don't guess. Profile first:

```bash
go test -bench=SlowFunction -cpuprofile=cpu.prof
go tool pprof -http=:8080 cpu.prof
```

Find the actual bottleneck. Often it's not where you'd expect.

## The Honest Take

Go's built-in benchmarking is one of its genuinely great features. Zero setup, good enough for most needs.

**What Go does better:**
- Zero dependencies for benchmarking
- Integrated profiling
- pprof is excellent
- Quick feedback loop
- Live application profiling is easy

**What BenchmarkDotNet does better:**
- More rigorous statistical analysis
- Better output formatting
- Multiple runtime comparison
- More configuration options
- Memory diagnostics are more detailed

**The verdict:**
For day-to-day "is this fast enough?" benchmarking, Go's built-in tools are excellent. For publishing performance claims or deep analysis, BenchmarkDotNet is more thorough.

But Go wins on the "I can just do this" factor. No packages to install. No project to configure. Write a function, run a command, get numbers. That low friction means you actually benchmark things.

---

*That wraps up Phase 2 on the ecosystem—project structure, testing, mocking, and benchmarking. These are the tools you'll use every day. Go's approach is consistently simpler than .NET's, with trade-offs in power and flexibility. But for most work, simpler is better.*
