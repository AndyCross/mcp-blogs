+++
title = "GORM and Friends: When You Do Want an ORM"
date = "2025-01-04"
draft = false
tags = ["go", "dotnet", "database", "orm", "gorm", "csharp"]
+++

Despite Go's "just write SQL" culture, ORMs exist and are popular. GORM is the most widely used. If you're coming from Entity Framework and miss the productivity, GORM might ease the transition.

Fair warning: GORM is controversial in the Go community. Some love it, many avoid it. Let's look at what it offers and the trade-offs.

## Basic GORM Usage

Define a model:

```go
import "gorm.io/gorm"

type User struct {
    ID        uint           `gorm:"primaryKey"`
    Name      string         `gorm:"size:255;not null"`
    Email     string         `gorm:"uniqueIndex;not null"`
    Age       int
    CreatedAt time.Time
    UpdatedAt time.Time
    DeletedAt gorm.DeletedAt `gorm:"index"`  // soft delete
}
```

Connect and auto-migrate:

```go
import (
    "gorm.io/gorm"
    "gorm.io/driver/postgres"
)

dsn := "host=localhost user=postgres password=secret dbname=myapp"
db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{})
if err != nil {
    log.Fatal(err)
}

// Create/update tables from structs
db.AutoMigrate(&User{})
```

## CRUD Operations

**Create:**

```go
user := User{Name: "Alice", Email: "alice@example.com", Age: 30}
result := db.Create(&user)
// user.ID is populated after insert

if result.Error != nil {
    return result.Error
}
fmt.Printf("Inserted %d rows\n", result.RowsAffected)
```

**Read:**

```go
// By primary key
var user User
db.First(&user, 1)  // find by ID

// By condition
db.First(&user, "email = ?", "alice@example.com")

// Multiple
var users []User
db.Where("age > ?", 25).Find(&users)

// All
db.Find(&users)
```

**Update:**

```go
// Update single field
db.Model(&user).Update("Name", "Bob")

// Update multiple fields
db.Model(&user).Updates(User{Name: "Bob", Age: 31})

// Update with map (includes zero values)
db.Model(&user).Updates(map[string]interface{}{"Name": "Bob", "Age": 0})
```

**Delete:**

```go
db.Delete(&user)  // soft delete if DeletedAt field exists
db.Unscoped().Delete(&user)  // hard delete
```

## Comparing to Entity Framework

```csharp
// EF Core
var user = await _context.Users.FindAsync(1);
user.Name = "Bob";
await _context.SaveChangesAsync();
```

```go
// GORM
var user User
db.First(&user, 1)
db.Model(&user).Update("Name", "Bob")
```

Similar concepts, different APIs. GORM doesn't have change tracking like EF—you explicitly call updates.

## Relationships

**One-to-Many:**

```go
type User struct {
    ID     uint
    Name   string
    Orders []Order  // has many
}

type Order struct {
    ID     uint
    UserID uint     // foreign key
    Total  float64
    User   User     // belongs to
}

// Load with association
var user User
db.Preload("Orders").First(&user, 1)

for _, order := range user.Orders {
    fmt.Println(order.Total)
}
```

**Many-to-Many:**

```go
type User struct {
    ID    uint
    Name  string
    Roles []Role `gorm:"many2many:user_roles;"`
}

type Role struct {
    ID   uint
    Name string
}

// Load
db.Preload("Roles").First(&user, 1)

// Associate
db.Model(&user).Association("Roles").Append(&Role{Name: "admin"})
```

## Preloading vs Eager Loading

Like EF's `Include`, GORM has `Preload`:

```go
// Single association
db.Preload("Orders").Find(&users)

// Nested
db.Preload("Orders.Items").Find(&users)

// Conditional preload
db.Preload("Orders", "total > ?", 100).Find(&users)

// All associations
db.Preload(clause.Associations).Find(&users)
```

No lazy loading by default. Explicit preloading only.

## Raw SQL

When the ORM isn't enough:

