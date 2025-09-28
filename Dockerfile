FROM rust:1.70-alpine

# Ensure standard directories exist for terminal-bench
RUN mkdir -p /tmp /var/tmp /usr/local/bin

# Install only runtime dependencies (NO test dependencies)
RUN apk add --no-cache \
    bash \
    curl \
    git \
    build-base \
    openssl-dev

# Create app directory
RUN mkdir -p /app

# Copy only essential runtime files (NO solution or tests)
COPY Cargo.toml /app/
COPY Cargo.lock /app/
COPY requirements.txt /app/
COPY src/ /app/src/
COPY run-tests.sh /app/

# Set executable permissions
RUN chmod +x /app/run-tests.sh

# Set working directory
WORKDIR /app

# Initialize a broken Rust project state
RUN rustc --version && cargo --version

CMD ["tail", "-f", "/dev/null"]
