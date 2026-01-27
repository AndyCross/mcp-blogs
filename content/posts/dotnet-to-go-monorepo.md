+++
title = "Multi-Module Repos: Monorepo Thinking"
date = "2025-01-03"
draft = false
tags = ["go", "dotnet", "modules", "monorepo", "csharp"]
series = ["step-over-to-go"]
+++

Most Go projects have one `go.mod` file at the root. One module, one version, simple. But what happens when your repo grows? When you have shared libraries, multiple services, and teams stepping on each other's toes?

You need multiple modules. And Go's support for this is... functional. Not beautiful, but functional.

## When One Module Isn't Enough

Stick with one module when you can. But consider multiple modules when:

**Independent versioning matters:**
Your repo has a shared library (`pkg/auth`) and two services (`cmd/api`, `cmd/worker`). Library changes shouldn't force service releases.

**Different dependency needs:**
One service needs a heavy dependency (ML framework, database driver) that others don't need.

**Teams need isolation:**
Different teams own different parts of the repo and want independent build/test/release cycles.

## The Multi-Module Layout

Here's what a multi-module repo looks like:

```
mycompany/
├── go.work              // workspace file (Go 1.18+)
├── services/
│   ├── api/
│   │   ├── go.mod       // module github.com/mycompany/services/api
│   │   ├── go.sum
│   │   └── main.go
│   └── worker/
│       ├── go.mod       // module github.com/mycompany/services/worker
│       ├── go.sum
│       └── main.go
└── libs/
    ├── auth/
    │   ├── go.mod       // module github.com/mycompany/libs/auth
    │   ├── go.sum
    │   └── auth.go
    └── database/
        ├── go.mod       // module github.com/mycompany/libs/database
        ├── go.sum
        └── database.go
```

Each directory with a `go.mod` is an independent module. They can be versioned, released, and depended upon separately.

## Go Workspaces

Before Go 1.18, working with multiple modules in one repo was painful. You'd constantly be editing `go.mod` files to use `replace` directives during development, then removing them before commit.

Go 1.18 introduced **workspaces**. Create a `go.work` file at the root:

```go
// go.work
go 1.22

use (
    ./services/api
    ./services/worker
    ./libs/auth
    ./libs/database
)
```

Now Go commands understand the whole repo:

```bash
# From repo root
go build ./...      # builds all modules
go test ./...       # tests all modules
go mod tidy         # tidies all modules
```

The `go.work` file is for local development. Don't commit it (add to `.gitignore`). Each module should work independently for CI/CD and consumers.

## Cross-Module Dependencies

Modules in the same repo can depend on each other:

```go
// services/api/go.mod
module github.com/mycompany/services/api

go 1.22

require (
    github.com/mycompany/libs/auth v0.2.0
    github.com/mycompany/libs/database v0.1.5
)
```

For published modules, this just works. Go fetches from the module proxy.

For local development without `go.work`, you'd need `replace` directives:

```go
// services/api/go.mod (during local dev only)
replace github.com/mycompany/libs/auth => ../../libs/auth
replace github.com/mycompany/libs/database => ../../libs/database
```

Workspaces make `replace` unnecessary for local work.

## Versioning Strategy

Each module is versioned independently. The repo might look like:

```
libs/auth           v0.2.0, v0.2.1, v0.3.0
libs/database       v0.1.0, v0.1.5
services/api        v1.0.0, v1.1.0
services/worker     v1.0.0
```

Use git tags to version modules:

```bash
git tag libs/auth/v0.3.0
git push origin libs/auth/v0.3.0
```

The tag format `path/vX.Y.Z` tells Go which module the version applies to.

## Comparing to .NET

C#'s approach to monorepos is different:

| Aspect | .NET | Go |
|--------|------|-----|
| Project file | `.csproj` per project | `go.mod` per module |
| Solution | `.sln` groups projects | `go.work` for workspace |
| Local references | `<ProjectReference>` | `replace` or `go.work` |
| Versioning | NuGet packages | Module versions (git tags) |
| Build all | `dotnet build MySolution.sln` | `go build ./...` |
| Private packages | Private NuGet feed | Private GOPROXY or replace |

.NET's solution file is more mature for multi-project scenarios. `go.work` is newer and simpler.

## The Practical Workflow

### Adding a New Module

```bash
mkdir -p services/newservice
cd services/newservice
go mod init github.com/mycompany/services/newservice
```

Add to `go.work`:

```go
use (
    // ... existing
    ./services/newservice
)
```

### Depending on a Local Module

In your module's code:

```go
import "github.com/mycompany/libs/auth"
```

Then run:

```bash
go get github.com/mycompany/libs/auth@latest
# or specific version
go get github.com/mycompany/libs/auth@v0.2.0
```

### Releasing a Module

1. Make your changes
2. Update version in dependents' `go.mod` files
3. Commit everything
4. Tag the module: `git tag libs/auth/v0.3.0`
5. Push: `git push origin libs/auth/v0.3.0`

### CI/CD Considerations

Your CI shouldn't use `go.work`. It should test each module independently:

```yaml
# Example GitHub Actions
jobs:
  test-auth:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - working-directory: libs/auth
        run: go test ./...

  test-api:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - working-directory: services/api
        run: go test ./...
```

Each module builds and tests in isolation.

## When NOT to Multi-Module

Multi-module adds complexity. Avoid it if:

- Your code is tightly coupled anyway
- You don't need independent versioning
- You're the only developer
- The repo isn't that big yet

Start with one module. Split when you feel the pain.

## The Honest Take

Go workspaces solved the biggest pain point (local development), but multi-module repos are still more work than single modules.

**What Go does okay:**
- Workspaces make local dev tolerable
- Independent versioning is powerful
- Module isolation is clear

**What's still awkward:**
- Tag-based versioning for paths is clunky (`libs/auth/v0.3.0`)
- No solution-level dependency management
- CI needs to understand module structure
- Tooling is module-centric, not repo-centric

**What .NET does better:**
- Solution files coordinate multiple projects elegantly
- Project references just work
- NuGet versioning is more flexible
- Better IDE support for multi-project workflows

**The verdict:**
If you need multi-module, Go can do it. But it's not as polished as .NET's multi-project experience. Keep your module count low, use workspaces for local dev, and accept some ceremony around releases.

---

*Next up: testing in Go. Why the built-in testing package might be all you need, and why you might not miss xUnit.*
