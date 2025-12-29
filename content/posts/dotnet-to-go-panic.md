+++
title = "Panic and Recover: The Emergency Exit"
date = "2024-12-30"
draft = false
tags = ["go", "dotnet", "errors", "csharp"]
+++

So Go doesn't have exceptions. Except... it kind of does. They're called `panic` and `recover`, and they work almost exactly like throw and catch.

Here's the thing: if you use them like exceptions, other Go developers will judge you. Harshly. Let's understand why they exist, when to use them, and why the judgment is (mostly) deserved.

## What Panic Does

`panic` stops normal execution and begins unwinding the stack:

```go
func divide(a, b int) int {
    if b == 0 {
        panic("division by zero")
    }
    return a / b
}

func main() {
    result := divide(10, 0)  // panics here
    fmt.Println(result)      // never reached
}
```

Output:

```
panic: division by zero

goroutine 1 [running]:
main.divide(...)
        /app/main.go:7
main.main()
        /app/main.go:12
exit status 2
```

Sound familiar? It's an unhandled exception with a stack trace.

Deferred functions still run during a panic:

```go
func riskyOperation() {
    defer fmt.Println("cleanup runs")  // this executes
    panic("oh no")
    fmt.Println("never reached")
}
```

## What Recover Does

`recover` catches a panic. It only works inside a deferred function:

```go
func safeOperation() (err error) {
    defer func() {
        if r := recover(); r != nil {
            err = fmt.Errorf("recovered from panic: %v", r)
        }
    }()
    
    riskyOperation()  // might panic
    return nil
}
```

If `riskyOperation` panics, `recover()` catches it and we convert it to an error. The function returns normally instead of crashing.

This is literally try/catch:

```csharp
// C# equivalent
try
{
    RiskyOperation();
}
catch (Exception ex)
{
    return new Error($"recovered from exception: {ex.Message}");
}
```

## Why Go Developers Judge You

So if panic/recover is just exceptions by another name, why not use them that way?

Because Go's error philosophy is that **errors are expected, panics are not**.

- Errors are things that can reasonably happen: file not found, network timeout, invalid input
- Panics are things that *shouldn't* happen: nil pointer dereference, index out of bounds, programmer bugs

When you use panic for normal errors, you're saying "this should never happen" when what you mean is "I didn't want to write `if err != nil`."

The community has strong opinions about this:

```go
// This will get you judged
func ParseConfig(path string) Config {
    data, err := os.ReadFile(path)
    if err != nil {
        panic(err)  // NO - missing file is a normal error
    }
    // ...
}

// This is fine
func MustParseConfig(path string) Config {
    // "Must" in the name signals this panics
    // Only use at startup where failure = can't run
}
```

## When Panic Is Appropriate

Despite the judgment, there are legitimate uses:

### 1. Truly Unrecoverable Programmer Errors

```go
func processItem(item *Item) {
    if item == nil {
        panic("processItem called with nil item")
    }
    // This is a programming error - the caller screwed up
    // Not a runtime condition we should handle gracefully
}
```

### 2. Initialisation Failures

```go
var db = mustConnect()

func mustConnect() *sql.DB {
    db, err := sql.Open("postgres", os.Getenv("DATABASE_URL"))
    if err != nil {
        panic(fmt.Sprintf("database connection failed: %v", err))
    }
    return db
}
```

If the program can't start without a database, panicking at init is reasonable. There's nothing useful to do with the error.

### 3. The "Must" Convention

Standard library examples:

```go
// template.Must panics if parsing fails
var templates = template.Must(template.ParseGlob("*.html"))

// regexp.MustCompile panics if pattern is invalid
var emailRegex = regexp.MustCompile(`^[a-z]+@[a-z]+\.[a-z]+$`)
```

The `Must` prefix tells callers "this panics on error—only use with compile-time constant inputs."

### 4. Deep Recursion Bailout

