+++
title = "Composition Over Inheritance (For Real This Time)"
date = "2025-01-02"
draft = false
tags = ["go", "dotnet", "composition", "embedding", "csharp"]
+++

We've all heard "favour composition over inheritance." We've all nodded sagely. And then we've all written class hierarchies three levels deep because, well, it's right there and it's easy.

Go doesn't give you the choice. There's no inheritance. Zero. You can't extend a type. You can't override methods. There's no `virtual`, no `abstract`, no `base`.

Instead, Go has **embedding**, a form of composition that feels almost like inheritance but isn't. And after using it for a while, I genuinely don't miss base classes.

## What Is Embedding?

Embedding is when you include one type inside another without giving it a field name:

```go
type Person struct {
    Name string
    Age  int
}

type Employee struct {
    Person              // embedded - no field name
    EmployeeID string
    Department string
}
```

Notice: `Person` is listed without a name. It's not `person Person`, just `Person`. That's embedding.

What does this give you? The embedded type's fields and methods are **promoted** to the outer type:

```go
emp := Employee{
    Person:     Person{Name: "Alice", Age: 30},
    EmployeeID: "E123",
    Department: "Engineering",
}

// These all work:
fmt.Println(emp.Name)        // "Alice" - promoted from Person
fmt.Println(emp.Age)         // 30 - promoted from Person
fmt.Println(emp.EmployeeID)  // "E123" - direct field
fmt.Println(emp.Person.Name) // "Alice" - explicit access still works
```

The `Employee` type didn't "inherit" from `Person`. It *contains* a `Person` and Go conveniently promotes its members.

## Methods Are Promoted Too

If `Person` has methods, `Employee` gets them:

```go
func (p Person) Greet() string {
    return fmt.Sprintf("Hi, I'm %s", p.Name)
}

emp := Employee{Person: Person{Name: "Alice"}}
fmt.Println(emp.Greet())  // "Hi, I'm Alice"
```

The method is promoted. You call it on `Employee`, but it executes as if called on the embedded `Person`. 

This looks like inheritance. But there's a crucial difference.

## It's Not Inheritance: The Receiver Stays the Same

In inheritance, an overridden method in a subclass can access `this`/`self` as the subclass type. That's polymorphism.

In embedding, the method's receiver is still the embedded type:

```go
type Person struct {
    Name string
}

func (p Person) Introduce() string {
    return fmt.Sprintf("I am %s", p.Name)
}

type Employee struct {
    Person
    Title string
}

// This is NOT overriding - it's shadowing
func (e Employee) Introduce() string {
    return fmt.Sprintf("I am %s, %s", e.Name, e.Title)
}
```

If `Person.Introduce()` called another method, that call wouldn't magically dispatch to `Employee`'s version:

```go
func (p Person) FullIntro() string {
    return p.Introduce() + ". Nice to meet you!"  // calls Person.Introduce, always
}

emp := Employee{Person: Person{Name: "Alice"}, Title: "Engineer"}
fmt.Println(emp.FullIntro())  // "I am Alice. Nice to meet you!"
// Not "I am Alice, Engineer. Nice to meet you!"
```

There's no dynamic dispatch based on the outer type. The embedded `Person` doesn't know it's inside an `Employee`. It just does its thing.

This is composition, not inheritance. It's a feature, not a limitation.

## Multiple Embedding

You can embed multiple types:

```go
type Reader struct { ... }
func (r Reader) Read(p []byte) (int, error) { ... }

type Writer struct { ... }
func (w Writer) Write(p []byte) (int, error) { ... }

type ReadWriter struct {
    Reader
    Writer
}

// ReadWriter now has both Read and Write methods
```

This is like implementing multiple interfaces, except you're getting actual implementations, not just contracts.

If there are conflicts (both embedded types have a method with the same name), you get a compile error when you try to call the ambiguous method. You resolve it by calling explicitly:

```go
rw.Reader.SomeMethod()  // explicit disambiguation
rw.Writer.SomeMethod()
```

## Embedding Interfaces

You can also embed interfaces in interfaces:

```go
type Reader interface {
    Read(p []byte) (n int, err error)
}

type Writer interface {
    Write(p []byte) (n int, err error)
}

type ReadWriter interface {
    Reader  // embedded
    Writer  // embedded
}
```

This is just interface composition. `ReadWriter` requires both `Read` and `Write` methods.

And you can embed interfaces in structs:

```go
type MyHandler struct {
    http.Handler  // embedded interface
}
```

