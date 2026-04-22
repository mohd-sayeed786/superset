import subprocess
import json

proc = subprocess.Popen(
    ["docker", "exec", "-i",
     "-e", "SUPERSET_URL=http://localhost:8088",
     "-e", "SUPERSET_USERNAME=admin",
     "-e", "SUPERSET_PASSWORD=admin",
     "-e", "MCP_DEV_USERNAME=admin",
     "hackathon-superset-1", "python", "-m", "superset.mcp_service"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
)

def send(msg):
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()

def recv():
    """Read next JSON-RPC response, skipping notifications."""
    while True:
        line = proc.stdout.readline()
        if not line.strip():
            return None
        msg = json.loads(line)
        if "id" in msg:  # It's a response, not a notification
            return msg
        # Skip notifications (no "id" field)
        print(f"  📝 notification: {msg.get('method', 'unknown')}")

# 1. Initialize
send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
    "protocolVersion": "2024-11-05", "capabilities": {},
    "clientInfo": {"name": "test", "version": "1.0"}
}})
resp = recv()
print("✅ INIT:", resp["result"]["serverInfo"])

# 2. Initialized notification
send({"jsonrpc": "2.0", "method": "notifications/initialized"})

# 3. health_check tool
send({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
    "name": "health_check", "arguments": {}
}})
resp2 = recv()
print("✅ HEALTH_CHECK:", json.dumps(resp2, indent=2)[:300])

# 4. list_databases tool
send({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
    "name": "list_databases", "arguments": {"request": {}}
}})
resp3 = recv()
print("✅ LIST_DATABASES:", json.dumps(resp3, indent=2)[:500])

proc.stdin.close()
proc.wait(timeout=15)
print("\n🎉 All MCP tools responded successfully!")
