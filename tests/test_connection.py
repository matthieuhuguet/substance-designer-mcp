#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test de connexion au plugin SD MCP v0.2.0 (length-prefix framing protocol).
Opens a fresh TCP connection, sends one framed command, receives one framed response, closes.
"""
import socket
import struct
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PORT = 9880
HOST = "localhost"
HEADER_SIZE = 4


def send_framed(sock, data: bytes):
    header = struct.pack(">I", len(data))
    sock.sendall(header + data)


def recv_exact(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return b""
        buf += chunk
    return buf


def recv_framed(sock):
    header = recv_exact(sock, HEADER_SIZE)
    if not header:
        return None
    msg_len = struct.unpack(">I", header)[0]
    if msg_len == 0:
        return b""
    return recv_exact(sock, msg_len)


def test_command(command, label=""):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(10)
        sock.connect((HOST, PORT))
        print(f"  Connected on {HOST}:{PORT}")

        data = json.dumps(command).encode("utf-8")
        send_framed(sock, data)
        print(f"  Sent: {command['type']}")

        response_bytes = recv_framed(sock)
        if response_bytes is None:
            print(f"  FAIL: No response received")
            return False

        response = json.loads(response_bytes.decode("utf-8"))
        status = response.get("status", "unknown")
        print(f"  Status: {status}")

        if status == "success":
            result = response.get("result", {})
            # Truncate for display
            result_str = json.dumps(result, indent=2)
            if len(result_str) > 500:
                result_str = result_str[:500] + "..."
            print(f"  Result: {result_str}")
            return True
        else:
            print(f"  Error: {response.get('message', 'unknown')}")
            return False

    except ConnectionRefusedError:
        print(f"  FAIL: Connection refused on {HOST}:{PORT}")
        print("  Check that Substance Designer is open with the MCP plugin active.")
        return False
    except socket.timeout:
        print("  FAIL: Timeout - no response")
        return False
    except Exception as e:
        print(f"  FAIL: {e}")
        return False
    finally:
        sock.close()


print("=" * 60)
print("Substance Designer MCP Plugin v0.2.0 - Connection Test")
print("=" * 60)

# Test 1: get_scene_info
print("\n[Test 1] get_scene_info")
ok1 = test_command({"type": "get_scene_info", "params": {}})

# Test 2: list_node_definitions (with filter)
print("\n[Test 2] list_node_definitions (filter='blend')")
ok2 = test_command({"type": "list_node_definitions", "params": {"filter_text": "blend"}})

# Test 3: Rapid sequential commands (tests connection-per-command model)
print("\n[Test 3] Rapid sequential commands (5x get_scene_info)")
ok3 = True
for i in range(5):
    print(f"  --- Iteration {i+1}/5 ---")
    if not test_command({"type": "get_scene_info", "params": {}}):
        ok3 = False
        break

# Summary
print("\n" + "=" * 60)
results = [("get_scene_info", ok1), ("list_node_definitions", ok2), ("rapid sequential", ok3)]
for name, ok in results:
    print(f"  {'PASS' if ok else 'FAIL'}: {name}")
print("=" * 60)

all_passed = all(ok for _, ok in results)
print(f"\n{'All tests passed!' if all_passed else 'Some tests failed.'}")
sys.exit(0 if all_passed else 1)
