+++
title = "AWS Lambda and Go: Cold Starts That Don't Hurt"
date = "2025-01-05"
draft = false
tags = ["go", "dotnet", "aws", "lambda", "serverless", "csharp"]
+++

If you've run .NET on Lambda, you know the cold start pain. 3-5 seconds for a managed runtime. Even Native AOT helps but doesn't eliminate it.

Go on Lambda cold starts in ~100-200ms. Sometimes faster. It's not magic—it's the same static binary advantage, applied to serverless.

## Go Lambda Basics

```go
package main

import (
    "context"
    "github.com/aws/aws-lambda-go/lambda"
)

type Request struct {
    Name string `json:"name"`
}

type Response struct {
    Message string `json:"message"`
}

func handler(ctx context.Context, req Request) (Response, error) {
    return Response{
        Message: "Hello, " + req.Name,
    }, nil
}

func main() {
    lambda.Start(handler)
}
```

Build and deploy:

```bash
GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" -o bootstrap main.go
zip function.zip bootstrap
aws lambda create-function \
  --function-name my-function \
  --runtime provided.al2023 \
  --handler bootstrap \
  --zip-file fileb://function.zip \
  --role arn:aws:iam::123456789:role/lambda-role
```

The binary must be named `bootstrap` for custom runtimes.

## ARM64 for Better Performance

AWS Graviton2 processors offer better price-performance:

```bash
GOOS=linux GOARCH=arm64 go build -ldflags="-s -w" -o bootstrap main.go
```

Create the function with ARM:

```bash
aws lambda create-function \
  --function-name my-function \
  --runtime provided.al2023 \
  --architectures arm64 \
  --handler bootstrap \
  --zip-file fileb://function.zip \
  --role arn:aws:iam::123456789:role/lambda-role
```

ARM64 is typically ~20% cheaper and often faster for Go.

## Cold Start Comparison

Rough numbers (highly variable, your mileage will vary):

| Runtime | Cold Start | Warm Invocation |
|---------|-----------|-----------------|
| Go (custom runtime) | 100-200ms | 1-5ms |
| .NET 8 Managed | 2-4 seconds | 5-20ms |
| .NET 8 Native AOT | 300-800ms | 3-10ms |
| Node.js | 200-400ms | 5-15ms |
| Python | 200-300ms | 10-30ms |

Go's cold start is competitive with Python and Node, but with the performance of a compiled language.

## API Gateway Integration

For HTTP APIs:

```go
package main

import (
    "context"
    "encoding/json"
    "github.com/aws/aws-lambda-go/events"
    "github.com/aws/aws-lambda-go/lambda"
)

func handler(ctx context.Context, req events.APIGatewayProxyRequest) (events.APIGatewayProxyResponse, error) {
    name := req.QueryStringParameters["name"]
    if name == "" {
        name = "World"
    }
    
    body, _ := json.Marshal(map[string]string{
        "message": "Hello, " + name,
    })
    
    return events.APIGatewayProxyResponse{
        StatusCode: 200,
        Headers:    map[string]string{"Content-Type": "application/json"},
        Body:       string(body),
    }, nil
}

func main() {
    lambda.Start(handler)
}
```

## Using HTTP Frameworks

Want to use your existing HTTP code? Use an adapter:

```go
package main

import (
    "net/http"
    "github.com/aws/aws-lambda-go/lambda"
    "github.com/awslabs/aws-lambda-go-api-proxy/httpadapter"
)

func main() {
    mux := http.NewServeMux()
    mux.HandleFunc("/hello", helloHandler)
    mux.HandleFunc("/users", usersHandler)
    
    lambda.Start(httpadapter.New(mux).ProxyWithContext)
}
```

Or with chi:

```go
import "github.com/awslabs/aws-lambda-go-api-proxy/chiadapter"

r := chi.NewRouter()
r.Get("/hello", helloHandler)

lambda.Start(chiadapter.New(r).ProxyWithContext)
```

Your HTTP handlers work both locally and on Lambda.

## Keeping Warm

If cold starts still matter, provision concurrency:

```bash
aws lambda put-provisioned-concurrency-config \
  --function-name my-function \
  --qualifier prod \
  --provisioned-concurrent-executions 5
```

Keeps 5 instances warm. You pay for them, but no cold starts.

For Go, you rarely need this. 100ms cold starts are acceptable for most use cases.

## SAM Template

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Globals:
  Function:
    Timeout: 30
    MemorySize: 256
    Runtime: provided.al2023
    Architectures:
      - arm64

Resources:
  MyFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: ./
      Handler: bootstrap
      Events:
        Api:
          Type: Api
          Properties:
            Path: /hello
            Method: get
    Metadata:
      BuildMethod: go1.x
```

Build and deploy:

```bash
sam build
sam deploy --guided
```

## Comparing to .NET Lambda

**.NET Managed Runtime:**
```csharp
public class Function
{
    public string Handler(string input, ILambdaContext context)
    {
        return $"Hello, {input}";
    }
}
```

Deploy as zip with .NET 8 runtime. Cold starts: 2-4 seconds.

**.NET Native AOT:**
Better cold starts (~500ms), but:
- Limited reflection
- Longer build times
- Larger deployment packages than Go

**Go Custom Runtime:**
- Fastest cold starts
- Smallest packages
- Full language features
- Simple deployment

## Local Development

Test locally with SAM:

```bash
sam local invoke MyFunction -e event.json
sam local start-api
```

Or just run your Go code directly—it's a normal program:

```go
func main() {
    if os.Getenv("AWS_LAMBDA_FUNCTION_NAME") != "" {
        lambda.Start(handler)
    } else {
        // Local development
        http.HandleFunc("/", httpHandler)
        http.ListenAndServe(":8080", nil)
    }
}
```

## The Honest Take

Go is excellent for Lambda.

**What Go does better:**
- Fastest cold starts of compiled languages
- Small deployment packages
- Simple deployment model
- ARM64 support trivial
- No runtime version management

**What .NET does better:**
- Richer AWS SDK (sometimes)
- Better IDE tooling for Lambda
- Managed runtime means no bootstrap binary
- .NET-specific integrations

**The verdict:**
If Lambda cold starts have frustrated you in .NET, Go is the answer. 100ms cold starts mean serverless actually feels instant.

The deployment model is simple: build a binary, zip it, upload. No runtime versions, no layer management, no framework configuration.

For latency-sensitive serverless workloads, Go is hard to beat.

---

*Next up: Kubernetes and Go—health checks, graceful shutdown, and playing nice with orchestration.*
