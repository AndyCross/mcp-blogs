+++
title = "Where Did My Properties Go?"
date = "2024-12-29"
draft = false
tags = ["go", "dotnet", "types", "csharp"]
series = ["step-over-to-go"]
+++

Coming from C#, one of the first things you'll notice is that Go structs look... naked. Where are the `{ get; set; }` blocks? Where's `private` and `public`? How do you encapsulate anything?

The answer involves capitalisation, a complete absence of properties, and a philosophy that might make you uncomfortable before it makes you productive.

## Visibility via Capitalisation

Go has exactly two visibility levels:

- **Exported** (capital first letter): visible outside the package
- **Unexported** (lowercase first letter): visible only within the package

That's it. No `public`, `private`, `protected`, `internal`. Just case.

```go
package user

type User struct {
    Name  string    // Exported - other packages can access
    Email string    // Exported
    hash  string    // unexported - only this package can access
}

func (u *User) SetPassword(password string) {
    u.hash = hashPassword(password)  // can access hash internally
}

func hashPassword(p string) string {  // unexported function
    // ...
}
```

From another package:

```go
package main

import "myapp/user"

func main() {
    u := user.User{Name: "Alice", Email: "alice@example.com"}
    u.SetPassword("secret")  // works - SetPassword is exported
    
    // u.hash = "something"  // won't compile - hash is unexported
}
```

### The Mental Adjustment

In C#, visibility is per-member and you have fine-grained control. In Go, the package is the unit of encapsulation.

| C# | Go Equivalent |
|----|---------------|
| `public` | Capitalised name |
| `private` | Lowercase name |
| `protected` | Doesn't exist |
| `internal` | Lowercase (package = assembly, roughly) |
| `private protected` | Doesn't exist |

The lack of `protected` is the big one. There's no "visible to derived types" because there are no derived types. Embedding doesn't grant special access. Embedded types can only access their own unexported members.

## No Properties, Just Fields

Here's the controversial bit. Go doesn't have properties. No getters. No setters. Just fields.

In C#, you'd write:

```csharp
public class User
{
    private string _email;
    
    public string Email
    {
        get => _email;
        set
        {
            ValidateEmail(value);
            _email = value.ToLowerInvariant();
        }
    }
}
```

In Go, the idiomatic approach is... don't do that:

```go
type User struct {
    Email string
}
```

Wait, what about validation? What about normalisation?

Go's answer: if you need to do something when a value changes, make a method for it:

```go
type User struct {
    email string  // unexported
}

func (u *User) Email() string {
    return u.email
}

func (u *User) SetEmail(email string) error {
    if !isValidEmail(email) {
        return errors.New("invalid email")
    }
    u.email = strings.ToLower(email)
    return nil
}
```

This is more verbose than C# properties. Undeniably. You write more code.

But now the call site makes it obvious that something's happening.

```go
// Caller knows this might fail
err := user.SetEmail("alice@example.com")

// vs a property that silently transforms or might panic
user.Email = "alice@example.com"  // what does this actually do?
```

### When to Use Bare Fields

The Go community's guidance is: **export fields when they're truly just data**.

```go
// Config is just data, exported fields are fine
type Config struct {
    Host     string
    Port     int
    Timeout  time.Duration
    Debug    bool
}

// User has invariants to maintain, unexport fields + methods
type User struct {
    id        int64
    email     string
    createdAt time.Time
}
```

This feels wrong to C# developers who've been taught that bare fields are always bad. But Go's standard library is full of exported fields:

```go
// From net/http
type Request struct {
    Method string
    URL    *url.URL
    Header Header
    Body   io.ReadCloser
    // ... many more exported fields
}
```

The `http.Request` struct has exported fields because that's what makes sense. You read and modify them directly. No ceremony.

## The "Getter/Setter" Convention

When you do need accessor methods, Go has a naming convention that'll trip you up:

```go
// C# instinct - WRONG in Go
func (u *User) GetEmail() string { return u.email }
func (u *User) SetEmail(e string) { u.email = e }

// Go convention - CORRECT
func (u *User) Email() string { return u.email }
func (u *User) SetEmail(e string) { u.email = e }
```

