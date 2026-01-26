+++
title = "Kubernetes and Go: A Natural Fit"
date = "2025-01-05"
draft = false
tags = ["go", "dotnet", "kubernetes", "containers", "csharp"]
+++

Kubernetes is written in Go. The CLI tools are Go. The ecosystem is Go. Running Go services on Kubernetes feels natural. The patterns align.

But there are things you need to get right: health checks, graceful shutdown, resource limits. Let's cover what Kubernetes expects and how Go delivers it.

## Health Checks: Liveness and Readiness

Kubernetes uses probes to manage your containers:

- **Liveness**: Is the process alive? Restart if not.
- **Readiness**: Can it serve traffic? Remove from load balancer if not.
- **Startup**: Has it finished starting? (For slow-starting apps)

### Implementing Health Endpoints

```go
package main

import (
    "net/http"
    "sync/atomic"
)

var ready atomic.Bool

func main() {
    // Health endpoints
    http.HandleFunc("/healthz", healthzHandler)   // liveness
    http.HandleFunc("/readyz", readyzHandler)     // readiness
    
    // Your app routes
    http.HandleFunc("/", appHandler)
    
    // Start background initialization
    go func() {
        initializeApp()
        ready.Store(true)
    }()
    
    http.ListenAndServe(":8080", nil)
}

func healthzHandler(w http.ResponseWriter, r *http.Request) {
    // Liveness: can we respond at all?
    w.WriteHeader(http.StatusOK)
    w.Write([]byte("ok"))
}

func readyzHandler(w http.ResponseWriter, r *http.Request) {
    // Readiness: are we ready to serve traffic?
    if ready.Load() {
        w.WriteHeader(http.StatusOK)
        w.Write([]byte("ok"))
    } else {
        w.WriteHeader(http.StatusServiceUnavailable)
        w.Write([]byte("not ready"))
    }
}
```

### Kubernetes Manifest

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: myapp
        image: myapp:latest
        ports:
        - containerPort: 8080
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /readyz
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "64Mi"
            cpu: "100m"
          limits:
            memory: "128Mi"
            cpu: "500m"
```

## Graceful Shutdown

When Kubernetes wants to stop your pod, it sends SIGTERM. You have `terminationGracePeriodSeconds` (default 30) to finish in-flight requests before SIGKILL.

```go
package main

import (
    "context"
    "log"
    "net/http"
    "os"
    "os/signal"
    "syscall"
    "time"
)

func main() {
    srv := &http.Server{
        Addr:    ":8080",
        Handler: router(),
    }
    
    // Start server in goroutine
    go func() {
        log.Printf("Starting server on %s", srv.Addr)
        if err := srv.ListenAndServe(); err != http.ErrServerClosed {
            log.Fatalf("Server error: %v", err)
        }
    }()
    
    // Wait for shutdown signal
    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
    <-quit
    
    log.Println("Shutting down server...")
    
    // Give in-flight requests time to complete
    ctx, cancel := context.WithTimeout(context.Background(), 25*time.Second)
    defer cancel()
    
    if err := srv.Shutdown(ctx); err != nil {
        log.Fatalf("Server shutdown error: %v", err)
    }
    
    log.Println("Server stopped")
}
```

### The Shutdown Sequence

1. Kubernetes sends SIGTERM
2. Kubernetes removes pod from Service endpoints (readiness fails)
3. Your app stops accepting new connections
4. In-flight requests complete (or timeout)
5. If not done in grace period, SIGKILL

### Coordinating with Readiness

Stop being ready before shutdown completes:

```go
var (
    ready    atomic.Bool
    stopping atomic.Bool
)

func readyzHandler(w http.ResponseWriter, r *http.Request) {
    if ready.Load() && !stopping.Load() {
        w.WriteHeader(http.StatusOK)
    } else {
        w.WriteHeader(http.StatusServiceUnavailable)
    }
}

func main() {
    // ... setup ...
    
    <-quit
    stopping.Store(true)  // Stop readiness immediately
    
    // Wait a moment for Kubernetes to update endpoints
    time.Sleep(5 * time.Second)
    
    // Then shutdown
    srv.Shutdown(ctx)
}
```

## Resource Limits

Go respects container resource limits automatically since Go 1.19:

```go
import "runtime"

