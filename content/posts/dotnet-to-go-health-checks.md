+++
title = "Health Checks and Readiness Probes"
date = "2025-01-05"
draft = false
tags = ["go", "dotnet", "health-checks", "kubernetes", "csharp"]
+++

We touched on health checks in the Kubernetes post. Let's go deeper. Proper health checks that actually tell orchestrators useful information.

## The Three Probes

Kubernetes (and similar orchestrators) use three types of probes:

| Probe | Question | Failure Action |
|-------|----------|----------------|
| **Liveness** | Is the process alive? | Restart container |
| **Readiness** | Can it handle traffic? | Remove from load balancer |
| **Startup** | Has it finished starting? | Keep waiting |

Getting these right matters for reliability.

## Liveness: Am I Alive?

Liveness should answer: "Is this process fundamentally broken?"

```go
func livenessHandler(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
    w.Write([]byte("ok"))
}
```

That's it. If your process can respond, it's alive.

**Don't put in liveness:**
- Database connectivity checks
- External service checks
- Anything that might fail temporarily

Why? If your database is down and liveness fails, Kubernetes restarts your pod. But restarting won't fix the database. Now you're restart-looping instead of gracefully handling the outage.

Liveness = "Is my process fundamentally broken, like stuck in a deadlock?"

## Readiness: Can I Serve Traffic?

Readiness should answer: "Should I receive requests right now?"

```go
type HealthChecker struct {
    db    *sql.DB
    cache *redis.Client
    ready atomic.Bool
}

func (h *HealthChecker) ReadinessHandler(w http.ResponseWriter, r *http.Request) {
    if !h.ready.Load() {
        http.Error(w, "not ready", http.StatusServiceUnavailable)
        return
    }
    
    // Check critical dependencies
    ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
    defer cancel()
    
    if err := h.db.PingContext(ctx); err != nil {
        http.Error(w, "database unavailable", http.StatusServiceUnavailable)
        return
    }
    
    if err := h.cache.Ping(ctx).Err(); err != nil {
        http.Error(w, "cache unavailable", http.StatusServiceUnavailable)
        return
    }
    
    w.WriteHeader(http.StatusOK)
    w.Write([]byte("ok"))
}
```

If readiness fails, Kubernetes removes the pod from the Service endpoints. Traffic goes elsewhere. The pod isn't restarted. It just doesn't receive requests until it's ready again.

## Startup: Am I Done Initialising?

For apps with slow startup (loading ML models, warming caches, running migrations):

```go
type App struct {
    started atomic.Bool
}

func (a *App) StartupHandler(w http.ResponseWriter, r *http.Request) {
    if a.started.Load() {
        w.WriteHeader(http.StatusOK)
        return
    }
    http.Error(w, "starting", http.StatusServiceUnavailable)
}

func (a *App) Initialize() {
    // Slow startup work
    loadMLModel()
    warmCache()
    runMigrations()
    
    a.started.Store(true)
}
```

Kubernetes waits for startup probe to pass before checking liveness/readiness. Prevents premature restarts during slow initialization.

## Detailed Health Response

For debugging, return details:

```go
type HealthStatus struct {
    Status     string            `json:"status"`
    Checks     map[string]Check  `json:"checks"`
    Version    string            `json:"version,omitempty"`
    Uptime     string            `json:"uptime,omitempty"`
}

type Check struct {
    Status  string `json:"status"`
    Message string `json:"message,omitempty"`
}

func (h *HealthChecker) DetailedHealthHandler(w http.ResponseWriter, r *http.Request) {
    status := HealthStatus{
        Status:  "healthy",
        Checks:  make(map[string]Check),
        Version: version,
        Uptime:  time.Since(startTime).String(),
    }
    
    // Database check
    ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
    defer cancel()
    
    if err := h.db.PingContext(ctx); err != nil {
        status.Checks["database"] = Check{Status: "unhealthy", Message: err.Error()}
        status.Status = "unhealthy"
    } else {
        status.Checks["database"] = Check{Status: "healthy"}
    }
    
    // Cache check
    if err := h.cache.Ping(ctx).Err(); err != nil {
        status.Checks["cache"] = Check{Status: "unhealthy", Message: err.Error()}
        status.Status = "unhealthy"
    } else {
        status.Checks["cache"] = Check{Status: "healthy"}
    }
    
    w.Header().Set("Content-Type", "application/json")
    if status.Status == "healthy" {
        w.WriteHeader(http.StatusOK)
    } else {
        w.WriteHeader(http.StatusServiceUnavailable)
    }
    json.NewEncoder(w).Encode(status)
}
```

