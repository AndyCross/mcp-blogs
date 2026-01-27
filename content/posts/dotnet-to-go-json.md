+++
title = "JSON: Struct Tags and the Marshal Dance"
date = "2025-01-04"
draft = false
tags = ["go", "dotnet", "json", "serialization", "csharp"]
series = ["step-over-to-go"]
+++

In C#, you add `[JsonProperty("name")]` or rely on naming conventions. The serializer figures out the rest. Newtonsoft.Json has been battle-tested for over a decade, and System.Text.Json is catching up fast.

Go's `encoding/json` is simpler. Not worse, necessarily, but definitely more manual. And it has quirks that'll catch you out.

## The Basics

Go uses **struct tags** to control JSON field names:

```go
type User struct {
    ID        int       `json:"id"`
    FirstName string    `json:"first_name"`
    Email     string    `json:"email"`
    CreatedAt time.Time `json:"created_at"`
}
```

Those backtick strings are struct tags. The `json` key tells the JSON encoder how to handle each field.

Marshal to JSON:

```go
user := User{ID: 1, FirstName: "Alice", Email: "alice@example.com"}
data, err := json.Marshal(user)
// {"id":1,"first_name":"Alice","email":"alice@example.com","created_at":"0001-01-01T00:00:00Z"}
```

Unmarshal from JSON:

```go
var user User
err := json.Unmarshal([]byte(`{"id":1,"first_name":"Alice"}`), &user)
```

## Struct Tag Options

The `json` tag supports several options:

```go
type User struct {
    ID       int    `json:"id"`                    // rename to "id"
    Name     string `json:"name,omitempty"`        // omit if empty
    Password string `json:"-"`                     // never include
    Email    string `json:"email,omitempty"`       // rename + omit if empty
    internal string                                 // unexported, always ignored
}
```

| Tag | Effect |
|-----|--------|
| `json:"name"` | Field appears as "name" in JSON |
| `json:",omitempty"` | Omit if zero value |
| `json:"-"` | Never marshal/unmarshal |
| `json:"-,"` | Field literally named "-" (rare) |

## The omitempty Gotcha

`omitempty` omits **zero values**. This catches people:

```go
type Response struct {
    Count int  `json:"count,omitempty"`
    Found bool `json:"found,omitempty"`
}

r := Response{Count: 0, Found: false}
data, _ := json.Marshal(r)
// {} - both fields omitted because they're zero values!
```

If zero is a meaningful value, don't use `omitempty`. Or use a pointer:

```go
type Response struct {
    Count *int  `json:"count,omitempty"`  // nil omitted, 0 included
    Found *bool `json:"found,omitempty"`
}
```

## Encoding and Decoding Streams

For HTTP handlers, use encoders/decoders instead of Marshal/Unmarshal:

```go
// Reading request body
func handler(w http.ResponseWriter, r *http.Request) {
    var input CreateUserRequest
    if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
        http.Error(w, "Invalid JSON", http.StatusBadRequest)
        return
    }
    
    // ... process ...
    
    // Writing response
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(response)
}
```

More efficient than reading the body into a byte slice first.

## Custom Marshalling

Implement `json.Marshaler` and `json.Unmarshaler` for custom behaviour:

```go
type Status int

const (
    StatusPending Status = iota
    StatusActive
    StatusCompleted
)

func (s Status) MarshalJSON() ([]byte, error) {
    var str string
    switch s {
    case StatusPending:
        str = "pending"
    case StatusActive:
        str = "active"
    case StatusCompleted:
        str = "completed"
    default:
        str = "unknown"
    }
    return json.Marshal(str)
}

func (s *Status) UnmarshalJSON(data []byte) error {
    var str string
    if err := json.Unmarshal(data, &str); err != nil {
        return err
    }
    switch str {
    case "pending":
        *s = StatusPending
    case "active":
        *s = StatusActive
    case "completed":
        *s = StatusCompleted
    default:
        return fmt.Errorf("unknown status: %s", str)
    }
    return nil
}
```

Now `Status` marshals as a string:

