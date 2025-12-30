+++
title = "Linting and Formatting: gofmt Is Non-Negotiable"
date = "2025-01-04"
draft = false
tags = ["go", "dotnet", "tooling", "linting", "csharp"]
+++

In C#, code formatting is a matter of preference. Tabs or spaces? Braces on the same line or next? Teams debate, `.editorconfig` files proliferate, and nobody quite agrees.

In Go, formatting is not a discussion. `gofmt` defines the One True Format, and everyone uses it. There is no debate because there's no choice.

This sounds authoritarian. It's actually liberating.

## gofmt: The Formatter

Every Go file should be formatted by `gofmt`:

```bash
gofmt -w .              # format all files in place
go fmt ./...            # same thing, via go command
```

`gofmt` handles:
- Indentation (tabs, not spaces)
- Brace placement (same line, always)
- Spacing around operators
- Import grouping
- Line length (it doesn't wrap, but long lines are a code smell)

There are no options. No configuration. One format for all Go code, everywhere.

## The Philosophy

Rob Pike (Go co-creator): "Gofmt's style is no one's favourite, yet gofmt is everyone's favourite."

The point isn't that `gofmt`'s choices are optimal. The point is that *having* a choice wastes time. Every Go codebase looks the same, which means:

- No bikeshedding about style
- Pull reviews focus on logic, not formatting  
- New team members read unfamiliar code easily
- Tooling (IDEs, linters) can assume standard formatting

## goimports: gofmt Plus Import Management

`goimports` does everything `gofmt` does, plus:
- Adds missing imports
- Removes unused imports
- Groups imports (stdlib, external, internal)

```bash
go install golang.org/x/tools/cmd/goimports@latest
goimports -w .
```

Most developers use `goimports` instead of plain `gofmt`. Configure your editor to run it on save.

## Linting with golangci-lint

Formatting ensures consistency. Linting catches bugs and enforces best practices.

`golangci-lint` is the standard meta-linter—it runs many linters in one tool:

```bash
# Install
go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest

# Run
golangci-lint run
```

Default linters catch:
- Unused variables and imports
- Ineffective assignments  
- Missing error checks
- Suspicious constructs

## Common Linters

`golangci-lint` bundles dozens of linters. Key ones:

| Linter | Purpose |
|--------|---------|
| `errcheck` | Unchecked errors |
| `gosimple` | Simplification suggestions |
| `govet` | Suspicious constructs |
| `ineffassign` | Ineffectual assignments |
| `staticcheck` | Advanced static analysis |
| `unused` | Unused code |
| `gosec` | Security issues |
| `misspell` | Spelling mistakes |
| `gocyclo` | Cyclomatic complexity |
| `gocritic` | Opinionated style issues |

## Configuration

Create `.golangci.yml`:

```yaml
linters:
  enable:
    - errcheck
    - gosimple
    - govet
    - ineffassign
    - staticcheck
    - unused
    - gosec
    - misspell
    
linters-settings:
  errcheck:
    check-type-assertions: true
  govet:
    check-shadowing: true
  gocyclo:
    min-complexity: 15

issues:
  exclude-rules:
    - path: _test\.go
      linters:
        - gosec  # less strict in tests
```

Run with:

```bash
golangci-lint run
golangci-lint run --fix  # auto-fix where possible
```

## staticcheck

The most powerful individual linter. It catches subtle bugs:

```go
// staticcheck catches this
if x == nil {
    return x.String()  // nil dereference
}

// And this
for i := range items {
    go func() {
        process(items[i])  // captures loop variable
    }()
}
```

Many issues that would be runtime errors become compile-time warnings.

## Comparing to .NET Analyzers

| Feature | .NET Analyzers | Go Linting |
|---------|----------------|------------|
| Format enforcement | Optional (EditorConfig) | Mandatory (gofmt) |
| Built-in | Some analyzers | gofmt, go vet |
| Meta-linter | StyleCop, Roslyn | golangci-lint |
| IDE integration | Excellent | Good |
| CI integration | Easy | Easy |
| Auto-fix | Many rules | Some rules |

.NET has the advantage of the Roslyn compiler platform—analyzers can be very sophisticated. Go's linters are simpler but catch most issues.

## Editor Integration

### VS Code

Install the Go extension. Add to `settings.json`:

```json
{
    "go.formatTool": "goimports",
    "go.lintTool": "golangci-lint",
    "editor.formatOnSave": true,
    "[go]": {
        "editor.defaultFormatter": "golang.go",
        "editor.codeActionsOnSave": {
            "source.organizeImports": true
        }
    }
}
```

### GoLand

Built-in support. Enable "Reformat code" and "Optimize imports" on save.

### Vim/Neovim

Use `vim-go` or configure `gopls` (the Go language server) with your LSP setup.

## CI Integration

Add to your pipeline:

```yaml
# GitHub Actions
- name: golangci-lint
  uses: golangci/golangci-lint-action@v4
  with:
    version: latest
```

Or manually:

```bash
# Install
curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b $(go env GOPATH)/bin

# Run
golangci-lint run --timeout 5m
```

## Pre-commit Hooks

Enforce formatting before commit:

```bash
# .git/hooks/pre-commit
#!/bin/sh
gofmt -l . | read && echo "Files not formatted" && exit 1
golangci-lint run && exit 0 || exit 1
```

Or use [pre-commit](https://pre-commit.com/):

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/golangci/golangci-lint
    rev: v1.55.0
    hooks:
      - id: golangci-lint
```

## The Honest Take

Go's enforced formatting is one of its best features. No arguments, no decisions, no config files.

**What Go does better:**
- No bikeshedding—ever
- All code looks the same
- `gofmt` is fast and universal
- No configuration to maintain

**What .NET does better:**
- More formatting options (if you want them)
- Roslyn analyzers are very powerful
- Better code action suggestions
- More sophisticated refactoring

**The verdict:**
You'll miss zero formatting decisions. You won't miss the arguments about formatting. `golangci-lint` catches most issues; enable it and move on.

The Go community's attitude is refreshing: format your code, lint it, and spend your energy on actual problems.

---

*Next up: code generation with `go generate`—why Go developers love generating code.*
