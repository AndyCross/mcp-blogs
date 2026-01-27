+++
title = "The Million Dollar Mistake, Differently"
date = "2024-12-29"
draft = false
tags = ["go", "dotnet", "nil", "csharp"]
series = ["step-over-to-go"]
+++

Tony Hoare called null references his "billion dollar mistake." Both C# and Go inherited some form of this mistake, but they've evolved to handle it differently. Neither solution is perfect.

If you're coming from C# 8+ with nullable reference types enabled, Go's approach will feel like stepping backwards. And in some ways, it is. But there's nuance here.

## The C# Journey

C# started with null everywhere. Any reference type could be null, always. This gave us decades of `NullReferenceException` at runtime.

Then came nullable reference types (NRT) in C# 8:

```csharp
#nullable enable

public class User
{
    public string Name { get; set; }        // Non-nullable - compiler warns if null
    public string? MiddleName { get; set; } // Nullable - explicitly marked
}

public void Process(User user)
{
    Console.WriteLine(user.Name.Length);    // Safe - compiler knows it's not null
    Console.WriteLine(user.MiddleName.Length); // Warning! Might be null
    
    // Must check first
    if (user.MiddleName != null)
    {
        Console.WriteLine(user.MiddleName.Length); // Now safe
    }
}
```

The compiler tracks nullability and warns you. It's still a warning system, not a guarantee, but it catches loads of bugs at compile time.

## Go's Approach: Everything Is Potentially Nil (But Different)

Go has `nil`, and it works differently depending on the type. Here's the landscape:

| Type | Can be nil? | Zero value |
|------|-------------|------------|
| Pointers (`*T`) | Yes | `nil` |
| Slices | Yes | `nil` (but usable!) |
| Maps | Yes | `nil` (but NOT usable for writes) |
| Channels | Yes | `nil` |
| Interfaces | Yes | `nil` |
| Functions | Yes | `nil` |
| Structs | No | Zero struct |
| Primitives | No | 0, "", false, etc. |

Let's dig into the weird bits.

### Nil Slices Are Fine

This is the first surprise. A nil slice is usable:

```go
var s []int    // nil slice
len(s)         // 0 - works fine
cap(s)         // 0 - works fine
s = append(s, 1, 2, 3)  // works fine! Now s is [1, 2, 3]

for _, v := range s { } // works even when nil (iterates zero times)
```

A nil slice isn't "no slice". It's an empty slice with no backing array. Most operations work. This is intentional and idiomatic.

### Nil Maps Are NOT Fine

But a nil map will bite you:

```go
var m map[string]int  // nil map

v := m["key"]         // works! Returns zero value (0)
_, ok := m["key"]     // works! ok is false

m["key"] = 1          // PANIC: assignment to entry in nil map
```

Reading from a nil map works (returns zero values). Writing to a nil map panics. This inconsistency catches everyone at least once.

Always initialise maps:

```go
m := make(map[string]int)
// or
m := map[string]int{}
```

### The Interface Nil Trap

This one is properly confusing. An interface can be nil in two ways:

```go
type Writer interface {
    Write([]byte) (int, error)
}

var w Writer = nil     // nil interface - both type and value are nil
fmt.Println(w == nil)  // true

var buf *bytes.Buffer = nil  // nil pointer
var w2 Writer = buf          // interface with nil concrete value
fmt.Println(w2 == nil)       // FALSE!
```

Wait, what?

An interface value is nil only if both its type and value are nil. If you assign a nil pointer to an interface, the interface has a type (the pointer type) but a nil value. It's not a nil interface.

This causes bugs like:

```go
func process(w Writer) {
    if w != nil {
        w.Write(data)  // might panic! w could be non-nil interface with nil value
    }
}

var buf *bytes.Buffer = nil
process(buf)  // passes the nil check, then panics
```

The fix is to either check the concrete type too, or (better) never assign nil pointers to interfaces.

## Zero Values as Nullability

Go's approach to handling "absent" values is the zero value:

```go
type User struct {
    Name      string
    Email     string
    Age       int
    CreatedAt time.Time
}

var u User
// u is now {Name: "", Email: "", Age: 0, CreatedAt: zero time}
```

