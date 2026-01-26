+++
title = "No Enums? No Problem (Sort Of)"
date = "2024-12-29"
draft = false
tags = ["go", "dotnet", "enums", "csharp"]
+++

Go doesn't have enums. Not "Go has something enum-like". It genuinely doesn't have a dedicated enum construct. What it has instead is constants, a clever auto-incrementing keyword called `iota`, and convention.

For simple cases, this works fine. For anything more complex, you'll miss C#'s enums more than you expect.

## The Basic Pattern

In C#:

```csharp
public enum Status
{
    Pending,
    Active,
    Completed,
    Cancelled
}
```

In Go:

```go
type Status int

const (
    StatusPending Status = iota
    StatusActive
    StatusCompleted
    StatusCancelled
)
```

Let's break this down:

1. **Define a new type** based on an underlying type (usually `int`)
2. **Create a const block** with values of that type
3. **Use `iota`** to auto-increment values (0, 1, 2, 3...)

The `iota` keyword resets to 0 at each `const` block and increments for each line. It's surprisingly powerful:

```go
// Skip zero (useful when zero should mean "unset")
const (
    _ Status = iota  // 0 - discarded
    StatusPending    // 1
    StatusActive     // 2
    StatusCompleted  // 3
    StatusCancelled  // 4
)

// Bit flags
const (
    FlagRead  = 1 << iota  // 1
    FlagWrite              // 2
    FlagExec               // 4
)

// Custom formula
const (
    KB = 1 << (10 * (iota + 1))  // 1024
    MB                           // 1048576
    GB                           // 1073741824
)
```

## What's Missing

### No Exhaustive Switch

In C#, if you switch on an enum and miss a case, the compiler can warn you:

```csharp
Status status = GetStatus();
switch (status)
{
    case Status.Pending: // ...
    case Status.Active:  // ...
    // Missing Completed and Cancelled - compiler warning (with newer analyzers)
}
```

In Go, the compiler doesn't care:

```go
var status Status = getStatus()
switch status {
case StatusPending:
    // ...
case StatusActive:
    // ...
// Missing cases? Compiler doesn't notice.
}
```

You can use linters like `exhaustive` to catch this, but it's not built in.

### No Name Resolution

C#'s enums have built-in stringification:

```csharp
Status.Active.ToString()  // "Active"
Enum.Parse<Status>("Active")  // Status.Active
```

Go's "enums" are just integers. No automatic name mapping:

```go
fmt.Println(StatusActive)  // prints "1" - not useful

// You have to implement String() yourself
func (s Status) String() string {
    switch s {
    case StatusPending:
        return "Pending"
    case StatusActive:
        return "Active"
    case StatusCompleted:
        return "Completed"
    case StatusCancelled:
        return "Cancelled"
    default:
        return fmt.Sprintf("Status(%d)", s)
    }
}
```

This gets tedious. Tools like `stringer` can generate these methods, but it's an extra build step.

### No Type Safety (Not Really)

C#'s enums prevent you from using arbitrary values:

```csharp
Status s = (Status)999;  // Compiles but feels wrong
// Modern analyzers can warn about this
```

Go's "enums" are just typed integers. Any int can be cast:

```go
var s Status = 999  // Perfectly valid, no warning
```

