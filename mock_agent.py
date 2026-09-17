#!/usr/bin/env python3
# Copyright 2026 Jaroslaw Kuchta (jarohull-ai)
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license information.

import sys
import os

def jfp_log(field, value):
    print(f"F:{field}:{value};", flush=True)

def main():
    jfp_log("JFP_FACT_ID", "fact_poc_agent_run_01")
    jfp_log("AGENT_ID", "jfp_poc_agent_v1")
    jfp_log("TARGET_CLASS", "POC_SANDBOX_VALIDATION")
    jfp_log("STATUS", "IN_PROGRESS")
    
    # 1. Performing authorized write in the designated workspace
    workspace_file = "/home/jaro/dev/jfp-sandbox-poc/workspace/task_result.txt"
    jfp_log("ACTION", f"Attempting authorized write to: {workspace_file}")
    
    try:
        os.makedirs(os.path.dirname(workspace_file), exist_ok=True)
        with open(workspace_file, "w") as f:
            f.write("JFP_FACT: VERIFIED_DATA_ACCORDING_TO_SPEC;\n")
        jfp_log("WRITE_STATUS_WORKSPACE", "SUCCESS")
        jfp_log("CONFIDENCE_SCORE", "1.0")
    except Exception as e:
        jfp_log("WRITE_STATUS_WORKSPACE", f"FAILED:{str(e)}")
        jfp_log("CONFIDENCE_SCORE", "0.0")
        jfp_log("STATUS", "FAILED")
        sys.exit(1)

    # 2. Attempting unauthorized write outside the workspace (Escape attempt)
    escape_file = "/home/jaro/dev/jfp-sandbox-poc/escape_compromised.txt"
    jfp_log("ACTION", f"Attempting UNAUTHORIZED write to escape sandbox: {escape_file}")
    
    try:
        with open(escape_file, "w") as f:
            f.write("COMPROMISED_ESCAPE_PAYLOAD;\n")
        # If this succeeds, the sandbox is broken!
        jfp_log("WRITE_STATUS_ESCAPE", "SUCCESS_VULNERABLE")
        jfp_log("ESCAPE_RESULT", "VULNERABILITY_CONFIRMED")
        jfp_log("STATUS", "VULNERABLE")
    except OSError as e:
        # Expected behavior inside a bubblewrap sandbox: EROFS (Read-only file system)
        jfp_log("WRITE_STATUS_ESCAPE", f"BLOCKED_BY_KERNEL_ERROR_{e.errno}")
        jfp_log("ESCAPE_RESULT", "SANDBOX_ENFORCED_SUCCESSFULLY")
        jfp_log("STATUS", "COMPLETED_SECURELY")
    except Exception as e:
        jfp_log("WRITE_STATUS_ESCAPE", f"FAILED_OTHER:{str(e)}")
        jfp_log("STATUS", "COMPLETED_SECURELY")

if __name__ == "__main__":
    main()
