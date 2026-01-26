+++
title = "if err != nil: Your New Reality"
date = "2024-12-30"
draft = false
tags = ["go", "dotnet", "errors", "csharp"]
+++

Let's address the elephant in the room. You're going to write `if err != nil` hundreds of times. Thousands, probably. And for the first week, you're going to hate it.

Coming from C#, where exceptions handle the sad path invisibly, Go's explicit error handling feels like a step backwards. It's verbose. It's repetitive. It clutters your code with what looks like boilerplate.

Then something shifts. You start to see what you're gaining. Let's work through that shift.

## Why No Exceptions?

C# uses exceptions for error handling:

```csharp
try
{
    var data = await File.ReadAllTextAsync("config.json");
    var config = JsonSerializer.Deserialize<Config>(data);
    await database.Connect(config.ConnectionString);
}
catch (FileNotFoundException)
{
    logger.Error("Config file missing");
}
catch (JsonException ex)
{
    logger.Error($"Invalid config: {ex.Message}");
}
catch (Exception ex)
{
    logger.Error($"Unexpected error: {ex.Message}");
    throw;
}
```

This looks clean. The happy path is uncluttered. Errors are handled elsewhere.

But there's a hidden cost: **you can't see which lines can fail**. Any line might throw. Any function you call might throw. The `catch` block is disconnected from the code that caused the problem.

Go takes the opposite view: **errors are values, returned like any other value**:

```go
data, err := os.ReadFile("config.json")
if err != nil {
    return fmt.Errorf("reading config: %w", err)
}

var config Config
if err := json.Unmarshal(data, &config); err != nil {
    return fmt.Errorf("parsing config: %w", err)
}

if err := database.Connect(config.ConnectionString); err != nil {
    return fmt.Errorf("connecting to database: %w", err)
}
```

Verbose? Yes. But look at what you can see:

- Every line that can fail is marked with `err :=` or `, err`
- You know exactly what error each block handles
- The handling is right next to the call that produced the error
- No hidden control flow. The code does what it looks like it does

## The Error Interface

In Go, `error` is just an interface:

```go
type error interface {
    Error() string
}
```

Anything with an `Error()` method is an error. This is intentionally simple.

Creating errors:

```go
import "errors"

// Simple error
err := errors.New("something went wrong")

// Formatted error
err := fmt.Errorf("failed to load user %d: %w", userID, originalErr)
```

That `%w` verb is important. It wraps the original error, preserving the chain.

## The Pattern You'll Write Forever

Here's the basic pattern:

```go
result, err := doSomething()
if err != nil {
    return fmt.Errorf("doing something: %w", err)
}
// use result
```

Variations:

```go
// When there's no result to use
if err := doSomething(); err != nil {
    return err
}

// When you want to handle specific errors
if err := doSomething(); err != nil {
    if errors.Is(err, ErrNotFound) {
        return defaultValue, nil  // handle gracefully
    }
    return zero, err  // propagate others
}

// When you need to clean up on error
file, err := os.Create("output.txt")
if err != nil {
    return err
}
defer file.Close()

if err := writeData(file); err != nil {
    os.Remove("output.txt")  // clean up partial file
    return fmt.Errorf("writing data: %w", err)
}
```

## Wrapping Errors Properly

Go 1.13 introduced error wrapping. Use it:

```go
// BAD: loses the original error
if err != nil {
    return errors.New("failed to connect")
}

// BAD: concatenates as string, loses error chain
if err != nil {
    return fmt.Errorf("failed to connect: %s", err)
}

// GOOD: wraps the error, preserves the chain
if err != nil {
    return fmt.Errorf("failed to connect: %w", err)
}
```

The `%w` verb creates a chain that can be inspected:

```go
if errors.Is(err, sql.ErrNoRows) {
    // somewhere in the chain, there's a sql.ErrNoRows
}

var pathErr *os.PathError
if errors.As(err, &pathErr) {
    // somewhere in the chain, there's a *os.PathError
    fmt.Println(pathErr.Path)
}
```

## Sentinel Errors

For errors that callers need to check, define package-level sentinel errors:

```go
package user

var (
    ErrNotFound     = errors.New("user not found")
    ErrInvalidEmail = errors.New("invalid email address")
    ErrDuplicate    = errors.New("user already exists")
)

func Find(id string) (*User, error) {
    // ...
    if notFound {
        return nil, ErrNotFound
    }
    // ...
}
```

