#!/usr/bin/env python3
# Copyright 2026 Jaroslaw Kuchta (jarohull-ai)
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license information.

import sys
import os
import subprocess
import re

def parse_policy(policy_path):
    """
    Simple, robust parser for the jfp-policy.toml file, 
    independent of Python version (no external dependencies).
    """
    roots = []
    allow_network_fetch = False
    
    with open(policy_path, "r") as f:
        content = f.read()
    
    # Extract roots
    blocks = re.split(r'\[\[roots\]\]', content)
    for block in blocks[1:]:
        path_match = re.search(r'path\s*=\s*["\']([^"\']+)["\']', block)
        access_match = re.search(r'access\s*=\s*["\']([^"\']+)["\']', block)
        if path_match and access_match:
            roots.append({
                "path": path_match.group(1),
                "access": access_match.group(1)
            })
            
    # Extract allow_network_fetch
    net_match = re.search(r'allow_network_fetch\s*=\s*(true|false)', content)
    if net_match:
        allow_network_fetch = (net_match.group(1) == "true")
        
    return roots, allow_network_fetch

def run_agent(sandbox_enabled, target_script):
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    policy_path = os.path.join(BASE_DIR, "jfp-policy.toml")
    
    roots, allow_network_fetch = parse_policy(policy_path)
    
    if not sandbox_enabled:
        print(f">>> RUNNING {target_script} WITHOUT SANDBOX (VULNERABLE MODE) <<<", flush=True)
        # Execute directly
        cmd = [sys.executable, target_script]
        env = os.environ.copy()
    else:
        print(f">>> RUNNING {target_script} WITH SECURE KERNEL-ENFORCED JFP SANDBOX <<<", flush=True)
        
        # Base bubblewrap sandbox with robust isolation namespaces
        cmd = [
            "bwrap",
            "--ro-bind", "/", "/",
            "--dev", "/dev",
            "--proc", "/proc",
            "--tmpfs", "/tmp",
            "--unshare-pid",     # Isolate process IDs (completely hide host processes)
            "--unshare-ipc",     # Isolate IPC namespace
            "--unshare-uts",     # Isolate UTS namespace (needed to override hostname)
            "--hostname", "jfp-sandbox", # Virtual hostname
            "--clearenv",        # Wipe out host environment variables to prevent token leaks
            "--setenv", "PATH", "/usr/bin:/bin:/usr/local/bin",
            "--setenv", "TERM", "xterm-256color",
            "--setenv", "LANG", "C.UTF-8"
        ]
        
        # Enforce network isolation based on JFP policy
        # Note: We skip --unshare-net in GitHub Actions environments to avoid loopback RTM_NEWADDR failures in virtualized containers.
        if not allow_network_fetch and os.environ.get("GITHUB_ACTIONS") != "true":
            cmd.append("--unshare-net") # Completely block internet access
            
        # Add writable binds for roots from JFP policy
        for root in roots:
            # Replace hardcoded home path with local BASE_DIR for portability
            path = root["path"].replace("/home/jaro/dev/jfp-sandbox-poc", BASE_DIR)
            if root["access"] == "read-write":
                os.makedirs(path, exist_ok=True)
                cmd.extend(["--bind", path, path])
        
        # Append the command to execute the target script
        cmd.extend([sys.executable, target_script])
        env = {} # Keep empty, as bwrap clears environment via --clearenv anyway
        
    # Execute the process and capture output
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True, env=env if not sandbox_enabled else None)
        print(proc.stdout)
    except subprocess.CalledProcessError as e:
        print(f"ERROR executing process: {e}")
        print(f"STDOUT:\n{e.stdout}")
        print(f"STDERR:\n{e.stderr}")

if __name__ == "__main__":
    sandbox = True
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    target = os.path.join(BASE_DIR, "mock_agent.py")
    
    # Simple command line parsing
    args = sys.argv[1:]
    if "--no-sandbox" in args:
        sandbox = False
        args.remove("--no-sandbox")
        
    if len(args) > 0:
        target = args[0]
        
    run_agent(sandbox, target)
