+++
title = "You Know .NET, Now Meet the Go Toolchain"
date = "2024-12-28"
draft = false
tags = ["go", "dotnet", "tooling", "csharp"]
+++

After twenty-odd years writing C#, I'm learning Go. Not because .NET has failed me (it hasn't) but because some problems want a different shape of solution. Small binaries. Fast startup. Simple deployment. The kind of thing Go does without breaking a sweat.

This is the first post in a series documenting that journey. Not a tutorial (the Go docs are excellent), but an honest account of where my C# muscle memory helps, where it hinders, and what makes Go feel genuinely different rather than just superficially unfamiliar.

Let's start with the toolchain. Because before we write any code, we need to know where everything lives.

## The First Surprise: There's Only One Tool

In .NET, you've got `dotnet` for building, running, testing, and package management. Fair enough. But you've also got Visual Studio, Rider, or VS Code doing heavy lifting. MSBuild lurks underneath. NuGet has its own config. The SDK has versions. The runtime has versions. Different platforms have different workloads.

Go has `go`.

That's it. One command. Build, run, test, format, vet, mod management. All through the same tool. There's no separate "SDK" to install per project. No workload selectors. No runtime configuration.

```bash
go build    # compiles
go run      # compiles and runs
go test     # runs tests
go fmt      # formats code
go vet      # static analysis
go mod      # dependency management
go get      # adds dependencies
```

Coming from .NET, this feels almost suspiciously simple. Where's the configuration? Where are the project files? Where's the magic?

The answer: there isn't much. And that's the point.

## Where Your Code Lives

Here's where your C# instincts will immediately try to betray you.

In .NET, you create a solution, add projects, reference other projects, configure output paths, set up different configurations for debug and release... you know the drill. Projects live wherever you put them. References can point anywhere.

Go has opinions.

### GOPATH (The Old Way)

Originally, Go wanted all your code in a single workspace called `GOPATH`. Everything lived under `$GOPATH/src/`, organised by import path. If you were writing code for GitHub, it literally lived at `$GOPATH/src/github.com/yourname/yourproject`.

This drove people mad. Especially people coming from languages where "put your project wherever you like" is the norm.

### Modules (The Current Way)

Since Go 1.11, modules freed us from GOPATH. Now a project can live anywhere, and its identity comes from its `go.mod` file rather than its filesystem location.

```bash
mkdir myproject && cd myproject
go mod init github.com/yourname/myproject
```

That `go mod init` command creates a `go.mod` file, Go's equivalent of your `.csproj`. We'll dig into that properly in the next post.

The key insight: **the module path is the project's identity**. It's what other code uses to import your packages. Choose it thoughtfully.

## The Build Model

This is where things get properly different, and honestly? It took me a while to stop fighting it.

### C# Build Mental Model

In .NET, compilation is incremental and complex. MSBuild tracks dependencies between projects. The compiler emits IL. The runtime JITs it (or AOT compiles it, if you're being fancy). Builds produce assemblies. Assemblies reference other assemblies. There's a whole graph of dependencies that lives in your `bin` folder.

### Go Build Mental Model

Go compiles to machine code. Directly. No IL, no runtime, no JIT. The `go build` command produces a single static binary that you can copy anywhere and run.

```bash
go build -o myapp
./myapp  # just... runs
```

No `dotnet` required on the target machine. No runtime version matching. No framework-dependent vs self-contained deployment decisions. Copy the binary, run it. Done.

The tradeoff? Larger binaries than a framework-dependent .NET app (though smaller than self-contained). But the simplicity of deployment is remarkable.

### Cross-Compilation

Here's something that still delights me. Want to build for Linux from your Mac?

```bash
GOOS=linux GOARCH=amd64 go build -o myapp-linux
```

Done. No Docker, no separate SDK installation, no drama. Go's cross-compilation is a first-class citizen, not an afterthought.

## Project Structure

A minimal Go project looks nothing like a minimal C# project.

### C# (Minimal API, .NET 8)

```
MyProject/
├── MyProject.csproj
├── Program.cs
├── appsettings.json
├── appsettings.Development.json
├── Properties/
│   └── launchSettings.json
└── bin/
    └── Debug/
        └── net8.0/
            └── (loads of stuff)
```

### Go

```
myproject/
├── go.mod
└── main.go
```

That's it. Two files. The `go.mod` declares your module identity and dependencies. The `main.go` contains your code. Build it, get a binary.

No configuration hierarchy. No launch profiles. No bin/obj dance. Just source code and a module definition.

## The Gotchas (Already)

### Case Sensitivity Matters

Go uses case to control visibility. Uppercase first letter = exported (public). Lowercase = unexported (internal to the package).

```go
func ProcessData() {}  // exported, other packages can call this
func processData() {}  // unexported, package-private
```

Your C# brain will want to reach for `public` and `private` keywords. They don't exist in Go. Case *is* the visibility modifier.

### No Implicit Main Package

In C#, top-level statements let you skip the ceremony. In Go, you always need:

```go
package main

func main() {
    // your code
}
```

The `package main` declaration tells Go this is an executable. The `main()` function is the entry point. No variation. No magic. Every Go executable looks like this.

### File Organisation Isn't Free

In C#, namespaces and folders are loosely coupled. You can have a file in `Services/` that declares `namespace MyApp.Models`. Weird, but legal.

In Go, packages are directories. Every `.go` file in a directory must have the same `package` declaration. Want a different package? Different directory. No exceptions.

This feels restrictive at first. Then you realise it makes codebases significantly easier to navigate. You always know what package a file belongs to. Just look at where it lives.

## What We Haven't Covered

This is just orientation. We haven't touched:

- **How `go.mod` actually works** (next post)
- **How packages and imports differ from namespaces**
- **The `internal` directory convention**
- **Testing conventions**
- **The standard library**

All coming. But first, I wanted to establish the basic geography. Where code lives. How it builds. What tools you actually use.

## The Honest Assessment

After a few weeks with Go's toolchain, here's my take:

**Better than C#:**
- Simplicity. One tool, minimal configuration.
- Cross-compilation. Effortless.
- Build speed. It's properly fast.
- Deployment. Single binary, no runtime.

**Worse than C#:**
- IDE support. Go has good tooling, but it's not Rider/Visual Studio level.
- Refactoring. The tools exist, but they're less sophisticated.
- Debug experience. It's fine, but not the polished F5 experience you're used to.

**Different, neither better nor worse:**
- Project structure. Go's conventions feel strange, then liberating.
- Package system. We'll cover this properly, but it's a genuine paradigm shift.

The toolchain isn't trying to be .NET, or "simple .NET", or ".NET but faster". Different philosophy entirely: less configuration, more convention, explicit over implicit.

That last one will come up a lot in this series. Go loves explicitness. Coming from C#, where we've spent years making things implicit (top-level statements, global usings, minimal APIs), it takes adjustment.

But there's method to the explicitness. And honestly? I'm starting to appreciate it.

---

*Next up: go.mod in depth. Dependency management without NuGet, and why it's both simpler and more opinionated than you'd expect.*
