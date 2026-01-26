+++
title = "Metrics, Traces, and Logs: The OpenTelemetry Way"
date = "2025-01-05"
draft = false
tags = ["go", "dotnet", "observability", "opentelemetry", "csharp"]
+++

Observability in production means three things: metrics (what's happening), traces (how requests flow), and logs (what went wrong). OpenTelemetry unifies all three.

Go's OpenTelemetry support is mature. The project itself is Go-native. Let's instrument a Go service properly.

## OpenTelemetry Setup

Add dependencies:

```bash
go get go.opentelemetry.io/otel
go get go.opentelemetry.io/otel/sdk
go get go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp
go get go.opentelemetry.io/otel/exporters/otlp/otlpmetric/otlpmetrichttp
go get go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp
```

Initialize in main:

```go
package main

import (
    "context"
    "log"
    "time"
    
    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
    "go.opentelemetry.io/otel/sdk/resource"
    sdktrace "go.opentelemetry.io/otel/sdk/trace"
    semconv "go.opentelemetry.io/otel/semconv/v1.24.0"
)

func initTracer(ctx context.Context) (*sdktrace.TracerProvider, error) {
    exporter, err := otlptracehttp.New(ctx)
    if err != nil {
        return nil, err
    }
    
    res, err := resource.New(ctx,
        resource.WithAttributes(
            semconv.ServiceName("myservice"),
            semconv.ServiceVersion("1.0.0"),
        ),
    )
    if err != nil {
        return nil, err
    }
    
    tp := sdktrace.NewTracerProvider(
        sdktrace.WithBatcher(exporter),
        sdktrace.WithResource(res),
    )
    
    otel.SetTracerProvider(tp)
    return tp, nil
}

func main() {
    ctx := context.Background()
    
    tp, err := initTracer(ctx)
    if err != nil {
        log.Fatal(err)
    }
    defer tp.Shutdown(ctx)
    
    // Your app...
}
```

## Automatic HTTP Instrumentation

Wrap your HTTP handler:

```go
import "go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"

func main() {
    handler := http.HandlerFunc(myHandler)
    wrappedHandler := otelhttp.NewHandler(handler, "my-server")
    
    http.ListenAndServe(":8080", wrappedHandler)
}
```

Every request automatically creates a span with:
- HTTP method and path
- Status code
- Request duration
- Error information

## Manual Spans

For business logic:

```go
import "go.opentelemetry.io/otel"

var tracer = otel.Tracer("myservice")

func processOrder(ctx context.Context, orderID string) error {
    ctx, span := tracer.Start(ctx, "processOrder")
    defer span.End()
    
    span.SetAttributes(
        attribute.String("order.id", orderID),
    )
    
    // Process order...
    if err := validateOrder(ctx, orderID); err != nil {
        span.RecordError(err)
        span.SetStatus(codes.Error, err.Error())
        return err
    }
    
    return nil
}

func validateOrder(ctx context.Context, orderID string) error {
    ctx, span := tracer.Start(ctx, "validateOrder")
    defer span.End()
    
    // Validation logic...
    return nil
}
```

The context carries trace information. Child spans automatically link to parents.

## Metrics

```go
import (
    "go.opentelemetry.io/otel/metric"
    "go.opentelemetry.io/otel"
)

var (
    meter = otel.Meter("myservice")
    requestCounter metric.Int64Counter
    requestDuration metric.Float64Histogram
)

func init() {
    var err error
    requestCounter, err = meter.Int64Counter("http_requests_total",
        metric.WithDescription("Total HTTP requests"),
    )
    if err != nil {
        log.Fatal(err)
    }
    
    requestDuration, err = meter.Float64Histogram("http_request_duration_seconds",
        metric.WithDescription("HTTP request duration"),
    )
    if err != nil {
        log.Fatal(err)
    }
}

func handler(w http.ResponseWriter, r *http.Request) {
    start := time.Now()
    
    // Handle request...
    
    requestCounter.Add(r.Context(), 1,
        metric.WithAttributes(
            attribute.String("method", r.Method),
            attribute.String("path", r.URL.Path),
        ),
    )
    
    requestDuration.Record(r.Context(), time.Since(start).Seconds(),
        metric.WithAttributes(
            attribute.String("method", r.Method),
        ),
    )
}
```

## Structured Logging with Trace Context

Connect logs to traces:

```go
import (
    "log/slog"
    "go.opentelemetry.io/otel/trace"
)

func handler(w http.ResponseWriter, r *http.Request) {
    ctx := r.Context()
    span := trace.SpanFromContext(ctx)
    
    logger := slog.Default().With(
        "trace_id", span.SpanContext().TraceID().String(),
        "span_id", span.SpanContext().SpanID().String(),
    )
    
    logger.Info("processing request",
        "method", r.Method,
        "path", r.URL.Path,
    )
}
```

Now logs correlate with traces.

## Database Instrumentation

For `database/sql`:

```go
import (
    "github.com/XSAM/otelsql"
    semconv "go.opentelemetry.io/otel/semconv/v1.24.0"
)

func initDB() (*sql.DB, error) {
    db, err := otelsql.Open("postgres", connString,
        otelsql.WithAttributes(
            semconv.DBSystemPostgreSQL,
        ),
    )
    if err != nil {
        return nil, err
    }
    
    otelsql.RegisterDBStatsMetrics(db,
        otelsql.WithAttributes(semconv.DBSystemPostgreSQL),
    )
    
    return db, nil
}
```

## Complete Example

```go
package main

import (
    "context"
    "log/slog"
    "net/http"
    "os"
    "time"
    
    "go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/attribute"
    "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
    "go.opentelemetry.io/otel/sdk/resource"
    sdktrace "go.opentelemetry.io/otel/sdk/trace"
    semconv "go.opentelemetry.io/otel/semconv/v1.24.0"
    "go.opentelemetry.io/otel/trace"
)

var tracer = otel.Tracer("myservice")

func main() {
    ctx := context.Background()
    
    // Setup tracing
    tp, err := initTracer(ctx)
    if err != nil {
        slog.Error("failed to init tracer", "error", err)
        os.Exit(1)
    }
    defer tp.Shutdown(ctx)
    
    // Routes
    mux := http.NewServeMux()
    mux.HandleFunc("GET /users/{id}", getUserHandler)
    
    // Wrap with OTel
    handler := otelhttp.NewHandler(mux, "myservice")
    
    slog.Info("starting server", "addr", ":8080")
    http.ListenAndServe(":8080", handler)
}

func getUserHandler(w http.ResponseWriter, r *http.Request) {
    ctx := r.Context()
    span := trace.SpanFromContext(ctx)
    
    userID := r.PathValue("id")
    span.SetAttributes(attribute.String("user.id", userID))
    
    logger := slog.Default().With(
        "trace_id", span.SpanContext().TraceID().String(),
        "user_id", userID,
    )
    
    user, err := fetchUser(ctx, userID)
    if err != nil {
        span.RecordError(err)
        logger.Error("failed to fetch user", "error", err)
        http.Error(w, "user not found", http.StatusNotFound)
        return
    }
    
    logger.Info("user fetched successfully")
    json.NewEncoder(w).Encode(user)
}

func fetchUser(ctx context.Context, id string) (*User, error) {
    ctx, span := tracer.Start(ctx, "fetchUser")
    defer span.End()
    
    // Simulated database call
    time.Sleep(10 * time.Millisecond)
    
    return &User{ID: id, Name: "Alice"}, nil
}
```

## Comparing to .NET

| Aspect | .NET | Go |
|--------|------|-----|
| OTel SDK | Mature | Mature (Go-native) |
| Auto-instrumentation | Yes | Yes (via contrib) |
| ASP.NET integration | Built-in | Manual wrapping |
| DI integration | Built-in | Manual |
| Logging integration | ILogger + OTel | slog + manual |

.NET's integration is more automatic. Go requires more explicit setup but gives more control.

## Exporters

Send to your observability backend:

**OTLP (Jaeger, Tempo, etc.):**
```go
exporter, _ := otlptracehttp.New(ctx,
    otlptracehttp.WithEndpoint("tempo:4318"),
    otlptracehttp.WithInsecure(),
)
```

**Prometheus (metrics):**
```go
import "go.opentelemetry.io/otel/exporters/prometheus"

exporter, _ := prometheus.New()
http.Handle("/metrics", promhttp.Handler())
```

**stdout (debugging):**
```go
import "go.opentelemetry.io/otel/exporters/stdout/stdouttrace"

exporter, _ := stdouttrace.New(stdouttrace.WithPrettyPrint())
```

## The Honest Take

Go's OpenTelemetry support is excellent. The project is Go-native.

**What Go does well:**
- OTel is Go-native
- Explicit instrumentation is clear
- Good contrib library coverage
- Low overhead

**What .NET does better:**
- More automatic instrumentation
- Better DI integration
- Richer ASP.NET Core support
- Activity API is mature

**The verdict:**
OpenTelemetry in Go requires more explicit setup than .NET's automatic instrumentation. But once configured, it works well.

The key patterns (wrap HTTP handlers, propagate context, create spans for significant operations) are the same in any language. Go just makes you write them out.

---

*Next up: health checks and readiness probes. Patterns that work in container orchestrators.*
