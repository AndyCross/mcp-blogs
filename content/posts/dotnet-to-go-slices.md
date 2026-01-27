+++
title = "Slices Are Not Arrays (And Neither Is List<T>)"
date = "2024-12-31"
draft = false
tags = ["go", "dotnet", "memory", "slices", "csharp"]
series = ["step-over-to-go"]
+++

Every C# developer coming to Go makes the same mistake: they see `[]int` and think "array" or "list." It's neither. It's a slice, and it has semantics that will bite you if you don't understand them.

This is one of those Go concepts that seems simple until it isn't. Let's dig in.

## What a Slice Actually Is

A slice is a struct with three fields:

```go
// Conceptually:
type slice struct {
    array *T   // pointer to underlying array
    len   int  // number of elements in use
    cap   int  // total capacity of underlying array
}
```

When you create a slice, you're creating this header. The actual data lives in a backing array somewhere.

```go
s := []int{1, 2, 3, 4, 5}
// s.array -> [1, 2, 3, 4, 5, _, _, _]  (backing array, might have extra capacity)
// s.len = 5
// s.cap = 5 (or more)
```

This is fundamentally different from both C# arrays and `List<T>`.

## The C# Mental Model (And Why It's Wrong Here)

**C# arrays** are fixed-size, directly hold their data:

```csharp
int[] arr = new int[5];
// arr IS the array, fixed size, done
```

**C# List<T>** wraps an array with growth semantics:

```csharp
var list = new List<int> { 1, 2, 3 };
list.Add(4);  // might reallocate internally
// But list is a reference type - you always work with the same list object
```

**Go slices** are value types that point to arrays:

```go
s := []int{1, 2, 3}
s = append(s, 4)  // might return a NEW slice header pointing to NEW array
```

That last line is where people get burned. `append` might modify the backing array in place, or it might allocate a new array and return a slice pointing to it. **You must use the return value.**

## The append Trap

This looks fine:

```go
func addItem(items []int, item int) {
    items = append(items, item)
}

func main() {
    s := []int{1, 2, 3}
    addItem(s, 4)
    fmt.Println(s)  // [1 2 3] - item wasn't added!
}
```

The slice header is passed by value. `append` creates a new header (possibly pointing to a new array), but that new header only exists inside `addItem`. The caller's `s` is unchanged.

Fixes:

```go
// Option 1: Return the new slice
func addItem(items []int, item int) []int {
    return append(items, item)
}

s = addItem(s, 4)  // use the return value

// Option 2: Use a pointer to slice (less common)
func addItem(items *[]int, item int) {
    *items = append(*items, item)
}

addItem(&s, 4)
```

In C#, this wouldn't be a problem. `List<T>` is a reference type:

```csharp
void AddItem(List<int> items, int item) {
    items.Add(item);  // modifies the actual list
}
```

Go's slice is not a reference type. It's a value type that contains a pointer. Subtle but critical difference.

## Shared Backing Arrays (The Real Gotcha)

Here's where it gets properly dangerous:

```go
original := []int{1, 2, 3, 4, 5}
slice1 := original[1:3]  // [2, 3]
slice2 := original[2:4]  // [3, 4]

slice1[1] = 999  // modify slice1

fmt.Println(original)  // [1 2 999 4 5]
fmt.Println(slice1)    // [2 999]
fmt.Println(slice2)    // [999 4]
```

All three slices share the same backing array. Modify one, you modify them all.

This is nothing like C#:

```csharp
var original = new int[] { 1, 2, 3, 4, 5 };
var slice = original[1..3];  // creates a NEW array in C# 8+
slice[1] = 999;
Console.WriteLine(string.Join(", ", original));  // 1, 2, 3, 4, 5 - unchanged
```

C# ranges create copies. Go slices share memory. Neither is wrong, but they're completely different behaviours.

### The Capacity Gotcha

It gets worse. When you slice, you might have hidden capacity:

```go
original := []int{1, 2, 3, 4, 5}
slice := original[1:3]  // [2, 3], but capacity is 4!

fmt.Println(len(slice))  // 2
fmt.Println(cap(slice))  // 4 - can see elements 1-4 of original

slice = append(slice, 999)  // doesn't allocate new array - overwrites original!

fmt.Println(original)  // [1 2 3 999 5] - element 3 (index 3) was overwritten
```

