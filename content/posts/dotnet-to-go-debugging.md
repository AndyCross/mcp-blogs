+++
title = "Debugging: Delve vs Visual Studio's Comfort"
date = "2025-01-04"
draft = false
tags = ["go", "dotnet", "tooling", "debugging", "csharp"]
series = ["step-over-to-go"]
+++

Visual Studio's debugger is exceptional. Breakpoints, watch expressions, edit-and-continue, conditional breakpoints, data tips, memory inspection, async debugging... You can debug anything, easily.

Go's debugger is Delve (`dlv`). It's good. It's not Visual Studio.

Let's get you productive with what Go offers.

## Delve Basics

Install:

```bash
go install github.com/go-delve/delve/cmd/dlv@latest
```

Start debugging:

```bash
# Debug current package
dlv debug

# Debug specific package
dlv debug ./cmd/server

# Debug a test
dlv test

# Attach to running process
dlv attach <pid>
```

## Command-Line Debugging

Inside `dlv`:

```
(dlv) break main.go:15          # set breakpoint
(dlv) break main.handleRequest  # break on function
(dlv) continue                  # run until breakpoint
(dlv) next                      # step over
(dlv) step                      # step into
(dlv) stepout                   # step out
(dlv) print x                   # print variable
(dlv) locals                    # print local variables
(dlv) args                      # print function arguments
(dlv) goroutines                # list goroutines
(dlv) goroutine 5               # switch to goroutine 5
(dlv) stack                     # print stack trace
(dlv) exit                      # quit
```

## IDE Integration

Nobody uses `dlv` on the command line for daily work. Use your IDE.

### VS Code

The Go extension integrates Delve. Create `.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Launch",
            "type": "go",
            "request": "launch",
            "mode": "debug",
            "program": "${workspaceFolder}",
            "args": []
        },
        {
            "name": "Launch Server",
            "type": "go",
            "request": "launch",
            "mode": "debug",
            "program": "${workspaceFolder}/cmd/server",
            "args": ["-port", "8080"]
        },
        {
            "name": "Debug Test",
            "type": "go",
            "request": "launch",
            "mode": "test",
            "program": "${workspaceFolder}/pkg/service"
        },
        {
            "name": "Attach",
            "type": "go",
            "request": "attach",
            "mode": "remote",
            "remotePath": "",
            "port": 2345,
            "host": "127.0.0.1"
        }
    ]
}
```

Press F5 to debug. Breakpoints, watch variables, call stack. The usual.

### GoLand

JetBrains GoLand has excellent debugging. Click in the gutter to set breakpoints, right-click to run debug, use the Debug panel.

GoLand's debugger is the closest to Visual Studio's experience in the Go world.

## Debugging Tests

Debug a specific test in VS Code:

1. Open the test file
2. Click "debug test" above the test function
3. Or add a launch config with `"mode": "test"`

From command line:

```bash
dlv test -- -test.run TestSpecificFunction
```

## Conditional Breakpoints

Set a breakpoint that only triggers under conditions:

```
(dlv) break main.go:25
(dlv) condition 1 i > 100
```

In VS Code, right-click a breakpoint and select "Edit Breakpoint" to add conditions.

## Debugging Goroutines

This is where Go debugging gets interesting. Your program has many goroutines:

```
(dlv) goroutines
  Goroutine 1 - User: ./main.go:15 main.main (0x4a5b6c)
  Goroutine 2 - User: ./server.go:42 main.handleRequest (0x4a6d8e)
  Goroutine 3 - User: ./worker.go:28 main.processJob (0x4a7f90)
```

Switch between them:

```
(dlv) goroutine 2
(dlv) stack
```

In VS Code, the Call Stack panel shows all goroutines. Click to switch.

## Remote Debugging

Debug a process on another machine:

On the remote:

```bash
dlv debug --headless --listen=:2345 --api-version=2 ./cmd/server
```

On your machine, connect with VS Code:

```json
{
    "name": "Remote",
    "type": "go",
    "request": "attach",
    "mode": "remote",
    "remotePath": "/path/on/remote",
    "port": 2345,
    "host": "remote.server.com"
}
```

## Debugging in Containers

Add Delve to your container:

```dockerfile
FROM golang:1.22 AS builder
RUN go install github.com/go-delve/delve/cmd/dlv@latest
COPY . .
RUN go build -gcflags="all=-N -l" -o /app ./cmd/server

FROM alpine
COPY --from=builder /go/bin/dlv /usr/local/bin/
COPY --from=builder /app /app
EXPOSE 8080 2345
CMD ["dlv", "--listen=:2345", "--headless=true", "--api-version=2", "--accept-multiclient", "exec", "/app"]
```

The `-gcflags="all=-N -l"` disables optimisations for better debugging.

## Comparing to Visual Studio

| Feature | Visual Studio | Delve |
|---------|---------------|-------|
| Basic breakpoints | Excellent | Good |
| Conditional breakpoints | Excellent | Good |
| Watch expressions | Excellent | Good |
| Edit and continue | Yes | No |
| Data visualizers | Rich | Basic |
| Async/Task debugging | Excellent | Goroutines visible |
| Memory inspection | Detailed | Basic |
| Performance profiling | Integrated | Separate tools |
| Remote debugging | Excellent | Good |

## Common Issues

**"Could not launch process"**

Compilation failed. Check `go build` works first.

**Breakpoints not hitting**

Optimised builds skip breakpoints. Build with:

```bash
go build -gcflags="all=-N -l"
```

**Variables showing `<optimized out>`**

Same issue. Disable optimisations.

**Can't see struct fields**

Unexported fields don't show in some views. Use `print` command with full path:

```
(dlv) print user.internalField
```

## Debugging Tips

**Printf debugging is valid**

Sometimes `fmt.Println` is faster than setting up a debugger. Go compiles fast; the feedback loop is quick.

**Use slog for structured debugging**

```go
slog.Debug("processing request", 
    "request_id", requestID,
    "user_id", userID,
    "payload_size", len(payload),
)
```

Run with `DEBUG=true` or appropriate log level.

**Panic stack traces are helpful**

When Go panics, you get a full stack trace. Read it:

```
panic: runtime error: invalid memory address

goroutine 1 [running]:
main.processUser(...)
    /app/main.go:42
main.handleRequest(...)
    /app/main.go:28
main.main()
    /app/main.go:15
```

Line numbers and function names. Often enough to find the bug.

## The Honest Take

Delve is competent. It's not Visual Studio.

**What Delve does well:**
- Goroutine debugging
- Remote debugging
- IDE integration (especially GoLand)
- Fast startup

**What Visual Studio does better:**
- Edit and continue
- Data visualization
- Memory inspection
- Historical debugging
- Overall polish

**The verdict:**
You'll miss Visual Studio's refinement. GoLand gets closest to that experience. VS Code with Delve is good enough for most debugging.

The Go community relies more on logging, tests, and reading stack traces than step debugging. The fast compile times mean printf debugging has a quick feedback loop.

Adjust your expectations, learn Delve's commands, and you'll be productive. Just don't expect Visual Studio's magic.

---

*That wraps up the tooling section. Go's tools are simpler than .NET's: `gofmt` instead of formatting debates, `golangci-lint` instead of analyzer configuration, `go generate` instead of source generators. Simpler isn't always better, but it's often good enough.*
