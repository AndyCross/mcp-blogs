+++
title = "The switch Statement You Always Wanted"
date = "2024-12-30"
draft = false
tags = ["go", "dotnet", "control-flow", "csharp"]
+++

C#'s switch statement has evolved a lot over the years. Pattern matching, switch expressions, when guards—it's become genuinely powerful. But Go's switch has some tricks that'll make you wish C# worked this way.

Let's look at what Go's switch can do, including the bits that'll trip you up.

## Basic Switch: No Fallthrough by Default

First surprise: Go switches don't fall through by default.

```csharp
// C# - falls through if you forget break (historically)
switch (day)
{
    case "Monday":
        Console.WriteLine("Start of week");
        break;  // required!
    case "Friday":
        Console.WriteLine("End of week");
        break;
}
```

```go
// Go - no break needed, no fallthrough
switch day {
case "Monday":
    fmt.Println("Start of week")
    // automatically breaks here
case "Friday":
    fmt.Println("End of week")
}
```

This is a genuine improvement. The C# pattern of requiring `break` after every case was a source of bugs for decades. Go's default—exit after each case—matches what you almost always want.

## Multiple Values Per Case

Want the same code for multiple cases? In C#:

```csharp
switch (day)
{
    case "Saturday":
    case "Sunday":
        Console.WriteLine("Weekend");
        break;
}
```

In Go:

```go
switch day {
case "Saturday", "Sunday":
    fmt.Println("Weekend")
}
```

Cleaner. Multiple values in one case clause, comma-separated.

## No Expression Required

Here's something C# can't do. Go's switch doesn't need an expression:

```go
switch {
case hour < 12:
    fmt.Println("Good morning")
case hour < 17:
    fmt.Println("Good afternoon")
default:
    fmt.Println("Good evening")
}
```

This is equivalent to an if-else chain but often more readable:

```go
// Equivalent, but more verbose
if hour < 12 {
    fmt.Println("Good morning")
} else if hour < 17 {
    fmt.Println("Good afternoon")
} else {
    fmt.Println("Good evening")
}
```

I use expressionless switch constantly. It's particularly good for range checks and complex conditions.

## Fallthrough (When You Actually Want It)

Sometimes you genuinely need fallthrough. Go has a `fallthrough` keyword:

```go
switch day {
case "Thursday":
    fmt.Println("Almost Friday")
    fallthrough
case "Friday":
    fmt.Println("Weekend soon!")
}

// Thursday prints both lines
// Friday prints just "Weekend soon!"
```

Important: `fallthrough` must be the last statement in a case, and it falls into the next case unconditionally—it doesn't re-evaluate the case expression.

```go
// This is usually wrong
switch x {
case 1:
    fallthrough  // falls into case 2 even if x != 2
case 2:
    doSomething()
}
```

In practice, I rarely use `fallthrough`. Multiple values per case covers most needs.

## Type Switches

This is where Go's switch shines. You can switch on type:

```go
func describe(i interface{}) {
    switch v := i.(type) {
    case int:
        fmt.Printf("Integer: %d\n", v)
    case string:
        fmt.Printf("String: %s\n", v)
    case bool:
        fmt.Printf("Boolean: %t\n", v)
    case []int:
        fmt.Printf("Slice of ints: %v\n", v)
    default:
        fmt.Printf("Unknown type: %T\n", v)
    }
}
```

The `v := i.(type)` syntax extracts both the type (for the case matching) and the value (as the correctly typed `v`).

C# has pattern matching now which does something similar:

```csharp
static void Describe(object o)
{
    switch (o)
    {
        case int i:
            Console.WriteLine($"Integer: {i}");
            break;
        case string s:
            Console.WriteLine($"String: {s}");
            break;
        // etc.
    }
}
```

Go got there first, and the syntax is arguable cleaner.

### Multiple Types Per Case

```go
switch v := i.(type) {
case int, int32, int64:
    fmt.Println("Some kind of integer")
    // Note: v is interface{} here, not a specific int type
case string, []byte:
    fmt.Println("String-like")
default:
    fmt.Printf("Type: %T\n", v)
}
```

When you match multiple types, `v` has type `interface{}` because the compiler can't know which type matched.

## Initialisation Statements

Like `if`, you can have an initialisation statement:

```go
switch os := runtime.GOOS; os {
case "darwin":
    fmt.Println("macOS")
case "linux":
    fmt.Println("Linux")
default:
    fmt.Printf("Other: %s\n", os)
}
// os is not visible here
```

Keeps the variable scoped to where it's used.

## Comparing to C#'s Switch Expressions

C# 8 added switch expressions, which are excellent:

