+++
title = "Your Class Is Now a Struct (And That's Fine)"
date = "2024-12-29"
draft = false
tags = ["go", "dotnet", "types", "csharp"]
series = ["step-over-to-go"]
+++

Here's something that'll feel wrong for about a week: Go doesn't have classes. Not "Go has classes but calls them something else". It really doesn't have them. No inheritance. No class hierarchies. No `virtual` or `override`. No `protected`.

If you've spent years designing C# class hierarchies, this feels like having a limb removed. Then you start writing Go code and realise... you don't actually miss it that much.

Let's dig into why.

## The Basic Translation

In C#, you'd write:

```csharp
public class User
{
    public string Name { get; set; }
    public string Email { get; set; }
    public DateTime CreatedAt { get; set; }
    
    public User(string name, string email)
    {
        Name = name;
        Email = email;
        CreatedAt = DateTime.UtcNow;
    }
    
    public string DisplayName() => $"{Name} <{Email}>";
}
```

In Go:

```go
type User struct {
    Name      string
    Email     string
    CreatedAt time.Time
}

func NewUser(name, email string) User {
    return User{
        Name:      name,
        Email:     email,
        CreatedAt: time.Now().UTC(),
    }
}

func (u User) DisplayName() string {
    return fmt.Sprintf("%s <%s>", u.Name, u.Email)
}
```

A few things to notice:

1. **No constructor syntax**. `NewUser` is just a function. By convention, Go uses `NewX` functions, but there's nothing special about them.
2. **Methods are declared separately**. That `func (u User)` syntax attaches a method to the type.
3. **No access modifiers**. Capitalisation controls visibility (covered in the next post).
4. **Fields are just fields**. No properties, no getters/setters.

## Value Semantics by Default

Here's the big one. In C#, classes are reference types. When you pass a `User` to a method, you're passing a reference. Modifications affect the original.

```csharp
void UpdateEmail(User user)
{
    user.Email = "new@example.com";  // modifies the original
}
```

In Go, structs are value types by default. Pass a struct, you're passing a copy.

```go
func UpdateEmail(u User) {
    u.Email = "new@example.com"  // modifies the copy, original unchanged
}
```

If you want reference semantics, you use pointers explicitly:

```go
func UpdateEmail(u *User) {
    u.Email = "new@example.com"  // modifies the original via pointer
}
```

This explicitness is jarring at first. In C#, the type itself determines whether you get value or reference semantics (`struct` vs `class`). In Go, the *calling convention* determines it. Same type, different behaviour depending on whether you use `User` or `*User`.

### When to Use Pointers

The rule of thumb:

| Scenario | Use |
|----------|-----|
| Method modifies the receiver | `*User` (pointer receiver) |
| Struct is large | `*User` (avoid copy overhead) |
| You need nil to mean "absent" | `*User` (pointers can be nil) |
| Small, immutable data | `User` (value) |
| You want copy-on-pass safety | `User` (value) |

In practice, most methods use pointer receivers. It's more consistent, and you don't have to think about whether each method modifies state.

```go
// Pointer receiver - conventional for most methods
func (u *User) UpdateEmail(email string) {
    u.Email = email
}

// Value receiver - acceptable for pure getters on small structs
func (u User) DisplayName() string {
    return fmt.Sprintf("%s <%s>", u.Name, u.Email)
}
```

## Composition Over Inheritance

Go doesn't have inheritance. Full stop. No `class Admin : User`. No `protected` members. No `virtual` methods.

Instead, Go has embedding, a form of composition that feels almost like inheritance but isn't.

```go
type Person struct {
    Name string
    Age  int
}

func (p Person) Greet() string {
    return fmt.Sprintf("Hello, I'm %s", p.Name)
}

type Employee struct {
    Person          // embedded - not a field name, just the type
    EmployeeID string
    Department string
}
```

Now `Employee` has all of `Person`'s fields and methods:

```go
emp := Employee{
    Person:     Person{Name: "Alice", Age: 30},
    EmployeeID: "E123",
    Department: "Engineering",
}

fmt.Println(emp.Name)    // "Alice" - promoted from Person
fmt.Println(emp.Greet()) // "Hello, I'm Alice" - method promoted too
```

