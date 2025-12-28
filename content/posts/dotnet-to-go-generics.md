+++
title = "Generics: Late to the Party"
date = "2024-12-29"
draft = false
tags = ["go", "dotnet", "generics", "csharp"]
+++

Go shipped generics in version 1.18 (March 2022). C# has had them since 2.0 (November 2005). That's a seventeen-year head start, and it shows.

If you're coming from C# expecting the same power and flexibility, you'll be disappointed. Go's generics are deliberately constrained—they solve the common cases but won't let you build the same abstractions you're used to.

Let's look at what we've got, what's missing, and whether that matters.

## The Basic Syntax

A generic function in Go:

```go
func Map[T, U any](items []T, f func(T) U) []U {
    result := make([]U, len(items))
    for i, item := range items {
        result[i] = f(item)
    }
    return result
}

// Usage
numbers := []int{1, 2, 3, 4}
squared := Map(numbers, func(n int) int { return n * n })
```

Compare to C#:

```csharp
public static IEnumerable<U> Map<T, U>(IEnumerable<T> items, Func<T, U> f)
{
    foreach (var item in items)
        yield return f(item);
}

// Usage  
var numbers = new[] { 1, 2, 3, 4 };
var squared = Map(numbers, n => n * n);
```

The syntax is different but the concept is familiar. Type parameters go in square brackets in Go (`[T, U any]`) rather than angle brackets (`<T, U>`). The `any` is a constraint—more on that shortly.

## Constraints

Here's where Go's approach diverges. In C#, you constrain type parameters with `where`:

```csharp
public T Max<T>(T a, T b) where T : IComparable<T>
{
    return a.CompareTo(b) > 0 ? a : b;
}
```

In Go, constraints are interfaces:

```go
func Max[T cmp.Ordered](a, b T) T {
    if a > b {
        return a
    }
    return b
}
```

The `cmp.Ordered` constraint (from the standard library) allows the `>` operator. Without it, Go wouldn't know that `T` supports comparison.

### Built-in Constraints

Go provides some standard constraints in the `constraints` and `cmp` packages:

| Constraint | What it allows |
|-----------|----------------|
| `any` | Any type (alias for `interface{}`) |
| `comparable` | Types that support `==` and `!=` |
| `cmp.Ordered` | Types that support `<`, `>`, `<=`, `>=` |
| `constraints.Integer` | All integer types |
| `constraints.Float` | All float types |
| `constraints.Signed` | Signed integers |
| `constraints.Unsigned` | Unsigned integers |

### Custom Constraints

You can define your own constraints as interfaces:

```go
type Number interface {
    ~int | ~int64 | ~float64
}

func Sum[T Number](items []T) T {
    var total T
    for _, item := range items {
        total += item
    }
    return total
}
```

That `~int` syntax means "any type whose underlying type is int". This lets you include type aliases and defined types, not just the primitive itself.

## Generic Types

Generic structs work as you'd expect:

```go
type Stack[T any] struct {
    items []T
}

func (s *Stack[T]) Push(item T) {
    s.items = append(s.items, item)
}

func (s *Stack[T]) Pop() (T, bool) {
    if len(s.items) == 0 {
        var zero T
        return zero, false
    }
    item := s.items[len(s.items)-1]
    s.items = s.items[:len(s.items)-1]
    return item, true
}

// Usage
stack := &Stack[string]{}
stack.Push("hello")
value, ok := stack.Pop()
```

## Where the Gaps Hurt

Right, here's the honest bit. Go's generics are limited in ways that'll frustrate you coming from C#.

### No Generic Methods on Non-Generic Types

In C#, you can do this:

```csharp
public class Converter
{
    public T Convert<T>(string value) { ... }
}
```

In Go, you can't add a generic method to a non-generic type. This doesn't compile:

```go
type Converter struct{}

// ERROR: method must have no type parameters
func (c Converter) Convert[T any](value string) T { ... }
```

You have to use a generic function instead:

```go
func Convert[T any](c Converter, value string) T { ... }
```

It works, but it's clunkier and doesn't chain as nicely.

### No Specialisation

C# lets you specialise behaviour based on type arguments (with runtime checks or partial specialisation). Go doesn't. You can't do:

```go
func Process[T any](item T) {
    // Can't check "if T is string, do this"
    // Can't have different implementations for different T
}
```

Everything must work uniformly for all types that satisfy the constraint.