Every field has a defined zero value. There's no "unset" state, just "set to zero."

This works well for many cases:

```go
// Empty string often means "not set"
if user.Email == "" {
    // No email provided
}

// But what if 0 is a valid age?
if user.Age == 0 {
    // Is this "not set" or "newborn"?
}
```

When you need to distinguish "not set" from "zero value," you have options:

### Option 1: Pointers

```go
type User struct {
    Name  string
    Age   *int  // nil means not set, *int value means set
}

func (u User) HasAge() bool {
    return u.Age != nil
}
```

This is the closest to C#'s `int?`. But you pay the pointer indirection cost and the nil-checking overhead.

### Option 2: The "ok" Pattern

```go
type User struct {
    name    string
    nameSet bool
}

func (u User) Name() (string, bool) {
    return u.name, u.nameSet
}
```

Explicit, but verbose.

### Option 3: Wrapper Types

```go
import "database/sql"

type User struct {
    Name sql.NullString
    Age  sql.NullInt64
}

if user.Name.Valid {
    fmt.Println(user.Name.String)
}
```

The standard library has these for database interop. They're clunky but explicit.

## Error Handling and Nil

Go's error handling interacts with nil constantly:

```go
func LoadUser(id string) (*User, error) {
    // ...
}

user, err := LoadUser("123")
if err != nil {
    return nil, err
}
// Use user - we know it's not nil because no error
```

The convention is: if `err != nil`, don't trust the other return values. If `err == nil`, the values should be valid.

But this is convention, not enforcement. Nothing stops you from writing:

```go
return nil, nil  // No user, no error - bad practice!
```

The compiler won't save you from this. Code review and convention do.

## What I Miss from C#

**Compile-time nullability tracking.** C#'s NRT warns you when you dereference something that might be null. Go just lets you do it.

**The null-conditional operators.** `user?.Profile?.Address?.City` in C# is a single expression. In Go:

```go
var city string
if user != nil && user.Profile != nil && user.Profile.Address != nil {
    city = user.Profile.Address.City
}
```

**Null-coalescing.** `name ?? "Unknown"` vs:

```go
name := user.Name
if name == "" {
    name = "Unknown"
}
```

Go 1.22 added some helpers, but nothing as clean.

## What Go Does Well

**Zero values are useful defaults.** A zero `sync.Mutex` works. A zero `bytes.Buffer` works. You don't need constructor ceremonies for basic types.

**No null reference exceptions.** You get panics on nil pointer dereference, but nil slices, nil channels (blocks forever), and nil maps (read) don't crash.

**Explicit pointer semantics.** When something can be nil, it's a pointer. Value types can't be nil. The type tells you what to expect.

## The Comparison

| Aspect | C# (with NRT) | Go |
|--------|---------------|-----|
| Compile-time null tracking | Yes (warnings) | No |
| Runtime null safety | NullReferenceException | Panic on nil dereference |
| Nullable value types | `int?` / `Nullable<T>` | `*int` or wrapper types |
| Zero values | Default to null/zero | Always well-defined |
| Null-conditional | `?.`, `??` | Manual checks |
| Interface nil trap | No equivalent problem | Yes - be careful |

## Practical Advice

1. **Initialise maps eagerly.** Don't leave them nil.

2. **Never assign nil pointers to interfaces.** Return the zero interface instead:
   ```go
   // Bad
   var buf *bytes.Buffer = nil
   return buf
   
   // Good
   return nil
   ```

3. **Use pointers for optional fields sparingly.** Often the zero value is fine for "not set."

4. **Follow the error convention.** If returning an error, either return good values or nil values, not a mix.

5. **Check nil before method calls on pointer receivers.** Go lets you call methods on nil receivers, which can work or panic depending on the implementation.

6. **Accept that the compiler won't catch null dereferences.** Tests and careful coding are your only defence.

The lack of NRT-style static analysis is Go's weakest area compared to modern C#. Tools like `staticcheck` help, but they're not built into the language.

You'll write more nil checks. You'll occasionally miss one. That's the trade-off for Go's simplicity.

---

*Next up: Go's approach to enums. Const blocks, iota, and why you'll miss real enums more than you expected to.*
