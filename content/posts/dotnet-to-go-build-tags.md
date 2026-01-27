+++
title = "Shrinking Binaries and Build Tags"
date = "2025-01-05"
draft = false
tags = ["go", "dotnet", "deployment", "build-tags", "csharp"]
series = ["step-over-to-go"]
+++

Go binaries are already small compared to .NET self-contained deployments. But sometimes you want smaller: Lambda deployments, embedded systems, or just because.

Let's look at `ldflags` for stripping binaries and build tags for conditional compilation.

## Stripping with ldflags

The simplest optimisation:

```bash
go build -ldflags="-s -w" -o myapp
```

| Flag | Effect | Size Impact |
|------|--------|-------------|
| `-s` | Strip symbol table | ~15-20% smaller |
| `-w` | Strip DWARF debug info | ~10-15% smaller |

Combined, you might see 25-30% reduction.

Before:
```bash
go build -o myapp && ls -lh myapp
# 14M myapp
```

After:
```bash
go build -ldflags="-s -w" -o myapp && ls -lh myapp
# 10M myapp
```

### Embedding Version Information

Use `ldflags` to set variables at build time:

```go
// main.go
package main

var (
    version   = "dev"
    commit    = "none"
    buildTime = "unknown"
)

func main() {
    fmt.Printf("Version: %s, Commit: %s, Built: %s\n", version, commit, buildTime)
}
```

Build with values:

```bash
go build -ldflags="-s -w \
  -X main.version=1.2.3 \
  -X main.commit=$(git rev-parse --short HEAD) \
  -X main.buildTime=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  -o myapp
```

Now `myapp --version` shows real build info, baked in at compile time.

## Build Tags: Conditional Compilation

Build tags let you include/exclude files based on conditions. It's Go's equivalent to `#if DEBUG` or conditional compilation symbols.

### File-Level Tags

Add a comment at the top of a file:

```go
//go:build linux

package main

// This file only compiles on Linux
func platformSpecificSetup() {
    // Linux-specific code
}
```

Or exclude a platform:

```go
//go:build !windows

package main

// This file compiles everywhere except Windows
```

### Combining Tags

```go
//go:build linux && amd64

// Only Linux on x86-64
```

```go
//go:build linux || darwin

// Linux or macOS
```

```go
//go:build !cgo

// Only when CGO is disabled
```

### Custom Build Tags

Define your own:

```go
//go:build premium

package features

func PremiumFeatures() {
    // Only in premium builds
}
```

Build with:

```bash
go build -tags premium -o myapp-premium
```

Without the tag, files marked `//go:build premium` are excluded.

### Common Use Cases

**Debug vs Production:**

```go
//go:build debug

package main

func init() {
    log.SetLevel(log.DebugLevel)
}
```

```go
//go:build !debug

package main

func init() {
    log.SetLevel(log.InfoLevel)
}
```

**Feature Flags:**

```go
//go:build enterprise

package auth

func SSOLogin() { ... }
```

**Platform-Specific Implementations:**

```
mypackage/
├── file.go           // shared code
├── file_linux.go     // Linux-specific
├── file_windows.go   // Windows-specific
└── file_darwin.go    // macOS-specific
```

Go automatically selects by filename suffix: `_linux.go`, `_windows.go`, `_darwin.go`, `_amd64.go`, `_arm64.go`.

## UPX Compression (Controversial)

UPX compresses executables:

```bash
go build -ldflags="-s -w" -o myapp
upx --best myapp
```

Before UPX: 10MB
After UPX: 3MB

Sounds great, but:
- Slower startup (decompression)
- Some virus scanners flag UPX-packed binaries
- Can interfere with debugging
- Memory usage increases at runtime

Most Go developers skip UPX. The uncompressed binary is usually small enough.

## Trimpath for Reproducibility

Remove local paths from the binary:

```bash
go build -trimpath -o myapp
```

Without `-trimpath`, stack traces contain your local paths:

```
/Users/alice/projects/myapp/main.go:42
```

With `-trimpath`:

```
myapp/main.go:42
```

Cleaner error messages and reproducible builds.

## Comparing to .NET

| Feature | .NET | Go |
|---------|------|-----|
| Strip debug info | PublishTrimmed | `-ldflags="-s -w"` |
| Conditional compilation | `#if DEBUG` | Build tags |
| Platform-specific | Runtime checks or #if | File suffixes |
| Build-time variables | MSBuild properties | `-X main.var=value` |
| IL trimming | PublishTrimmed | N/A (no IL) |

.NET's trimming is more complex because it's trimming IL and dependencies. Go doesn't have this problem. It compiles to native code and includes only what's used.

## A Complete Production Build

```bash
#!/bin/bash

VERSION=$(git describe --tags --always --dirty)
COMMIT=$(git rev-parse --short HEAD)
BUILD_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)

go build \
  -trimpath \
  -ldflags="-s -w \
    -X main.version=$VERSION \
    -X main.commit=$COMMIT \
    -X main.buildTime=$BUILD_TIME" \
  -o myapp \
  ./cmd/server
```

This produces:
- Stripped binary (smaller)
- No local paths (reproducible)
- Version info embedded (debuggable in production)

## Build Tags in Practice

A common pattern for different build configurations:

```
cmd/server/
├── main.go
├── config_dev.go      //go:build dev
├── config_prod.go     //go:build !dev
```

config_dev.go:
```go
//go:build dev

package main

var defaultConfig = Config{
    LogLevel: "debug",
    Database: "localhost:5432",
}
```

config_prod.go:
```go
//go:build !dev

package main

var defaultConfig = Config{
    LogLevel: "info",
    Database: "",  // must be set via env
}
```

Build:
```bash
go build -tags dev -o myapp-dev   # includes config_dev.go
go build -o myapp                  # includes config_prod.go
```

## The Honest Take

Go's build customisation is simpler than .NET's MSBuild system.

**What Go does well:**
- Simple ldflags for common needs
- Build tags are straightforward
- File suffixes for platform code
- Fast rebuilds

**What .NET does better:**
- More sophisticated trimming
- Rich MSBuild conditionals
- Better IDE support for conditional code
- Source generators for build-time code

**The verdict:**
For most cases, `-ldflags="-s -w"` and maybe a build tag or two is all you need. Go's simplicity means less configuration and fewer surprises.

If you're coming from complex MSBuild configurations, you might miss the flexibility. But you probably won't miss the complexity.

---

*Next up: Dockerfiles for Go. Multi-stage builds, scratch images, and why Go containers are so small.*
