+++
title = "Configuration Without IOptions<T>"
date = "2025-01-04"
draft = false
tags = ["go", "dotnet", "configuration", "csharp"]
+++

In ASP.NET Core, configuration is a whole subsystem. `IConfiguration`, `IOptions<T>`, `IOptionsSnapshot<T>`, `IOptionsMonitor<T>`, multiple providers, hot reload, dependency injection integration... It's sophisticated. Maybe too sophisticated.

Go doesn't have a standard configuration library. The community uses environment variables, simple file parsing, or third-party libraries. It's less powerful and often exactly what you need.

## The Simplest Approach: Environment Variables

The Go standard library makes environment variables easy:

```go
port := os.Getenv("PORT")
if port == "" {
    port = "8080"
}

dbURL := os.Getenv("DATABASE_URL")
if dbURL == "" {
    log.Fatal("DATABASE_URL required")
}
```

That's it. No configuration provider chain. No dependency injection. Just read the environment.

For typed values:

```go
timeout, err := strconv.Atoi(os.Getenv("TIMEOUT_SECONDS"))
if err != nil {
    timeout = 30  // default
}

debug := os.Getenv("DEBUG") == "true"
```

## Struct-Based Configuration

Most projects define a config struct:

```go
type Config struct {
    Port        string
    DatabaseURL string
    Debug       bool
    Timeout     time.Duration
}

func LoadConfig() (*Config, error) {
    port := os.Getenv("PORT")
    if port == "" {
        port = "8080"
    }
    
    dbURL := os.Getenv("DATABASE_URL")
    if dbURL == "" {
        return nil, errors.New("DATABASE_URL required")
    }
    
    debug := os.Getenv("DEBUG") == "true"
    
    timeout := 30 * time.Second
    if t := os.Getenv("TIMEOUT"); t != "" {
        d, err := time.ParseDuration(t)
        if err != nil {
            return nil, fmt.Errorf("invalid TIMEOUT: %w", err)
        }
        timeout = d
    }
    
    return &Config{
        Port:        port,
        DatabaseURL: dbURL,
        Debug:       debug,
        Timeout:     timeout,
    }, nil
}
```

Then in main:

```go
func main() {
    cfg, err := LoadConfig()
    if err != nil {
        log.Fatalf("config error: %v", err)
    }
    
    server := NewServer(cfg)
    server.Run()
}
```

No interfaces. No DI. Pass the config struct to things that need it.

## envconfig: Less Boilerplate

The `envconfig` package reduces repetition:

```go
import "github.com/kelseyhightower/envconfig"

type Config struct {
    Port        string        `envconfig:"PORT" default:"8080"`
    DatabaseURL string        `envconfig:"DATABASE_URL" required:"true"`
    Debug       bool          `envconfig:"DEBUG" default:"false"`
    Timeout     time.Duration `envconfig:"TIMEOUT" default:"30s"`
}

func LoadConfig() (*Config, error) {
    var cfg Config
    if err := envconfig.Process("", &cfg); err != nil {
        return nil, err
    }
    return &cfg, nil
}
```

Struct tags define environment variable names, defaults, and requirements. Much cleaner.

## Viper: The Kitchen Sink

If you need file-based config, multiple formats, or hot reload, Viper is the standard choice:

```go
import "github.com/spf13/viper"

func LoadConfig() (*Config, error) {
    viper.SetConfigName("config")
    viper.SetConfigType("yaml")
    viper.AddConfigPath(".")
    viper.AddConfigPath("/etc/myapp/")
    
    // Environment variables override file
    viper.AutomaticEnv()
    viper.SetEnvPrefix("MYAPP")
    
    // Defaults
    viper.SetDefault("port", "8080")
    viper.SetDefault("timeout", "30s")
    
    if err := viper.ReadInConfig(); err != nil {
        if _, ok := err.(viper.ConfigFileNotFoundError); !ok {
            return nil, err
        }
        // Config file not found, continue with env vars and defaults
    }
    
    var cfg Config
    if err := viper.Unmarshal(&cfg); err != nil {
        return nil, err
    }
    
    return &cfg, nil
}
```

