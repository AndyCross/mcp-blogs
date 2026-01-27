+++
title = "Pointers Without the Pain"
date = "2024-12-31"
draft = false
tags = ["go", "dotnet", "memory", "pointers", "csharp"]
series = ["step-over-to-go"]
+++

Right, let's talk about pointers. If you've spent your career in C#, you've probably used pointers approximately never. Maybe you've seen `unsafe` blocks in performance-critical library code. Maybe you've used `ref` and `Span<T>` and felt rather clever about it.

In Go, pointers are everywhere. Every method receiver decision involves them. Every struct-passing decision involves them. You can't hide from them.

The good news: Go's pointers are considerably less terrifying than C's. The bad news: you actually have to think about them now.

## What C# Hides

C# makes a neat distinction: value types live on the stack (mostly), reference types live on the heap (mostly), and the runtime figures out the details. You don't think about addresses. You don't think about dereferencing. You just use stuff.

```csharp
var user = new User { Name = "Alice" };  // heap, reference semantics
var point = new Point(10, 20);           // stack (probably), value semantics

ProcessUser(user);   // passes reference
ProcessPoint(point); // passes copy
```

The runtime decides where things actually live. The JIT optimises. Escape analysis happens. You don't care.

Go is more... honest? Explicit? Annoying? All three, depending on your mood.

```go
user := User{Name: "Alice"}   // where does this live? Depends!
ptr := &User{Name: "Bob"}     // definitely a pointer

ProcessUser(user)   // passes copy
ProcessUser(&user)  // passes pointer
ProcessUserPtr(ptr) // passes pointer
```

You have to think about it. Every time.

## Go Pointer Basics

The syntax is C-style:

```go
x := 42
p := &x    // p is *int, pointing to x
fmt.Println(*p)  // 42 - dereference to get value
*p = 100   // x is now 100
```

Two operators, two meanings:

- `&` means "give me the address of this thing", where it lives in memory
- `*` means "follow this address to the thing it points at", dereferencing

### What's Dereferencing?

If a pointer is an address ("the data lives at memory location 0x1234") then dereferencing is following that address to get the actual data. It's a bit of a mouthful: "follow the pointer to the thing that is pointed at." That's why we just use a little `*`.

Think of it like a postal address. The pointer `p` is the address on an envelope. Dereferencing `*p` is going to that address and looking at what's actually there.

```go
x := 42       // x is the value 42, stored somewhere in memory
p := &x       // p holds the address of x (like "123 Memory Lane")
              // p itself is *int - "a pointer to an int"

fmt.Println(p)   // prints an address like 0xc000012345
fmt.Println(*p)  // prints 42 - we followed the address to get the value

*p = 100      // go to that address, change what's stored there
fmt.Println(x)   // prints 100 - x changed because p points to x
```

The `*` does double duty in Go (and C):
- In a type declaration, `*int` means "pointer to int"
- As an operator, `*p` means "dereference p, follow the pointer"

This is confusing for about a week, then it becomes second nature.

### Creating Pointers

```go
// These are equivalent
user := &User{Name: "Alice"}

// vs
user := new(User)
user.Name = "Alice"

// vs
var user User
user.Name = "Alice"
userPtr := &user
```

The `&` operator gives you a pointer. The `*` operator dereferences. If you've touched C or C++ at any point, this is familiar.

## The Nice Bit: Automatic Dereferencing

Unlike C, Go automatically dereferences pointers for field and method access:

```go
type User struct {
    Name string
}

func (u *User) SetName(name string) {
    u.Name = name  // not (*u).Name, just u.Name
}

user := &User{}
user.Name = "Alice"  // works, auto-dereferenced
user.SetName("Bob")  // works
```

In C, you'd write `user->Name` for pointer access and `user.Name` for value access. Go just uses dot notation for both and figures it out.

This is a genuine quality-of-life improvement. You don't need `->` vs `.` confusion. Dot notation works for both values and pointers.

## The Not-Nice Bit: Nil Pointer Panics

C# has `NullReferenceException`. Go has nil pointer panics. Same problem, different name.

```go
var user *User = nil
fmt.Println(user.Name)  // panic: runtime error: invalid memory address
```

