+++
title = "Testing Without a Framework"
date = "2025-01-03"
draft = false
tags = ["go", "dotnet", "testing", "csharp"]
series = ["step-over-to-go"]
+++

In C#, you pick a test framework: xUnit, NUnit, MSTest. You install packages. You learn attributes. You configure test runners.

In Go, you run `go test`. That's it. There's one testing approach, it's built in, and it's been there since the beginning.

This felt limiting at first. "Where are my attributes? Where's my dependency injection? Where's my `[Theory]` with `[InlineData]`?" Then I wrote some tests and realised: Go's simplicity is the point.

## The Basics

Test files end in `_test.go`. Test functions start with `Test`:

```go
// math.go
package math

func Add(a, b int) int {
    return a + b
}

// math_test.go
package math

import "testing"

func TestAdd(t *testing.T) {
    result := Add(2, 3)
    if result != 5 {
        t.Errorf("Add(2, 3) = %d; want 5", result)
    }
}
```

Run with:

```bash
go test
go test -v           # verbose output
go test ./...        # all packages
go test -run TestAdd # specific test
```

No attributes. No framework imports. Just a function that takes `*testing.T`.

## Comparing to xUnit

Here's the same test in xUnit:

```csharp
public class MathTests
{
    [Fact]
    public void Add_TwoNumbers_ReturnsSum()
    {
        var result = Math.Add(2, 3);
        Assert.Equal(5, result);
    }
}
```

Go's version is more verbose in the assertion (`if` + `t.Errorf` vs `Assert.Equal`), but there's no class wrapper, no attribute, no dependency on a test framework package.

## The testing.T Type

The `*testing.T` parameter is your test context. Key methods:

```go
func TestSomething(t *testing.T) {
    t.Log("informational message")      // only shown with -v
    t.Error("test failed but continue") // marks fail, continues
    t.Fatal("test failed, stop now")    // marks fail, stops this test
    t.Skip("skipping this test")        // skips test
    
    // Formatted versions
    t.Logf("value is %d", 42)
    t.Errorf("got %d, want %d", actual, expected)
    t.Fatalf("unexpected error: %v", err)
}
```

No assertion library needed. You write `if` statements and call `t.Error` or `t.Fatal`.

## Table-Driven Tests

This is Go's answer to `[Theory]` with `[InlineData]`. Instead of attributes, you use a slice of test cases:

```go
func TestAdd(t *testing.T) {
    tests := []struct {
        name     string
        a, b     int
        expected int
    }{
        {"positive numbers", 2, 3, 5},
        {"negative numbers", -1, -1, -2},
        {"zero", 0, 0, 0},
        {"mixed", -5, 10, 5},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            result := Add(tt.a, tt.b)
            if result != tt.expected {
                t.Errorf("Add(%d, %d) = %d; want %d", tt.a, tt.b, result, tt.expected)
            }
        })
    }
}
```

`t.Run` creates a subtest. Each case runs independently, shows up separately in output, and can be run individually:

```bash
go test -run TestAdd/positive_numbers
```

Compare to xUnit:

```csharp
[Theory]
[InlineData(2, 3, 5)]
[InlineData(-1, -1, -2)]
[InlineData(0, 0, 0)]
[InlineData(-5, 10, 5)]
public void Add_VariousInputs_ReturnsExpected(int a, int b, int expected)
{
    Assert.Equal(expected, Math.Add(a, b));
}
```

xUnit is more concise. Go's version is more explicit and doesn't require learning attribute syntax. Personal preference.

## Test Setup and Teardown

No `[SetUp]` or `[TearDown]` attributes. Use regular functions:

```go
func TestWithSetup(t *testing.T) {
    // Setup
    db := setupTestDatabase()
    defer db.Close()  // Teardown
    
    // Test
    result := QueryUsers(db)
    if len(result) != 0 {
        t.Error("expected empty database")
    }
}
```

For shared setup across tests, use `TestMain`:

