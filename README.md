# JFP Kernel Sandbox (bwrap PoC)

A Proof of Concept (PoC) demonstrating a robust, **kernel-enforced filesystem and resource sandbox** for AI agents. This project aligns with **JFP (JARO Flash Protocol) v14.0.0** and uses Linux **Bubblewrap (`bwrap`)** to enforce strict multi-root security policies, shifting the security boundary from voluntary/advisory agent cooperation to immutable OS-level enforcement.

---

## Why This Project Was Created

Multi-agent environments (like **Orca** or **Viper Chat / AionCore**) often orchestrate autonomous agents with broad host filesystem access. 
* **The Vulnerability:** Traditionally, security has been advisory. For instance, an agent is instructed via a policy or system prompt to "only read/write inside the workspace directory," or is expected to call a permission API (`session/request_permission`) before modifying the system.
* **The Danger:** This boundary is completely unenforceable. If an agent undergoes a **Prompt Injection** attack via an untrusted file or website, the compromised agent will ignore any advisory prompt/system constraints. Since it executes with the host user's shell privileges, it can easily leak SSH keys (`~/.ssh`), exfiltrate AWS credentials (`~/.aws`), or delete critical files.
* **The Axiom:** Any security boundary relying on the cooperative behavior of an LLM is a structural security flaw. **Only a system-level boundary independent of agent behavior can enforce security.**

---

## How the Problem Was Diagnosed

This PoC was inspired by a real-world security fix applied to **AionCore** (the Rust backend of Viper Chat / AionUI) on September 8, 2026. A live-tested agent (Pi) was found to write files outside of its declared workspace without initiating permission checks in its transcript.

To analyze other escape paths beyond simple filesystem writes, we implemented an **Adversarial Critic Scanner** (`exploit_tests.py`) and executed it inside a basic bubblewrap wrapper. We discovered three critical security leaks in standard container mount approaches:

1. **Network Leak:** Processes in standard mount namespaces can still connect to the internet to exfiltrate private credentials.
2. **PID Namespace Leak:** The agent could see all active host processes via `/proc`, allowing it to spy on other user applications or send kill signals.
3. **Environment Leak:** Sensitive host token environment variables (e.g., `ORCA_AGENT_HOOK_TOKEN`, `GITHUB_TOKEN`) were fully leaked, giving a compromised agent pre-authenticated access to host APIs.

---

## The Solution: JFP + Bubblewrap Integration

We designed a two-tiered defensive architecture:

1. **Deterministic Data Exchange (JFP Frame Protocol):**
   Agencies communicate via the **JARO Flash Protocol (JFP)** format (`F:FIELD:VALUE;`). This ensures parsing is entirely deterministic and strict, preventing text-based instruction injection.
2. **Hard Kernel Isolation (bwrap):**
   The agent's shell/interpreter process is wrapped at spawn time inside a Linux namespace sandbox where the root filesystem is mounted entirely read-only (`--ro-bind / /`), sensitive namespaces are unshared, and only explicitly zookept paths defined in `jfp-policy.toml` are overlaid as writeable.

### The Hardened Bubblewrap Sandbox Configuration:
```python
bwrap [
    "--ro-bind", "/", "/",              # Root filesystem is 100% read-only
    "--dev", "/dev",                    # Safe device nodes
    "--proc", "/proc",                  # Clean /proc mount
    "--tmpfs", "/tmp",                  # Clean memory-backed transient temp space
    "--unshare-pid",                    # Prevent seeing host processes
    "--unshare-ipc",                    # Isolate Inter-Process Communication
    "--unshare-uts",                    # Isolate hostname namespace
    "--unshare-net",                    # Disable network stack (blocks data exfiltration)
    "--hostname", "jfp-sandbox",        # Spoof hostname
    "--clearenv",                       # Clear all host environment variables (prevent token leaks)
    "--setenv", "PATH", "/usr/bin:/bin",# Feed only a clean, safe PATH
    "--bind", "/workspace", "/workspace" # Mount policy-approved writable directory ONLY
]
```

---

## Why It Works

When the sandboxed agent attempts to write outside its policy-defined workspace, **the Linux Kernel itself blocks the call at the syscall level**, returning `EROFS` (Read-only file system, error code `30`). 

No shell commands or Python filesystem operations can override this. Even if the agent is fully compromised, it cannot write to `/home/jaro`, spy on processes, or contact an external Command & Control server.

---

## Repository Structure

* `jfp-policy.toml` - Declares the writable workspace root and permissions.
* `sandbox_runner.py` - Parses the policy TOML and dynamically constructs the hardened `bwrap` command.
* `mock_agent.py` - A simulated agent that logs in JFP format, writes inside its workspace, and attempts a sandbox escape write.
* `exploit_tests.py` - An adversarial security auditor scanning for network, process namespace, and environmental leak vectors.
* `run_poc.sh` - Bash script to run and verify the entire vulnerability and validation suite.

---

## How to Run & Verify

Prerequisites: A Linux system with `bubblewrap` installed (`sudo apt install bubblewrap`).

Execute the automated test suite:
```bash
chmod +x run_poc.sh
./run_poc.sh
```

### Verification Outputs:
1. **Test 1 (Vulnerable Mode):** The agent succeeds in escaping and writes `escape_compromised.txt`.
2. **Test 2 (Secure Mode):** The filesystem write is blocked by the kernel (`BLOCKED_BY_KERNEL_ERROR_30`), but the agent safely writes to the approved `workspace/task_result.txt` and continues its run.
3. **Test 3 (Critic Scanner):** The exploit script executes inside the hardened sandbox and reports:
   - `F:TEST_RESULT_NETWORK:SECURE (Blocked as expected: [Errno 101] Network is unreachable);`
   - `F:TEST_RESULT_PID:SECURE (Only saw 2 processes in /proc);`
   - `F:TEST_RESULT_ENV:SECURE (Sensitive host environment variables cleared);`
   - `F:AUDIT_STATUS:ALL_SECURITY_TESTS_PASSED_SECURE;`

---

## Conclusion & Application to Orca

This PoC represents the gold standard of agentic environment isolation. To adapt this to **Orca**, we can implement this exact `bwrap` runner into Orca's terminal spawning logic (`orca terminal create`). When spawning workspace terminals (like Claude Code, Codex, etc.), Orca should automatically shield them behind this JFP-policy-enforcing kernel sandbox, ensuring that developer systems remain fully protected from prompt injections.