Notice: the getter is just `Email()`, not `GetEmail()`. The setter keeps the `Set` prefix.

This feels inconsistent until you see it in use:

```go
email := user.Email()          // reads like accessing a value
user.SetEmail("new@example.com")  // reads like an action
```

The asymmetry is intentional. Getting a value should feel like accessing a value. Setting a value should look like you're doing something.

## The Package as Encapsulation Boundary

Here's where Go's model actually shines: the package is the natural unit of encapsulation.

In C#, you often have one class per file, and you think about encapsulation at the class level. You might have `internal` methods that are really just for one other class in the same assembly.

In Go, all files in a package share the same namespace. Unexported identifiers are visible across all files in the package:

```go
// user/user.go
package user

type User struct {
    email string
}

// user/validation.go  
package user

func validateUser(u *User) error {
    // Can access u.email - same package
    if u.email == "" {
        return errors.New("email required")
    }
    return nil
}
```

This encourages small, focused packages where the implementation details can be shared freely within the package boundary, but the public API is carefully controlled.

### The `internal` Directory

Go has one more visibility mechanism: the `internal` directory convention.

```
myproject/
├── internal/
│   └── auth/
│       └── token.go    // only importable by myproject and its children
├── api/
│   └── handler.go      // can import internal/auth
└── main.go             // can import internal/auth
```

Packages under `internal/` can only be imported by packages rooted at the parent of `internal`. This gives you "internal to this module" visibility without language keywords.

## Struct Tags

One thing C# attributes do that Go handles differently: metadata on fields. Go uses struct tags:

```go
type User struct {
    ID        int64     `json:"id" db:"user_id"`
    Email     string    `json:"email" db:"email" validate:"required,email"`
    CreatedAt time.Time `json:"created_at" db:"created_at"`
}
```

These are just strings. The runtime and libraries parse them by convention. The `json` package looks for `json:` tags. Database libraries look for `db:` tags. Validation libraries look for `validate:` tags.

It's less type-safe than C# attributes (no compile-time checking of tag names), but it's simple and works.

## The Honest Take

After months of Go, here's where I've landed:

**Things I like better than C#:**

- **Simplicity of the model**. Two visibility levels, no exceptions.
- **Package-level encapsulation**. Encourages cohesive packages.
- **Explicit methods over magic properties**. Call sites are clear about what's happening.
- **The `internal` convention**. Solves the "internal to this module" case elegantly.

**Things I miss from C#:**

- **`protected` for library extension**. Sometimes you want "derived types only" access.
- **Computed properties**. `user.FullName` is nicer than `user.FullName()` when it's actually just a computed value.
- **Init-only setters**. Go has no equivalent to `init` for construction-time-only setting.
- **Attributes**. Struct tags work but aren't type-safe.

**Things that are just different:**

- **Capitalisation visibility**. Weird for a week, then invisible.
- **No `get`/`set` syntax**. More typing, but more explicit.
- **Fields vs properties**. Go trusts you to know when bare fields are appropriate.

## Practical Advice

1. **Start with exported fields for DTOs**. Structs that just carry data (configs, API responses, database rows) don't need method accessors.

2. **Use unexported fields when invariants matter**. If setting a value could break something, make it unexported and provide methods.

3. **Name getters without `Get`**. It's `Email()`, not `GetEmail()`.

4. **Return errors from setters that validate**. Don't panic, don't silently fail.

5. **Keep packages small and focused**. The package boundary is your encapsulation tool. Make packages that are cohesive enough that sharing unexported identifiers makes sense.

6. **Use `internal/` for module-private packages**. Better than making everything unexported in a shared package.

The shift from "everything should have properties" to "fields are fine, methods when needed" takes time. But once you stop fighting it, Go code ends up pleasantly straightforward.

---

*Next up: generics in Go. What we got in Go 1.18, where the gaps are, and why you'll need to adjust your expectations if you're used to C#'s mature generics.*