```go
var testDB *Database

func TestMain(m *testing.M) {
    // Setup before all tests
    testDB = setupTestDatabase()
    
    // Run tests
    code := m.Run()
    
    // Teardown after all tests
    testDB.Close()
    
    os.Exit(code)
}

func TestSomething(t *testing.T) {
    // testDB is available
}
```

`TestMain` is the entry point for the test binary. It's like a test fixture that wraps all tests.

## Parallel Tests

Run tests in parallel:

```go
func TestParallel1(t *testing.T) {
    t.Parallel()
    // This test can run alongside other parallel tests
}

func TestParallel2(t *testing.T) {
    t.Parallel()
    // So can this one
}
```

`t.Parallel()` marks a test as safe to run concurrently. Go runs parallel tests up to `GOMAXPROCS` simultaneously.

## Test Coverage

Built in:

```bash
go test -cover                     # show coverage percentage
go test -coverprofile=coverage.out # generate profile
go tool cover -html=coverage.out   # view in browser
```

No third-party tools needed. Coverage is a first-class feature.

## Subtests for Organisation

Group related tests:

```go
func TestUser(t *testing.T) {
    t.Run("Create", func(t *testing.T) {
        t.Run("valid input", func(t *testing.T) { ... })
        t.Run("missing name", func(t *testing.T) { ... })
        t.Run("invalid email", func(t *testing.T) { ... })
    })
    
    t.Run("Update", func(t *testing.T) {
        t.Run("existing user", func(t *testing.T) { ... })
        t.Run("non-existent user", func(t *testing.T) { ... })
    })
}
```

Run specific groups:

```bash
go test -run TestUser/Create
go test -run TestUser/Create/valid_input
```

## Helper Functions

Mark a function as a test helper so errors report the caller's line:

```go
func assertEqual(t *testing.T, got, want int) {
    t.Helper()  // errors will show caller's line number
    if got != want {
        t.Errorf("got %d, want %d", got, want)
    }
}

func TestSomething(t *testing.T) {
    assertEqual(t, Add(2, 2), 4)  // error shows this line, not assertEqual
}
```

## What About Assertions?

Go's standard library has no assertion functions. You write:

```go
if result != expected {
    t.Errorf("got %v, want %v", result, expected)
}
```

Instead of:

```csharp
Assert.Equal(expected, result);
```

This is verbose. Many people use the `testify` package for assertions:

```go
import "github.com/stretchr/testify/assert"

func TestAdd(t *testing.T) {
    assert.Equal(t, 5, Add(2, 3))
    assert.NotNil(t, somePointer)
    assert.Contains(t, "hello world", "world")
}
```

Testify is popular, but some Go developers consider it unnecessary. The standard approach works fine; it's just more typing.

## The Comparison

| Feature | xUnit/NUnit | Go testing |
|---------|-------------|------------|
| Test discovery | Attributes | Naming convention (`Test*`) |
| Assertions | Rich library | Manual or testify |
| Parameterised tests | `[Theory]` | Table-driven |
| Setup/Teardown | Attributes | Manual or `TestMain` |
| Parallel | `[Collection]` | `t.Parallel()` |
| Coverage | Third-party or VS | Built-in |
| Mocking | Moq, NSubstitute | Interfaces + manual |
| Test runner | Separate tool | `go test` |

## The Honest Take

Go's testing is simpler but more manual. You write more code per test, but there's less framework magic to understand.

**What Go does better:**
- Zero dependencies for basic testing
- Coverage built in
- `go test` just works
- Table-driven tests are powerful
- No framework version conflicts

**What C# does better:**
- Rich assertion libraries
- Better IDE integration (Test Explorer)
- More flexible parameterised tests
- Better test output formatting
- Mature mocking ecosystem

**The verdict:**
For simple unit tests, Go's built-in testing is fine. You'll write more boilerplate, but you'll spend zero time configuring frameworks.

For complex test scenarios, you might miss xUnit's features. But honestly? Most tests are simple. Go's approach handles them perfectly well.

---

*Next up: mocking in Go. Interfaces, hand-written fakes, and when to reach for testify/mock.*
