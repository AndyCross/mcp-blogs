+++
title = "Mocking in a Language Without Mockito"
date = "2025-01-03"
draft = false
tags = ["go", "dotnet", "testing", "mocking", "csharp"]
series = ["step-over-to-go"]
+++

In C#, you reach for Moq or NSubstitute without thinking. Interface? Mock it. Verify calls? Easy. Set up return values? One line.

Go doesn't have a standard mocking framework. There's no reflection-based proxy generation. No `Mock<IUserService>()`. The Go way is more manual, and that's... actually fine? Let me explain.

## The C# Approach

You've done this a thousand times:

```csharp
public interface IUserRepository
{
    User GetById(int id);
    void Save(User user);
}

[Fact]
public void ProcessUser_CallsRepository()
{
    var mockRepo = new Mock<IUserRepository>();
    mockRepo.Setup(r => r.GetById(1)).Returns(new User { Id = 1, Name = "Alice" });
    
    var service = new UserService(mockRepo.Object);
    service.Process(1);
    
    mockRepo.Verify(r => r.GetById(1), Times.Once);
}
```

Clean, expressive, powerful. Moq generates a proxy class at runtime that implements the interface and records calls.

## The Go Approach: Hand-Written Fakes

Go doesn't have reflection-based mocking (well, it does, but it's not idiomatic). Instead, you write your own test doubles:

```go
type UserRepository interface {
    GetByID(id int) (*User, error)
    Save(user *User) error
}

// Fake implementation for testing
type FakeUserRepo struct {
    Users map[int]*User
    SaveCalled bool
    SavedUser *User
}

func (f *FakeUserRepo) GetByID(id int) (*User, error) {
    user, ok := f.Users[id]
    if !ok {
        return nil, ErrNotFound
    }
    return user, nil
}

func (f *FakeUserRepo) Save(user *User) error {
    f.SaveCalled = true
    f.SavedUser = user
    return nil
}
```

Then in your test:

```go
func TestProcessUser(t *testing.T) {
    repo := &FakeUserRepo{
        Users: map[int]*User{
            1: {ID: 1, Name: "Alice"},
        },
    }
    
    service := NewUserService(repo)
    service.Process(1)
    
    if !repo.SaveCalled {
        t.Error("expected Save to be called")
    }
}
```

More code. More manual work. But you control everything, and there's no magic.

## Why Go Developers Accept This

Three reasons:

**1. Interfaces are small**

Go's implicit interfaces encourage tiny interfaces. One or two methods. Writing a fake for a two-method interface is trivial.

```go
type Saver interface {
    Save(user *User) error
}

// Fake is one function
type FakeSaver struct {
    Err error
}

func (f *FakeSaver) Save(user *User) error {
    return f.Err
}
```

Compare to C#'s larger interfaces with 10+ methods. Moq saves significant effort there.

**2. Fakes are reusable**

You write the fake once, use it everywhere. Put it in a `testing` package or `_test.go` file:

```go
// In repository/testing.go or repository/fake_test.go
type FakeUserRepo struct { ... }
```

Now all tests can use it. The upfront cost pays off.

**3. Explicit is better than magic**

Go's philosophy. When a test fails, you can see exactly what the fake does. No proxy magic. No setup/verify DSL to decode.

## The testify/mock Package

If you really want Moq-style mocking, testify provides it:

```go
import "github.com/stretchr/testify/mock"

type MockUserRepo struct {
    mock.Mock
}

func (m *MockUserRepo) GetByID(id int) (*User, error) {
    args := m.Called(id)
    if args.Get(0) == nil {
        return nil, args.Error(1)
    }
    return args.Get(0).(*User), args.Error(1)
}

func (m *MockUserRepo) Save(user *User) error {
    args := m.Called(user)
    return args.Error(0)
}
```

Then use it:

```go
func TestProcessUser(t *testing.T) {
    repo := new(MockUserRepo)
    repo.On("GetByID", 1).Return(&User{ID: 1, Name: "Alice"}, nil)
    repo.On("Save", mock.Anything).Return(nil)
    
    service := NewUserService(repo)
    service.Process(1)
    
    repo.AssertCalled(t, "Save", mock.Anything)
}
```