config.yaml:

```yaml
port: "8080"
database_url: "postgres://localhost/myapp"
debug: false
timeout: "30s"
```

Viper is powerful but adds complexity. Use it when you need it.

## Comparing to .NET

| Feature | .NET IConfiguration | Go |
|---------|---------------------|-----|
| Multiple sources | Built-in | Viper or manual |
| Environment variables | Provider | `os.Getenv` |
| JSON/YAML files | Providers | Viper or manual |
| Strong typing | `IOptions<T>` | Struct + unmarshal |
| Validation | Data annotations | Manual or validator |
| Hot reload | `IOptionsMonitor<T>` | Viper.WatchConfig |
| DI integration | Built-in | Manual |
| Secrets | User secrets, Key Vault | Env vars, external |

.NET's configuration system is more integrated. Go's is simpler but less cohesive.

## Configuration Patterns

### Environment-Specific Loading

```go
func LoadConfig() (*Config, error) {
    env := os.Getenv("APP_ENV")
    if env == "" {
        env = "development"
    }
    
    // Base config
    cfg := Config{
        Port:    "8080",
        Debug:   false,
        Timeout: 30 * time.Second,
    }
    
    // Environment overrides
    switch env {
    case "production":
        cfg.Debug = false
    case "development":
        cfg.Debug = true
    }
    
    // Env vars override everything
    if port := os.Getenv("PORT"); port != "" {
        cfg.Port = port
    }
    // ... more overrides
    
    return &cfg, nil
}
```

### Validation

```go
func (c *Config) Validate() error {
    if c.DatabaseURL == "" {
        return errors.New("database_url is required")
    }
    if c.Port == "" {
        return errors.New("port is required")
    }
    if c.Timeout <= 0 {
        return errors.New("timeout must be positive")
    }
    return nil
}

func LoadConfig() (*Config, error) {
    cfg := &Config{...}
    // ... load values ...
    
    if err := cfg.Validate(); err != nil {
        return nil, fmt.Errorf("config validation: %w", err)
    }
    
    return cfg, nil
}
```

### Immutable Config

Make config read-only after loading:

```go
type Config struct {
    port        string
    databaseURL string
}

func (c *Config) Port() string        { return c.port }
func (c *Config) DatabaseURL() string { return c.databaseURL }

func LoadConfig() *Config {
    return &Config{
        port:        os.Getenv("PORT"),
        databaseURL: os.Getenv("DATABASE_URL"),
    }
}
```

Unexported fields + getter methods = immutable from outside the package.

## What About IOptions<T>?

.NET's `IOptions<T>` pattern has benefits:
- Strongly typed configuration sections
- Validation on startup
- Hot reload with `IOptionsMonitor<T>`
- Clean injection into services

Go's equivalent is just... passing a struct:

```go
// .NET
public class MyService
{
    public MyService(IOptions<DatabaseConfig> options)
    {
        _connectionString = options.Value.ConnectionString;
    }
}

// Go
type MyService struct {
    connString string
}

func NewMyService(cfg *Config) *MyService {
    return &MyService{connString: cfg.DatabaseURL}
}
```

Less ceremony in Go. But also less framework support if you want validation, hot reload, or named options.

## The Honest Take

Go's configuration story is simpler. Whether that's better depends on your needs.

**What Go does well:**
- Environment variables are trivial
- No framework to learn
- Full control over loading logic
- Fast startup (no config system initialization)

**What .NET does better:**
- Integrated with DI
- Multiple providers out of the box
- Better hot reload story
- Options validation built-in
- Secrets management

**The verdict:**
For microservices that read environment variables and a config file, Go's approach is fine. `envconfig` handles 90% of cases.

For complex applications with layered configuration, validation requirements, and hot reload, you'll either use Viper or miss .NET's configuration system.

Start simple. Environment variables and `envconfig` get you far. Reach for Viper when you actually need its features.

---

*Next up: logging with slog—Go's new structured logging standard and how it compares to ILogger.*
