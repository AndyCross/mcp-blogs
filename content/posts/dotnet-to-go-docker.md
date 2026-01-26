+++
title = "Dockerfile for Go: Simpler Than You'd Think"
date = "2025-01-05"
draft = false
tags = ["go", "dotnet", "docker", "containers", "csharp"]
+++

Go's static binaries make for tiny Docker images. Where a .NET container might be 200MB+, a Go container can be under 20MB. Sometimes under 10MB.

This isn't just about bragging rights. Smaller images mean faster pulls, faster scaling, smaller attack surface, and lower storage costs.

## The Simplest Dockerfile

```dockerfile
FROM golang:1.22 AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /app/server ./cmd/server

FROM scratch
COPY --from=builder /app/server /server
ENTRYPOINT ["/server"]
```

That's it. A multi-stage build producing a minimal image.

### What's Happening

**Stage 1: Build**
- Start from official Go image
- Copy and download dependencies first (layer caching)
- Copy source and build
- `CGO_ENABLED=0` ensures static linking

**Stage 2: Run**
- `scratch` is an empty image (literally nothing)
- Copy just the binary
- Run it

Result: an image containing only your binary.

## Image Size Comparison

```bash
docker images
REPOSITORY          TAG       SIZE
myapp-go            latest    12MB
myapp-dotnet-aot    latest    45MB
myapp-dotnet-scd    latest    210MB
```

Go with scratch: ~10-15MB
.NET AOT: ~40-80MB
.NET self-contained: ~200-300MB

## The scratch vs distroless Decision

### scratch

Literally empty. No shell, no utilities, no nothing.

```dockerfile
FROM scratch
COPY myapp /myapp
ENTRYPOINT ["/myapp"]
```

Pros:
- Smallest possible
- Minimal attack surface
- Nothing to exploit

Cons:
- No shell for debugging (`docker exec` won't help)
- No CA certificates (HTTPS fails)
- No timezone data

### distroless

Google's minimal images, just enough to run binaries:

```dockerfile
FROM gcr.io/distroless/static-debian12
COPY myapp /myapp
ENTRYPOINT ["/myapp"]
```

Pros:
- Includes CA certificates
- Includes timezone data
- Still very small (~2MB base)
- Some debugging possible

Cons:
- Slightly larger than scratch
- Still no shell

### alpine

Minimal Linux with shell:

```dockerfile
FROM alpine:3.19
RUN apk add --no-cache ca-certificates tzdata
COPY myapp /myapp
ENTRYPOINT ["/myapp"]
```

Pros:
- Has a shell
- Easy debugging
- Package manager available
- ~5MB base

Cons:
- Uses musl libc (usually fine for Go)
- Larger than scratch/distroless
- More attack surface

## A Production Dockerfile

```dockerfile
# Build stage
FROM golang:1.22-alpine AS builder

WORKDIR /app

# Dependencies first for layer caching
COPY go.mod go.sum ./
RUN go mod download

# Copy source
COPY . .

# Build with optimizations
ARG VERSION=dev
ARG COMMIT=unknown
RUN CGO_ENABLED=0 GOOS=linux go build \
    -trimpath \
    -ldflags="-s -w -X main.version=${VERSION} -X main.commit=${COMMIT}" \
    -o server ./cmd/server

# Runtime stage
FROM gcr.io/distroless/static-debian12

# Copy binary
COPY --from=builder /app/server /server

# Copy any config files needed
COPY --from=builder /app/config.yaml /config.yaml

# Non-root user (distroless provides nonroot user)
USER nonroot:nonroot

EXPOSE 8080

ENTRYPOINT ["/server"]
```

### Build It

```bash
docker build \
  --build-arg VERSION=$(git describe --tags) \
  --build-arg COMMIT=$(git rev-parse --short HEAD) \
  -t myapp:latest .
```

## Handling HTTPS and Certificates

If your app makes HTTPS calls, you need CA certificates.

**Option 1: distroless (includes them)**
```dockerfile
FROM gcr.io/distroless/static-debian12
```

**Option 2: Copy from builder**
```dockerfile
FROM scratch
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
```

**Option 3: alpine base**
```dockerfile
FROM alpine:3.19
RUN apk add --no-cache ca-certificates
```

## Timezone Data

Go needs timezone data for `time.LoadLocation()`:

**Option 1: distroless (includes it)**

**Option 2: Embed in binary** (Go 1.15+)
```go
import _ "time/tzdata"
```

Adds ~500KB to binary but works everywhere.

**Option 3: Copy from builder**
```dockerfile
COPY --from=builder /usr/share/zoneinfo /usr/share/zoneinfo
```

## Layer Caching Strategy

Order your Dockerfile for maximum cache hits:

```dockerfile
# 1. Base image (rarely changes)
FROM golang:1.22 AS builder

# 2. Dependencies (change occasionally)
COPY go.mod go.sum ./
RUN go mod download

# 3. Source code (changes frequently)
COPY . .

# 4. Build
RUN go build -o /app ./cmd/server
```

If only your source changes, steps 1-2 are cached.

## Comparing to .NET Dockerfiles

.NET self-contained:
```dockerfile
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY *.csproj ./
RUN dotnet restore
COPY . .
RUN dotnet publish -c Release -o /app --self-contained -r linux-x64

FROM mcr.microsoft.com/dotnet/runtime-deps:8.0
COPY --from=build /app .
ENTRYPOINT ["./MyApp"]
```

Result: 200MB+ image

.NET AOT:
```dockerfile
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY . .
RUN dotnet publish -c Release -r linux-x64 -p:PublishAot=true -o /app

FROM mcr.microsoft.com/dotnet/runtime-deps:8.0
COPY --from=build /app .
ENTRYPOINT ["./MyApp"]
```

Result: 50-80MB image (better, but still needs runtime-deps base)

Go:
```dockerfile
FROM golang:1.22 AS build
COPY . .
RUN CGO_ENABLED=0 go build -o /app

FROM scratch
COPY --from=build /app /app
ENTRYPOINT ["/app"]
```

Result: 10-15MB image

## Docker Compose for Development

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgres://postgres:secret@db:5432/myapp
    depends_on:
      - db

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: myapp
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

## The Honest Take

Go + Docker is a perfect match.

**What Go does better:**
- Static binaries → scratch/distroless
- Small images by default
- No runtime to include
- Fast builds in containers

**What .NET does... differently:**
- Runtime-deps base required
- Larger images even with AOT
- More complex Dockerfiles
- But better Windows container support

**The verdict:**
If container size and simplicity matter, Go wins decisively. A 10MB image that starts instantly is operationally simpler than a 200MB image, especially at scale.

This is one of Go's genuine strengths. Embrace it.

---

*Next up: AWS Lambda and Go. Serverless without the cold start tax.*