```csharp
var message = day switch
{
    "Monday" => "Start of week",
    "Friday" => "End of week",
    "Saturday" or "Sunday" => "Weekend",
    _ => "Midweek"
};
```

Go doesn't have switch expressions—switch is always a statement, not an expression. You can't do:

```go
// This doesn't work in Go
message := switch day {
case "Monday":
    "Start of week"
// ...
}
```

You have to use a variable:

```go
var message string
switch day {
case "Monday":
    message = "Start of week"
case "Friday":
    message = "End of week"
case "Saturday", "Sunday":
    message = "Weekend"
default:
    message = "Midweek"
}
```

This is one area where C# is genuinely more elegant.

## When Guards (Sort Of)

C# has `when` guards in pattern matching:

```csharp
switch (response)
{
    case HttpResponse { StatusCode: var code } when code >= 400:
        HandleError(code);
        break;
}
```

Go doesn't have `when`, but expressionless switch achieves similar things:

```go
switch {
case response.StatusCode >= 500:
    handleServerError(response)
case response.StatusCode >= 400:
    handleClientError(response)
case response.StatusCode >= 200:
    handleSuccess(response)
}
```

Not quite as powerful as full pattern matching, but covers most cases.

## The Default Case

Go's `default` case can appear anywhere (not just at the end):

```go
switch day {
default:
    fmt.Println("Weekday")
case "Saturday", "Sunday":
    fmt.Println("Weekend")
}
```

Convention says put it last, but Go doesn't enforce it.

## Switching on Errors

A common pattern for error handling:

```go
err := doSomething()
switch {
case err == nil:
    // success
case errors.Is(err, ErrNotFound):
    // handle not found
case errors.Is(err, ErrPermissionDenied):
    // handle permission error
default:
    // unknown error
    return err
}
```

Sometimes cleaner than a chain of if-else-if.

## The Comparison

| Feature | C# | Go |
|---------|-----|-----|
| Break required | No (modern) | No |
| Fallthrough | By omitting break (legacy) | `fallthrough` keyword |
| Multiple values | `case a, b:` (older) or `case a or b:` | `case a, b:` |
| Expression switch | Yes (switch expression) | No (statement only) |
| Type switching | Pattern matching | `switch v := x.(type)` |
| No expression | No | Yes (`switch { case cond: }`) |
| When guards | Yes | No (use expressionless switch) |
| Init statement | No | Yes |

## Practical Patterns

### State Machine

```go
type State int

const (
    StateIdle State = iota
    StateRunning
    StatePaused
    StateStopped
)

func (s *Machine) handleEvent(event Event) {
    switch s.state {
    case StateIdle:
        switch event {
        case EventStart:
            s.state = StateRunning
        default:
            // ignore
        }
    case StateRunning:
        switch event {
        case EventPause:
            s.state = StatePaused
        case EventStop:
            s.state = StateStopped
        }
    // etc.
    }
}
```

### Command Dispatch

```go
func handleCommand(cmd string, args []string) error {
    switch cmd {
    case "list":
        return listItems()
    case "add":
        if len(args) < 1 {
            return errors.New("add requires an item name")
        }
        return addItem(args[0])
    case "remove":
        if len(args) < 1 {
            return errors.New("remove requires an item name")
        }
        return removeItem(args[0])
    default:
        return fmt.Errorf("unknown command: %s", cmd)
    }
}
```

### Parsing JSON with Type Switch

```go
func processValue(v interface{}) {
    switch val := v.(type) {
    case map[string]interface{}:
        for k, v := range val {
            fmt.Printf("Object key: %s\n", k)
            processValue(v)  // recurse
        }
    case []interface{}:
        for i, item := range val {
            fmt.Printf("Array index: %d\n", i)
            processValue(item)  // recurse
        }
    case string:
        fmt.Printf("String: %s\n", val)
    case float64:  // JSON numbers are float64
        fmt.Printf("Number: %f\n", val)
    case bool:
        fmt.Printf("Boolean: %t\n", val)
    case nil:
        fmt.Println("Null")
    }
}
```

## The Honest Take

Go's switch is one of the language's better features:

**Things I like:**
- No fallthrough by default (prevents bugs)
- Expressionless switch for complex conditions
- Type switches for working with interfaces
- Multiple values per case
- Init statements for scoping

**Things C# does better:**
- Switch expressions (returning values directly)
- Pattern matching with `when` guards
- Recursive patterns (`case Person { Age: > 18 }`)

**The verdict:**
Go's switch is simpler and covers the common cases elegantly. C#'s switch has more features for complex matching. Use what each language gives you.

---

*That wraps up Phase 3 on control flow and error handling. Next we'll move into concurrency—goroutines, channels, and why Go's approach to parallelism is fundamentally different from async/await.*
