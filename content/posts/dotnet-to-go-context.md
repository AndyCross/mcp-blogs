+++
title = "Context Is King"
date = "2025-01-01"
draft = false
tags = ["go", "dotnet", "concurrency", "context", "csharp"]
+++

Every Go function that does I/O, might take a while, or should be cancellable will take a `context.Context` as its first parameter. It's Go's answer to `CancellationToken`, plus request-scoped values, all in one.

If you're not using context properly, you're not writing idiomatic Go. It's that fundamental.

## The Basics

```go
func DoSomething(ctx context.Context) error {
    // Check if already cancelled
    select {
    case <-ctx.Done():
        return ctx.Err()
    default:
    }
    
    // Do work...
    return nil
}
```

Every context has a `Done()` channel that closes when the context is cancelled. You check it periodically during long operations.

## Creating Contexts

Start with a background or TODO context:

```go
ctx := context.Background()  // root context, never cancelled
ctx := context.TODO()        // placeholder when you're not sure what context to use
```

Then derive child contexts with cancellation or deadlines:

```go
// Manual cancellation
ctx, cancel := context.WithCancel(parentCtx)
defer cancel()  // always call cancel to release resources

// Timeout
ctx, cancel := context.WithTimeout(parentCtx, 5*time.Second)
defer cancel()

// Deadline (absolute time)
ctx, cancel := context.WithDeadline(parentCtx, time.Now().Add(5*time.Second))
defer cancel()
```

When you cancel a context, all contexts derived from it are also cancelled. It's a tree.

## The C# Comparison

C#'s `CancellationToken`:

```csharp
public async Task DoSomethingAsync(CancellationToken ct)
{
    ct.ThrowIfCancellationRequested();
    
    // Do work...
}

// Usage
var cts = new CancellationTokenSource(TimeSpan.FromSeconds(5));
await DoSomethingAsync(cts.Token);
```

Similar concepts:

| Go | C# |
|-----|-----|
| `context.Context` | `CancellationToken` |
| `context.WithCancel` | `new CancellationTokenSource()` |
| `context.WithTimeout` | `new CancellationTokenSource(TimeSpan)` |
| `ctx.Done()` channel | `token.IsCancellationRequested` |
| `ctx.Err()` | `token.ThrowIfCancellationRequested()` |
| `context.WithValue` | `AsyncLocal<T>` / HttpContext.Items |

The big difference: Go's context also carries request-scoped values. C# separates cancellation (`CancellationToken`) from request-scoped data (`HttpContext`, `AsyncLocal<T>`, etc.).

## Context as First Parameter

By convention, context is always the first parameter:

```go
// CORRECT
func GetUser(ctx context.Context, id string) (*User, error)

// WRONG - context should be first
func GetUser(id string, ctx context.Context) (*User, error)

// WRONG - don't put context in structs
type UserService struct {
    ctx context.Context  // NO!
}
```

This convention is enforced by linters and universally followed. Don't be creative.

## Proper Cancellation Checking

In long operations, check for cancellation periodically:

```go
func ProcessItems(ctx context.Context, items []Item) error {
    for _, item := range items {
        // Check at the start of each iteration
        select {
        case <-ctx.Done():
            return ctx.Err()
        default:
        }
        
        if err := processItem(ctx, item); err != nil {
            return err
        }
    }
    return nil
}
```

For I/O operations, pass the context through:

```go
func FetchData(ctx context.Context, url string) ([]byte, error) {
    req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
    if err != nil {
        return nil, err
    }
    
    resp, err := http.DefaultClient.Do(req)
    if err != nil {
        return nil, err  // includes context cancellation
    }
    defer resp.Body.Close()
    
    return io.ReadAll(resp.Body)
}
```

When the context is cancelled, the HTTP request is aborted. Same for database queries, gRPC calls, etc.

## Context Values

Context can carry request-scoped values:

```go
type contextKey string

const userIDKey contextKey = "userID"

func WithUserID(ctx context.Context, userID string) context.Context {
    return context.WithValue(ctx, userIDKey, userID)
}

func GetUserID(ctx context.Context) (string, bool) {
    userID, ok := ctx.Value(userIDKey).(string)
    return userID, ok
}
```

Use sparingly! Context values should be:
- Request-scoped data that transits process boundaries (request IDs, auth tokens)
- Not a replacement for function parameters

