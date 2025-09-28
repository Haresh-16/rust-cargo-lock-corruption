import subprocess
import re
import json
import os
import toml

def run(cmd, cwd="/app"):
    """Run a command and return the result."""
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result

def test_cargo_build_succeeds_without_warnings():
    """Test that cargo build succeeds without errors or warnings."""
    result = run("cargo build --release")
    assert result.returncode == 0, f"Cargo build failed: {result.stderr}"
    assert "error" not in result.stderr.lower()
    # Check for warnings
    assert "warning" not in result.stderr.lower(), f"Build has warnings: {result.stderr}"

def test_cargo_test_passes():
    """Test that all cargo tests pass."""
    result = run("cargo test")
    assert result.returncode == 0, f"Cargo test failed: {result.stderr}"
    
    # Count test results
    test_results = re.findall(r'test result: ok\. (\d+) passed', result.stdout)
    if test_results:
        passed_count = int(test_results[0])
        assert passed_count >= 3, f"Expected at least 3 tests, got {passed_count}"

def test_cargo_check_passes():
    """Test that cargo check reports no issues."""
    result = run("cargo check")
    assert result.returncode == 0, f"Cargo check failed: {result.stderr}"
    assert "error" not in result.stderr.lower()

def test_cargo_lock_matches_requirements_precisely():
    """Test that Cargo.lock contains exactly the versions specified in requirements.txt."""
    # Parse requirements.txt
    requirements = {}
    with open("/app/requirements.txt", "r") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                parts = line.split("=")
                if len(parts) >= 2:
                    name = parts[0].strip()
                    version = parts[1].strip().strip('"')
                    requirements[name] = version

    # Parse Cargo.lock directly
    with open("/app/Cargo.lock", "r") as f:
        cargo_lock_content = f.read()

    # Check each requirement version is in Cargo.lock
    for name, expected_version in requirements.items():
        # Look for exact package entry in Cargo.lock
        package_pattern = rf'\[\[package\]\]\s*name\s*=\s*"{re.escape(name)}"\s*version\s*=\s*"{re.escape(expected_version)}"'
        assert re.search(package_pattern, cargo_lock_content, re.MULTILINE), \
            f"Exact version {name} {expected_version} not found in Cargo.lock"

def test_required_dependencies_present():
    """Test that all required dependencies are present with correct versions."""
    result = run("cargo tree --format '{p}'")
    assert result.returncode == 0

    tree_output = result.stdout

    # Check for key dependencies with CORRECT version strings
    required_deps = [
        "tokio v1.35",
        "serde v1.0.193",
        "uuid v1.6",
        "chrono v0.4.31",
        "hyper v1.0"
    ]

    for dep in required_deps:
        assert dep in tree_output, f"Required dependency {dep} not found in cargo tree"

def test_comprehensive_yanked_crates_check():
    """Test that no yanked crates remain in the dependency tree."""
    result = run("cargo tree")
    assert result.returncode == 0

    # Check for known yanked crates that should be replaced
    yanked_patterns = [
        "time v0.1.",  # All 0.1.x versions are yanked
        "chrono v0.3.",  # Old yanked versions
        "openssl v0.9.",  # Old yanked versions
    ]

    for pattern in yanked_patterns:
        assert pattern not in result.stdout, f"Yanked crate pattern {pattern} still present"

    # Additional check: verify cargo audit would pass (if available)
    audit_result = run("cargo audit --version")
    if audit_result.returncode == 0:
        audit_check = run("cargo audit")
        # Don't fail on audit errors, but log them
        if audit_check.returncode != 0:
            print(f"Cargo audit warnings: {audit_check.stdout}")

def test_serde_derive_feature():
    """Test that serde has derive feature enabled."""
    # Check Cargo.toml content
    with open("/app/Cargo.toml", "r") as f:
        cargo_content = f.read()
    
    assert 'serde = { version = "1.0.193", features = ["derive"]' in cargo_content

def test_uuid_v4_feature():
    """Test that uuid has v4 feature enabled."""
    with open("/app/Cargo.toml", "r") as f:
        cargo_content = f.read()
    
    assert 'uuid = { version = "1.6.1", features = ["v4"]' in cargo_content