Sometimes you're deep in recursion and unwinding through error returns is painful:

```go
func parse(tokens []Token) (result AST, err error) {
    defer func() {
        if r := recover(); r != nil {
            if parseErr, ok := r.(parseError); ok {
                err = parseErr
            } else {
                panic(r)  // re-panic if it's not our error
            }
        }
    }()
    
    return parseExpression(tokens), nil
}

func parseExpression(tokens []Token) AST {
    // Deep recursive descent
    // ...
    if somethingWrong {
        panic(parseError{msg: "unexpected token", pos: pos})
    }
}
```

This is controversial but accepted in parsers and similar deep-recursion scenarios. Note that the panic is recovered at the boundary and converted to an error.

## The Boundary Pattern

The key pattern: **never let panics escape your package**.

If your code might panic (or call code that might panic), recover at the boundary:

```go
// Public API - never panics
func (s *Service) ProcessRequest(req Request) (Response, error) {
    defer func() {
        if r := recover(); r != nil {
            // Log, maybe alert
            log.Printf("panic in ProcessRequest: %v", r)
        }
    }()
    
    return s.doProcess(req)  // internal, might panic
}
```

HTTP handlers often do this:

```go
func recoveryMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        defer func() {
            if err := recover(); err != nil {
                log.Printf("panic: %v\n%s", err, debug.Stack())
                http.Error(w, "Internal Server Error", 500)
            }
        }()
        next.ServeHTTP(w, r)
    })
}
```

A panic in a handler becomes a 500 response, not a crashed server.

## Panic Values

Unlike C# where you throw `Exception` objects, you can panic with any value:

```go
panic("a string")
panic(42)
panic(errors.New("an error"))
panic(MyCustomType{})
```

When recovering, you get an `interface{}`:

```go
if r := recover(); r != nil {
    switch v := r.(type) {
    case error:
        log.Printf("error: %v", v)
    case string:
        log.Printf("string: %s", v)
    default:
        log.Printf("unknown: %v", v)
    }
}
```

Best practice: panic with `error` values or strings. Makes recovery predictable.

## Comparison with C#

| Aspect | C# Exceptions | Go Panic/Recover |
|--------|---------------|------------------|
| Normal errors | Often used | Strongly discouraged |
| Programmer bugs | Appropriate | Appropriate |
| Syntax | `try`/`catch`/`finally` | `defer`/`recover` |
| Stack traces | Automatic | Available via `debug.Stack()` |
| Filtering | Catch by type | Check recovered value |
| Re-throwing | `throw;` | `panic(r)` |
| Custom types | Exception subclasses | Any type (usually error) |
| Cultural norm | Expected | Emergency only |

## The Test Exception

One place where panic is universally accepted: tests.

```go
func TestSomething(t *testing.T) {
    result := process(input)
    
    if result != expected {
        t.Fatalf("got %v, want %v", result, expected)  // this panics
    }
}
```

`t.Fatal` and `t.Fatalf` panic to abort the test. This is fine—tests are the one place where "stop everything" is the right response to failure.

## The Honest Take

**When I use panic:**
- `Must` functions for startup initialisation
- Genuinely impossible conditions (defensive programming)
- Test assertions via `t.Fatal`

**When I don't use panic:**
- File not found
- Network errors
- Invalid user input
- Anything that can reasonably happen at runtime

**The rule I follow:**
If I'm tempted to panic, I ask: "Is this a bug in my program, or is this something that could happen in production?" Bugs can panic. Production conditions should return errors.

## What About Performance?

One argument for panic: "it's faster because you don't have to check errors at every level."

This is technically true but practically irrelevant. Error checking is a comparison and conditional jump. The performance difference is unmeasurable in real code.

Don't let performance justify panic. If you're that performance-sensitive, you're probably not writing Go anyway.

---

*Coming up: Go's switch statement—more powerful than C#'s, with type switching, expression cases, and some surprises around fallthrough.*
