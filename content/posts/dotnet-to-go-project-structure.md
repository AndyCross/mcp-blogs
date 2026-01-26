+++
title = "Organising a Real Project"
date = "2025-01-03"
draft = false
tags = ["go", "dotnet", "project-structure", "packages", "csharp"]
+++

So you've got the basics. You can write Go code. Now you need to organise it into something that won't become a tangled mess in six months.

Go has opinions about project structure. Some are enforced by the compiler. Some are conventions so universal they might as well be enforced. Coming from .NET's solution/project/namespace hierarchy, Go's flat package model takes adjustment.

Let's figure out how to structure a real project.

## The Mental Model Shift

In C#, you think in layers:

```
Solution (MySolution.sln)
  └── Project (MyApp.csproj)
        └── Namespace (MyApp.Services)
              └── Class (UserService.cs)
```

In Go, it's flatter:

```
Module (go.mod)
  └── Package (directory)
        └── Files (*.go)
```

There's no solution concept. No `.csproj` files. A module is a collection of packages, and packages are directories. That's it.

## Package Basics

A package is a directory. Every `.go` file in that directory must have the same `package` declaration:

```
myproject/
├── go.mod
├── main.go           // package main
└── user/
    ├── user.go       // package user
    └── validation.go // package user (same package!)
```

All files in `user/` share the same package namespace. They can access each other's unexported (lowercase) identifiers. It's like they're all one file, split for organisation.

### Package vs Directory Name

By convention, the package name matches the directory name:

```go
// In directory "user/"
package user  // matches directory name
```

You *can* name them differently, but don't. It confuses everyone.

### Importing

Import paths are relative to the module root:

```go
// go.mod says: module github.com/myname/myproject

import "github.com/myname/myproject/user"

func main() {
    u := user.New("Alice")  // user is the package name
}
```

## A Real Project Layout

Here's a layout that works for most non-trivial projects:

```
myproject/
├── go.mod
├── go.sum
├── main.go                 // or cmd/myapp/main.go
├── internal/
│   ├── config/
│   │   └── config.go
│   ├── database/
│   │   ├── database.go
│   │   └── migrations.go
│   └── handlers/
│       ├── user.go
│       └── product.go
├── pkg/
│   └── validation/
│       └── validation.go
└── api/
    └── openapi.yaml
```

Let's break this down.

### `internal/`: The Privacy Fence

The `internal` directory is magic. The Go compiler enforces that packages under `internal/` can only be imported by code rooted at the parent of `internal/`.

```
myproject/
├── internal/
│   └── secret/       // only myproject can import this
└── cmd/
    └── myapp/
        └── main.go   // can import internal/secret
```

If someone else imports your module, they *cannot* import `internal/secret`. The compiler refuses.

This is Go's answer to `internal` visibility in C#. Use it for implementation details you don't want to be part of your public API.

### `pkg/`: Exportable Packages (Convention)

The `pkg/` directory is purely convention (not enforced). It signals "these packages are intended for external use."

```
myproject/
├── internal/         // private
└── pkg/              // public (by convention)
    └── validation/   // anyone can import this
```

Some projects skip `pkg/` and put public packages at the root. Both are fine. Just be consistent.

### `cmd/`: Multiple Binaries

If your module produces multiple executables:

```
myproject/
├── cmd/
│   ├── server/
│   │   └── main.go   // builds to 'server' binary
│   └── cli/
│       └── main.go   // builds to 'cli' binary
└── internal/
    └── shared/       // shared by both
```

Build with:

```bash
go build ./cmd/server
go build ./cmd/cli
```

### No `src/` Directory

Coming from Java or older Go (GOPATH era), you might want a `src/` directory. Don't. Modern Go modules don't use it. Put your code at the root.

## Avoiding Circular Dependencies

Go doesn't allow circular imports. If package A imports package B, package B cannot import package A. The compiler rejects it.

This is different from C#, where circular references between projects are blocked but classes within a project can reference each other freely.

### The Problem