This *looks* like inheritance, but it's not:

- No polymorphism. You can't pass an `Employee` where a `Person` is expected.
- No `override`. If `Employee` defines its own `Greet()`, it shadows `Person.Greet()`.
- The embedded type is still accessible. `emp.Person.Name` works.

### When You'll Miss Inheritance

Let's be honest: sometimes you'll miss it.

**Template Method Pattern**: In C#, you'd have a base class with a `virtual` method that subclasses override. Go has no direct equivalent. You use interfaces and composition instead, which works but feels more verbose.

**Protected Members**: There's no "visible to derived types" concept. Everything is either exported (public) or unexported (package-private). For library design, this can be limiting.

**Deep Hierarchies**: If your C# design has `Animal -> Mammal -> Dog -> Labrador`, Go will make you rethink that structure entirely. Usually for the better, but the rethinking takes effort.

## Interfaces Are Implicit

This is where Go gets properly interesting. Interfaces are satisfied implicitly. No `implements` keyword.

In C#:

```csharp
public interface IGreeter
{
    string Greet();
}

public class Person : IGreeter  // explicit implementation
{
    public string Name { get; set; }
    public string Greet() => $"Hello, I'm {Name}";
}
```

In Go:

```go
type Greeter interface {
    Greet() string
}

type Person struct {
    Name string
}

func (p Person) Greet() string {
    return fmt.Sprintf("Hello, I'm %s", p.Name)
}

// Person now implements Greeter - no declaration needed
```

If a type has the methods an interface requires, it implements that interface. Period. No ceremony.

This has profound implications:

1. **You can define interfaces after the fact**. Create an interface that existing types already satisfy.
2. **Small interfaces are encouraged**. The standard library is full of one-method interfaces.
3. **Testing is trivial**. Any type with the right methods can be substituted.

The `io.Reader` interface is the canonical example:

```go
type Reader interface {
    Read(p []byte) (n int, err error)
}
```

One method. But files, network connections, byte buffers, HTTP response bodies: they all implement it. Polymorphism without inheritance.

## The Comparison

| Aspect | C# Classes | Go Structs |
|--------|-----------|------------|
| Reference/value | Reference by default | Value by default |
| Inheritance | Full class inheritance | Embedding (composition) |
| Interface implementation | Explicit (`implements`) | Implicit (duck typing) |
| Constructors | Special syntax | Convention (`NewX` functions) |
| Access modifiers | `public`, `private`, `protected`, `internal` | Exported (capital) or unexported |
| Polymorphism | Inheritance + interfaces | Interfaces only |
| Method declaration | Inside class body | Separate, attached to type |

## What I Actually Miss

After a few months, here's my honest assessment:

**Don't miss at all:**
- Complex inheritance hierarchies (they were usually a mistake anyway)
- The `virtual`/`override` dance
- Explicit interface implementation for conflicts

**Sometimes miss:**
- `protected` for carefully designed extension points
- Abstract classes with partial implementations
- The template method pattern (can be done in Go, just clunkier)

**Actively prefer Go's approach:**
- Implicit interface satisfaction
- Explicit value vs reference choice at call site
- Composition via embedding
- Small, focused interfaces

The shift from "design your class hierarchy upfront" to "compose small pieces and let interfaces emerge" takes adjustment. But it tends to produce simpler code.

## The Practical Bit

If you're converting C# code to Go, here's the process I use:

1. **Start with structs for data**. No methods yet, just fields.
2. **Add methods as needed**. Use pointer receivers by default.
3. **Extract interfaces late**. When you need polymorphism, create the smallest interface that works.
4. **Embed for code reuse**. Not "inheritance", just "I want those fields and methods too".
5. **Resist the urge to build hierarchies**. If you're thinking "base class", stop and reconsider.

The code ends up flatter. More types, shallower relationships. It's different, not worse.

---

*Next up: visibility and the death of properties. Why Go uses capitalisation instead of access modifiers, and why you'll stop missing getters and setters faster than you'd expect.*
