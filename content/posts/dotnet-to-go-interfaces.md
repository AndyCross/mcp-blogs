+++
title = "Implicit Interfaces: Scary Then Brilliant"
date = "2025-01-02"
draft = false
tags = ["go", "dotnet", "interfaces", "csharp"]
+++

Here's a sentence that'll make every C# developer uncomfortable: Go interfaces don't require an `implements` keyword. You never explicitly declare that a type implements an interface. If your type has the right methods, it implements the interface. Automatically. Implicitly.

This sounds like chaos. It felt like chaos to me for the first week. Then it clicked, and now C#'s explicit interface declarations feel like unnecessary paperwork.

## The C# Way: Explicit Declaration

In C#, implementing an interface is a contract you sign explicitly:

```csharp
public interface IWriter
{
    void Write(byte[] data);
}

public class FileWriter : IWriter  // explicit declaration
{
    public void Write(byte[] data)
    {
        // write to file
    }
}
```

The `: IWriter` is required. Without it, `FileWriter` doesn't implement `IWriter`, even if it has a matching `Write` method. The compiler enforces this contract.

## The Go Way: Implicit Satisfaction

Go flips this around:

```go
type Writer interface {
    Write(p []byte) (n int, err error)
}

type FileWriter struct {
    // fields
}

func (f *FileWriter) Write(p []byte) (n int, err error) {
    // write to file
    return len(p), nil
}

// FileWriter now implements Writer. No declaration needed.
```

There's no `implements Writer` anywhere. The `FileWriter` type has a method `Write(p []byte) (n int, err error)`, which matches the `Writer` interface's signature. Therefore, `FileWriter` implements `Writer`. Done.

This is called **structural typing** or, less formally, **duck typing**: if it walks like a duck and quacks like a duck, it's a duck. If your type has the methods an interface requires, it implements that interface.

## Why This Is Actually Good

I know, I know. "But how do I know what interfaces my type implements?" "What if I accidentally implement something?" "How do I document my intent?"

Let me address these, because they were my exact objections.

### You Can Define Interfaces After the Fact

This is the killer feature. In C#, if you want an interface, you design it upfront, or you go back and modify all implementing types when you add one later.

In Go, you can define an interface that existing types already satisfy:

```go
// You wrote this last month
type Database struct { ... }
func (db *Database) Query(sql string) ([]Row, error) { ... }
func (db *Database) Exec(sql string) error { ... }

// Today you want to test something that uses Database
type Querier interface {
    Query(sql string) ([]Row, error)
}

// Database already implements Querier. No changes needed.
func ProcessData(q Querier) { ... }
```

You created a new interface. `Database` implements it without any modification. Your production code doesn't change. Your tests can use a mock `Querier`. Beautiful.

In C#, you'd need to go back and add `: IQuerier` to `Database`. That's a code change, a new commit, potentially a new deployment—all for what should be a refactoring detail.

### Small Interfaces Are Encouraged

Go's standard library is full of tiny interfaces:

```go
type Reader interface {
    Read(p []byte) (n int, err error)
}

type Writer interface {
    Write(p []byte) (n int, err error)
}

type Closer interface {
    Close() error
}
```

One method each. Dozens of types implement `Reader`—files, network connections, HTTP response bodies, byte buffers, compression streams. They don't know about each other. They just happen to have a `Read` method.

This leads to highly composable code. Functions take the smallest interface they need:

```go
func Copy(dst Writer, src Reader) (int64, error)
```

Anything readable to anything writable. Files to network. Network to memory. Whatever. If it has the methods, it works.

In C#, you'd need `IReadable` and `IWritable` interfaces defined somewhere, and every type would need to explicitly implement them. The friction means you'd probably just use concrete types or create fat interfaces.

### Accidental Implementation Is Rare

"But what if I accidentally implement an interface I didn't mean to?"

In practice, this almost never happens. Interfaces in Go tend to have method names specific to their purpose. The odds that your `type Banana struct{}` accidentally has a method `func (b Banana) Read(p []byte) (int, error)` are slim.

