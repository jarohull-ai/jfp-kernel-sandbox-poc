# JFP Kernel Sandbox (bwrap PoC)

A Proof of Concept (PoC) demonstrating a robust, **kernel-enforced filesystem and resource sandbox** for autonomous AI agents. This project aligns with **JFP (JARO Flash Protocol) v14.0.0** and uses Linux **Bubblewrap (`bwrap`)** to enforce strict multi-root security policies, shifting the security boundary from voluntary/advisory agent cooperation to immutable OS-level enforcement.

---

## Why This Matters

Multi-agent orchestration frameworks and agent runtime environments often execute autonomous code generators or file-handling agents with broad host filesystem access. 
* **The Vulnerability:** Traditionally, security has been advisory. For instance, an agent is instructed via system prompts to "only read/write inside the workspace directory," or is expected to voluntarily call a permission verification API before acting.
* **The Danger:** This boundary is completely unenforceable. If an agent undergoes a **Prompt Injection** attack via an untrusted file, email, or crawled website, the compromised agent will ignore any advisory system constraints. Since it executes with the host user's shell privileges, it can easily exfiltrate private SSH keys, leak API tokens, or corrupt system configurations.
* **The Axiom:** Any security boundary relying on the cooperative behavior of an LLM is a structural security flaw. **Only an operating system-level boundary independent of agent behavior can enforce security.**

---

## Technical Deconstruction of the Problem

To analyze potential escape paths beyond simple filesystem writes, we implemented an **Adversarial Critic Scanner** (`exploit_tests.py`) and executed it inside a basic namespace wrapper. We identified three major security leaks common in naive agent container mount setups:

1. **Network Leak:** Processes inside standard namespaces can still connect to the internet to exfiltrate private credentials.
2. **PID Namespace Leak:** The agent can see all active host processes via `/proc`, allowing it to spy on other user applications or send signals to host processes.
3. **Environment Leak:** Sensitive host token environment variables are fully leaked, giving a compromised agent pre-authenticated access to host APIs.

---

## The Solution: JFP + Bubblewrap Integration

This PoC demonstrates a two-tiered defensive architecture applicable to any agent runtime or multi-agent system:

1. **Deterministic Data Exchange (JFP Frame Protocol):**
   Agents communicate via the **JARO Flash Protocol (JFP)** format (`F:FIELD:VALUE;`). This ensures parsing is entirely deterministic and strict, preventing text-based instruction injection during multi-agent handoffs.
2. **Hard Kernel Isolation (bwrap):**
   The agent's process is wrapped at spawn time inside a Linux namespace sandbox where the root filesystem is mounted entirely read-only (`--ro-bind / /`), sensitive namespaces are unshared, and only explicitly defined paths in `jfp-policy.toml` are overlaid as writeable.

### Hardened Sandbox Configuration Pattern:
```bash
bwrap \
    --ro-bind / / \
    --dev /dev \
    --proc /proc \
    --tmpfs /tmp \
    --unshare-pid \
    --unshare-ipc \
    --unshare-uts \
    --unshare-net \
    --hostname jfp-sandbox \
    --clearenv \
    --setenv PATH /usr/bin:/bin \
    --bind /workspace /workspace
```

---

## Why It Works

When the sandboxed agent attempts to write outside its policy-defined workspace, **the Linux Kernel itself blocks the call at the syscall level**, returning `EROFS` (Read-only file system, error code `30`). 

No shell commands or filesystem operations can override this. Even if the agent is fully compromised, it cannot write to `/home`, spy on processes, or contact an external Command & Control server.

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

## How to Integrate with Any Agent Runtime

Any multi-agent framework or IDE spawning agent subprocesses can implement this pattern:
1. **Define a Policy Schema:** Maintain a simple TOML or JSON policy declaring allowed workspace directories (`roots`).
2. **Wrap Spawning Logic:** Modify the process spawner (whether in Rust, Node, Python, or Go) to construct and invoke the executable wrapped in the `bwrap` utility rather than a direct shell invocation.
3. **Format Inputs/Outputs:** Enforce deterministic frame structures (like JFP) on stdin/stdout to block any shell or instruction injection attacks.

---

## License

This project is licensed under the Apache License 2.0 — see the [LICENSE](LICENSE) file for details.

Copyright 2026 Jaroslaw Kuchta (jarohull-ai)
