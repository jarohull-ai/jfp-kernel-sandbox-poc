#!/usr/bin/env bash
set -e

POC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ESCAPE_FILE="${POC_DIR}/escape_compromised.txt"
WORKSPACE_FILE="${POC_DIR}/workspace/task_result.txt"

# Ensure executable permissions
chmod +x "${POC_DIR}/mock_agent.py"
chmod +x "${POC_DIR}/exploit_tests.py"
chmod +x "${POC_DIR}/sandbox_runner.py"

# Clean up before testing
rm -f "$ESCAPE_FILE"
rm -f "$WORKSPACE_FILE"

echo "=========================================================================="
echo "      JFP & BUBBLEWRAP KERNEL SANDBOX PROOF OF CONCEPT (PoC) "
echo "=========================================================================="
echo ""

# PHASE 1: VULNERABLE RUN (NO SANDBOX)
echo "--- TEST 1: AGENT RUN OUTSIDE SANDBOX (VULNERABLE) ---"
python3 "${POC_DIR}/sandbox_runner.py" --no-sandbox

# Verify escape file presence
if [ -f "$ESCAPE_FILE" ]; then
    echo "Verification: Escape file WAS successfully written to the host filesystem!"
    echo "Content of escape file: $(cat "$ESCAPE_FILE")"
    echo "STATUS: VULNERABLE TO EXPLOIT (Agent has full host filesystem access)."
else
    echo "STATUS: Escape file was not written (unexpected)."
fi
echo ""

# Clean up before Phase 2
rm -f "$ESCAPE_FILE"
rm -f "$WORKSPACE_FILE"

# PHASE 2: SECURE RUN (WITH KERNEL SANDBOX ENFORCED VIA JFP POLICY)
echo "--- TEST 2: AGENT RUN INSIDE KERNEL-ENFORCED JFP SANDBOX (SECURE) ---"
python3 "${POC_DIR}/sandbox_runner.py"

# Verify escape file absence & workspace file presence
if [ -f "$ESCAPE_FILE" ]; then
    echo "ERROR: Escape file was written! The sandbox failed."
else
    echo "Verification: No escape file exists outside the workspace! Kernel-level protection worked."
fi

if [ -f "$WORKSPACE_FILE" ]; then
    echo "Verification: Authorized file was successfully written to: $WORKSPACE_FILE"
    echo "Content of authorized file: $(cat "$WORKSPACE_FILE")"
else
    echo "ERROR: Authorized file was not written."
fi
echo ""

# PHASE 3: AUDITING THE SECURITY HOLES IN THE SANDBOX (EXPLOIT TESTS)
echo "--- TEST 3: RUNNING THE ADVERSARIAL CRITIC SCANNER ---"
echo "We will run exploit_tests.py inside the sandbox to search for leaks in network, PID, and environment variables..."
echo ""
python3 "${POC_DIR}/sandbox_runner.py" "${POC_DIR}/exploit_tests.py"

# Clean up temporary test files at the end of execution
rm -f "$ESCAPE_FILE"
rm -f "$WORKSPACE_FILE"

echo "=========================================================================="
echo " PoC COMPLETED SUCCESSFULLY: JFP deterministic tracing and kernel-level "
echo " bubblewrap sandboxing fully verified and audited! "
echo "=========================================================================="