When you try to dereference a nil pointer (follow an address that doesn't point anywhere) Go panics. There's nothing at that address to read.

No nullable reference types. No compile-time null safety. Just runtime panics.

C# 8+ with nullable reference types:

```csharp
#nullable enable
User? user = null;
Console.WriteLine(user.Name);  // compiler warning: possible null reference
```

Go doesn't help you here. You check for nil manually, or you panic at runtime. Welcome to 2009.

## When to Use Pointers

The decision tree:

**Use pointers when:**

1. **The method modifies the receiver**
   ```go
   func (u *User) SetEmail(email string) {
       u.Email = email  // needs to modify the original
   }
   ```
   Without the pointer, `SetEmail` would modify a copy, and the caller's `User` would be unchanged.

2. **The struct is large**
   ```go
   type BigStruct struct {
       Data [1024]byte
       // ... lots of fields
   }
   
   func Process(b *BigStruct) {  // don't copy 1KB every call
       // ...
   }
   ```

3. **You need nil to mean "absent"**
   ```go
   type Config struct {
       Timeout *time.Duration  // nil means "not set", use default
   }
   ```

4. **Consistency with other methods on the type**
   If some methods need pointer receivers, use pointers everywhere for that type. Mixing is legal but confusing.

**Use values when:**

1. **The data is small and immutable**
   ```go
   type Point struct {
       X, Y int
   }
   
   func (p Point) Distance(other Point) float64 {
       // fine to copy two ints
   }
   ```

2. **You want copy-on-pass safety**
   Value semantics mean the callee can't modify your data.

3. **The zero value is useful**
   ```go
   var mu sync.Mutex  // zero Mutex is valid, unlocked
   ```

## The "Everything Is a Pointer Receiver" School

Some Go developers just use pointer receivers everywhere. It's simpler. Consistent. No thinking required.

```go
func (u *User) Name() string { return u.name }      // pointer receiver
func (u *User) SetName(n string) { u.name = n }    // pointer receiver
func (u *User) IsActive() bool { return u.active } // pointer receiver
```

Is this optimal? No. Does it matter? Rarely.

The performance difference between passing a pointer vs a small struct is negligible for most code. Consistency and clarity usually matter more.

## What You Can't Do

Go's pointers are garbage-collected. You can't:

- Do pointer arithmetic (no `p++` to walk through memory)
- Free memory manually (the GC handles it)
- Have dangling pointers (the GC keeps referenced memory alive)
- Cast pointers to integers (without `unsafe`)

This is why Go pointers are "safe". They're really just references with explicit syntax. All the scary C stuff is locked behind the `unsafe` package.

## The `unsafe` Package

Go has an escape hatch:

```go
import "unsafe"

func scary() {
    var x int64 = 42
    ptr := unsafe.Pointer(&x)
    // Now you can do terrible things
}
```

The `unsafe` package lets you:
- Convert between pointer types
- Do pointer arithmetic
- Access struct padding
- Generally shoot yourself in the foot

If you're using `unsafe` outside of extremely low-level code, you're probably doing something wrong. It exists for syscalls, memory-mapped I/O, and interop. Not for your web handlers.

## Comparing to C# `ref` and Pointers

C# has several ways to get pointer-like semantics:

| C# | Go Equivalent | Notes |
|-----|---------------|-------|
| `ref` parameter | `*T` parameter | Pass by reference |
| `in` parameter | `*T` (readonly discipline) | Go has no `const` pointers |
| `out` parameter | `*T` or multiple returns | Go prefers multiple returns |
| `Span<T>` | Slices | Different semantics, similar purpose |
| `unsafe` pointers | `unsafe.Pointer` | Both are escape hatches |
| `ref struct` | No equivalent | Go doesn't have stack-only types |

C#'s `ref struct` and `Span<T>` are rather more sophisticated than anything Go offers. If you're doing zero-allocation parsing or high-performance buffer manipulation, .NET's tooling is better.

Go's answer is "use slices and let the GC handle it." Less control, simpler mental model, occasionally more allocation.

## The Honest Take

Look, I'll be straight with you: C#'s memory model is more sophisticated. The runtime does more for you. Nullable reference types catch null bugs at compile time. `Span<T>` gives you safe, zero-copy views into memory. `ref struct` prevents heap allocation entirely.

Go gives you... pointers. The same pointers we've had since the 1970s, except garbage-collected so you can't corrupt memory.

**What Go does better:**
- Simpler mental model (it's just pointers)
- Explicit about copies vs references
- No hidden boxing/unboxing
- Can't accidentally capture stack memory (escape analysis handles it)

**What C# does better:**
- Nullable reference types
- `Span<T>` and memory-safe slicing
- `ref struct` for stack-only types  
- More escape hatches that are actually usable (`stackalloc`, etc.)
- The whole `System.Memory` namespace

**The verdict:**
If you're writing performance-critical code where every allocation matters, C# has more tools. If you're writing normal application code, Go's "just use pointers" simplicity is fine.

You'll write `*User` a lot. You'll occasionally forget to check for nil. You'll survive.

---

*Next up: stack vs heap allocation and escape analysis. Go decides where your variables live, and you don't always get a vote.*