Callers can check:

```go
user, err := user.Find("123")
if errors.Is(err, user.ErrNotFound) {
    // handle not found specifically
}
```

## Custom Error Types

When you need more context, create a custom error type:

```go
type ValidationError struct {
    Field   string
    Message string
}

func (e *ValidationError) Error() string {
    return fmt.Sprintf("%s: %s", e.Field, e.Message)
}

func ValidateUser(u *User) error {
    if u.Email == "" {
        return &ValidationError{Field: "email", Message: "required"}
    }
    if !strings.Contains(u.Email, "@") {
        return &ValidationError{Field: "email", Message: "invalid format"}
    }
    return nil
}
```

Callers can extract details:

```go
if err := ValidateUser(u); err != nil {
    var valErr *ValidationError
    if errors.As(err, &valErr) {
        fmt.Printf("Validation failed on %s: %s\n", valErr.Field, valErr.Message)
    }
}
```

## Strategies That Help

### Early Returns

Embrace early returns. Don't nest error handling:

```go
// BAD: nested, hard to follow
func process() error {
    data, err := loadData()
    if err == nil {
        parsed, err := parseData(data)
        if err == nil {
            result, err := transform(parsed)
            if err == nil {
                return save(result)
            } else {
                return err
            }
        } else {
            return err
        }
    } else {
        return err
    }
}

// GOOD: flat, obvious
func process() error {
    data, err := loadData()
    if err != nil {
        return fmt.Errorf("loading: %w", err)
    }
    
    parsed, err := parseData(data)
    if err != nil {
        return fmt.Errorf("parsing: %w", err)
    }
    
    result, err := transform(parsed)
    if err != nil {
        return fmt.Errorf("transforming: %w", err)
    }
    
    return save(result)
}
```

### Naming Consistency

Keep error variable names consistent within a function:

```go
// Use 'err' for the standard error variable
data, err := load()
if err != nil { ... }

result, err := process(data)  // reuse 'err'
if err != nil { ... }

// Use descriptive names when you have multiple errors in scope
loadErr := load()
processErr := process()
if loadErr != nil || processErr != nil { ... }
```

### The "Must" Pattern

For initialisation code where errors are truly unrecoverable:

```go
var templates = template.Must(template.ParseGlob("templates/*.html"))
var config = MustLoadConfig("config.yaml")

func MustLoadConfig(path string) Config {
    cfg, err := LoadConfig(path)
    if err != nil {
        panic(fmt.Sprintf("loading config: %v", err))
    }
    return cfg
}
```

Use `Must` functions sparingly. Only for program setup where failure means "can't start."

## What You're Actually Getting

After the initial frustration wears off, here's what explicit errors give you:

**Visible failure points.** Every line that can fail is marked. No surprises.

**Local reasoning.** You handle errors where they occur. No tracing back through call stacks.

**No performance penalty.** Error returns are just values. No stack unwinding, no runtime cost.

**Forced consideration.** You can't ignore errors accidentally. (Well, you can with `_`, but it's deliberate.)

**Simpler debugging.** When something fails, the error message tells you exactly what happened at each level.

## The Comparison

| Aspect | C# Exceptions | Go Errors |
|--------|--------------|-----------|
| Syntax | `try`/`catch`/`throw` | `if err != nil` |
| Control flow | Non-local jump | Normal return |
| Performance | Cost on throw | No overhead |
| Visibility | Hidden failure points | Explicit everywhere |
| Ignoring errors | Silent (dangerous) | Requires explicit `_` |
| Stack traces | Automatic | Manual (or wrap carefully) |
| Recovery | `catch` blocks | Caller decides |

## The Honest Take

**Things I like better than C#:**

- You can see which calls can fail
- Error handling is local and explicit
- No surprise exceptions from deep in the stack
- Errors are values. You can store, compare, wrap them

**Things I miss from C#:**

- The happy path being uncluttered
- Automatic stack traces
- `finally` blocks (defer is close but not identical)
- Not writing the same three lines a thousand times

**The verdict:**

Go's approach is more verbose but more honest. Once you accept that error handling is part of your code (not something that happens off to the side) the verbosity starts to feel appropriate.

You're not writing boilerplate. You're writing error handling. It just happens to look the same every time because handling errors correctly *is* repetitive.

---

*Next up: panic and recover. Go's actual exception mechanism, why it exists, and why using it for normal errors will get you judged.*
