+++
title = "Database Access: database/sql vs Entity Framework"
date = "2025-01-04"
draft = false
tags = ["go", "dotnet", "database", "sql", "csharp"]
+++

Entity Framework is an ORM. It maps objects to tables, generates SQL, tracks changes, handles migrations. You can build entire applications barely writing SQL.

Go's `database/sql` is a thin abstraction over database drivers. You write SQL. You scan results into structs. There's no change tracking, no LINQ, no automatic migrations.

This is going to feel like stepping back twenty years. But there's value in the simplicity.

## The Basics

Connect to a database:

```go
import (
    "database/sql"
    _ "github.com/lib/pq"  // PostgreSQL driver
)

db, err := sql.Open("postgres", "postgres://user:pass@localhost/mydb?sslmode=disable")
if err != nil {
    log.Fatal(err)
}
defer db.Close()

// Verify connection
if err := db.Ping(); err != nil {
    log.Fatal(err)
}
```

The `sql.Open` doesn't actually connect. It just validates the connection string. `Ping` makes the actual connection.

## Querying

Single row:

```go
var user User
err := db.QueryRowContext(ctx, 
    "SELECT id, name, email FROM users WHERE id = $1", 
    userID,
).Scan(&user.ID, &user.Name, &user.Email)

if err == sql.ErrNoRows {
    return nil, ErrNotFound
}
if err != nil {
    return nil, fmt.Errorf("query user: %w", err)
}
```

Multiple rows:

```go
rows, err := db.QueryContext(ctx, "SELECT id, name, email FROM users")
if err != nil {
    return nil, err
}
defer rows.Close()

var users []User
for rows.Next() {
    var u User
    if err := rows.Scan(&u.ID, &u.Name, &u.Email); err != nil {
        return nil, err
    }
    users = append(users, u)
}

if err := rows.Err(); err != nil {
    return nil, err
}
```

Note the explicit `rows.Close()` and `rows.Err()` checks. Nothing is automatic.

## Executing Statements

Insert, update, delete:

```go
result, err := db.ExecContext(ctx,
    "INSERT INTO users (name, email) VALUES ($1, $2)",
    name, email,
)
if err != nil {
    return err
}

id, _ := result.LastInsertId()      // not all drivers support this
affected, _ := result.RowsAffected()
```

## Scanning Structs

You scan columns into variables one by one. This is tedious:

```go
// Manual scanning
rows.Scan(&u.ID, &u.Name, &u.Email, &u.CreatedAt, &u.UpdatedAt)
```

If your SELECT has 15 columns, you write 15 arguments.

Libraries like `sqlx` help:

```go
import "github.com/jmoiron/sqlx"

type User struct {
    ID        int       `db:"id"`
    Name      string    `db:"name"`
    Email     string    `db:"email"`
    CreatedAt time.Time `db:"created_at"`
}

// sqlx scans by struct tag
var users []User
err := db.SelectContext(ctx, &users, "SELECT * FROM users")

var user User
err := db.GetContext(ctx, &user, "SELECT * FROM users WHERE id = $1", id)
```

`sqlx` is `database/sql` with convenience methods. Not an ORM (still raw SQL) but much less boilerplate.

## Transactions

```go
tx, err := db.BeginTx(ctx, nil)
if err != nil {
    return err
}
defer tx.Rollback()  // no-op if committed

_, err = tx.ExecContext(ctx, "UPDATE accounts SET balance = balance - $1 WHERE id = $2", amount, fromID)
if err != nil {
    return err
}

_, err = tx.ExecContext(ctx, "UPDATE accounts SET balance = balance + $1 WHERE id = $2", amount, toID)
if err != nil {
    return err
}

return tx.Commit()
```

The `defer tx.Rollback()` is safe. It does nothing if already committed.

## Connection Pooling

`sql.DB` is a connection pool. Configure it:

