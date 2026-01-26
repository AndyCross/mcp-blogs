+++
title = "The Phrasebook: C# Concepts in Go Terms"
date = "2024-12-28"
draft = false
tags = ["go", "dotnet", "syntax", "csharp"]
+++

Before we get into the weeds of types and patterns, let's establish some vocabulary. Go uses different names for familiar concepts, and has operators you've never seen. This post is a reference. Skim it now, bookmark it for later.

## The Terminology Swap

Your C# brain thinks in certain words. Here's the translation:

| C# Term | Go Term | Notes |
|---------|---------|-------|
| `List<T>` | slice | Dynamic array, the workhorse collection |
| `T[]` (array) | slice (usually) | Go has arrays, but you'll rarely use them |
| `Dictionary<K,V>` | map | `map[string]int` instead of `Dictionary<string, int>` |
| namespace | package | But packages are directories, not hierarchies |
| `null` | `nil` | Same concept, different spelling |
| class | struct | No inheritance, but methods work |
| property | field (+ methods) | No get/set syntax |
| `var` | `var` or `:=` | Two ways to declare variables |
| `async`/`await` | goroutines + channels | Completely different model |
| exception | error | Errors are values, not control flow |
| `try`/`catch` | `if err != nil` | Explicit checking, no unwinding |
| `using` | `defer` | Cleanup runs at function exit |
| `lock` | `sync.Mutex` | Manual lock/unlock |
| `foreach` | `for range` | Single construct for iteration |
| `out`/`ref` | pointers | Explicit `*` and `&` |
| LINQ | nothing built-in | Loops, or generics since 1.18 |
| extension methods | nothing | Define functions, not methods |
| partial class | nothing | All code in the package shares scope |
| static class | package-level functions | No class, just functions |

### Arrays vs Slices

This one catches everyone. In C#, "array" means a fixed-size, contiguous block:

```csharp
int[] numbers = new int[5];  // fixed size 5
```

In Go, this is also called an array, but you almost never use them directly:

```go
var numbers [5]int  // array - fixed size, rarely used
```

What you use instead is a **slice**, a dynamic view over an array:

```go
numbers := []int{1, 2, 3, 4, 5}  // slice - this is what you want
numbers = append(numbers, 6)     // grows automatically
```

Think of slices as `List<T>` that happens to have array-like syntax. They grow, shrink, and pass by reference (sort of: the header is copied, but the backing array is shared).

**The rule:** if you're reaching for an array in Go, you probably want a slice.

### Maps

`Dictionary<K, V>` becomes `map[K]V`. The syntax is inside-out:

```csharp
// C#
var scores = new Dictionary<string, int>
{
    ["Alice"] = 100,
    ["Bob"] = 85
};
```

```go
// Go
scores := map[string]int{
    "Alice": 100,
    "Bob":   85,
}
```

Key differences:
- Maps must be initialised before use (nil maps panic on write)
- Missing keys return the zero value
- Use the two-value form to check existence: `val, ok := m[key]`

```go
score, exists := scores["Charlie"]
if !exists {
    fmt.Println("Charlie not found")
}
```

## Operators You Haven't Met

Go has several operators and constructs that don't exist in C#. Here's your cheat sheet.

### `:=` Short Variable Declaration

This is the one you'll use constantly:

```go
// These are equivalent
var name string = "Alice"
name := "Alice"  // type inferred, shorter
```

The `:=` operator declares AND assigns. It only works inside functions, and only for new variables.

```go
name := "Alice"
name := "Bob"    // ERROR: no new variables on left side
name = "Bob"     // OK: just assignment, no declaration
```

**The gotcha:** `:=` in an inner scope creates a new variable that shadows the outer one:

```go
name := "Alice"
if true {
    name := "Bob"  // new variable, shadows outer 'name'
    fmt.Println(name)  // "Bob"
}
fmt.Println(name)  // "Alice" - outer unchanged!
```

This is a common source of bugs. Use `=` for assignment when the variable already exists.

### `_` Blank Identifier

The underscore discards a value. You'll use it constantly because Go requires you to use all declared variables:

```go
// Ignore the index in a range loop
for _, value := range items {
    fmt.Println(value)
}

// Ignore an unwanted return value
_, err := doSomething()

// Ignore the second return value (existence check)
value, _ := myMap[key]  // don't care if it exists

// Interface compliance check (compile-time)
var _ io.Reader = (*MyType)(nil)
```

### `<-` Channel Operator

Channels are Go's concurrency primitive. The `<-` operator sends and receives:

```go
ch := make(chan int)

go func() {
    ch <- 42  // send 42 into the channel
}()

value := <-ch  // receive from the channel
fmt.Println(value)  // 42
```

The arrow points in the direction of data flow. Send: `ch <- value`. Receive: `value := <-ch`.

### `...` Variadic and Spread

Two related uses for the ellipsis:

