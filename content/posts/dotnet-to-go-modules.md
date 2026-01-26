+++
title = "Goodbye .csproj, Hello go.mod"
date = "2024-12-28"
draft = false
tags = ["go", "dotnet", "dependencies", "csharp"]
+++

Right, let's talk about dependencies. In .NET land, we've got NuGet, `.csproj` files, `PackageReference` elements, version ranges, transitive dependencies, and `packages.lock.json` if we're being careful. It's a mature ecosystem with excellent tooling.

Go does things differently. There's no NuGet. There's no package registry at all, actually. And that sounds mental until you understand why. It works rather well.

## The go.mod File

Every Go module has a `go.mod` file at its root. Here's a real one:

```go
module github.com/yourname/yourproject

go 1.22

require (
    github.com/gin-gonic/gin v1.9.1
    github.com/stretchr/testify v1.8.4
)

require (
    github.com/bytedance/sonic v1.9.1 // indirect
    github.com/gabriel-vasile/mimetype v1.4.2 // indirect
    // ... more indirect dependencies
)
```

Let's break this down.

### Module Declaration

```go
module github.com/yourname/yourproject
```

This is your module's identity, its import path. When someone writes `import "github.com/yourname/yourproject/pkg/whatever"`, Go knows where to find it because of this declaration.

Unlike a `.csproj` where the assembly name is mostly internal, this path is *the* identifier. Choose it thoughtfully.

### Go Version

```go
go 1.22
```

This declares the minimum Go version required. Not quite the same as `<TargetFramework>net8.0</TargetFramework>`. You're not compiling for a specific runtime. You're just saying "this code uses features from Go 1.22, don't try to build it with something older."

### Dependencies

```go
require (
    github.com/gin-gonic/gin v1.9.1
    github.com/stretchr/testify v1.8.4
)
```

Here's where it gets interesting. These are your direct dependencies, the packages you actually import in your code.

Notice the format: `module-path version`. The version uses semantic versioning prefixed with `v`. No version ranges. No floating versions. Exactly this version, every time.

### Indirect Dependencies

```go
require (
    github.com/bytedance/sonic v1.9.1 // indirect
)
```

The `// indirect` comment marks transitive dependencies, packages that your dependencies need, but you don't import directly. Go tracks these explicitly in `go.mod`.

## No Central Registry

Here's the thing that confused me coming from NuGet: Go doesn't have a package registry.

NuGet has nuget.org. npm has npmjs.com. Go has... URLs.

When you `go get github.com/gin-gonic/gin`, Go literally fetches from GitHub. The module path isn't an identifier that maps to a registry. It's a resolvable URL (with some clever translation rules).

This means:
- No registry account needed to publish
- No central point of failure
- Dependencies are wherever their code lives

But also:
- No central search (though pkg.go.dev indexes public modules)
- No private registry without extra setup
- Version discovery is... different

## Adding Dependencies

Here's the workflow comparison:

### In .NET

```bash
dotnet add package Newtonsoft.Json --version 13.0.3
```

Or edit your `.csproj`:

```xml
<PackageReference Include="Newtonsoft.Json" Version="13.0.3" />
```

Then `dotnet restore`.

### In Go

```bash
go get github.com/gin-gonic/gin@v1.9.1
```

Or just import it in your code:

```go
import "github.com/gin-gonic/gin"
```

Then run `go mod tidy`. Go will fetch the dependency, resolve versions, and update `go.mod` automatically.

That `go mod tidy` command is your friend. It adds missing dependencies, removes unused ones, and generally keeps your `go.mod` clean. I run it roughly as often as I save files.

## Version Selection

Go's approach to version selection is refreshingly simple, and it took me a while to appreciate it.

### The Problem With Version Ranges

In NuGet, you might declare:

```xml
<PackageReference Include="SomeLib" Version="[1.0, 2.0)" />
```

Meaning "any version from 1.0 up to but not including 2.0." The actual version you get depends on what's available, what other packages need, and the resolver's algorithm.

This flexibility is powerful but creates problems:
- Different machines might resolve different versions
- Lock files become essential
- "Works on my machine" is often a version resolution issue

### Go's Minimum Version Selection

Go uses something called Minimum Version Selection (MVS). The idea: given all the version constraints, pick the *minimum* version that satisfies everything.

If you require `v1.9.1` and a dependency requires `v1.8.0` of the same module, Go picks `v1.9.1`. The minimum version that satisfies both.