```
myproject/
├── user/
│   └── user.go       // imports "myproject/order"
└── order/
    └── order.go      // imports "myproject/user" - COMPILE ERROR
```

### Solutions

**1. Extract shared types to a third package:**

```
myproject/
├── user/
│   └── user.go       // imports "myproject/models"
├── order/
│   └── order.go      // imports "myproject/models"
└── models/
    └── models.go     // shared types, imports neither
```

**2. Use interfaces at boundaries:**

```go
// order/order.go
package order

type UserGetter interface {
    GetUser(id string) (*User, error)
}

type OrderService struct {
    users UserGetter  // interface, not concrete user.Service
}
```

Now `order` doesn't import `user`. It depends on an interface that `user.Service` happens to implement.

**3. Merge packages:**

Sometimes the cycle means the packages are too closely related to be separate. Merge them.

## Package Design Principles

### Small, Focused Packages

Go encourages small packages with clear responsibilities. Not one giant `utils` package.

```
// BAD
utils/
├── string_helpers.go
├── http_helpers.go
├── database_helpers.go
└── random_stuff.go

// BETTER
stringutil/
    └── stringutil.go
httputil/
    └── httputil.go
database/
    └── helpers.go
```

### Name Packages by What They Provide

Package names should be nouns describing what they provide:

```
// GOOD
http, json, user, config, database

// BAD  
helpers, utils, common, misc
```

### Avoid Stutter

The package name is part of the identifier when used:

```go
// BAD - stutters
user.UserService
http.HTTPClient
config.ConfigLoader

// GOOD - no stutter
user.Service
http.Client
config.Loader
```

### One Package, One Purpose

Each package should have a single, clear purpose. If you're struggling to name it, it might be doing too much.

## Comparing to C# Project Structure

| C# | Go |
|-----|-----|
| Solution (`.sln`) | Module (`go.mod`) |
| Project (`.csproj`) | Package (directory) |
| Namespace | Package |
| `internal` modifier | `internal/` directory |
| Folder structure | Package structure (folders = packages) |
| Circular project refs blocked | Circular imports blocked |
| Multiple assemblies | Multiple packages |
| Multiple executables | `cmd/` subdirectories |

## A Practical Example

Let's say you're building an API server. Here's how I'd structure it:

```
myapi/
├── go.mod
├── go.sum
├── main.go                      // entry point, wires things up
├── internal/
│   ├── api/
│   │   ├── router.go            // HTTP routing
│   │   ├── middleware.go        // auth, logging, etc.
│   │   └── handlers/
│   │       ├── users.go
│   │       └── products.go
│   ├── domain/
│   │   ├── user.go              // User type and business logic
│   │   └── product.go
│   ├── repository/
│   │   ├── user_repo.go         // database operations
│   │   └── product_repo.go
│   └── config/
│       └── config.go
├── pkg/
│   └── response/
│       └── response.go          // shared API response types
└── migrations/
    └── 001_initial.sql
```

- `internal/` keeps implementation details private
- `domain/` has business types with no external dependencies
- `repository/` handles persistence
- `api/handlers/` maps HTTP to domain operations
- `pkg/response/` is a utility others could use

## The Honest Take

Go's package system is simpler than C#'s project/namespace hierarchy. That simplicity is mostly good: less configuration, clearer structure.

**What Go does better:**
- `internal/` is enforced by the compiler, not convention
- No `.csproj` files to manage
- Package = directory is clear and simple
- Forced to avoid circular dependencies

**What C# does better:**
- Namespaces can span multiple assemblies
- More flexibility in organisation
- Better tooling for refactoring package structure
- Multiple classes per file without namespace issues

**The verdict:**
Go's constraints push you toward better design. No circular dependencies means you think about boundaries upfront. `internal/` enforced by the compiler means you actually use it.

It's more restrictive, but those restrictions prevent the spaghetti that large C# solutions sometimes become.

---

*Next up: multi-module repos. When you need more than one `go.mod` and how to think about monorepo structure in Go.*