Closer to Moq, but you still write the mock struct manually. testify handles the setup/verification plumbing.

## Generated Mocks: mockgen and mockery

Tools can generate mock implementations:

**mockgen** (from gomock):

```bash
mockgen -source=repository.go -destination=mock_repository.go
```

**mockery**:

```bash
mockery --name=UserRepository
```

These generate the boilerplate. You still use them manually in tests.

## Patterns for Effective Fakes

### Function Fields

For simple cases, use function fields:

```go
type FakeNotifier struct {
    NotifyFunc func(userID int, message string) error
}

func (f *FakeNotifier) Notify(userID int, message string) error {
    if f.NotifyFunc != nil {
        return f.NotifyFunc(userID, message)
    }
    return nil
}
```

In tests:

```go
notifier := &FakeNotifier{
    NotifyFunc: func(userID int, message string) error {
        if userID != 1 {
            t.Errorf("unexpected userID: %d", userID)
        }
        return nil
    },
}
```

Inline behaviour per test. No shared state.

### Recording Calls

Track what was called:

```go
type FakeNotifier struct {
    Calls []NotifyCall
}

type NotifyCall struct {
    UserID  int
    Message string
}

func (f *FakeNotifier) Notify(userID int, message string) error {
    f.Calls = append(f.Calls, NotifyCall{userID, message})
    return nil
}
```

Then assert:

```go
if len(notifier.Calls) != 1 {
    t.Errorf("expected 1 call, got %d", len(notifier.Calls))
}
if notifier.Calls[0].UserID != 1 {
    t.Errorf("wrong userID: %d", notifier.Calls[0].UserID)
}
```

### Error Injection

Make errors configurable:

```go
type FakeRepo struct {
    GetErr  error
    SaveErr error
}

func (f *FakeRepo) GetByID(id int) (*User, error) {
    if f.GetErr != nil {
        return nil, f.GetErr
    }
    return &User{ID: id}, nil
}
```

Test error paths:

```go
repo := &FakeRepo{GetErr: sql.ErrNoRows}
// test handles error correctly
```

## The Comparison

| Feature | Moq/NSubstitute | Go Fakes | testify/mock |
|---------|-----------------|----------|--------------|
| Boilerplate | None | Manual | Some |
| Setup syntax | Fluent | Manual | Method calls |
| Verification | Built-in | Manual | Built-in |
| Type safety | Good | Excellent | Okay (strings) |
| Debugging | Proxy magic | Clear code | Some magic |
| Learning curve | Moderate | Low | Low |
| Generation | Not needed | Optional | Optional |

## When to Use What

**Hand-written fakes when:**
- Interface is small (1-3 methods)
- You need the fake in multiple tests
- You want maximum clarity
- You prefer no dependencies

**testify/mock when:**
- Interface is larger
- You need verification of call counts/order
- You're comfortable with the DSL
- You want Moq-like experience

**Generated mocks when:**
- Interface is large and changes frequently
- You have many interfaces to mock
- You want consistency across the codebase

## The Honest Take

I thought I'd miss Moq. I don't, really.

**What Go does better:**
- No mock magic to debug
- Fakes are real code you can step through
- Small interfaces mean small fakes
- No framework dependency

**What C# does better:**
- Zero boilerplate for any interface
- Powerful verification syntax
- Better for large interfaces
- Established patterns and tooling

**The verdict:**
Go's approach is more work for each interface, but that work is simple and debuggable. If you design with small interfaces (as Go encourages), the fake-writing burden is minimal.

Start with hand-written fakes. Reach for testify/mock if you find yourself writing the same patterns repeatedly. Use generated mocks for genuinely large interfaces.

The bigger lesson: good interface design reduces mocking complexity in any language. Go just makes that more obvious.

---

*Next up: benchmarks and profiling. `go test -bench` and pprof for understanding where your performance actually goes.*
