+++
title = "The Empty Interface and Type Assertions"
date = "2025-01-02"
draft = false
tags = ["go", "dotnet", "interfaces", "any", "csharp"]
series = ["step-over-to-go"]
+++

Go has a type called `any`. Before Go 1.18, it was written `interface{}`. Same thing, nicer name. And it's basically Go's version of `object`, the type that can hold anything.

Every type in Go implements `any` because `any` has no methods. Zero requirements means universal satisfaction. And that means when you use `any`, you're opting out of the type system.

Let's talk about when that's okay, when it's not, and how to get your types back when you need them.

## What Is `any` / `interface{}`?

An empty interface is an interface with no methods:

```go
interface{}  // the old syntax
any          // alias added in Go 1.18, same thing
```

Since there are no required methods, every type satisfies this interface. Everything is an `any`.

```go
var x any

x = 42              // int
x = "hello"         // string
x = []int{1, 2, 3}  // slice
x = struct{}{}      // empty struct
x = nil             // nil
```

All valid. `any` is the universal container.

## The C# Equivalent: `object`

C#'s `object` is the same idea:

```csharp
object x;
x = 42;
x = "hello";
x = new List<int> { 1, 2, 3 };
```

Both languages have this escape hatch for "I don't know the type at compile time." Both languages encourage you to avoid it when possible.

## Why `any` Exists

Sometimes you genuinely don't know the type:

**JSON with unknown structure:**

```go
var data any
json.Unmarshal(rawBytes, &data)
// data is now map[string]any or []any or a primitive
```

**Generic containers before Go had generics:**

```go
// Before Go 1.18
type Stack struct {
    items []interface{}
}

func (s *Stack) Push(item interface{}) {
    s.items = append(s.items, item)
}
```

**Function parameters that accept anything:**

```go
func Println(a ...any) (n int, err error)
```

`fmt.Println` takes `any` because it prints anything.

## Type Assertions: Getting Types Back

When you have an `any` and need the actual type, you use a **type assertion**:

```go
var x any = "hello"

s := x.(string)  // assert x is a string
fmt.Println(s)   // "hello"
```

The syntax is `value.(Type)`. It says "I believe this `any` contains a `Type`, give it to me."

### The Danger: Panics

If you're wrong, it panics:

```go
var x any = 42
s := x.(string)  // panic: interface conversion: int is not string
```

This is like an invalid cast exception in C#:

```csharp
object x = 42;
string s = (string)x;  // InvalidCastException
```

### The Safe Way: Comma-OK Idiom

Always use the two-value form in real code:

```go
var x any = 42

s, ok := x.(string)
if !ok {
    fmt.Println("x is not a string")
} else {
    fmt.Println(s)
}
```

If the assertion fails, `ok` is `false` and `s` is the zero value of `string`. No panic.

This is like C#'s `as` operator plus null check:

```csharp
object x = 42;
if (x is string s)
{
    Console.WriteLine(s);
}
else
{
    Console.WriteLine("x is not a string");
}
```

## Type Switches: Handling Multiple Types

When you need to handle different types, use a type switch:

```go
func describe(x any) {
    switch v := x.(type) {
    case int:
        fmt.Printf("int: %d\n", v)
    case string:
        fmt.Printf("string: %s\n", v)
    case bool:
        fmt.Printf("bool: %t\n", v)
    case []int:
        fmt.Printf("slice of ints: %v\n", v)
    default:
        fmt.Printf("unknown type: %T\n", v)
    }
}
```

The `x.(type)` syntax only works in a switch. Each case binds `v` to the correctly typed value.

This is cleaner than chained type assertions:

```go
// DON'T do this
if i, ok := x.(int); ok {
    // ...
} else if s, ok := x.(string); ok {
    // ...
} else if b, ok := x.(bool); ok {
    // ...
}

// DO this
switch v := x.(type) {
case int:
    // v is int
case string:
    // v is string
case bool:
    // v is bool
}
```

## Working with JSON

This is where `any` shows up most in real code. JSON decoding into unknown structures:

```go
func processJSON(raw []byte) error {
    var data any
    if err := json.Unmarshal(raw, &data); err != nil {
        return err
    }
    
    return walkJSON(data)
}

func walkJSON(v any) error {
    switch val := v.(type) {
    case map[string]any:
        for key, value := range val {
            fmt.Printf("key: %s\n", key)
            walkJSON(value)
        }
    case []any:
        for i, item := range val {
            fmt.Printf("index: %d\n", i)
            walkJSON(item)
        }
    case string:
        fmt.Printf("string: %s\n", val)
    case float64:  // JSON numbers are float64
        fmt.Printf("number: %f\n", val)
    case bool:
        fmt.Printf("bool: %t\n", val)
    case nil:
        fmt.Println("null")
    }
    return nil
}
```

JSON objects become `map[string]any`. Arrays become `[]any`. Numbers are always `float64` (JSON doesn't distinguish int from float).

## The Performance Cost

There's overhead to `any`. The interface value stores two pointers (type and value), and type assertions have runtime cost.

For hot paths, you want concrete types:

```go
// Slower - any with type assertion
func processAny(x any) {
    if n, ok := x.(int); ok {
        // work with n
    }
}

// Faster - concrete type
func processInt(n int) {
    // work with n
}
```

With generics in Go 1.18+, you often don't need `any`:

```go
// Before generics
func Contains(slice []any, item any) bool { ... }

// With generics - type safe, no assertions needed
func Contains[T comparable](slice []T, item T) bool { ... }
```

## When to Use `any`

**Legitimate uses:**

- JSON/YAML with unknown structure
- Reflection-based code
- Interfacing with dynamic systems
- Printf-style variadic functions

**Code smells:**

- Using `any` to avoid thinking about types
- `map[string]any` as a "flexible" data structure (define a struct)
- `any` parameters when a specific interface would work
- Type assertions scattered throughout code

## Comparing to C#

| Aspect | Go `any` | C# `object` |
|--------|----------|-------------|
| Boxing value types | No (pointers stored) | Yes |
| Type assertion | `x.(Type)` | `(Type)x` or `x as Type` |
| Safe assertion | `v, ok := x.(Type)` | `x is Type v` |
| Type switch | `switch v := x.(type)` | `switch (x)` with patterns |
| Performance cost | Yes | Yes (especially boxing) |

C# has better pattern matching:

```csharp
object x = GetSomething();
var result = x switch
{
    int i => $"int: {i}",
    string s => $"string: {s}",
    IEnumerable<int> list => $"list with {list.Count()} items",
    { } obj => $"object: {obj}",
    null => "null"
};
```

Go's type switch is simpler but less powerful.

## The Honest Take

`any` is an escape hatch. Sometimes you need it. Most of the time, you don't.

**What Go does okay:**
- Clear syntax for type assertions
- Type switches are readable
- No boxing for value types (unlike C#)

**What C# does better:**
- Richer pattern matching
- `is` and `as` operators are more intuitive
- Better tooling for discovering what types you'll encounter

**What both should make you do:**
- Reach for generics first
- Define concrete interfaces where possible
- Use `any` only at boundaries (JSON parsing, reflection, interop)

**The verdict:**
Every time you write `any`, ask yourself: "Do I really not know the type here?" Often you do know it, or you could define an interface that captures what you need.

`any` is the "I give up" of Go's type system. Sometimes giving up is appropriate. A well-designed API rarely needs it.

---

*That wraps up the interfaces and composition section. Go's approach is simpler than C#'s: implicit interfaces, embedding instead of inheritance, and a minimal `any` type for the truly dynamic cases. It's less powerful in some ways, but the constraints push you toward cleaner designs.*