Now `MyHandler` has a field of type `http.Handler`, and its methods are promoted. You can create a `MyHandler` with any `http.Handler` implementation.

This is useful for decorating or wrapping behaviour.

## The "Delegation" Pattern

Want to wrap something and override specific behaviour? Embed and shadow:

```go
type LoggingWriter struct {
    io.Writer  // embedded interface
}

func (lw LoggingWriter) Write(p []byte) (n int, err error) {
    log.Printf("writing %d bytes", len(p))
    return lw.Writer.Write(p)  // delegate to embedded
}
```

`LoggingWriter` embeds an `io.Writer`. It has its own `Write` method that logs then delegates. Everything else passes through unchanged.

Use it like:

```go
file, _ := os.Create("output.txt")
logged := LoggingWriter{Writer: file}
logged.Write([]byte("hello"))  // logs then writes
```

This is the decorator pattern, but simple and type-safe.

## Comparing to C# Inheritance

Let's see the same concept in C#:

```csharp
public class Person
{
    public string Name { get; set; }
    public virtual string Greet() => $"Hi, I'm {Name}";
}

public class Employee : Person
{
    public string EmployeeID { get; set; }
    public override string Greet() => $"Hi, I'm {Name}, employee {EmployeeID}";
}
```

With inheritance, `Employee` IS-A `Person`. Polymorphism works. Override methods get called even when accessed through a base reference.

```csharp
Person p = new Employee { Name = "Alice", EmployeeID = "E123" };
Console.WriteLine(p.Greet());  // "Hi, I'm Alice, employee E123" - polymorphic!
```

Go's embedding doesn't do this. `Employee` HAS-A `Person`. No polymorphism. No override resolution.

## When You'll Miss Inheritance

Let's be honest: there are patterns that inheritance handles elegantly.

**Template Method Pattern:**

```csharp
public abstract class DataProcessor
{
    public void Process()
    {
        var data = LoadData();
        var transformed = Transform(data);  // subclass provides this
        Save(transformed);
    }
    
    protected abstract object Transform(object data);
}
```

In Go, you'd use an interface:

```go
type Transformer interface {
    Transform(data any) any
}

type DataProcessor struct {
    transformer Transformer
}

func (dp *DataProcessor) Process() {
    data := dp.LoadData()
    transformed := dp.transformer.Transform(data)
    dp.Save(transformed)
}
```

More explicit, arguably clearer, but more code.

**Protected Members:**

C# has `protected`, visible to derived classes. Go has nothing like this. Everything is either exported (public) or unexported (package-private).

If you want controlled extension points, you design them explicitly with interfaces, not protected methods.

## When Embedding Shines

**Extending functionality without modification:**

```go
type CountingReader struct {
    io.Reader
    count int
}

func (cr *CountingReader) Read(p []byte) (n int, err error) {
    n, err = cr.Reader.Read(p)
    cr.count += n
    return
}
```

Wrap any reader. Count bytes. Original reader unchanged.

**Combining capabilities:**

```go
type Server struct {
    http.Server       // get all http.Server fields and methods
    Logger *log.Logger
    Metrics *Metrics
}
```

Your server has everything `http.Server` has, plus your additions.

**Implementing interfaces via delegation:**

```go
type DB struct {
    pool *sql.DB  // not embedded, private
}

// Expose only what you want
func (db *DB) Query(q string) (*sql.Rows, error) {
    return db.pool.Query(q)
}
```

Control the surface area. Don't embed if you don't want to expose everything.

## The Honest Take

I was skeptical. "Composition over inheritance" sounded like coping. Then I used Go for six months and realised: I don't miss inheritance. Not really.

**What Go does better:**
- Forces you to think about composition
- No fragile base class problem
- No diamond inheritance nightmare
- Clear delegation chain
- Easy to wrap and extend behaviour

**What C# does better:**
- Polymorphism when you actually need it
- Template method pattern
- Protected members for controlled extension
- Clearer "IS-A" relationships in domain modelling

**The verdict:**
Inheritance is a sharp tool. It's powerful when used well and creates brittle, tangled hierarchies when used poorly. Go removes the temptation.

Embedding plus interfaces gives you most of what you need. The rest can be solved with explicit design patterns. You'll write more code sometimes, but it'll be clearer code.

And honestly? Those deep inheritance hierarchies you built in C#? They probably shouldn't have been inheritance anyway.

---

*Next up: the empty interface and type assertions. When you're basically back to `object`, and how to work with Go's dynamic typing escape hatch.*
