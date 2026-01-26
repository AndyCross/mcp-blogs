+++
title = "Single Binary Deploys: The Killer Feature"
date = "2025-01-05"
draft = false
tags = ["go", "dotnet", "deployment", "cross-compilation", "csharp"]
+++

What sold me on Go for production: you build a binary, you copy it to a server, you run it. No runtime to install. No framework version matching. No dependency hell. Just a file.

If you've ever dealt with .NET runtime versioning on servers, or debugged why `dotnet` can't find the right SDK, or explained to ops why they need to install framework X before deploying your app, Go's deployment model will feel like a revelation.

## The .NET Deployment Model

In .NET, you have choices:

**Framework-dependent (FDD)**:
```bash
dotnet publish -c Release
# Produces DLLs, needs .NET runtime on target
```

Small output, but requires runtime installation and version matching.

**Self-contained (SCD)**:
```bash
dotnet publish -c Release --self-contained -r linux-x64
# Produces executable + runtime + dependencies
# ~70MB+ for a simple API
```

Everything included, but large.

**Single-file**:
```bash
dotnet publish -c Release --self-contained -r linux-x64 -p:PublishSingleFile=true
# Extracts to temp on first run
```

One file, but it's a bundle that extracts itself.

**Native AOT** (.NET 7+):
```bash
dotnet publish -c Release -r linux-x64 -p:PublishAot=true
# True native binary, ~10-30MB
```

Finally a real binary, but limited reflection support.

## The Go Model: Just Build

```bash
go build -o myapp ./cmd/server
```

That's it. `myapp` is a statically-linked binary. Copy it anywhere with the same OS/architecture and run it.

```bash
scp myapp server:/usr/local/bin/
ssh server '/usr/local/bin/myapp'
```

No runtime. No dependencies. No extraction. No installation.

## Cross-Compilation

This is where Go shines. Build for any platform from any platform:

```bash
# From macOS, build for Linux
GOOS=linux GOARCH=amd64 go build -o myapp-linux

# Build for Windows
GOOS=windows GOARCH=amd64 go build -o myapp.exe

# Build for ARM (Raspberry Pi, AWS Graviton)
GOOS=linux GOARCH=arm64 go build -o myapp-arm64
```

No Docker, no VMs, no cross-compilers to install. Set environment variables, build.

### All Platforms

Common targets:

| GOOS | GOARCH | Target |
|------|--------|--------|
| linux | amd64 | Standard Linux servers |
| linux | arm64 | AWS Graviton, ARM servers |
| darwin | amd64 | Intel Macs |
| darwin | arm64 | Apple Silicon Macs |
| windows | amd64 | Windows servers |

```bash
# Build for all common targets
for os in linux darwin windows; do
  for arch in amd64 arm64; do
    GOOS=$os GOARCH=$arch go build -o myapp-$os-$arch ./cmd/server
  done
done
```

## Static Linking by Default

Go binaries are statically linked by default. No shared library dependencies:

```bash
ldd myapp
# not a dynamic executable
```

Compare to a typical C program:

```bash
ldd /usr/bin/ls
# linux-vdso.so.1
# libselinux.so.1
# libc.so.6
# libpcre2-8.so.0
# ...
```

Static linking means:
- No "works on my machine" due to library versions
- Deploy to minimal containers (scratch, distroless)
- No glibc compatibility concerns

### CGO and Dynamic Linking

The exception is CGO, Go code that calls C libraries:

```go
// #include <sqlite3.h>
import "C"
```

CGO produces dynamically-linked binaries. Disable it if you don't need it:

```bash
CGO_ENABLED=0 go build -o myapp
```

Most pure-Go programs don't need CGO.

## Binary Size

A simple Go HTTP server: ~10-15MB
A typical Go CLI tool: ~5-10MB
A complex service with many dependencies: ~20-30MB

Compare to .NET self-contained: 70-150MB
Compare to .NET Native AOT: 10-30MB

Go binaries are competitive with .NET AOT and much smaller than self-contained.

## Build Reproducibility

Go builds are reproducible by default. Same inputs, same binary:

```bash
go build -o app1 ./cmd/server
go build -o app2 ./cmd/server
sha256sum app1 app2
# Same hash (usually)
```

For guaranteed reproducibility:

```bash
go build -trimpath -ldflags="-s -w" -o myapp
```

- `-trimpath`: removes file paths from binary
- `-s -w`: strips debug info and DWARF

## Deployment Patterns

### Direct Binary Deployment

```bash
# Build
go build -o myapp ./cmd/server

# Deploy
scp myapp server:/opt/myapp/
ssh server 'systemctl restart myapp'
```

Systemd unit file:

```ini
[Unit]
Description=My App
After=network.target

[Service]
Type=simple
ExecStart=/opt/myapp/myapp
Restart=always
Environment=PORT=8080

[Install]
WantedBy=multi-user.target
```

### Tarball Distribution

```bash
# Build and package
go build -o myapp ./cmd/server
tar -czvf myapp-linux-amd64.tar.gz myapp config.yaml

# Distribute
curl -L https://releases.example.com/myapp-linux-amd64.tar.gz | tar xz
./myapp
```

### Container (Preview for Later)

```dockerfile
FROM scratch
COPY myapp /myapp
ENTRYPOINT ["/myapp"]
```

A container with just your binary. We'll cover this properly in the Dockerfile post.

## The Comparison

| Aspect | .NET SCD | .NET AOT | Go |
|--------|----------|----------|-----|
| Binary size | 70-150MB | 10-30MB | 10-20MB |
| Cross-compilation | Limited | Limited | Trivial |
| Runtime required | No | No | No |
| Reflection support | Full | Limited | Full |
| CGO equivalent | P/Invoke | P/Invoke | CGO |
| Build time | Moderate | Slow | Fast |
| Static linking | Optional | Default | Default |

## The Honest Take

Single binary deployment is Go's killer feature for operations.

**What Go does better:**
- Trivial cross-compilation
- Fast builds
- Small binaries by default
- No runtime installation
- Static linking by default

**What .NET does better:**
- .NET AOT is catching up
- Better Windows integration
- Richer ecosystem for some domains
- Native AOT on more platforms (eventually)

**The verdict:**
If deployment simplicity matters (and it should) Go wins. One binary, one target, done. 

Your ops team will thank you. Your deployment scripts will be three lines. Your containers will be tiny. Your CI/CD will be simple.

This is the feature that keeps Go relevant in a world of VMs and containers. Simplicity scales.

---

*Next up: shrinking binaries and build tags. ldflags, conditional compilation, and getting even leaner.*
