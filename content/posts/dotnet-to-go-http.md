+++
title = "HTTP Services: net/http vs ASP.NET Core"
date = "2025-01-04"
draft = false
tags = ["go", "dotnet", "http", "web", "csharp"]
+++

ASP.NET Core is a sophisticated web framework. Dependency injection, middleware pipelines, model binding, routing with attributes, OpenAPI generation... it does a lot for you.

Go's `net/http` is a standard library package. It does HTTP. That's about it.

This sounds like a step down. It is, in some ways. But there's power in simplicity, and Go's HTTP story is more capable than it first appears.

## The Simplest Server

Go:

```go
package main

import (
    "fmt"
    "net/http"
)

func main() {
    http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
        fmt.Fprintf(w, "Hello, World!")
    })
    
    http.ListenAndServe(":8080", nil)
}
```

C# minimal API:

```csharp
var app = WebApplication.Create();
app.MapGet("/", () => "Hello, World!");
app.Run();
```

C#'s is shorter. But Go's has zero dependencies, zero configuration, and zero framework magic.

## Handlers: The Building Block

In ASP.NET Core, you have controllers, minimal API delegates, or Razor Pages. In Go, you have handlers.

A handler is anything that implements `http.Handler`:

```go
type Handler interface {
    ServeHTTP(ResponseWriter, *Request)
}
```

One method. That's it.

```go
type HelloHandler struct {
    greeting string
}

func (h HelloHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
    fmt.Fprintf(w, "%s, visitor!", h.greeting)
}

func main() {
    http.Handle("/hello", HelloHandler{greeting: "Welcome"})
    http.ListenAndServe(":8080", nil)
}
```

Or use `http.HandlerFunc` for simpler cases:

```go
http.HandleFunc("/hello", func(w http.ResponseWriter, r *http.Request) {
    fmt.Fprintf(w, "Hello!")
})
```

## Request and Response

The `*http.Request` contains everything about the incoming request:

```go
func handler(w http.ResponseWriter, r *http.Request) {
    // Method
    method := r.Method  // "GET", "POST", etc.
    
    // URL and path
    path := r.URL.Path
    query := r.URL.Query().Get("id")
    
    // Headers
    contentType := r.Header.Get("Content-Type")
    
    // Body
    body, _ := io.ReadAll(r.Body)
    defer r.Body.Close()
    
    // Form data
    r.ParseForm()
    name := r.FormValue("name")
    
    // Context (for cancellation, deadlines, values)
    ctx := r.Context()
}
```

The `http.ResponseWriter` is how you respond:

```go
func handler(w http.ResponseWriter, r *http.Request) {
    // Set headers (before writing body)
    w.Header().Set("Content-Type", "application/json")
    
    // Set status code (before writing body)
    w.WriteHeader(http.StatusCreated)
    
    // Write body
    w.Write([]byte(`{"status": "ok"}`))
    
    // Or use fmt
    fmt.Fprintf(w, `{"id": %d}`, 123)
}
```

Order matters: headers and status must be set before writing the body.

## Routing: The Weak Spot

Go 1.22 improved the standard library router significantly:

```go
mux := http.NewServeMux()

mux.HandleFunc("GET /users", listUsers)
mux.HandleFunc("POST /users", createUser)
mux.HandleFunc("GET /users/{id}", getUser)      // path parameters!
mux.HandleFunc("DELETE /users/{id}", deleteUser)

http.ListenAndServe(":8080", mux)
```

Access path parameters:

```go
func getUser(w http.ResponseWriter, r *http.Request) {
    id := r.PathValue("id")  // Go 1.22+
    // ...
}
```

Before 1.22, you needed a third-party router. Many projects still use them:

**chi**: lightweight, idiomatic:
```go
r := chi.NewRouter()
r.Get("/users/{id}", getUser)
```

**gorilla/mux**: feature-rich (now maintained by community):
```go
r := mux.NewRouter()
r.HandleFunc("/users/{id}", getUser).Methods("GET")
```

**gin**: fast, popular, framework-like:
```go
r := gin.Default()
r.GET("/users/:id", getUser)
```