```go
type Order struct {
    ID     int    `json:"id"`
    Status Status `json:"status"`
}

order := Order{ID: 1, Status: StatusActive}
data, _ := json.Marshal(order)
// {"id":1,"status":"active"}
```

## Handling Unknown Fields

By default, Go ignores unknown JSON fields:

```go
var user User
json.Unmarshal([]byte(`{"id":1,"unknown_field":"ignored"}`), &user)
// No error, unknown_field silently ignored
```

To catch unknown fields, use a decoder:

```go
dec := json.NewDecoder(r.Body)
dec.DisallowUnknownFields()
if err := dec.Decode(&user); err != nil {
    // Error if unknown fields present
}
```

## Working with Dynamic JSON

When you don't know the structure, use `map[string]any` or `any`:

```go
var data map[string]any
json.Unmarshal(rawJSON, &data)

// Access fields
name := data["name"].(string)  // type assertion needed
```

Or use `json.RawMessage` to defer parsing:

```go
type Event struct {
    Type    string          `json:"type"`
    Payload json.RawMessage `json:"payload"`  // parse later
}

var event Event
json.Unmarshal(data, &event)

// Now parse payload based on type
switch event.Type {
case "user_created":
    var payload UserCreatedPayload
    json.Unmarshal(event.Payload, &payload)
}
```

## Comparing to C#

| Feature | System.Text.Json | Go encoding/json |
|---------|------------------|------------------|
| Attribute/Tag syntax | `[JsonPropertyName]` | Struct tags |
| Naming policy | JsonNamingPolicy | Manual per-field |
| Ignore null | `[JsonIgnore]` + conditions | `omitempty` (but for zero values) |
| Custom converters | JsonConverter | Marshaler/Unmarshaler interfaces |
| Unknown fields | Configurable | Ignored by default |
| Streaming | Yes | Yes (Encoder/Decoder) |
| Performance | Very good | Good |
| Source generators | Yes (AOT-friendly) | No |

C# has more configuration options. Go is more explicit but less flexible.

## Common Patterns

### Response Wrappers

```go
type APIResponse[T any] struct {
    Data  T      `json:"data,omitempty"`
    Error string `json:"error,omitempty"`
}

func respondJSON[T any](w http.ResponseWriter, status int, data T) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(status)
    json.NewEncoder(w).Encode(APIResponse[T]{Data: data})
}

func respondError(w http.ResponseWriter, status int, message string) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(status)
    json.NewEncoder(w).Encode(APIResponse[any]{Error: message})
}
```

### Embedded Structs for Composition

```go
type Timestamps struct {
    CreatedAt time.Time `json:"created_at"`
    UpdatedAt time.Time `json:"updated_at"`
}

type User struct {
    ID   int    `json:"id"`
    Name string `json:"name"`
    Timestamps
}

// JSON: {"id":1,"name":"Alice","created_at":"...","updated_at":"..."}
```

Embedded struct fields are flattened.

### Different Input/Output Types

```go
// For creating
type CreateUserRequest struct {
    Name  string `json:"name"`
    Email string `json:"email"`
}

// For responses (includes computed fields)
type UserResponse struct {
    ID        int       `json:"id"`
    Name      string    `json:"name"`
    Email     string    `json:"email"`
    CreatedAt time.Time `json:"created_at"`
}
```

Don't try to use one struct for everything. Separate request and response types.

## The Honest Take

Go's JSON handling is straightforward but manual. You write more code, but there's less magic.

**What Go does well:**
- Simple and predictable
- Struct tags are readable
- Custom marshalling is easy
- Streaming encoders/decoders

**What C# does better:**
- Naming policies (automatic camelCase)
- Source generators for performance
- More attribute options
- Better handling of null vs missing
- `System.Text.Json` is very fast

**The verdict:**
You'll miss automatic naming policies. You'll write more struct tags than you want to. But Go's JSON handling works fine for most cases.

For complex JSON needs (polymorphic types, extensive customization), consider third-party libraries like `easyjson` (fast, generated) or `jsoniter` (drop-in replacement, more features).

---

*Next up: configuration. How to load config without IOptions<T> and why simplicity wins.*
