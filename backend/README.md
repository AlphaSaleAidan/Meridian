# Meridian Backend

This is the Kotlin Spring Boot backend for Meridian.

## Getting Started Locally

We provide an automated script to boot up the local environment, which includes the Supabase stack (Database, Auth API, Edge Functions) and the Spring Boot Backend running via Docker Compose.

### Prerequisites
- [Docker](https://www.docker.com/) & Docker Compose
- [Supabase CLI](https://supabase.com/docs/guides/cli) (`brew install supabase/tap/supabase`)

### 1. Start the Environment
From the `backend/` directory, simply run:
```bash
./scripts/start-local.sh
```

This script will:
1. Boot up your local Supabase stack (`supabase start`).
2. Build and start the Meridian Backend container (`docker-compose up --build`).

### 2. Testing the APIs
Once running, the backend is available at `http://localhost:8080`.

**Signup**
```bash
curl -X POST http://localhost:8080/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "securepassword123"}'
```

**Login (save session)**
```bash
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "securepassword123"}' \
  -c cookies.txt
```

**Access Protected Route**
```bash
curl -X GET http://localhost:8080/api/health \
  -b cookies.txt
```

### Alternative: Running Without Docker
If you prefer to run the Spring Boot app directly on your host machine (e.g. from IntelliJ or via Gradle), ensure the Supabase stack is running first:

```bash
cd supabase
supabase start
```
Then start the app with the `local` profile:
```bash
./gradlew bootRun --args='--spring.profiles.active=local'
```
