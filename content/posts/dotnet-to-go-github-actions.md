+++
title = "GitHub Actions for Go Projects"
date = "2025-01-05"
draft = false
tags = ["go", "dotnet", "ci-cd", "github-actions", "csharp"]
+++

CI/CD for Go projects is refreshingly simple. Fast builds, built-in testing, cross-compilation—everything you need is in the standard toolchain.

Let's set up a proper GitHub Actions workflow.

## Basic Workflow

`.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Go
        uses: actions/setup-go@v5
        with:
          go-version: '1.22'
      
      - name: Download dependencies
        run: go mod download
      
      - name: Test
        run: go test -v ./...
```

That's a working CI pipeline. Test on every push and PR.

## Adding Linting

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'
      
      - name: golangci-lint
        uses: golangci/golangci-lint-action@v4
        with:
          version: latest
```

The golangci-lint action handles caching and configuration.

## Full CI Workflow

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'
      - uses: golangci/golangci-lint-action@v4
        with:
          version: latest

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'
      - run: go test -v -race -coverprofile=coverage.out ./...
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: coverage.out

  build:
    runs-on: ubuntu-latest
    needs: [lint, test]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'
      - run: go build -v ./...
```

Jobs run in parallel where possible. Build only runs after lint and test pass.

## Cross-Platform Testing

Test on multiple OSes:

```yaml
test:
  strategy:
    matrix:
      os: [ubuntu-latest, macos-latest, windows-latest]
      go: ['1.21', '1.22']
  runs-on: ${{ matrix.os }}
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-go@v5
      with:
        go-version: ${{ matrix.go }}
    - run: go test -v ./...
```

## Releasing with GoReleaser

GoReleaser automates release builds. Create `.goreleaser.yaml`:

```yaml
version: 1

builds:
  - env:
      - CGO_ENABLED=0
    goos:
      - linux
      - darwin
      - windows
    goarch:
      - amd64
      - arm64
    ldflags:
      - -s -w
      - -X main.version={{.Version}}
      - -X main.commit={{.Commit}}
      - -X main.date={{.Date}}

archives:
  - format: tar.gz
    name_template: "{{ .ProjectName }}_{{ .Os }}_{{ .Arch }}"
    format_overrides:
      - goos: windows
        format: zip

checksum:
  name_template: 'checksums.txt'

changelog:
  sort: asc
  filters:
    exclude:
      - '^docs:'
      - '^test:'
```

Release workflow:

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'
      
      - name: Run GoReleaser
        uses: goreleaser/goreleaser-action@v5
        with:
          version: latest
          args: release --clean
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Tag a release:
```bash
git tag v1.0.0
git push origin v1.0.0
```

GoReleaser builds binaries for all platforms, creates a GitHub release, and uploads artifacts.

## Docker Image Publishing

```yaml
name: Docker

on:
  push:
    tags:
      - 'v*'

jobs:
  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          push: true
          platforms: linux/amd64,linux/arm64
          tags: |
            ghcr.io/${{ github.repository }}:${{ github.ref_name }}
            ghcr.io/${{ github.repository }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

Multi-arch Docker images published to GitHub Container Registry.

## Caching Dependencies

Go module caching is automatic with `setup-go@v5`:

```yaml
- uses: actions/setup-go@v5
  with:
    go-version: '1.22'
    cache: true  # enabled by default
```

For more control:

```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/.cache/go-build
      ~/go/pkg/mod
    key: ${{ runner.os }}-go-${{ hashFiles('**/go.sum') }}
    restore-keys: |
      ${{ runner.os }}-go-
```

## Comparing to .NET

| Aspect | .NET | Go |
|--------|------|-----|
| Build time | Moderate | Fast |
| Test runner | dotnet test | go test |
| Linting | dotnet format + analyzers | golangci-lint |
| Release tooling | Manual or custom | GoReleaser |
| Cross-compilation | Complex | Trivial |
| Docker build | Multi-stage | Multi-stage |

Go's faster builds mean faster CI. Cross-compilation means simpler release matrices.

## Complete Workflow

Here's everything together:

```yaml
name: CI/CD

on:
  push:
    branches: [main]
    tags: ['v*']
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'
      - uses: golangci/golangci-lint-action@v4

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'
      - run: go test -v -race -coverprofile=coverage.out ./...
      - uses: codecov/codecov-action@v4
        with:
          files: coverage.out

  build:
    runs-on: ubuntu-latest
    needs: [lint, test]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'
      - run: go build -v ./cmd/...

  release:
    if: startsWith(github.ref, 'refs/tags/')
    needs: [build]
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'
      - uses: goreleaser/goreleaser-action@v5
        with:
          version: latest
          args: release --clean
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  docker:
    if: startsWith(github.ref, 'refs/tags/')
    needs: [build]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v5
        with:
          push: true
          platforms: linux/amd64,linux/arm64
          tags: ghcr.io/${{ github.repository }}:${{ github.ref_name }}
```

## The Honest Take

Go CI/CD is simple and fast.

**What Go does well:**
- Fast builds = fast feedback
- Built-in testing and coverage
- Cross-compilation is trivial
- GoReleaser is excellent

**What .NET does better:**
- Richer test output
- Better IDE integration
- More mature release tooling
- NuGet publishing is simpler

**The verdict:**
Setting up CI for Go is straightforward. The standard toolchain does most of what you need. GoReleaser handles releases elegantly.

If you're used to complex MSBuild configurations and NuGet publishing workflows, Go's simplicity is refreshing.

---

*Next up: versioning your modules—semantic versioning, tags, and avoiding dependency hell.*