And if it does? So what? If your banana can be read from, maybe someone will find a creative use for that. The type system isn't going to explode.

## Checking Interface Satisfaction

If you want to verify at compile time that a type implements an interface, use this pattern:

```go
var _ Writer = (*FileWriter)(nil)
```

This declares an anonymous variable of type `Writer` and assigns a nil `*FileWriter` to it. If `*FileWriter` doesn't implement `Writer`, compilation fails.

The variable is discarded (assigned to `_`), so there's no runtime cost. It's purely a compile-time check.

```go
// In your file, somewhere near the type definition
var _ io.Reader = (*MyReader)(nil)
var _ io.Writer = (*MyWriter)(nil)
var _ http.Handler = (*MyHandler)(nil)
```

This is the Go equivalent of declaring intent. Use it when the interface implementation is non-obvious or contractually important.

## Interface Values: Two Components

Here's something C# developers don't think about: an interface value in Go has two components:

1. **The type**: what concrete type is stored
2. **The value**: the actual data

```go
var w Writer
fmt.Printf("type: %T, value: %v\n", w, w)
// type: <nil>, value: <nil>

w = &FileWriter{}
fmt.Printf("type: %T, value: %v\n", w, w)
// type: *main.FileWriter, value: &{...}
```

This matters because of the nil interface trap we covered earlier. An interface is only `nil` when both type and value are nil. Assign a nil pointer and the type is set, so the interface isn't nil.

## Interfaces on Values vs Pointers

Methods can have value receivers or pointer receivers. This affects interface implementation:

```go
type Speaker interface {
    Speak() string
}

type Dog struct{ Name string }

// Value receiver
func (d Dog) Speak() string {
    return "Woof!"
}

var s Speaker
s = Dog{Name: "Rex"}   // OK - Dog implements Speaker
s = &Dog{Name: "Rex"}  // OK - *Dog also implements Speaker (Go is helpful here)
```

But watch what happens with pointer receivers:

```go
type Cat struct{ Name string }

// Pointer receiver
func (c *Cat) Speak() string {
    return "Meow!"
}

var s Speaker
s = &Cat{Name: "Whiskers"}  // OK - *Cat implements Speaker
s = Cat{Name: "Whiskers"}   // ERROR - Cat does NOT implement Speaker
```

Why? Because you can always get a pointer from a value (`&cat`), but you can't always get an addressable value from a pointer. Go is strict about this.

**The rule**: if any method has a pointer receiver, use pointers with that interface.

## Comparing to C# Interface Features

| Feature | C# | Go |
|---------|-----|-----|
| Explicit implementation | Required (`: IInterface`) | Not possible |
| Implicit implementation | Not possible | Automatic |
| Default methods | Yes (C# 8+) | No |
| Static methods | Yes (C# 11) | No |
| Properties | Yes | No (use methods) |
| Generic interfaces | Yes | Yes (Go 1.18+) |
| Explicit interface implementation | Yes (`IFoo.Bar()`) | No |
| Covariance/contravariance | Yes (`out`/`in`) | No |

Go interfaces are simpler. That simplicity is the point.

## The Honest Take

Implicit interfaces felt wrong. "How will I know what my type implements?" "How will I communicate intent?"

Then I realised: the caller defines what it needs. The implementer just provides capabilities. If those match, great. If not, no harm done.

**What Go does better:**
- Define interfaces at the point of use, not declaration
- Small, composable interfaces are natural
- No ceremony—just write the methods
- Retroactive interface satisfaction
- Decouples interface from implementation completely

**What C# does better:**
- Clear documentation of intent (`: IInterface`)
- IDE "go to implementations" is easier
- Explicit interface implementation for conflicts
- Default interface methods
- Richer interface features (properties, statics)

**The verdict:**
Once you stop thinking "I need to declare my interfaces upfront" and start thinking "I'll define an interface when I need the abstraction," Go's approach makes beautiful sense. It's just a different philosophy.

The interface belongs to the consumer, not the producer. That inversion takes time to internalise, but it's powerful.

---

*Next up: composition via embedding—Go's alternative to inheritance, and why you really won't miss base classes.*
