+++
title = "What I Actually Miss From C#"
date = "2025-01-15"
draft = false
tags = ["go", "dotnet", "reflection", "csharp"]
+++

I've been writing Go full-time for a couple of months now. I like it. I'm productive. But let's be honest: there are things I miss from C#. Not everything Go does differently is better, and pretending otherwise would be tribal nonsense.

Here's my genuine list of features I wish Go had. Not complaints, just honest observations about trade-offs.

## LINQ

God, I miss LINQ.

```csharp
var activeUsers = users
    .Where(u => u.IsActive)
    .OrderBy(u => u.Name)
    .Select(u => new { u.Id, u.Name })
    .ToList();
```

In Go:

```go
var activeUsers []UserSummary
for _, u := range users {
    if u.IsActive {
        activeUsers = append(activeUsers, UserSummary{ID: u.ID, Name: u.Name})
    }
}
sort.Slice(activeUsers, func(i, j int) bool {
    return activeUsers[i].Name < activeUsers[j].Name
})
```

More lines. More manual work. No lazy evaluation. No composition.

Yes, there are libraries like `lo` that add LINQ-like functions:

```go
activeUsers := lo.Filter(users, func(u User, _ int) bool {
    return u.IsActive
})
```

But it's not the same. LINQ is integrated into the language. It's type-safe. It composes elegantly. Go's approach works but lacks the expressiveness.

## Nullable Reference Types

C# 8's nullable reference types are genuinely excellent:

```csharp
#nullable enable
User? user = GetUser();
if (user != null)
{
    Console.WriteLine(user.Name); // Compiler knows it's not null here
}
```

Go has nil, and the compiler doesn't help you track it:

```go
user := GetUser()
if user != nil {
    fmt.Println(user.Name) // You remembered to check, compiler didn't care
}
```

The number of nil pointer panics I've written in Go that C#'s nullable analysis would have caught... it's not zero.

## Properties with Logic

Sometimes I want computed properties:

```csharp
public class Rectangle
{
    public double Width { get; set; }
    public double Height { get; set; }
    public double Area => Width * Height;  // clean
}
```

Go:

```go
type Rectangle struct {
    Width  float64
    Height float64
}

func (r Rectangle) Area() float64 {
    return r.Width * r.Height
}

// Usage: rect.Area() not rect.Area
```

The parentheses seem minor but they matter for readability. A computed value should look like accessing a value, not calling a function.

## Async/Await for Simple Cases

Yes, goroutines are more powerful. Yes, no coloured functions is elegant. But sometimes I just want:

```csharp
var user = await GetUserAsync(id);
var orders = await GetOrdersAsync(user.Id);
return await BuildSummaryAsync(user, orders);
```

The sequential async flow is clean. In Go, this is just synchronous code (which is fine), but when you need to collect results from parallel operations, channels feel heavyweight compared to:

```csharp
var results = await Task.WhenAll(tasks);
```

## Extension Methods

Adding methods to types you don't own:

```csharp
public static string Truncate(this string s, int maxLength) =>
    s.Length <= maxLength ? s : s[..maxLength] + "...";

// Usage
var short = longString.Truncate(100);
```

Go has no extension methods. You write functions:

```go
func Truncate(s string, maxLength int) string {
    if len(s) <= maxLength {
        return s
    }
    return s[:maxLength] + "..."
}

// Usage
short := Truncate(longString, 100)
```

Works, but doesn't chain as nicely. Discovery is harder too. You can't just type `string.` and see available operations.

## Pattern Matching

C#'s pattern matching is wonderful:

```csharp
var message = obj switch
{
    int i when i > 0 => $"positive: {i}",
    int i => $"non-positive: {i}",
    string s => $"string: {s}",
    null => "null",
    _ => "unknown"
};
```

Go's type switches are good but not as powerful:

```go
switch v := obj.(type) {
case int:
    if v > 0 {
        message = fmt.Sprintf("positive: %d", v)
    } else {
        message = fmt.Sprintf("non-positive: %d", v)
    }
case string:
    message = fmt.Sprintf("string: %s", v)
// no null case, no default with value access
}
```

The `when` guards and the expression form are genuinely missed.

## Rich IDE Support

Rider and Visual Studio are exceptional. The refactoring tools, the code analysis, the debugging experience... Go tooling is good and improving, but it's not at the same level.

"Rename symbol across solution" in Rider is flawless. In gopls, it's usually fine but occasionally misses things.

## Proper Enums

I covered this in an earlier post, but I still miss them:

```csharp
public enum Status { Pending, Active, Completed }
Status.Pending.ToString()  // "Pending"
Enum.Parse<Status>("Active")  // Status.Active
```

Go's `const` + `iota` requires so much boilerplate for basic enum functionality.

## Generic Variance

`IEnumerable<Dog>` is assignable to `IEnumerable<Animal>` in C#. Go has no variance. A `[]Dog` is not a `[]Animal`. This comes up more often than you'd think when designing APIs.

## What I Don't Miss

For balance, here's what I thought I'd miss but don't:

**Inheritance**: Embedding and interfaces cover everything I actually need.

**Exceptions**: Explicit error handling grew on me. It's more code but clearer.

**Heavyweight frameworks**: Building with minimal dependencies is refreshing.

**Complex configuration**: No more XML config files and DI containers to wire up.

**Slow startup**: Go starts instantly. .NET apps... don't always.

## The Reality Check

None of these missing features make Go unusable. I'm productive. I ship code. The simplicity has real benefits that offset these gaps.

But when Go advocates say "you won't miss anything from C#," they're being tribal. These are real features that make real tasks easier. Go chose different trade-offs. Those trade-offs are sometimes worse for specific use cases.

Acknowledging that doesn't mean Go is bad. It means it's a tool with trade-offs, like every language.

---

*Next up: the features I'll never go back for. The Go patterns that have genuinely ruined me for other languages.*
