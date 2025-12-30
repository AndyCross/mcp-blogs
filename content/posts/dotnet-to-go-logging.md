+++
title = "Logging: slog and the Structured Logging Story"
date = "2025-01-04"
draft = false
tags = ["go", "dotnet", "logging", "slog", "csharp"]
+++

For years, Go's logging story was "use the `log` package or pick a third-party library." The standard `log` package is basic—no levels, no structure, no context. Everyone used zerolog, zap, or logrus.

Then Go 1.21 shipped `log/slog`. Finally, structured logging in the standard library. And it's actually good.

## The Old Way: log Package

Go's original `log` package:

```go
import "log"

log.Println("server starting")
log.Printf("listening on port %d", 8080)
log.Fatal("failed to connect")  // logs and calls os.Exit(1)
```

Output:

```
2025/01/04 10:30:00 server starting
2025/01/04 10:30:00 listening on port 8080
```

No levels. No structure. Just text. Fine for simple programs, inadequate for production.

## The New Way: slog

Go 1.21's `log/slog` package:

```go
import "log/slog"

slog.Info("server starting")
slog.Info("listening", "port", 8080)
slog.Error("failed to connect", "error", err, "host", hostname)
```

Default text output:

```
2025/01/04 10:30:00 INFO server starting
2025/01/04 10:30:00 INFO listening port=8080
2025/01/04 10:30:00 ERROR failed to connect error="connection refused" host="db.example.com"
```

Or JSON:

```go
logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
slog.SetDefault(logger)
```

```json
{"time":"2025-01-04T10:30:00Z","level":"INFO","msg":"listening","port":8080}
```

## Log Levels

slog has four levels:

```go
slog.Debug("detailed debugging info")
slog.Info("normal operation")
slog.Warn("something unexpected")
slog.Error("something failed")
```

Set the minimum level:

```go
opts := &slog.HandlerOptions{
    Level: slog.LevelDebug,  // show Debug and above
}
logger := slog.New(slog.NewJSONHandler(os.Stdout, opts))
```

## Structured Attributes

Add key-value pairs to log entries:

```go
// Alternating key-value pairs
slog.Info("user created", "user_id", userID, "email", email)

// Or use slog.Attr for type safety
slog.Info("user created",
    slog.Int("user_id", userID),
    slog.String("email", email),
    slog.Time("created_at", time.Now()),
)
```

## Logger with Context

Add attributes that appear in every log entry:

```go
logger := slog.Default().With(
    "service", "user-api",
    "version", "1.2.3",
)

logger.Info("request received")
// {"time":"...","level":"INFO","msg":"request received","service":"user-api","version":"1.2.3"}
```

Or create child loggers:

```go
func handleRequest(r *http.Request) {
    requestID := r.Header.Get("X-Request-ID")
    log := slog.Default().With("request_id", requestID)
    
    log.Info("processing request")
    // ... later
    log.Info("request complete")  // both have request_id
}
```

## Comparing to ILogger

C#'s `ILogger`:

```csharp
_logger.LogInformation("User created: {UserId} {Email}", userId, email);
```

Go's slog:

```go
slog.Info("user created", "user_id", userID, "email", email)
```

Similar structured logging. Different syntax.

| Feature | ILogger | slog |
|---------|---------|------|
| Structured logging | Yes | Yes |
| Log levels | 6 (Trace-Critical) | 4 (Debug-Error) |
| Scopes | `BeginScope()` | `With()` |
| DI integration | Built-in | Manual |
| Providers | Many built-in | Handlers (fewer) |
| Message templates | `{Named}` placeholders | Key-value pairs |
| Log categories | Type-based | Manual grouping |

## Using slog with HTTP Context

Pass loggers through context:

```go
type ctxKey struct{}

func WithLogger(ctx context.Context, logger *slog.Logger) context.Context {
    return context.WithValue(ctx, ctxKey{}, logger)
}

func FromContext(ctx context.Context) *slog.Logger {
    if logger, ok := ctx.Value(ctxKey{}).(*slog.Logger); ok {
        return logger
    }
    return slog.Default()
}
```

Middleware to add request context:

```go
func loggingMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        logger := slog.Default().With(
            "request_id", r.Header.Get("X-Request-ID"),
            "method", r.Method,
            "path", r.URL.Path,
        )
        
        ctx := WithLogger(r.Context(), logger)
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}

// In handlers
func handler(w http.ResponseWriter, r *http.Request) {
    log := FromContext(r.Context())
    log.Info("processing")  // includes request context
}
```

## Custom Handlers

slog uses handlers for output. Write your own:

```go
type PrettyHandler struct {
    slog.Handler
    w io.Writer
}

func (h *PrettyHandler) Handle(ctx context.Context, r slog.Record) error {
    // Custom formatting
    fmt.Fprintf(h.w, "[%s] %s: %s\n",
        r.Time.Format("15:04:05"),
        r.Level,
        r.Message,
    )
    r.Attrs(func(a slog.Attr) bool {
        fmt.Fprintf(h.w, "  %s=%v\n", a.Key, a.Value)
        return true
    })
    return nil
}
```

Or wrap existing handlers for filtering, sampling, etc.

## Third-Party Integration

slog plays well with existing libraries:

**Output to zerolog:**
```go
// zerolog adapter available
```

**Output to zap:**
```go
// zapslog adapter available
```

You can use slog's API with your preferred backend.

## Performance Considerations

slog is designed for production:

```go
// Avoid allocation if level disabled
if slog.Default().Enabled(ctx, slog.LevelDebug) {
    slog.Debug("expensive operation", "data", expensiveComputation())
}
```

Or use `LogAttrs` for zero-allocation logging:

```go
slog.Default().LogAttrs(ctx, slog.LevelInfo, "event",
    slog.String("key", value),
    slog.Int("count", n),
)
```

## The Honest Take

slog is a welcome addition. Not as mature as the third-party options, but good enough for most uses.

**What slog does well:**
- Standard library (no dependencies)
- Good API design
- Structured by default
- Handler abstraction for extensibility

**What ILogger does better:**
- More log levels
- Richer ecosystem
- DI integration
- Better provider options (Application Insights, Seq, etc.)
- Message templates with semantic meaning

**What third-party Go loggers do better:**
- zerolog: extremely fast, zero allocation
- zap: battle-tested, rich features
- Both: more production-proven

**The verdict:**
For new projects, slog is a solid choice. It's in the standard library, it's structured, it works.

For high-performance logging or specific output requirements, zerolog or zap might still be better.

If you're coming from ILogger, you'll find slog familiar but simpler. Fewer features, but the core functionality is there.

---

*Next up: database access with database/sql—raw SQL, connection pooling, and missing your ORM.*