No ranges. No "latest compatible." Just: here are the minimums everyone needs, let's use those.

The result? Given the same `go.mod` and `go.sum` files, you'll always get exactly the same versions. No lock file randomness. No surprising upgrades.

### The go.sum File

Speaking of which, `go.sum` is Go's integrity file:

```
github.com/gin-gonic/gin v1.9.1 h1:4idEAncQnU5...
github.com/gin-gonic/gin v1.9.1/go.mod h1:RdK04...
```

It contains cryptographic hashes of every dependency. If a module's contents don't match the recorded hash, the build fails.

Commit this file. It's your guarantee of reproducible builds.

## Updating Dependencies

The version-pinning approach means updates are explicit:

```bash
# Update a specific dependency
go get github.com/gin-gonic/gin@v1.10.0

# Update all dependencies to latest minor/patch
go get -u ./...

# Update all dependencies to latest (including major)
go get -u=patch ./...
```

There's no equivalent to NuGet's floating versions. When you want an update, you ask for it specifically. Some find this tedious; I find it clarifying.

## Major Versions Are Different Modules

Here's where Go does something clever (and initially bewildering).

In semantic versioning, major version bumps signal breaking changes. `v2.0.0` might have a completely different API from `v1.9.0`.

Go handles this by treating major versions as *different modules*:

```go
// v1.x
import "github.com/go-redis/redis/v8"

// v9.x (yes, they jumped)
import "github.com/redis/go-redis/v9"
```

The import path includes the major version. `v2`, `v3`, etc. are literally different modules.

This means:
- You can use v1 and v2 of the same library simultaneously (different import paths)
- Breaking changes are impossible to accidentally adopt
- Library authors must maintain separate module paths for major versions

It's awkward at first. Then you realise you've never had a build broken by an accidental major version upgrade.

## The Comparison

| Aspect | NuGet/.csproj | Go Modules |
|--------|---------------|------------|
| Registry | Central (nuget.org) | Distributed (any URL) |
| Version syntax | Ranges allowed | Exact versions only |
| Resolution | Complex algorithm | Minimum Version Selection |
| Lock file | Optional but recommended | go.sum (hashes only) |
| Private packages | Private feeds | Various options (GOPROXY) |
| Major versions | Same package ID | Different module paths |

## What Actually Trips You Up

After a few weeks, here's what caught me out:

### Import Path Confusion

Your IDE might autocomplete an import as `github.com/gin-gonic/gin/v2` when you wanted `v1`. Check your imports when things don't compile.

### Forgetting go mod tidy

Add an import, wonder why it doesn't work, realise you never fetched the dependency. `go mod tidy`. Learn to love it.

### Private Repositories

Public modules "just work." Private repos need GOPROXY configuration or GOPRIVATE settings. It's not hard, but it's not automatic either.

### Vendor Directory

Go can vendor dependencies (copy them into a `vendor/` directory in your project). Some teams mandate this for reproducibility. If you see a vendor directory, know that `go build` will use it by default.

## The Honest Take

**Things I like better than NuGet:**

- Reproducibility. Same inputs, same outputs, always.
- No central registry dependency. Dependencies are just code at URLs.
- Major version handling. Breaking changes are structurally isolated.
- Simplicity. One file, explicit versions, done.

**Things I miss from NuGet:**

- Proper package search. pkg.go.dev is decent but not nuget.org.
- Private feeds. Azure Artifacts, MyGet, etc. are more polished than GOPROXY setup.
- .NET's tooling. `dotnet add package` with tab completion is lovely.
- Version ranges. Sometimes I *want* "latest patch version" and Go says no.

**Things that are just different:**

- Import paths being URLs. It's not better or worse, just a different model.
- go.sum vs lock files. Similar goal, different mechanism.
- The vendor directory. Some love it, some ignore it entirely.

## The Philosophy

There's a reason Go's dependency management feels different: it was designed later, learning from problems with other systems.

The Ruby and Node ecosystems taught us that flexible version resolution leads to "works on my machine" nightmares. Go said: fine, no flexibility. Exact versions always.

The npm left-pad incident taught us that central registries are single points of failure. Go said: fine, no central registry. Your dependencies are wherever their source code lives.

Whether you prefer this philosophy is personal. But understanding *why* Go made these choices helps you work with the system rather than fighting it.

---

*Next in the series: packages and imports. Why Go's package system is nothing like namespaces, and how to stop your C# brain from making it harder than it needs to be.*
