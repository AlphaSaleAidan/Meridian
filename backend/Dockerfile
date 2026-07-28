# --- Build stage ---
FROM eclipse-temurin:26-jdk AS build
WORKDIR /app

# Install Gradle wrapper deps
COPY gradlew gradlew
COPY gradle/ gradle/
RUN chmod +x gradlew

# Cache dependencies — copy build files first
COPY build.gradle.kts settings.gradle.kts ./
RUN ./gradlew dependencies --no-daemon || true

# Copy source and build
COPY src/ src/
RUN ./gradlew bootJar --no-daemon -x test

# --- Runtime stage ---
FROM eclipse-temurin:26-jre-alpine
WORKDIR /app

RUN addgroup -S meridian && adduser -S meridian -G meridian \
    && apk add --no-cache curl

COPY --from=build /app/build/libs/*.jar app.jar

EXPOSE 8080

USER meridian

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8080/api/health || exit 1

ENTRYPOINT ["java", "-jar", "app.jar"]