The `append` saw capacity, used it, and stomped on data that logically wasn't part of `slice` but physically was in the backing array.

To prevent this:

```go
// Limit capacity when slicing
slice := original[1:3:3]  // [low:high:max] - capacity is high-low = 2

// Or copy explicitly
slice := make([]int, 2)
copy(slice, original[1:3])
```

## Length vs Capacity

This distinction doesn't exist in `List<T>` (internally it does, but you don't see it):

```go
s := make([]int, 3, 10)  // length 3, capacity 10
fmt.Println(len(s))  // 3
fmt.Println(cap(s))  // 10

s[0] = 1  // OK
s[5] = 1  // panic: index out of range - len is 3!

s = s[:cap(s)]  // extend slice to full capacity
s[5] = 1        // now OK
```

Length is how many elements are accessible. Capacity is how many could be before reallocation. This is an implementation detail that Go exposes and expects you to understand.

## nil vs Empty Slice

Oh good, more nil pain:

```go
var s1 []int          // nil slice
s2 := []int{}         // empty slice
s3 := make([]int, 0)  // empty slice

fmt.Println(s1 == nil)  // true
fmt.Println(s2 == nil)  // false
fmt.Println(s3 == nil)  // false

// But they all behave the same for most operations
fmt.Println(len(s1), len(s2), len(s3))  // 0 0 0
```

A nil slice and an empty slice are functionally equivalent for `len`, `cap`, `append`, and `range`. But they're not equal to each other, and some JSON encoders treat them differently.

```go
json.Marshal(s1)  // might produce "null"
json.Marshal(s2)  // produces "[]"
```

Wonderful.

## Patterns That Help

### Always Capture append's Return

```go
s = append(s, item)  // always assign back
```

### Copy When Returning Subslices

```go
func getSubset(data []int) []int {
    subset := data[10:20]
    
    // Bad: caller might have data, mutating subset affects data
    return subset
    
    // Good: caller gets independent slice
    result := make([]int, len(subset))
    copy(result, subset)
    return result
}
```

### Preallocate When Size Is Known

```go
// Might reallocate multiple times
results := []int{}
for _, item := range items {
    results = append(results, transform(item))
}

// Single allocation
results := make([]int, 0, len(items))
for _, item := range items {
    results = append(results, transform(item))
}

// Or even better, known length
results := make([]int, len(items))
for i, item := range items {
    results[i] = transform(item)
}
```

### Use the Three-Index Slice for Safety

```go
// Dangerous: slice might have hidden capacity
sub := data[a:b]

// Safe: capacity is limited
sub := data[a:b:b]
```

## The Comparison

| Aspect | C# Array | C# List<T> | Go Slice |
|--------|----------|------------|----------|
| Fixed size | Yes | No | No |
| Reference type | Yes | Yes | No (value type with pointer) |
| Slicing copies | Yes (ranges) | N/A | No (shares memory) |
| append semantics | N/A | Add modifies list | Returns new header |
| Hidden capacity | No | Yes (internal) | Yes (exposed) |
| nil vs empty | null vs new int[0] | null vs new List | Different behaviours |

## The Honest Take

Slices are Go's most footgun-laden feature. They look simple, they have subtle semantics, and the gotchas aren't obvious until you've been bitten.

**What Go gets right:**
- Efficient memory sharing when you want it
- Clear distinction between length and capacity
- `append` is convenient (when used correctly)
- No boxing, good cache locality

**What C# does better:**
- `List<T>` is a reference type, modifications are visible everywhere
- Range slicing copies by default, no surprise aliasing
- `Span<T>` gives you explicit no-copy semantics when you want them
- You don't have to remember the three-index slice syntax

**The verdict:**
Slices are powerful and efficient. They're also a sharp tool that will cut you. Every Go developer has been bitten by shared backing arrays or forgotten `append` returns.

My advice: be paranoid about slice aliasing. Copy when returning subslices. Always use the return value of `append`. And when something mutates unexpectedly, check your slices first.

---

*That wraps up the memory section. Next we'll move into concurrency: goroutines, channels, and why Go's approach is fundamentally different from async/await.*