Nothing stops you from creating invalid values. The type gives you some protection (can't accidentally pass an `int` where `Status` is expected), but it's weak.

### No Flag Enums with Utility Methods

C#'s `[Flags]` attribute gives you `HasFlag`:

```csharp
[Flags]
public enum Permissions
{
    None = 0,
    Read = 1,
    Write = 2,
    Execute = 4
}

var perms = Permissions.Read | Permissions.Write;
perms.HasFlag(Permissions.Read)  // true
```

Go gives you nothing. You do bit manipulation manually:

```go
const (
    PermissionNone = 0
    PermissionRead = 1 << iota
    PermissionWrite
    PermissionExecute
)

perms := PermissionRead | PermissionWrite
hasRead := perms&PermissionRead != 0  // manual check
```

Not hard, but not helpful either.

## Making It Better

Here's how the Go community works around these limitations:

### The Stringer Tool

Generate `String()` methods automatically:

```bash
go install golang.org/x/tools/cmd/stringer@latest
```

Add a generate directive:

```go
//go:generate stringer -type=Status

type Status int

const (
    StatusPending Status = iota
    StatusActive
    StatusCompleted
    StatusCancelled
)
```

Run `go generate ./...` and you get a `status_string.go` file with the `String()` method implemented.

### Validation Methods

Add explicit validation:

```go
func (s Status) IsValid() bool {
    switch s {
    case StatusPending, StatusActive, StatusCompleted, StatusCancelled:
        return true
    default:
        return false
    }
}
```

### Slice of All Values

Useful for iteration and testing:

```go
var AllStatuses = []Status{
    StatusPending,
    StatusActive,
    StatusCompleted,
    StatusCancelled,
}

func (s Status) IsValid() bool {
    return slices.Contains(AllStatuses, s)
}
```

### Parse Functions

For deserialisation:

```go
func ParseStatus(s string) (Status, error) {
    switch s {
    case "Pending", "pending":
        return StatusPending, nil
    case "Active", "active":
        return StatusActive, nil
    case "Completed", "completed":
        return StatusCompleted, nil
    case "Cancelled", "cancelled":
        return StatusCancelled, nil
    default:
        return 0, fmt.Errorf("unknown status: %s", s)
    }
}
```

### JSON Marshalling

By default, Go's JSON marshaller uses the integer value. You probably want the string:

```go
func (s Status) MarshalJSON() ([]byte, error) {
    return json.Marshal(s.String())
}

func (s *Status) UnmarshalJSON(data []byte) error {
    var str string
    if err := json.Unmarshal(data, &str); err != nil {
        return err
    }
    parsed, err := ParseStatus(str)
    if err != nil {
        return err
    }
    *s = parsed
    return nil
}
```

## A Complete "Enum" Implementation

Here's what a production-ready Go "enum" looks like:

```go
type Status int

const (
    StatusPending Status = iota + 1  // start at 1, 0 means "unset"
    StatusActive
    StatusCompleted
    StatusCancelled
)

var statusNames = map[Status]string{
    StatusPending:   "Pending",
    StatusActive:    "Active",
    StatusCompleted: "Completed",
    StatusCancelled: "Cancelled",
}

var statusValues = map[string]Status{
    "Pending":   StatusPending,
    "Active":    StatusActive,
    "Completed": StatusCompleted,
    "Cancelled": StatusCancelled,
}

func (s Status) String() string {
    if name, ok := statusNames[s]; ok {
        return name
    }
    return fmt.Sprintf("Status(%d)", s)
}

func ParseStatus(s string) (Status, error) {
    if v, ok := statusValues[s]; ok {
        return v, nil
    }
    return 0, fmt.Errorf("invalid status: %q", s)
}

func (s Status) IsValid() bool {
    _, ok := statusNames[s]
    return ok
}

func (s Status) MarshalJSON() ([]byte, error) {
    return json.Marshal(s.String())
}

func (s *Status) UnmarshalJSON(data []byte) error {
    var str string
    if err := json.Unmarshal(data, &str); err != nil {
        return err
    }
    v, err := ParseStatus(str)
    if err != nil {
        return err
    }
    *s = v
    return nil
}
```

Compare that to C#:

```csharp
public enum Status { Pending, Active, Completed, Cancelled }
```

Yeah.

## The Honest Assessment

| Feature | C# Enum | Go "Enum" |
|---------|---------|-----------|
| Declaration | One line | Const block |
| Type safety | Strong | Weak (any int assignable) |
| String conversion | Built-in | Manual or generated |
| Parsing | Built-in | Manual |
| Exhaustive switch | Analyzers available | External linter |
| Flag support | `[Flags]` + `HasFlag` | Manual bit ops |
| JSON serialisation | Configurable | Manual implementation |
| Iteration over values | `Enum.GetValues` | Manual slice |

Go's approach is simpler in concept but more work in practice. For a type you use once, it's fine. For a type used throughout a codebase with JSON APIs, database columns, and validation requirements, you'll write a lot of boilerplate.

## When to Reach for Alternatives

**String constants instead of int enums:**

```go
type Status string

const (
    StatusPending   Status = "pending"
    StatusActive    Status = "active"
    StatusCompleted Status = "completed"
    StatusCancelled Status = "cancelled"
)
```

Pros: Natural JSON serialisation, readable in logs/databases.
Cons: More memory, slower comparison, still no exhaustive switch checking.

**Third-party enum packages:**

Libraries like `go-enum` generate all the boilerplate. Worth considering for large projects.

**Interface-based enums:**

```go
type Status interface {
    status()  // unexported marker method
    String() string
}

type statusPending struct{}
func (statusPending) status() {}
func (statusPending) String() string { return "Pending" }

var StatusPending Status = statusPending{}
```

Type-safe (can't create arbitrary values), but verbose and unusual.

## Practical Advice

1. **Use `stringer` for any enum in production code.** The manual `String()` method will fall out of sync.

2. **Start const values at 1 if zero means "unset."** Or use an explicit `StatusUnknown = 0` value.

3. **Always add an `IsValid()` method.** Check it at system boundaries (API inputs, database reads).

4. **Use string-based enums for external APIs.** They're more forgiving and self-documenting.

5. **Accept the boilerplate.** Fighting it is pointless. Copy-paste or generate.

6. **Use the `exhaustive` linter.** It's the only way to get switch statement coverage warnings.

Go's lack of proper enums is one of its genuine weaknesses. The workarounds work, but they're workarounds. Every Go developer I know has a personal template or snippet for "proper" enum implementation.

Maybe we'll get real enums eventually. Until then, embrace `iota` and keep your boilerplate consistent.

---

*That wraps up Phase 2 on types and data. Next we'll move into Phase 3: Functions, Methods, and Interfaces, where Go's composition-over-inheritance philosophy really starts to show its strengths.*
