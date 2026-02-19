#!/usr/bin/env python
"""Test MCP bridge via stdio like Claude Code does."""
import subprocess
import json
import sys

def test_mcp_tool_call():
    """Test calling get_scene_info via the MCP bridge."""

    # Start the bridge process
    cmd = [
        "uv", "run", "python", "sd_mcp_bridge.py", "--port", "9880"
    ]

    print("Starting MCP bridge...")
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=r"E:\Create\Build\DCC\MCP\SubstanceDesignerMCP\server"
    )

    try:
        # MCP initialization handshake
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }

        print("Sending initialize request...")
        proc.stdin.write(json.dumps(init_request) + "\n")
        proc.stdin.flush()

        # Read response
        response = proc.stdout.readline()
        print(f"Initialize response: {response.strip()}")

        # Send initialized notification
        initialized_notif = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        proc.stdin.write(json.dumps(initialized_notif) + "\n")
        proc.stdin.flush()

        # Now call the tool
        tool_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "get_scene_info",
                "arguments": {}
            }
        }

        print("\nSending tool call request...")
        proc.stdin.write(json.dumps(tool_request) + "\n")
        proc.stdin.flush()

        # Read tool response
        response = proc.stdout.readline()
        print(f"Tool call response: {response.strip()}")

        result = json.loads(response)
        if "result" in result:
            print("\n✓ Tool call succeeded!")
            return True
        else:
            print("\n❌ Tool call failed")
            return False

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        proc.terminate()
        proc.wait(timeout=2)

if __name__ == "__main__":
    success = test_mcp_tool_call()
    sys.exit(0 if success else 1)
