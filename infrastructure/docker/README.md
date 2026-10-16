# Containerized Execution Sandbox Infrastructure

This directory contains the container specifications and security constraints for the Concept-Aware Code Evaluation SaaS execution runner.

## Security Constraints Enforced

When running in containerized mode (`EXECUTION_RUNNER_MODE=docker`), every untrusted student submission is executed inside an ephemeral Docker container with the following active constraints:

| Security Constraint | Docker Flag | Purpose |
|---|---|---|
| **Non-Root Identity** | `--user=10001:10001` | Runs as unprivileged `sandbox` user. Prevents host root escalation. |
| **Network Egress Blocked** | `--network=none` | Disables network interfaces except loopback. Prevents data exfiltration and SSRF. |
| **Read-Only Root Filesystem** | `--read-only` | Root filesystem (`/`) is immutable. Untrusted scripts cannot modify binaries or libraries. |
| **Dedicated Tmpfs** | `--tmpfs /tmp:rw,noexec,nosuid,size=32m`<br>`--tmpfs /sandbox/workspace:rw,size=64m` | Provides in-memory scratch space with `noexec` to block binary drop-and-execute attacks. |
| **Drop Linux Capabilities** | `--cap-drop=ALL` | Strips all Linux kernel capabilities (including `CAP_NET_RAW`, `CAP_SYS_ADMIN`). |
| **Prevent Privilege Escalation**| `--security-opt=no-new-privileges:true` | Forbids processes from gaining additional privileges via `setuid` binaries. |
| **Cgroup Memory Limit** | `--memory=128m --memory-swap=128m` | Hard memory boundary. Prevents memory exhaustion / host OOM crashes. |
| **Cgroup CPU Quota** | `--cpus=1.0` | Prevents CPU starvation by infinite computational loops. |
| **Process Limit (PIDs)** | `--pids-limit=64` | Defends against fork bombs and infinite thread creation attacks. |
| **No Host Mounts** | `-v <script_path>:/sandbox/submission.py:ro` | Only the single temporary submission script is mounted, strictly read-only. No host paths are exposed. |
| **Automatic Cleanup** | `--rm` | Container state is destroyed immediately upon exit. |

## Build and Setup Instructions

### 1. Build the Hardened Runner Image
```bash
docker build -t concept-eval-runner:latest -f infrastructure/docker/runner.Dockerfile .
```

### 2. Verify Container Hardening
Run the image with security flags to verify that network and filesystem access are locked down:

```bash
# Verify non-root user (should output 10001)
docker run --rm concept-eval-runner:latest -c "import os; print(os.getuid())"

# Verify network access is blocked (should raise OSError: Network is unreachable)
docker run --rm --network=none concept-eval-runner:latest -c "import urllib.request; urllib.request.urlopen('http://1.1.1.1', timeout=1)"

# Verify root filesystem is read-only (should raise Read-only file system error)
docker run --rm --read-only concept-eval-runner:latest -c "open('/test.txt', 'w').write('exploit')"
```

## Fail-Safe Policy

If `EXECUTION_RUNNER_MODE=docker` is configured (or in `APP_ENV=production`) and the Docker daemon is offline or unavailable:
1. `DockerRunner.is_available()` returns `False`.
2. `CodeExecutor` returns `error_type="SANDBOX_UNAVAILABLE"`.
3. **The system NEVER falls back to executing student code directly on the host.**
4. The evaluation task catches the infrastructure failure, triggers bounded retries, and marks `submission.status = "infrastructure_error"`.