```go
// Raw query
var users []User
db.Raw("SELECT * FROM users WHERE age > ?", 25).Scan(&users)

// Raw exec
db.Exec("UPDATE users SET age = age + 1 WHERE birthday = ?", today)

// Mix GORM and raw
db.Where("age > ?", 25).Order("name").Find(&users)
```

## Transactions

```go
err := db.Transaction(func(tx *gorm.DB) error {
    if err := tx.Create(&user).Error; err != nil {
        return err  // rollback
    }
    
    if err := tx.Create(&order).Error; err != nil {
        return err  // rollback
    }
    
    return nil  // commit
})
```

Or manual:

```go
tx := db.Begin()
defer func() {
    if r := recover(); r != nil {
        tx.Rollback()
    }
}()

// ... operations on tx ...

tx.Commit()
```

## Hooks (Lifecycle Events)

```go
func (u *User) BeforeCreate(tx *gorm.DB) error {
    u.CreatedAt = time.Now()
    return nil
}

func (u *User) AfterCreate(tx *gorm.DB) error {
    // Send welcome email
    return sendWelcomeEmail(u.Email)
}
```

Like EF's `SaveChanges` interceptors or domain events.

## The Controversies

GORM has critics. Common complaints:

**1. Magic and Reflection**

GORM uses reflection heavily. Errors can be cryptic, and behaviour isn't always obvious.

```go
db.Where("name = ?", name).First(&user)
// What SQL does this generate? Have to check docs or logs.
```

**2. Struct Tag Complexity**

```go
type Product struct {
    ID        uint    `gorm:"primaryKey;autoIncrement"`
    Code      string  `gorm:"type:varchar(100);uniqueIndex"`
    Price     float64 `gorm:"precision:2"`
    CreatedAt time.Time `gorm:"autoCreateTime"`
}
```

The tags can get complex. Errors are runtime, not compile time.

**3. Query Builder Limitations**

Complex queries sometimes fight the API:

```go
// This gets awkward
db.Where("status = ? AND (priority = ? OR deadline < ?)", 
    "active", "high", time.Now())
```

**4. Performance**

Reflection has overhead. For high-throughput scenarios, raw SQL is faster.

## Alternatives to GORM

**sqlx**: Not an ORM, just convenience over `database/sql`:

```go
var users []User
db.SelectContext(ctx, &users, "SELECT * FROM users WHERE age > $1", 25)
```

**ent**: Facebook's ORM, generates type-safe code:

```go
client.User.Query().
    Where(user.AgeGT(25)).
    All(ctx)
```

**sqlc**: Generates Go code from SQL:

```sql
-- queries.sql
-- name: GetUser :one
SELECT * FROM users WHERE id = $1;
```

```go
// Generated code
user, err := queries.GetUser(ctx, userID)
```

**bun**: Lightweight ORM with better SQL control:

```go
err := db.NewSelect().
    Model(&users).
    Where("age > ?", 25).
    Scan(ctx)
```

## The Honest Take

GORM vs EF Core isn't a fair fight. EF is more mature, better integrated with .NET, and has superior tooling.

**When GORM makes sense:**
- You want EF-like productivity
- Your queries are mostly CRUD
- You're okay with the magic
- Team is familiar with ORMs

**When to avoid GORM:**
- Complex queries are common
- Performance is critical
- You prefer explicit SQL
- Team prefers "no magic"

**What GORM does well:**
- Fast development
- Relationship handling
- Migrations (basic)
- Familiar to ORM users

**What EF does better:**
- LINQ (type-safe queries)
- Change tracking
- Migration tooling
- Integration with ASP.NET

**The verdict:**
If you're building a CRUD service and miss EF's productivity, GORM is reasonable. If you're doing complex queries or care about explicit control, stick with `database/sql` + sqlx.

Many Go developers start with GORM, then move to sqlx or sqlc as they get comfortable with Go's explicit style. That's a valid journey.

---

*Next up: tooling—linting, formatting, and why gofmt is non-negotiable.*