```go
// BAD: Using context to avoid passing parameters
ctx = context.WithValue(ctx, "db", database)
ctx = context.WithValue(ctx, "logger", logger)
// Now your function signatures lie about their dependencies

// GOOD: Pass dependencies explicitly, use context for request-scoped data
func HandleRequest(ctx context.Context, db *Database, logger *Logger) {
    requestID := GetRequestID(ctx)  // request-scoped, appropriate
    // ...
}
```

## HTTP Server Context

In HTTP servers, the request carries context:

```go
func handler(w http.ResponseWriter, r *http.Request) {
    ctx := r.Context()  // cancelled if client disconnects
    
    result, err := doExpensiveOperation(ctx)
    if err != nil {
        if errors.Is(err, context.Canceled) {
            // Client disconnected, don't bother responding
            return
        }
        http.Error(w, err.Error(), 500)
        return
    }
    
    json.NewEncoder(w).Encode(result)
}
```

The request context is automatically cancelled when:
- The client closes the connection
- The request times out
- The server is shutting down (with proper setup)

## Timeout Patterns

Setting per-operation timeouts:

```go
func QueryWithTimeout(ctx context.Context, query string) ([]Row, error) {
    ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
    defer cancel()
    
    return db.QueryContext(ctx, query)
}
```

The timeout is scoped to this operation. If the parent context has a shorter deadline, that wins.

```go
// Parent has 3 second deadline
parentCtx, _ := context.WithTimeout(context.Background(), 3*time.Second)

// Child requests 5 seconds, but will actually timeout at 3
childCtx, _ := context.WithTimeout(parentCtx, 5*time.Second)
```

Child contexts can only be more restrictive than parents, never less.

## Cancellation Propagation

When you start goroutines, propagate the context:

```go
func ProcessInParallel(ctx context.Context, items []Item) error {
    g, ctx := errgroup.WithContext(ctx)  // from golang.org/x/sync/errgroup
    
    for _, item := range items {
        item := item
        g.Go(func() error {
            return process(ctx, item)  // same context
        })
    }
    
    return g.Wait()
}
```

The `errgroup` package creates a derived context that cancels when any goroutine returns an error. All other goroutines see the cancellation.

## Common Mistakes

**Don't store context in structs:**
```go
// WRONG
type Worker struct {
    ctx context.Context
}

// RIGHT: pass context to methods
func (w *Worker) Do(ctx context.Context) error
```

**Don't use string keys for context values:**
```go
// WRONG: key collisions possible
ctx = context.WithValue(ctx, "userID", id)

// RIGHT: unexported type prevents collisions
type contextKey string
const userIDKey contextKey = "userID"
```

**Don't ignore context cancellation:**
```go
// WRONG: ignoring cancellation
func slowOperation(ctx context.Context) {
    time.Sleep(10 * time.Second)  // doesn't respect context
}

// RIGHT: check context
func slowOperation(ctx context.Context) error {
    select {
    case <-time.After(10 * time.Second):
        return nil
    case <-ctx.Done():
        return ctx.Err()
    }
}
```

## The Comparison

| Aspect | Go context.Context | C# CancellationToken |
|--------|-------------------|---------------------|
| Cancellation | Yes | Yes |
| Timeouts | Yes (WithTimeout) | Yes (CTS constructor) |
| Request values | Yes (WithValue) | No (use HttpContext) |
| First parameter convention | Always | Often last |
| Integrated with I/O | Yes | Yes |
| Tree structure | Yes (parent-child) | Yes (linked tokens) |

## The Honest Take

Context is one of Go's better patterns. It unifies cancellation and request-scoped values into one concept that permeates the ecosystem.

**What Go does well:**
- Single abstraction for cancellation + deadlines + values
- Universal convention (first parameter)
- Clean propagation through call chains
- Well integrated with stdlib (http, database/sql, etc.)

**What C# does better:**
- Clearer separation of concerns (CancellationToken vs HttpContext)
- `CancellationToken` is optional by default (overloads without it)
- Easier to add cancellation to existing APIs
- Less ceremony for simple cases

**The verdict:**
Context feels heavyweight at first—every function needs `ctx context.Context` as its first parameter. But the consistency pays off. You can always cancel. You can always set timeouts. You can always trace request IDs through your system.

Once you're used to it, going back to languages without pervasive cancellation support feels limiting.

---

*That wraps up the concurrency section. Go's model is different from async/await, but it's powerful and consistent. Goroutines for concurrency, channels for communication, context for cancellation and request-scoping. Learn those three and you've got Go's concurrency story.*
