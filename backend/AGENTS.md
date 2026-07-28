## Backend Coding Guidelines (Kotlin Spring Boot)

### 1. The Controller Layer (Web/Presentation)
- **Responsibility:** Handling HTTP requests, validating input, and returning HTTP responses.
- **NO Business Logic:** Controllers must not contain `if/else` statements dictating business rules.
- **NO Database Knowledge:** Controllers should never inject Repositories.
- **DTOs Only:** Controllers should accept Request DTOs and return Response DTOs. Never expose raw Database Entities.
- **Delegation:** Receive the request, hand it to the Service Layer, wrap the result in `ResponseEntity`.

### 2. The Service Layer (Business Logic)
- **Responsibility:** Enforcing business rules, managing database transactions, and orchestrating external API calls.
- **NO HTTP Knowledge:** Services should never import `HttpServletRequest`, `HttpResponse`, or know about HTTP status codes.
- **Transactions:** Use `@Transactional` at the service level.
- **Authorization:** Check if the user has permission to perform the action.
- **DTO ↔ Entity Mapping:** The Service layer is responsible for converting between DTOs and JPA Entities. Controllers never touch Entities; Repositories never touch DTOs.

### 3. The Persistence Layer (Data Access/Repository)
- **Responsibility:** Fetching and saving data to Supabase (Spring Data JPA).
- **NO Business Logic:** Repositories contain only data retrieval logic.
- **Entities Only:** This layer deals strictly with JPA Entities, not DTOs.

### 4. Package Structure
All backend code must follow this package convention:
```
com.meridian.controller   — REST controllers
com.meridian.service       — Business logic
com.meridian.repository    — JPA repositories
com.meridian.entity        — JPA entities
com.meridian.dto           — Request/Response DTOs
com.meridian.exception     — Domain-specific exceptions
com.meridian.config        — Spring configuration classes (Security, CORS, etc.)
```

### 5. Kotlin & Spring Best Practices
- **Global Exception Handling:** Throw domain-specific exceptions in the Service layer. Use a `@RestControllerAdvice` globally to map these to standard HTTP error responses.
- **Immutability:** Use Kotlin `data class` with `val` for DTOs.
- **Null Safety:** Leverage Kotlin's null safety (`?`). Never use the `!!` (not-null assertion) operator.
- **Constructor Injection:** Always use constructor injection. Never use `@Autowired` on variables (field injection).
- **Dependency Management:** Always use the Version Catalog (`gradle/libs.versions.toml`) to manage dependency versions. Do not hardcode strings (e.g., use `implementation(libs.example)` instead of `implementation("com.example:example:1.0")` in `build.gradle.kts`).
- **Logging:** Use SLF4J via `LoggerFactory`. Never use `println()` for debugging or logging.

### 6. Testing Conventions
- **Unit Tests:** Tests that do not require a database or Spring context. Run with `./gradlew unitTest`.
- **Integration Tests:** Use `@SpringBootTest` with Testcontainers. Tag with `@Tag("integration")` and extend `PostgresIntegrationTest`. Run with `./gradlew integrationTest`.
- **All Tests:** `./gradlew test` runs both unit and integration tests.
- **Controller Tests:** Use `@WebMvcTest` with mocked services to test HTTP layer behavior in isolation.
- **Mocking:** Favor **MockK** over Mockito for mocking dependencies in Kotlin (e.g., use `mockk<Service>()` and `coEvery { ... }`).
- **Shared Base:** All integration tests must extend `com.meridian.support.PostgresIntegrationTest` to reuse the Testcontainers setup. Do not duplicate the `companion object` boilerplate.

### 7. Code Formatting
- **KtLint:** Always run `./gradlew ktlintFormat` from the `backend` directory after making any Kotlin code changes to ensure consistent styling.

### 8. Agent Behavior
- **Granular Implementation:** Do not write the entire feature at once. Break the implementation down into granular steps (e.g., one class, one complex method, or one layer at a time).
- **Mandatory Review Pauses:** After completing a granular step, **stop working completely** and ask the user to review the code (`git diff` or in-IDE). Do not proceed to the next class or method until the user explicitly confirms the code is correct and says to move on.
- **Explicit Permission Required:** Always check with the user and ask for explicit permission before modifying any existing code, making architectural changes, or executing commands that alter the environment.

### 9. External Services & Configuration
- **Interfaces First:** Any service that interacts with an external API (like Supabase Auth, Stripe, etc.) must implement an interface (e.g., `AuthService`). This allows for easy mocking in tests and swap-ability.
- **Naming Convention:** Implementations of these interfaces should append `Impl` to the descriptive name (e.g., `SupabaseAuthServiceImpl` implements `AuthService`).
- **Configuration Beans:** Do not use `@Service` or `@Component` directly on external service implementations. Instead, create a `@Configuration` class (e.g., `AuthConfig`) and explicitly declare the implementation using an `@Bean` method.