### No Variance

C# has covariance (`out T`) and contravariance (`in T`) for generic interfaces. Go has neither. A `Stack[Dog]` is not a `Stack[Animal]`, even if `Dog` implements `Animal`. Ever.

### No Arithmetic Constraints (Sort Of)

Want to write a generic sum function? You need to constrain to types that support `+`:

```go
func Sum[T constraints.Integer | constraints.Float](items []T) T {
    var total T
    for _, item := range items {
        total += item
    }
    return total
}
```

This works, but you can't easily extend it to custom numeric types. The constraint system is based on underlying types, not operators.

### No Default Type Arguments

C# has:

```csharp
public class Cache<TKey, TValue, TSerializer = JsonSerializer> { }
```

Go doesn't. Every type parameter must be specified at use sites (though type inference helps for functions).

## The Standard Library's Generics

Go 1.21+ added generic functions to the standard library. These are genuinely useful:

```go
import (
    "maps"
    "slices"
)

// Slices
numbers := []int{3, 1, 4, 1, 5, 9}
slices.Sort(numbers)
found := slices.Contains(numbers, 4)
maxVal := slices.Max(numbers)

// Maps  
m := map[string]int{"a": 1, "b": 2}
keys := maps.Keys(m)    // iterator over keys
values := maps.Values(m) // iterator over values
maps.Clone(m)           // shallow copy
```

Before generics, you'd write these loops by hand every time. Now they're type-safe and reusable.

## When You'll Feel the Gaps

**Building Fluent APIs**

In C#, you might build a fluent configuration API with generic methods:

```csharp
builder
    .WithOption<ConnectionOptions>(opts => opts.Timeout = 30)
    .WithOption<RetryOptions>(opts => opts.MaxRetries = 3)
    .Build();
```

This pattern is harder in Go because you can't have generic methods. You'd need a different approach—probably top-level functions or a less fluent API.

**Repository Patterns**

The classic `IRepository<T>` with `Find<TKey>` is awkward:

```go
// This doesn't work - can't have generic method
type Repository[T any] interface {
    Find[K comparable](id K) (T, error)  // ERROR
}

// You'd need this instead
type Repository[T any, K comparable] interface {
    Find(id K) (T, error)
}
```

Two type parameters instead of one, threaded through everything.

**LINQ-style Operations**

C# LINQ chains beautifully with generic extension methods:

```csharp
items.Where(x => x.Active).Select(x => x.Name).OrderBy(x => x).ToList();
```

Go has no extension methods. You'd write:

```go
result := slices.Sorted(
    slices.Collect(
        Map(
            Filter(items, func(x Item) bool { return x.Active }),
            func(x Item) string { return x.Name },
        ),
    ),
)
```

Functional, but not as elegant.

## The Practical Advice

After working with Go's generics, here's how I use them:

**Do use generics for:**
- Data structures (stacks, queues, trees, caches)
- Collection utilities (map, filter, reduce)
- Type-safe wrappers around `interface{}`
- Eliminating repetitive code across similar types

**Don't use generics for:**
- Everything. Go's non-generic code is often clearer.
- Patterns that require generic methods (rethink the design)
- Complex type relationships (the constraint syntax gets unwieldy)

**Accept these limitations:**
- Write more concrete types, fewer abstractions
- Use interfaces for polymorphism, generics for type safety
- Sometimes duplicate code is clearer than a generic contortion

## The Honest Assessment

| Aspect | C# Generics | Go Generics |
|--------|------------|-------------|
| Maturity | 20 years | 3 years |
| Generic methods | Yes | Only on generic types |
| Variance | Full (in/out) | None |
| Constraints | Rich (interfaces, new(), class, struct) | Interfaces only |
| Specialisation | Partial (with runtime checks) | None |
| Standard library | Extensive | Growing |

Go's generics are *good enough* for most real-world needs. They eliminate the pre-1.18 pain of `interface{}` everywhere or code generation. But they're not trying to match C#'s power.

The Go team explicitly chose to ship a simpler system first, with room to expand. Whether the gaps will be filled or the community will adapt around them remains to be seen.

For now? Lower your expectations, use generics where they help, and don't twist yourself into knots trying to replicate C# patterns that don't translate well.

---

*Next up: nil in Go versus nullable reference types in C#—two different approaches to the billion dollar mistake, and why both languages still get caught out.*
