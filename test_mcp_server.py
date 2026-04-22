"""
Test MCP server via stdio using proper JSON-RPC framing.
"""

import json
import os
import subprocess
import sys
import threading
import time
import queue

BASE_DIR = "/Users/mohammadsayeed/Documents/Tata_Digital/main_folder_vscode/hackathon"


def reader_thread(pipe, q, label):
    """Read lines from a pipe and put them in a queue."""
    try:
        for line in iter(pipe.readline, ""):
            q.put((label, line.rstrip("\n")))
    except Exception as e:
        q.put((label, f"ERROR: {e}"))
    finally:
        q.put((label, None))


def main():
    print("=" * 60)
    print("MCP Server Independent Test (v2)")
    print("=" * 60)

    env = {
        **os.environ,
        "FASTMCP_TRANSPORT": "stdio",
        "SUPERSET_SECRET_KEY": "test-secret-key-for-mcp-testing-1234567890",
    }

    print("\n[1] Starting MCP server...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "superset.mcp_service"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=BASE_DIR,
        env=env,
        bufsize=1,
    )

    stdout_q = queue.Queue()
    stderr_q = queue.Queue()
    threading.Thread(target=reader_thread, args=(proc.stdout, stdout_q, "stdout"), daemon=True).start()
    threading.Thread(target=reader_thread, args=(proc.stderr, stderr_q, "stderr"), daemon=True).start()

    print("   Waiting for startup (15s)...")
    start = time.time()
    while time.time() - start < 15:
        try:
            label, line = stderr_q.get(timeout=0.5)
            if line is not None:
                print(f"   [stderr] {line}")
        except queue.Empty:
            pass

    if proc.poll() is not None:
        print(f"   ❌ Server exited with code {proc.returncode}")
        return 1

    print(f"   ✅ Server running (PID {proc.pid})")

    def send_msg(msg):
        raw = json.dumps(msg)
        try:
            proc.stdin.write(raw + "\n")
            proc.stdin.flush()
        except BrokenPipeError:
            print("   ❌ Broken pipe - server died")
            return False
        return True

    def recv_msg(timeout=30):
        start = time.time()
        while time.time() - start < timeout:
            try:
                while True:
                    label, line = stderr_q.get_nowait()
                    if line is not None:
                        print(f"   [stderr] {line}")
            except queue.Empty:
                pass
            try:
                label, line = stdout_q.get(timeout=1.0)
                if line is None:
                    print("   [stdout] EOF")
                    return None
                if line.strip():
                    try:
                        return json.loads(line)
                    except json.JSONDecodeError:
                        print(f"   [stdout non-json] {line[:200]}")
            except queue.Empty:
                pass
        return None

    tests_passed = 0
    tests_failed = 0

    # Test 1: Initialize
    print("\n[2] Test: Initialize")
    ok = send_msg({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    })
    if not ok:
        return 1

    resp = recv_msg(timeout=30)
    if resp and "result" in resp:
        print(f"   ✅ Initialize OK: {json.dumps(resp['result'].get('serverInfo', {}))}")
        tests_passed += 1
        send_msg({"jsonrpc": "2.0", "method": "notifications/initialized"})
        time.sleep(2)
    else:
        print(f"   ❌ Initialize failed: {resp}")
        tests_failed += 1

    # Test 2: List Tools
    print("\n[3] Test: List Tools")
    send_msg({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    resp = recv_msg(timeout=30)
    if resp and "result" in resp:
        tools = resp["result"].get("tools", [])
        names = sorted(t["name"] for t in tools)
        print(f"   ✅ Found {len(tools)} tools: {', '.join(names)}")
        expected = {"health_check", "list_dashboards", "list_charts", "execute_sql"}
        missing = expected - set(names)
        if missing:
            print(f"   ⚠️  Missing: {missing}")
            tests_failed += 1
        else:
            tests_passed += 1
    else:
        print(f"   ❌ List tools failed: {resp}")
        tests_failed += 1

    # Test 3: health_check
    print("\n[4] Test: Call health_check")
    send_msg({
        "jsonrpc": "2.0", "id": 3,
        "method": "tools/call",
        "params": {"name": "health_check", "arguments": {}},
    })
    resp = recv_msg(timeout=30)
    if resp and "result" in resp:
        content = resp["result"].get("content", [])
        for c in content:
            print(f"   Response: {c.get('text', '')[:500]}")
        tests_passed += 1
    elif resp and "error" in resp:
        print(f"   ❌ Error: {resp['error']}")
        tests_failed += 1
    else:
        print(f"   ❌ No response: {resp}")
        tests_failed += 1

    # Test 4: list_dashboards
    print("\n[5] Test: Call list_dashboards")
    send_msg({
        "jsonrpc": "2.0", "id": 4,
        "method": "tools/call",
        "params": {"name": "list_dashboards", "arguments": {"request": {"page": 1, "page_size": 3}}},
    })
    resp = recv_msg(timeout=30)
    if resp and "result" in resp:
        content = resp["result"].get("content", [])
        for c in content:
            print(f"   Response: {c.get('text', '')[:800]}")
        tests_passed += 1
    elif resp and "error" in resp:
        print(f"   ❌ Error: {resp['error']}")
        tests_failed += 1
    else:
        print(f"   ❌ No response: {resp}")
        tests_failed += 1

    # Test 5: list_charts
    print("\n[6] Test: Call list_charts")
    send_msg({
        "jsonrpc": "2.0", "id": 5,
        "method": "tools/call",
        "params": {"name": "list_charts", "arguments": {"request": {"page": 1, "page_size": 3}}},
    })
    resp = recv_msg(timeout=30)
    if resp and "result" in resp:
        content = resp["result"].get("content", [])
        for c in content:
            print(f"   Response: {c.get('text', '')[:800]}")
        tests_passed += 1
    elif resp and "error" in resp:
        print(f"   ❌ Error: {resp['error']}")
        tests_failed += 1
    else:
        print(f"   ❌ No response: {resp}")
        tests_failed += 1

    # Cleanup
    print("\n" + "=" * 60)
    print(f"Results: {tests_passed} passed, {tests_failed} failed out of {tests_passed + tests_failed}")
    print("=" * 60)

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

    return 0 if tests_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())


