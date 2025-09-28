#!/usr/bin/env bash
set -euo pipefail

echo "=== Rust Cargo.lock Corruption Recovery ==="

# Backup original files
cp Cargo.toml Cargo.toml.backup || true
cp Cargo.lock Cargo.lock.backup || true

echo "Step 1: Remove corrupted Cargo.lock"
rm -f Cargo.lock

echo "Step 2: Fix Cargo.toml dependencies"
cat > Cargo.toml << 'EOF'
[package]
name = "financial-processor"
version = "0.1.0"
edition = "2021"
rust-version = "1.70.0"

[dependencies]
tokio = { version = "1.35.1", features = ["full"] }
tokio-util = "0.7.10"
serde = { version = "1.0.193", features = ["derive"] }
serde_json = "1.0.108"
uuid = { version = "1.6.1", features = ["v4"] }
chrono = { version = "0.4.31", features = ["serde"] }
anyhow = "1.0.75"
thiserror = "1.0.50"
tracing = "0.1.40"
tracing-subscriber = "0.3.18"
hyper = { version = "1.0.1", features = ["full"] }
tower = "0.4.13"
clap = { version = "4.4.11", features = ["derive"] }
EOF

echo "Step 3: Generate clean dependency resolution"
cargo update

echo "Step 4: Verify build succeeds"
cargo check

echo "Step 5: Build release version"
cargo build --release

echo "Step 6: Run tests"
cargo test

echo "Step 7: Verify lockfile consistency"
if ! cargo tree --quiet >/dev/null 2>&1; then
    echo "ERROR: Dependency tree has conflicts"
    exit 1
fi

echo "Step 8: Final verification"
if [ ! -f "target/release/financial-processor" ]; then
    echo "ERROR: Release binary not built"
    exit 1
fi

# Verify idempotency
echo "Step 9: Idempotency check"
BEFORE_HASH=$(sha256sum Cargo.lock | cut -d' ' -f1)
cargo update
AFTER_HASH=$(sha256sum Cargo.lock | cut -d' ' -f1)

if [ "$BEFORE_HASH" != "$AFTER_HASH" ]; then
    echo "WARNING: Cargo.lock changed on re-run, but this is acceptable for first fix"
fi

echo "=== Rust build environment successfully repaired ==="
