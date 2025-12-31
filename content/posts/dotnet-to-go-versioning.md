+++
title = "Versioning Your Modules"
date = "2025-01-05"
draft = false
tags = ["go", "dotnet", "versioning", "modules", "csharp"]
+++

Versioning in Go is simple in concept—semantic versioning with git tags—but has quirks that'll catch you if you're coming from NuGet's more flexible model.

Let's cover how to version your modules properly.

## Basic Versioning

Go modules use semantic versioning: `vMAJOR.MINOR.PATCH`

```
v1.0.0  - initial stable release
v1.1.0  - new features, backward compatible
v1.1.1  - bug fixes
v2.0.0  - breaking changes
```

Version with git tags:

```bash
git tag v1.0.0
git push origin v1.0.0
```

That's it. No version numbers in code, no configuration files to update.

## The Module Path and Major Versions

Here's Go's unique aspect: **major versions v2+ change the module path**.

```go
// v1.x
module github.com/myname/mylib

// v2.x
module github.com/myname/mylib/v2

// v3.x
module github.com/myname/mylib/v3
```

The import path changes too:

```go
import "github.com/myname/mylib"    // v1.x
import "github.com/myname/mylib/v2" // v2.x
```

Why? So you can use both versions simultaneously:

```go
import (
    v1 "github.com/myname/mylib"
    v2 "github.com/myname/mylib/v2"
)
```

Different modules, different import paths, no conflict.

## Creating v2

When you make breaking changes:

**Option 1: Major branch**

```bash
git checkout -b v2
# Update go.mod
sed -i 's|module github.com/myname/mylib|module github.com/myname/mylib/v2|' go.mod
# Update internal imports
# Commit and tag
git tag v2.0.0
git push origin v2 v2.0.0
```

**Option 2: Subdirectory**

```
mylib/
├── go.mod           # module github.com/myname/mylib (v1.x)
├── v2/
│   ├── go.mod       # module github.com/myname/mylib/v2
│   └── ...
```

Option 1 is more common for libraries. Option 2 works for monorepos.

## Pre-release Versions

Use semver pre-release suffixes:

```
v1.0.0-alpha.1
v1.0.0-beta.2
v1.0.0-rc.1
v1.0.0
```

```bash
git tag v1.0.0-beta.1
git push origin v1.0.0-beta.1
```

Pre-release versions aren't selected by default—users must request them explicitly:

```bash
go get github.com/myname/mylib@v1.0.0-beta.1
```

## v0.x: The Wild West

Versions before v1.0.0 are considered unstable. Go allows breaking changes in minor versions:

```
v0.1.0 -> v0.2.0  # breaking changes allowed
v0.2.0 -> v0.2.1  # should be backward compatible
```

Stay in v0.x until your API is stable. Once you tag v1.0.0, you're making a stability commitment.

## Minimum Version Selection

Go's dependency resolution differs from NuGet:

**NuGet**: Gets the *latest* version that satisfies all constraints

**Go**: Gets the *minimum* version that satisfies all constraints (Minimum Version Selection)

If you require `v1.2.0` and a dependency requires `v1.1.0`, Go uses `v1.2.0`—the minimum that satisfies both.

This makes builds reproducible. The same `go.mod` and `go.sum` always produce the same dependencies.

## Updating Dependencies

```bash
# Update a specific dependency
go get github.com/some/dep@v1.2.3

# Update to latest minor/patch
go get -u github.com/some/dep

# Update all dependencies
go get -u ./...

# Update to latest including major versions
go get github.com/some/dep@latest
```

After updating:

```bash
go mod tidy  # clean up go.mod and go.sum
```

## Comparing to NuGet

| Aspect | NuGet | Go Modules |
|--------|-------|------------|
| Version source | .nuspec/.csproj | Git tags |
| Version ranges | Yes (`[1.0, 2.0)`) | No (exact versions) |
| Resolution | Latest satisfying | Minimum satisfying |
| Major version path | Same package ID | Different module path |
| Lock file | packages.lock.json | go.sum (hashes only) |
| Pre-release | `-alpha`, `-beta` | Same |
| Central registry | nuget.org | No central registry |

## Best Practices

### 1. Don't Tag Until Stable

Stay on v0.x until you're confident in your API:

```go
module github.com/myname/mylib

go 1.22
```

Tag `v0.1.0`, `v0.2.0`, etc. Breaking changes are expected.

### 2. Use Meaningful Tags

```bash
# Good
git tag v1.2.3

# Bad - no 'v' prefix
git tag 1.2.3
```

Go requires the `v` prefix.

### 3. Document Breaking Changes

In your CHANGELOG:

```markdown
## v2.0.0 - 2025-01-05

### Breaking Changes
- Removed deprecated `OldFunction`
- Changed `Config` struct fields
- Renamed `Process` to `Execute`

### Migration Guide
See MIGRATION.md for upgrade instructions.
```

### 4. Use Retract for Broken Versions

If you publish a broken version, retract it:

```go
// go.mod
module github.com/myname/mylib

go 1.22

retract (
    v1.2.3 // Contains critical bug, use v1.2.4
    [v1.0.0, v1.1.0] // Known issues in range
)
```

Users are warned when they try to use retracted versions.

### 5. Version Internal Tools Separately

If your repo has a library and a CLI:

```
myproject/
├── go.mod           # module github.com/myname/myproject
├── cmd/
│   └── mytool/
└── pkg/
    └── mylib/
```

Consider separate modules if they have different release cadences.

## Releasing a Library

Checklist:

1. **Update CHANGELOG**
2. **Run tests**: `go test ./...`
3. **Check for breaking changes**: API compatible?
4. **Determine version**: major/minor/patch
5. **Update go.mod** if major version change
6. **Commit**: `git commit -m "Release v1.2.3"`
7. **Tag**: `git tag v1.2.3`
8. **Push**: `git push origin main v1.2.3`
9. **Verify**: `go get github.com/myname/mylib@v1.2.3`

The Go module proxy indexes your tag automatically.

## The Honest Take

Go's versioning is simpler but more rigid than NuGet's.

**What Go does well:**
- Git tags = source of truth
- Reproducible builds (MVS)
- v2+ as different paths is clever
- No version file to maintain

**What NuGet does better:**
- Version ranges for flexibility
- Same package ID across majors
- Central registry with search
- Richer metadata

**The verdict:**
If you're used to version ranges (`[1.0,2.0)`), Go's exact versioning feels restrictive. But it eliminates "works on my machine" dependency issues.

The major version path change (`/v2`) is controversial but ensures you can't accidentally break dependents with a major update.

Learn the patterns, version thoughtfully, and your users will thank you.

---

*That wraps up Phase 3 on deployment and production. Go's operational story is strong: single binaries, tiny containers, fast builds, simple CI/CD. The tooling is less sophisticated than .NET's in places, but the simplicity makes up for it.*