Response:
```json
{
  "status": "healthy",
  "checks": {
    "database": {"status": "healthy"},
    "cache": {"status": "healthy"}
  },
  "version": "1.2.3",
  "uptime": "4h32m15s"
}
```

## Graceful Degradation

Sometimes you can serve traffic even if a dependency is down:

```go
func (h *HealthChecker) ReadinessHandler(w http.ResponseWriter, r *http.Request) {
    ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
    defer cancel()
    
    // Database is critical
    if err := h.db.PingContext(ctx); err != nil {
        http.Error(w, "database unavailable", http.StatusServiceUnavailable)
        return
    }
    
    // Cache is nice-to-have, log but don't fail readiness
    if err := h.cache.Ping(ctx).Err(); err != nil {
        slog.Warn("cache unavailable", "error", err)
        // Don't fail readiness - we can operate without cache
    }
    
    w.WriteHeader(http.StatusOK)
}
```

## Comparing to .NET

.NET's health check system:

```csharp
builder.Services.AddHealthChecks()
    .AddDbContextCheck<AppDbContext>()
    .AddRedis(redisConnectionString)
    .AddCheck("custom", () => HealthCheckResult.Healthy());

app.MapHealthChecks("/healthz");
app.MapHealthChecks("/readyz", new HealthCheckOptions {
    Predicate = check => check.Tags.Contains("ready")
});
```

| Aspect | .NET | Go |
|--------|------|-----|
| Built-in framework | Yes (`IHealthCheck`) | No |
| Dependency injection | Automatic | Manual |
| Pre-built checks | Many (EF, Redis, etc.) | Few libraries |
| Configuration | Options pattern | Manual |
| UI available | Yes (HealthChecksUI) | No |

.NET's health check system is more sophisticated. Go requires manual implementation.

## Health Check Libraries

Some Go libraries help:

**alexliesenfeld/health:**
```go
checker := health.NewChecker(
    health.WithCheck(health.Check{
        Name:    "database",
        Timeout: 2 * time.Second,
        Check:   db.PingContext,
    }),
)

http.Handle("/healthz", health.NewHandler(checker))
```

**hellofresh/health-go:**
```go
h, _ := health.New(health.WithChecks(
    health.Config{
        Name:  "database",
        Check: func(ctx context.Context) error { return db.PingContext(ctx) },
    },
))

http.Handle("/healthz", h.Handler())
```

But honestly, health checks are simple enough that most Go developers write them by hand.

## Best Practices

1. **Keep liveness simple**. Don't check dependencies.
2. **Make readiness reflect reality**. Check what matters for serving traffic.
3. **Use timeouts**. Don't let health checks hang forever.
4. **Return quickly**. Health checks shouldn't be expensive.
5. **Log failures**. Debugging health issues needs information.
6. **Test health checks**. They're code, they can have bugs.

## Kubernetes Configuration

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 15
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /readyz
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 2

startupProbe:
  httpGet:
    path: /startupz
    port: 8080
  initialDelaySeconds: 0
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 30  # 30 * 5s = 2.5 minutes max startup
```

## The Honest Take

Health checks aren't glamorous, but they're essential for production reliability.

**What Go does well:**
- Simple to implement
- Full control over logic
- Fast checks (no framework overhead)

**What .NET does better:**
- Built-in framework
- Pre-built checks for common dependencies
- UI for monitoring
- Better integration with DI

**The verdict:**
Go makes you write health checks yourself. That's fine. They're not complicated. The patterns are the same in any language: liveness for "am I stuck?", readiness for "can I serve traffic?".

Get these right and your services will be resilient. Get them wrong and you'll have restart loops and cascading failures.

---

*Next up: GitHub Actions for Go. CI/CD with testing, linting, and releasing.*