If you're starting fresh with Go 1.22+, try the standard library first.

## Middleware

Middleware in Go is just a function that wraps a handler:

```go
func loggingMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        start := time.Now()
        next.ServeHTTP(w, r)
        log.Printf("%s %s %v", r.Method, r.URL.Path, time.Since(start))
    })
}

func authMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        token := r.Header.Get("Authorization")
        if !isValidToken(token) {
            http.Error(w, "Unauthorized", http.StatusUnauthorized)
            return
        }
        next.ServeHTTP(w, r)
    })
}
```

Chain them:

```go
handler := loggingMiddleware(authMiddleware(myHandler))
http.Handle("/api/", handler)
```

Compare to ASP.NET Core:

```csharp
app.UseLogging();
app.UseAuthentication();
app.MapControllers();
```

Go's is more manual but the pattern is explicit.

## Comparing to ASP.NET Core

| Feature | ASP.NET Core | Go net/http |
|---------|--------------|-------------|
| DI | Built-in | Manual or wire |
| Routing | Attribute or minimal | Method + path (1.22+) |
| Model binding | Automatic | Manual (JSON decode) |
| Validation | DataAnnotations | Manual or validator lib |
| Middleware | Pipeline | Function wrapping |
| OpenAPI | Swashbuckle | Third-party (swag, etc.) |
| Auth | Identity, policies | Manual or third-party |
| Config | IConfiguration | Environment or libs |

ASP.NET Core does more out of the box. Go makes you build it yourself or choose libraries.

## A Realistic Handler

Here's what a real handler looks like:

```go
type UserHandler struct {
    repo UserRepository
}

func (h *UserHandler) GetUser(w http.ResponseWriter, r *http.Request) {
    id := r.PathValue("id")
    
    user, err := h.repo.FindByID(r.Context(), id)
    if err != nil {
        if errors.Is(err, ErrNotFound) {
            http.Error(w, "User not found", http.StatusNotFound)
            return
        }
        http.Error(w, "Internal error", http.StatusInternalServerError)
        return
    }
    
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(user)
}

func (h *UserHandler) CreateUser(w http.ResponseWriter, r *http.Request) {
    var input CreateUserRequest
    if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
        http.Error(w, "Invalid JSON", http.StatusBadRequest)
        return
    }
    
    // Validation
    if input.Email == "" {
        http.Error(w, "Email required", http.StatusBadRequest)
        return
    }
    
    user, err := h.repo.Create(r.Context(), input)
    if err != nil {
        http.Error(w, "Failed to create user", http.StatusInternalServerError)
        return
    }
    
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusCreated)
    json.NewEncoder(w).Encode(user)
}
```

More code than an ASP.NET Core controller. But you can see exactly what's happening.

## Graceful Shutdown

Something ASP.NET Core handles automatically that Go requires explicitly:

```go
func main() {
    srv := &http.Server{
        Addr:    ":8080",
        Handler: router,
    }
    
    go func() {
        if err := srv.ListenAndServe(); err != http.ErrServerClosed {
            log.Fatalf("listen: %v", err)
        }
    }()
    
    // Wait for interrupt signal
    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
    <-quit
    
    // Graceful shutdown with timeout
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()
    
    if err := srv.Shutdown(ctx); err != nil {
        log.Fatalf("shutdown: %v", err)
    }
    
    log.Println("Server stopped")
}
```

## The Honest Take

ASP.NET Core is a full-featured web framework. Go's `net/http` is a building block.

**What Go does better:**
- Simple mental model
- No framework lock-in
- Explicit control over everything
- Very fast startup
- Small binaries

**What ASP.NET Core does better:**
- Batteries included
- Model binding and validation
- Authentication/authorization
- OpenAPI generation
- Richer middleware ecosystem

**The verdict:**
For simple services, `net/http` is delightfully straightforward. For complex APIs with lots of endpoints, validation, and documentation needs, you'll either write a lot of code or reach for a framework like Gin or Echo.

Neither is wrong. Go gives you the choice that ASP.NET Core makes for you.

---

*Next up: JSON handling. Struct tags, marshalling, and why it's more manual than Newtonsoft.*