**Variadic parameters** (like C#'s `params`):

```go
func Sum(numbers ...int) int {
    total := 0
    for _, n := range numbers {
        total += n
    }
    return total
}

Sum(1, 2, 3)  // works
Sum(1, 2, 3, 4, 5)  // also works
```

**Spreading a slice** into variadic arguments:

```go
numbers := []int{1, 2, 3, 4, 5}
Sum(numbers...)  // unpacks the slice
```

### `&` and `*` (Pointers)

These exist in C# but you probably haven't used them much. In Go, they're everywhere:

```go
x := 42
p := &x   // p is *int, points to x
*p = 100  // dereference: x is now 100
```

More commonly, you'll see them with structs:

```go
type User struct {
    Name string
}

u := User{Name: "Alice"}
ptr := &u           // *User
ptr.Name = "Bob"    // Go auto-dereferences for field access
```

### `make()` and `new()`

Two built-in functions for creating things:

**`make()`** is for slices, maps, and channels, types that need initialisation:

```go
s := make([]int, 0, 10)     // slice with length 0, capacity 10
m := make(map[string]int)   // initialised map (not nil!)
ch := make(chan int)        // unbuffered channel
ch := make(chan int, 10)    // buffered channel, capacity 10
```

**`new()`** allocates and returns a pointer to the zero value:

```go
p := new(User)  // *User, pointing to User{}
```

In practice, you'll use `make()` often and `new()` rarely. The composite literal with `&` is more common:

```go
p := &User{Name: "Alice"}  // equivalent to new + field assignment
```

## The `for` Loop (It's the Only One)

Go has one loop construct: `for`. It does everything.

```go
// Traditional for loop (like C#)
for i := 0; i < 10; i++ {
    fmt.Println(i)
}

// While loop (condition only)
for condition {
    // ...
}

// Infinite loop
for {
    // break to exit
}

// Range over slice (like foreach)
for index, value := range items {
    fmt.Println(index, value)
}

// Range over map
for key, value := range myMap {
    fmt.Println(key, value)
}

// Range over string (gives runes, not bytes)
for index, char := range "hello" {
    fmt.Printf("%d: %c\n", index, char)
}

// Range over channel
for msg := range messages {
    fmt.Println(msg)  // until channel is closed
}
```

Use `_` to ignore index or value:

```go
for _, value := range items { }  // ignore index
for index := range items { }     // ignore value (just omit it)
```

## `defer` Instead of `using`

C#'s `using` statement disposes resources at block exit:

```csharp
using var file = File.OpenRead("data.txt");
// file is disposed when scope exits
```

Go's `defer` schedules a function call to run when the *function* exits:

```go
file, err := os.Open("data.txt")
if err != nil {
    return err
}
defer file.Close()  // runs when this function returns

// use file...
```

Key differences:
- `defer` runs at function exit, not block exit
- Multiple defers run in LIFO order (last defer runs first)
- Deferred calls capture their arguments when the defer statement executes

```go
func example() {
    defer fmt.Println("first")
    defer fmt.Println("second")
    defer fmt.Println("third")
}
// Output: third, second, first
```

## Error Handling: `if err != nil`

This is the biggest mental shift. No exceptions, no try/catch. Errors are values.

```go
file, err := os.Open("data.txt")
if err != nil {
    return fmt.Errorf("failed to open: %w", err)
}
defer file.Close()

data, err := io.ReadAll(file)
if err != nil {
    return fmt.Errorf("failed to read: %w", err)
}
```

You'll write `if err != nil` hundreds of times. It's verbose. It's explicit. It works.

The `%w` verb wraps errors, preserving the chain for later inspection with `errors.Is()` and `errors.As()`.

## Multiple Return Values

Go functions can return multiple values. This is how errors are returned:

```go
func Divide(a, b float64) (float64, error) {
    if b == 0 {
        return 0, errors.New("division by zero")
    }
    return a / b, nil
}

result, err := Divide(10, 2)
if err != nil {
    // handle error
}
```

You can also use named return values:

```go
func Divide(a, b float64) (result float64, err error) {
    if b == 0 {
        err = errors.New("division by zero")
        return  // returns named values
    }
    result = a / b
    return
}
```

Named returns are sometimes clearer, sometimes not. Use your judgement.

## Type Assertions and Switches

When you have an `interface{}` (or `any`) and need the concrete type:

```go
// Type assertion
value := something.(string)  // panics if not string

// Safe type assertion
value, ok := something.(string)
if !ok {
    // not a string
}

// Type switch
switch v := something.(type) {
case string:
    fmt.Println("string:", v)
case int:
    fmt.Println("int:", v)
default:
    fmt.Println("unknown type")
}
```

## Quick Reference Card

Keep this handy until it's automatic:

| When you want to... | C# | Go |
|---------------------|-----|-----|
| Declare and assign | `var x = 5;` | `x := 5` |
| Declare without assign | `int x;` | `var x int` |
| Create a list | `new List<int>()` | `[]int{}` or `make([]int, 0)` |
| Create a dictionary | `new Dictionary<K,V>()` | `make(map[K]V)` |
| Append to list | `list.Add(x)` | `slice = append(slice, x)` |
| Get dictionary value | `dict[key]` | `val := m[key]` or `val, ok := m[key]` |
| Check key exists | `dict.ContainsKey(k)` | `_, ok := m[k]` |
| Iterate collection | `foreach (var x in items)` | `for _, x := range items` |
| Null check | `if (x == null)` | `if x == nil` |
| String format | `$"Hello {name}"` | `fmt.Sprintf("Hello %s", name)` |
| Error handling | `try { } catch { }` | `if err != nil { }` |
| Cleanup | `using var x = ...` | `defer x.Close()` |
| Async | `await Task.Run(...)` | `go func() { }()` |

---

*This post is a reference, not a deep dive. We'll cover structs, visibility, and the type system properly in the next posts. But now you've got the vocabulary and the operators. The rest should make more sense.*
