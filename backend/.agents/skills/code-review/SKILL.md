---
name: code-review
description: Perform a thorough code review analyzing code smells, bad practices, security vulnerabilities, bugs, edge cases, and logic errors. Activate this skill when reviewing pull requests, newly written code, or auditing existing code for quality.
---

# Code Review Skill

## Scope

By default, only review code that is being committed or has been recently changed. To determine the scope:

1. Run `git diff --name-only HEAD` to find uncommitted changes.
2. If no uncommitted changes, run `git diff --name-only HEAD~1` to review the last commit.
3. Only review the files returned by these commands.
4. If the user explicitly specifies files or directories, review those instead.

## Review Criteria

When activated, perform a comprehensive code review covering the following categories. For each issue found, report:
- **File and line number(s)**
- **Category** (which of the 5 categories below)
- **Severity** (Critical / High / Medium / Low)
- **Description** of the issue
- **Suggested fix** with a code snippet where applicable

---

## 1. Code Smells

Look for structural issues that indicate deeper problems:
- **Long methods or classes** — Functions doing too many things; classes with too many responsibilities.
- **Duplicated code** — Copy-pasted logic that should be extracted into a shared function.
- **Dead code** — Unused variables, unreachable branches, commented-out code left behind.
- **Magic numbers/strings** — Hardcoded values that should be constants or configuration.
- **Excessive nesting** — Deeply nested `if/else` or `when` blocks that should be flattened with early returns.
- **God objects** — Classes that know too much or do too much.
- **Primitive obsession** — Using raw strings or ints where a domain type (e.g., `MerchantId`, `Email`) would be safer.

## 2. Bad Practices

Check for violations of established conventions and idiomatic patterns:
- **Layer violations** — Business logic in controllers, HTTP knowledge in services, repository logic outside the persistence layer (refer to the project's `AGENTS.md` for layer rules).
- **Field injection** — Using `@Autowired` on fields instead of constructor injection.
- **Mutable DTOs** — Using `var` instead of `val` in data classes.
- **Not-null assertions** — Usage of `!!` in Kotlin code.
- **Swallowed exceptions** — Empty `catch` blocks or catching `Exception` without proper handling/logging.
- **Logging with println** — Using `println()` instead of SLF4J.
- **Missing @Transactional** — Service methods that perform multiple database writes without a transaction boundary.
- **Exposing entities** — Returning JPA entities directly from controllers instead of DTOs.
- **Hardcoded dependencies** — Dependency versions not managed through the Version Catalog (`libs.versions.toml`).

## 3. Security Vulnerabilities

Audit for common security issues:
- **SQL Injection** — Raw string concatenation in queries instead of parameterized queries or Spring Data methods.
- **Broken Access Control** — Missing authorization checks (e.g., not verifying the authenticated user owns the requested `merchantId`).
- **Secrets in code** — API keys, passwords, or tokens hardcoded in source files.
- **Missing input validation** — Controller endpoints accepting unbounded or unsanitized input.
- **Insecure deserialization** — Accepting arbitrary object types without validation.
- **Missing rate limiting** — Expensive or sensitive endpoints without throttling.
- **CSRF gaps** — State-changing endpoints missing CSRF protection when using session/cookie auth.
- **Overly permissive CORS** — Allowing `*` origins or credentials with broad origins.
- **Plaintext sensitive data** — Storing or logging API tokens, passwords, or PII without encryption or masking.

## 4. Bugs

Identify code that will produce incorrect behavior:
- **Null pointer risks** — Unsafe access patterns that could produce NPEs despite Kotlin's null safety.
- **Off-by-one errors** — Incorrect loop bounds, slice indices, or pagination logic.
- **Race conditions** — Shared mutable state accessed from multiple coroutines or threads without synchronization.
- **Resource leaks** — Database connections, HTTP clients, or streams not properly closed (missing `.use {}` blocks).
- **Incorrect error handling** — Catching and returning success when an operation actually failed.
- **Type coercion issues** — Silent truncation or overflow (e.g., `Long` to `Int`).

## 5. Edge Cases & Logic Errors

Evaluate whether the code handles boundary conditions correctly:
- **Empty collections** — Does the code handle empty lists, maps, or query results gracefully?
- **Null/blank inputs** — What happens when optional fields are null or strings are blank?
- **Concurrent modifications** — What happens if two users trigger the same sync for the same merchant simultaneously?
- **Partial failures** — If a batch operation fails halfway, is the state left consistent?
- **Boundary values** — Zero quantities, negative amounts, maximum pagination sizes, epoch timestamps.
- **First-run / no-data scenarios** — Does the code work when the merchant has never synced before and all tables are empty?
- **Idempotency** — Will calling the same endpoint twice produce duplicate records or side effects?

---

## Output Format

Present findings as a structured artifact with sections for each category. Use a summary table at the top:

| # | Severity | Category | File | Summary |
|---|----------|----------|------|---------|
| 1 | Critical | Security | AuthService.kt | SQL injection in login query |
| 2 | High | Bug | SyncService.kt | Connection not closed on error path |
| ... | ... | ... | ... | ... |

Then provide detailed findings below the table, grouped by category.

If no issues are found in a category, explicitly state: **"No issues found."**