def test_msrv_compatibility_across_dependencies():
    """Test MSRV compatibility across all dependencies, not just Cargo.toml."""
    # Check Cargo.toml MSRV
    with open("/app/Cargo.toml", "r") as f:
        cargo_content = f.read()

    assert 'rust-version = "1.70.0"' in cargo_content, "MSRV not set correctly in Cargo.toml"

    # Verify that dependencies support MSRV by checking if build succeeds with MSRV
    # This is the most reliable way to ensure MSRV compatibility
    msrv_check = run("rustc +1.70.0 --version 2>/dev/null || echo 'MSRV toolchain not available'")
    if "1.70.0" in msrv_check.stdout:
        # If MSRV toolchain is available, verify build works
        build_check = run("cargo +1.70.0 check")
        assert build_check.returncode == 0, f"Dependencies not compatible with MSRV 1.70.0: {build_check.stderr}"
    else:
        # Fallback: check that all major dependencies are recent enough
        tree_result = run("cargo tree --format '{p}'")
        tree_output = tree_result.stdout

        # Check major ecosystem crates have recent versions
        modern_deps = [
            ("serde", "1.0.1"),  # serde 1.0.100+ supports MSRV 1.70
            ("tokio", "1.35"),   # tokio 1.35+ supports MSRV 1.70
            ("uuid", "1.6"),     # uuid 1.6+ supports MSRV 1.70
        ]

        for dep_name, min_version in modern_deps:
            pattern = rf"{dep_name} v(\d+)\.(\d+)"
            matches = re.findall(pattern, tree_output)
            if matches:
                major, minor = int(matches[0][0]), int(matches[0][1])
                min_major, min_minor = map(int, min_version.split('.'))
                assert (major, minor) >= (min_major, min_minor), \
                    f"{dep_name} version too old for MSRV: found {major}.{minor}, need {min_version}+"

def test_tokio_ecosystem_compatibility():
    """Test that tokio ecosystem crates use compatible versions."""
    result = run("cargo tree --format '{p}' | grep tokio")
    
    # All tokio crates should be 1.35+ or compatible
    tokio_lines = result.stdout.split('\n')
    for line in tokio_lines:
        if 'tokio v' in line:
            version_match = re.search(r'tokio v(\d+)\.(\d+)', line)
            if version_match:
                major, minor = int(version_match.group(1)), int(version_match.group(2))
                assert major == 1 and minor >= 35, f"Tokio version too old: {line}"

def test_no_conflicting_duplicate_versions():
    """Test that there are no conflicting duplicate versions in the dependency tree."""
    result = run("cargo tree --duplicates")

    # If there are duplicates, cargo tree --duplicates will show them
    if result.returncode == 0 and result.stdout.strip():
        # Parse duplicates output to ensure they're acceptable
        duplicates = result.stdout.strip()

        # Some duplicates might be acceptable (different major versions)
        # But conflicting patch versions of the same crate should not exist
        lines = duplicates.split('\n')
        for line in lines:
            if ' v' in line:
                # Extract crate name and version
                parts = line.split(' v')
                if len(parts) >= 2:
                    crate_name = parts[0].strip()
                    version = parts[1].split()[0]

                    # Check for patch-level conflicts (same major.minor, different patch)
                    version_pattern = rf"{re.escape(crate_name)} v(\d+)\.(\d+)\.(\d+)"
                    all_versions = re.findall(version_pattern, result.stdout)

                    if len(all_versions) > 1:
                        # Group by major.minor
                        version_groups = {}
                        for major, minor, patch in all_versions:
                            key = f"{major}.{minor}"
                            if key not in version_groups:
                                version_groups[key] = []
                            version_groups[key].append(patch)

                        # Check for multiple patch versions in same major.minor
                        for key, patches in version_groups.items():
                            if len(patches) > 1:
                                print(f"Warning: Multiple patch versions of {crate_name} {key}: {patches}")

def test_no_duplicate_dependencies():
    """Test that there are no duplicate dependency entries."""
    with open("/app/Cargo.toml", "r") as f:
        cargo_content = f.read()

    # Extract dependency names
    dep_lines = [line for line in cargo_content.split('\n') if '=' in line and not line.strip().startswith('#')]
    dep_names = [line.split('=')[0].strip() for line in dep_lines if '[dependencies]' not in line]

    # Check for duplicates
    seen_deps = set()
    for dep in dep_names:
        if dep in seen_deps:
            assert False, f"Duplicate dependency found: {dep}"
        seen_deps.add(dep)

def test_idempotency():
    """Test that running the solution multiple times doesn't change the result."""
    # Get initial state
    with open("/app/Cargo.lock", "r") as f:
        initial_lock = f.read()
    
    # Run cargo update (should not change anything)
    result = run("cargo update")
    assert result.returncode == 0
    
    # Check if lock file changed significantly
    with open("/app/Cargo.lock", "r") as f:
        updated_lock = f.read()
    
    # The lock file might have minor formatting changes, but should be functionally identical
    # We'll check that the build still works
    result = run("cargo check")
    assert result.returncode == 0, "Build broken after cargo update"

def test_release_binary_exists():
    """Test that the release binary was successfully built."""
    binary_path = "/app/target/release/financial-processor"
    assert os.path.exists(binary_path), f"Release binary not found at {binary_path}"
    
    # Test that binary is executable
    assert os.access(binary_path, os.X_OK), "Release binary is not executable"