func main() {
    // GOMAXPROCS is set automatically based on CPU limits
    log.Printf("GOMAXPROCS: %d", runtime.GOMAXPROCS(0))
}
```

For memory, Go's GC works within limits, but can still OOM. Set appropriate limits:

```yaml
resources:
  requests:
    memory: "64Mi"
    cpu: "100m"
  limits:
    memory: "128Mi"
    cpu: "500m"
```

Go apps are typically memory-efficient. Start small, increase based on actual usage.

## Configuration via ConfigMaps and Secrets

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: myapp-config
data:
  LOG_LEVEL: "info"
  MAX_CONNECTIONS: "100"
---
apiVersion: v1
kind: Secret
metadata:
  name: myapp-secrets
type: Opaque
stringData:
  DATABASE_URL: "postgres://..."
---
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
      - name: myapp
        envFrom:
        - configMapRef:
            name: myapp-config
        - secretRef:
            name: myapp-secrets
```

Your Go app reads environment variables:

```go
logLevel := os.Getenv("LOG_LEVEL")
dbURL := os.Getenv("DATABASE_URL")
```

## A Complete Example

```go
package main

import (
    "context"
    "log/slog"
    "net/http"
    "os"
    "os/signal"
    "sync/atomic"
    "syscall"
    "time"
)

var ready atomic.Bool

func main() {
    logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
    slog.SetDefault(logger)
    
    mux := http.NewServeMux()
    
    // Health endpoints
    mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, r *http.Request) {
        w.WriteHeader(http.StatusOK)
    })
    mux.HandleFunc("GET /readyz", func(w http.ResponseWriter, r *http.Request) {
        if ready.Load() {
            w.WriteHeader(http.StatusOK)
        } else {
            w.WriteHeader(http.StatusServiceUnavailable)
        }
    })
    
    // App routes
    mux.HandleFunc("GET /", func(w http.ResponseWriter, r *http.Request) {
        w.Write([]byte("Hello from Kubernetes!"))
    })
    
    srv := &http.Server{
        Addr:    ":8080",
        Handler: mux,
    }
    
    // Start server
    go func() {
        slog.Info("starting server", "addr", srv.Addr)
        if err := srv.ListenAndServe(); err != http.ErrServerClosed {
            slog.Error("server error", "error", err)
            os.Exit(1)
        }
    }()
    
    // Initialization (simulate startup work)
    time.Sleep(2 * time.Second)
    ready.Store(true)
    slog.Info("ready to serve traffic")
    
    // Wait for shutdown
    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
    <-quit
    
    slog.Info("shutdown signal received")
    ready.Store(false)
    
    // Grace period for endpoint updates
    time.Sleep(5 * time.Second)
    
    ctx, cancel := context.WithTimeout(context.Background(), 25*time.Second)
    defer cancel()
    
    if err := srv.Shutdown(ctx); err != nil {
        slog.Error("shutdown error", "error", err)
    }
    
    slog.Info("server stopped")
}
```

## Comparing to .NET

| Aspect | .NET | Go |
|--------|------|-----|
| Health checks | `IHealthCheck` interface | HTTP handlers |
| Graceful shutdown | `IHostedService` lifecycle | Signal handling |
| Resource awareness | Manual GOMAXPROCS | Automatic (Go 1.19+) |
| Container size | 200MB+ | 10-15MB |
| Startup time | 1-2 seconds | <100ms |

.NET has more framework support for health checks. Go requires manual implementation but it's trivial.

## The Honest Take

Go and Kubernetes work well together. They're from the same ecosystem.

**What Go does well:**
- Fast startup (important for scaling)
- Small images (fast pulls)
- Low memory usage
- Automatic GOMAXPROCS
- Native signal handling

**What .NET does better:**
- `IHealthCheck` abstraction
- Richer hosted service lifecycle
- Better DI integration
- ASP.NET Core middleware patterns

**The verdict:**
For Kubernetes workloads, Go's operational characteristics are excellent. Fast startup means fast scaling. Small images mean fast deployment. Low resource usage means efficient clusters.

The patterns shown here (health endpoints, graceful shutdown, signal handling) are the same patterns you'd use in any language. Go just makes them explicit.

---

*Next up: observability with OpenTelemetry. Metrics, traces, and logs for production Go services.*