```go
db.SetMaxOpenConns(25)              // max concurrent connections
db.SetMaxIdleConns(5)               // max idle connections
db.SetConnMaxLifetime(5 * time.Minute)  // max connection age
db.SetConnMaxIdleTime(1 * time.Minute)  // max idle time
```

This is built in. EF Core has connection pooling too, but you rarely configure it.

## Comparing to Entity Framework

| Feature | Entity Framework | database/sql |
|---------|------------------|--------------|
| Query language | LINQ | Raw SQL |
| Mapping | Automatic (conventions/attributes) | Manual or sqlx |
| Change tracking | Yes | No |
| Migrations | EF Migrations | External tools |
| Connection pooling | Built-in | Built-in |
| Transactions | DbContext/SaveChanges | Explicit Begin/Commit |
| Lazy loading | Supported | No |
| Relationships | Navigation properties | Manual joins |
| Learning curve | Higher | Lower (if you know SQL) |

## The Repository Pattern

Without an ORM, you write repositories manually:

```go
type UserRepository struct {
    db *sql.DB
}

func (r *UserRepository) FindByID(ctx context.Context, id int) (*User, error) {
    var u User
    err := r.db.QueryRowContext(ctx,
        "SELECT id, name, email, created_at FROM users WHERE id = $1",
        id,
    ).Scan(&u.ID, &u.Name, &u.Email, &u.CreatedAt)
    
    if err == sql.ErrNoRows {
        return nil, ErrNotFound
    }
    return &u, err
}

func (r *UserRepository) Create(ctx context.Context, u *User) error {
    return r.db.QueryRowContext(ctx,
        "INSERT INTO users (name, email) VALUES ($1, $2) RETURNING id, created_at",
        u.Name, u.Email,
    ).Scan(&u.ID, &u.CreatedAt)
}

func (r *UserRepository) Update(ctx context.Context, u *User) error {
    _, err := r.db.ExecContext(ctx,
        "UPDATE users SET name = $1, email = $2 WHERE id = $3",
        u.Name, u.Email, u.ID,
    )
    return err
}
```

More code than EF, but you control every query.

## Handling NULLs

SQL NULLs don't map to Go zero values cleanly:

```go
// This fails if middle_name is NULL
var middleName string
rows.Scan(&middleName)  // error: converting NULL to string

// Use sql.NullString
var middleName sql.NullString
rows.Scan(&middleName)
if middleName.Valid {
    fmt.Println(middleName.String)
}

// Or use pointers
var middleName *string
rows.Scan(&middleName)
if middleName != nil {
    fmt.Println(*middleName)
}
```

`sql.NullString`, `sql.NullInt64`, etc. for nullable columns. Or use pointers.

## Migrations

No built-in migrations. Popular tools:

- **golang-migrate**: SQL files, version tracking
- **goose**: SQL or Go migrations
- **atlas**: Schema-as-code approach

```bash
# golang-migrate example
migrate create -ext sql -dir migrations create_users_table
migrate -path migrations -database "postgres://..." up
```

You write the SQL yourself. No automatic schema generation from structs.

## The Honest Take

Going from EF to `database/sql` is a shock. You're back to writing SQL, managing scans, handling nulls manually.

**What Go does well:**
- Full control over queries
- No ORM magic to debug
- Excellent connection pooling
- Predictable performance
- sqlx makes it tolerable

**What EF does better:**
- LINQ for type-safe queries
- Automatic change tracking
- Migration generation
- Navigation properties
- Much less boilerplate

**The verdict:**
If you like writing SQL and want control, `database/sql` is fine. Add `sqlx` for convenience.

If you're building CRUD apps and value productivity over control, you'll miss EF. A lot.

The Go community is more accepting of ORMs than it used to be. GORM exists, and we'll cover it next. But many Go developers prefer the explicit approach.

---

*Next up: GORM. When you do want an ORM, and how it compares to Entity Framework.*
