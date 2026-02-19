"""
Substance Designer MCP Plugin v3.1.0
=====================================
ARCHITECTURE
============
LLM -> stdio -> sd_mcp_bridge.py (FastMCP) -> TCP -> this plugin -> sd.api
PORT: 9881 (all clients: Claude Code, Claude Desktop, Cursor)
PROTOCOL: Length-prefix framing [4-byte big-endian length][JSON payload]
CONNECTION MODEL: Fresh TCP socket per command (no persistent connections)
THREADING: ALL sd.api calls on Qt main thread via Signal/Slot queued dispatch

═══════════════════════════════════════════════════════════════════════════════
NEW IN v3.0.0
═══════════════════════════════════════════════════════════════════════════════
  - RECIPE ENGINE: 34 complete PBR material recipes built-in
  - SMART GRAPH BUILDER: validates ALL nodes/ports before touching SD
  - ATOMIC PORT REGISTRY: no more wrong port names crashing SD
  - LIBRARY NODE CACHE: caches discovered pkg:// URLs per session
  - BATCH GRAPH with library node support (resolves URLs internally)
  - HEIGHTMAP BUILDER: specialized tool for cliff/rock/terrain heightmaps
  - MATERIAL BUILDER: one-call full PBR graph (diffuse+normal+rough+metal+AO)
  - WARP CHAIN BUILDER: complex warp networks in one call
  - SUB-GRAPH MERGE: create partial graphs then merge them
  - COLOR PALETTE TOOL: set baseColor with specific HSL values
  - DIAGNOSTIC TOOL: full scene health check
  - GRAPH SNAPSHOT: export node list + connections as JSON
  - RECIPE PREVIEW: list available recipes with descriptions

═══════════════════════════════════════════════════════════════════════════════
CRITICAL RULES - DO NOT VIOLATE
═══════════════════════════════════════════════════════════════════════════════
  - ONE CALL AT A TIME. NEVER parallel. NEVER batch from outside.
  - newNode(unknown_def) HANGS SD 15 permanently
  - SDUsage.sNew() HANGS SD 15 permanently
  - arrange_nodes() DESTROYS ALL connections
  - Library node outputs are NEVER "unique_filter_output"
  - directionalwarp warp map port = "inputintensity" (NOT inputgradient)
  - connect_nodes with wrong port = crash. Plugin validates before calling SD.
═══════════════════════════════════════════════════════════════════════════════

SD API NOTES (confirmed from live SD 15.0.3 introspection)
===========================================================
  SDPackage has NO deleteResource() — use resource.delete() on the SDResource itself
  SDPackage methods: findResourceFromUrl, getChildrenResources, getFilePath, isModified
  SDResource.delete() — removes graph from package (confirmed working, 156 graphs deleted)

VERSION HISTORY
===============
  1.x.x - Initial releases
  2.x.x - PySide6 injection, Signal/Slot dispatcher, recipe stubs
  3.0.0 - Full recipe engine, 34 materials, smart builder, all tools
  3.1.0 - SD crash fixes (SDValueInt2 on float, SDValueFloat on enum), build_heightmap bug fix
  3.2.x - Reporting bug fix (library node definition field), recipes v5.0 (78 recipes, JP architecture)
"""

import sd
import os
import re
import json
import struct
import socket
import select
import threading
import traceback
import sys
import io
import time
import queue
import importlib as _importlib
from contextlib import redirect_stdout, redirect_stderr

# ── SD API imports ───────────────────────────────────────────────────────────
from sd.api.sdproperty import SDPropertyCategory
from sd.api.sdbasetypes import float2, float3, float4, ColorRGBA, int2, int3, int4
from sd.api.sdvaluefloat   import SDValueFloat
from sd.api.sdvalueint     import SDValueInt
from sd.api.sdvalueint2    import SDValueInt2
from sd.api.sdvalueint3    import SDValueInt3
from sd.api.sdvalueint4    import SDValueInt4
from sd.api.sdvaluebool    import SDValueBool
from sd.api.sdvaluestring  import SDValueString
from sd.api.sdvaluefloat2  import SDValueFloat2
from sd.api.sdvaluefloat3  import SDValueFloat3
from sd.api.sdvaluefloat4  import SDValueFloat4
from sd.api.sdvaluecolorrgba import SDValueColorRGBA
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph

# ── Configuration ────────────────────────────────────────────────────────────
DEFAULT_PORTS     = [9881]
PLUGIN_VERSION    = (3, 2, 0)
HEADER_SIZE       = 4
COMMAND_TIMEOUT   = 120
CLIENT_TIMEOUT    = 130
ACCEPT_BACKLOG    = 5
MAX_MSG_SIZE      = 100 * 1024 * 1024   # 100 MB

# System properties not valid as connection targets
_SYSTEM_PARAMS = frozenset({
    "$outputsize", "$format", "$pixelsize", "$pixelratio",
    "$tiling", "$randomseed", "$time"
})

# ── Known atomic node port registry ─────────────────────────────────────────
# Source: Adobe SD docs + empirical testing. Prevents wrong-port crashes.
ATOMIC_PORTS = {
    "sbs::compositing::blend": {
        "inputs":  ["source", "destination", "opacity"],
        "outputs": ["unique_filter_output"],
    },
    "sbs::compositing::levels": {
        "inputs":  ["input1"],
        "outputs": ["unique_filter_output"],
    },
    "sbs::compositing::curve": {
        "inputs":  ["input1"],
        "outputs": ["unique_filter_output"],
    },
    "sbs::compositing::hsl": {
        "inputs":  ["input1"],
        "outputs": ["unique_filter_output"],
    },
    "sbs::compositing::blur": {
        "inputs":  ["input1"],
        "outputs": ["unique_filter_output"],
    },
    "sbs::compositing::sharpen": {
        "inputs":  ["input1"],
        "outputs": ["unique_filter_output"],
    },
    "sbs::compositing::warp": {
        "inputs":  ["input1", "inputgradient"],
        "outputs": ["unique_filter_output"],
    },
    "sbs::compositing::directionalwarp": {
        "inputs":  ["input1", "inputintensity"],   # NOT inputgradient !
        "outputs": ["unique_filter_output"],
    },
    "sbs::compositing::normal": {
        "inputs":  ["input1"],
        "outputs": ["unique_filter_output"],
    },
    "sbs::compositing::transformation": {
        "inputs":  ["input1"],
        "outputs": ["unique_filter_output"],
    },
    "sbs::compositing::distance": {
        "inputs":  ["input1"],
        "outputs": ["unique_filter_output"],
    },
    "sbs::compositing::grayscaleconversion": {
        "inputs":  ["input1"],
        "outputs": ["unique_filter_output"],
    },
    "sbs::compositing::shuffle": {
        "inputs":  ["input1"],
        "outputs": ["unique_filter_output"],
    },
    "sbs::compositing::emboss": {
        "inputs":  ["input1"],
        "outputs": ["unique_filter_output"],
    },
    "sbs::compositing::passthrough": {
        "inputs":  ["input1"],
        "outputs": ["unique_filter_output"],
    },
    "sbs::compositing::uniform": {
        "inputs":  [],
        "outputs": ["unique_filter_output"],
    },
    "sbs::compositing::output": {
        "inputs":  ["inputNodeOutput"],
        "outputs": [],
    },
    "sbs::compositing::input_color": {
        "inputs":  [],
        "outputs": ["unique_filter_output"],
    },
    "sbs::compositing::input_grayscale": {
        "inputs":  [],
        "outputs": ["unique_filter_output"],
    },
    "sbs::compositing::gradient": {
        "inputs":  ["input1", "gradient"],
        "outputs": ["unique_filter_output"],
    },
    "sbs::compositing::pixelprocessor": {
        "inputs":  ["input1"],
        "outputs": ["unique_filter_output"],
    },
    "sbs::compositing::fxmaps": {
        "inputs":  ["input1"],
        "outputs": ["unique_filter_output"],
    },
}

# ── Blend mode constants ─────────────────────────────────────────────────────
BLEND_MODES = {
    "copy": 0, "normal": 0,
    "add": 1, "linear_dodge": 1,
    "subtract": 2,
    "multiply": 3,
    "max": 4, "lighten": 4,
    "min": 5, "darken": 5,
    "overlay": 9,
    "screen": 10,
    "soft_light": 11,
    "hard_light": 12,
    "divide": 13,
    "difference": 14,
}

# ── Globals ──────────────────────────────────────────────────────────────────
_server = None
_library_cache = {}   # filter_text -> list of {identifier, url, package}

# ── Logging ──────────────────────────────────────────────────────────────────
def _log(msg):
    print("[SD-MCP] {}".format(msg))


# ── PySide6 path injection ───────────────────────────────────────────────────
def _inject_sd_pyside_path():
    candidates = []
    try:
        import psutil
        for proc in psutil.process_iter(['name', 'exe']):
            name = (proc.info.get('name') or '').lower()
            if 'substance' in name and 'designer' in name:
                exe = proc.info.get('exe') or ''
                if exe:
                    candidates.append(os.path.dirname(exe))
    except Exception:
        pass

    try:
        exe_dir = os.path.dirname(sys.executable)
        for _ in range(4):
            site_pkg = os.path.join(exe_dir, 'Lib', 'site-packages')
            if os.path.isdir(os.path.join(site_pkg, 'PySide6')):
                candidates.append(exe_dir)
                break
            exe_dir = os.path.dirname(exe_dir)
    except Exception:
        pass

    try:
        for drive in ('C:', 'D:', 'E:', 'F:'):
            for base in (
                drive + '\\Program Files\\Adobe',
                drive + '\\Program Files (x86)\\Adobe',
                drive + '\\Create\\Build\\DCC\\SubstanceDesigner',
            ):
                if not os.path.isdir(base):
                    continue
                for item in os.listdir(base):
                    if 'substance' in item.lower() and 'designer' in item.lower():
                        candidates.append(os.path.join(base, item))
    except Exception:
        pass

    for sd_root in candidates:
        site_pkg = os.path.join(sd_root, 'plugins', 'pythonsdk', 'Lib', 'site-packages')
        if os.path.isdir(os.path.join(site_pkg, 'PySide6')):
            if site_pkg not in sys.path:
                sys.path.insert(0, site_pkg)
            return site_pkg
    return None


_pyside_path = _inject_sd_pyside_path()

_QTimer = None
_QT_BINDING_USED = None
for _qt_binding in ("PySide6.QtCore", "PySide2.QtCore"):
    try:
        _qtcore_mod = _importlib.import_module(_qt_binding)
        _QTimer = _qtcore_mod.QTimer
        _QT_BINDING_USED = _qt_binding
        break
    except Exception:
        pass


# ── Qt main-thread invoker ───────────────────────────────────────────────────
class _Invoker:
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls._build()
        return cls._instance

    @staticmethod
    def _build():
        if not _QT_BINDING_USED:
            return None
        try:
            qtcore = _importlib.import_module(_QT_BINDING_USED)

            class Invoker(qtcore.QObject):
                invoke_signal = qtcore.Signal()

                def __init__(self):
                    super().__init__()
                    self._queue = queue.Queue()
                    self.invoke_signal.connect(self._execute, qtcore.Qt.QueuedConnection)

                def schedule(self, fn):
                    self._queue.put(fn)
                    self.invoke_signal.emit()

                def _execute(self):
                    try:
                        fn = self._queue.get_nowait()
                        fn()
                    except queue.Empty:
                        pass
                    except Exception as e:
                        _log("Invoker._execute error: {}".format(e))

            return Invoker()
        except Exception as e:
            _log("Warning: _Invoker build failed: {}".format(e))
            return None


class MainThreadDispatcher:
    def dispatch(self, fn, *args, **kwargs):
        if threading.current_thread() is threading.main_thread():
            try:
                return fn(*args, **kwargs), None
            except Exception as e:
                return None, e

        invoker = _Invoker.instance()
        if invoker is None:
            hint = (" injected: {}".format(_pyside_path)
                    if _pyside_path else " (pythonsdk not found)")
            return None, RuntimeError(
                "Qt invoker unavailable — cannot dispatch to main thread." + hint)

        result_holder = [None, None]
        done = threading.Event()

        def _call():
            try:
                result_holder[0] = fn(*args, **kwargs)
            except Exception as e:
                result_holder[1] = e
            finally:
                done.set()

        invoker.schedule(_call)

        if not done.wait(timeout=COMMAND_TIMEOUT):
            return None, TimeoutError(
                "Main thread dispatch timed out after {}s".format(COMMAND_TIMEOUT))

        return result_holder[0], result_holder[1]


_dispatcher = MainThreadDispatcher()


def _run_on_main(fn, *args, **kwargs):
    result, exc = _dispatcher.dispatch(fn, *args, **kwargs)
    if exc is not None:
        raise exc
    return result


# ── Length-prefix protocol ───────────────────────────────────────────────────
def _recv_exact(sock, n, timeout=COMMAND_TIMEOUT):
    sock.settimeout(timeout)
    buf = b""
    while len(buf) < n:
        try:
            chunk = sock.recv(n - len(buf))
        except socket.timeout:
            raise socket.timeout("Timed out reading {} bytes (got {})".format(n, len(buf)))
        if not chunk:
            return None
        buf += chunk
    return buf


def _recv_framed(sock, timeout=COMMAND_TIMEOUT):
    header = _recv_exact(sock, HEADER_SIZE, timeout)
    if not header:
        return None
    msg_len = struct.unpack(">I", header)[0]
    if msg_len == 0:
        return None
    if msg_len > MAX_MSG_SIZE:
        raise ValueError("Message too large: {} bytes".format(msg_len))
    payload = _recv_exact(sock, msg_len, timeout)
    if not payload:
        return None
    return payload


def _send_framed(sock, data):
    sock.sendall(struct.pack(">I", len(data)) + data)


# ── TCP Server ───────────────────────────────────────────────────────────────
class SDMCPServer:
    def __init__(self, ports=None):
        self.host = 'localhost'
        self.ports = ports or DEFAULT_PORTS
        self.running = False
        self.listeners = {}
        self._thread = None
        self._handler = CommandHandler()

    def start(self):
        self.running = True
        for port in self.ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((self.host, port))
                sock.listen(ACCEPT_BACKLOG)
                sock.setblocking(False)
                self.listeners[port] = sock
                _log("Listening on {}:{}".format(self.host, port))
            except Exception as e:
                _log("Failed to bind port {}: {}".format(port, e))

        if not self.listeners:
            _log("ERROR: No ports could be opened!")
            return

        self._thread = threading.Thread(
            target=self._serve_loop, daemon=True, name="SD-MCP-Serve")
        self._thread.start()
        _log("v{} running on ports: {}".format(
            ".".join(map(str, PLUGIN_VERSION)), list(self.listeners.keys())))

    def stop(self):
        self.running = False
        for sock in self.listeners.values():
            try:
                sock.close()
            except Exception:
                pass
        self.listeners.clear()
        _log("Server stopped")

    def _serve_loop(self):
        while self.running:
            readable = list(self.listeners.values())
            if not readable:
                time.sleep(0.1)
                continue
            try:
                ready, _, _ = select.select(readable, [], [], 0.1)
            except (OSError, ValueError):
                if not self.running:
                    break
                time.sleep(0.1)
                continue

            for listener in ready:
                port = next((p for p, s in self.listeners.items() if s is listener), None)
                if port is None:
                    continue
                try:
                    client, addr = listener.accept()
                except (BlockingIOError, OSError):
                    continue
                try:
                    self._handle_client(client, addr, port)
                except Exception as e:
                    _log("Unexpected error: {}".format(e))

    def _handle_client(self, client, addr, port):
        try:
            client.setblocking(True)
            client.settimeout(CLIENT_TIMEOUT)
            _log("Client on port {}: {}".format(port, addr))

            payload = _recv_framed(client, timeout=CLIENT_TIMEOUT)
            if payload is None:
                return

            try:
                command = json.loads(payload.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                _send_framed(client, json.dumps(
                    {"status": "error", "message": "Invalid JSON: {}".format(e)}
                ).encode("utf-8"))
                return

            response = self._execute_safe(command)
            _send_framed(client, json.dumps(response, default=_json_safe).encode("utf-8"))

        except socket.timeout:
            _log("Timeout from client on port {}".format(port))
        except ConnectionResetError:
            pass
        except Exception as e:
            _log("Error handling client on port {}: {}".format(port, e))
        finally:
            try:
                client.close()
            except Exception:
                pass

    def _execute_safe(self, command):
        try:
            cmd_type = command.get("type")
            params   = command.get("params", {})
            _log("Executing: {}".format(cmd_type))
            result = _run_on_main(self._handler.dispatch, cmd_type, params)
            _log("Done: {}".format(cmd_type))
            return {"status": "success", "result": result if result is not None else {}}
        except Exception as e:
            _log("Error in {}: {}".format(command.get("type", "?"), e))
            try:
                traceback.print_exc()
            except Exception:
                pass
            return {"status": "error", "message": str(e)}


def _json_safe(obj):
    if isinstance(obj, float):
        if obj != obj:
            return None
        if obj == float('inf'):
            return 1e308
        if obj == float('-inf'):
            return -1e308
    return str(obj)


# ── Helper: infer SD value type from Python ──────────────────────────────────
# CRITICAL: bare int scalars → "float" because almost all SD node params are float.
# Only explicit {"value": x, "type": "int"} should produce SDValueInt.
# Sending SDValueInt to a float param CRASHES SD 15 silently.
def _infer_type(value):
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "float"   # int scalar → float (avoids SDValueInt crash on float params)
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (list, tuple)):
        n = len(value)
        # CRITICAL: SD 15 silently crashes on SDValueInt2/3/4 applied to float params.
        # Always use float vectors — int vector params MUST use explicit {"value":..., "type":"int2"}
        if n == 2:
            return "float2"
        if n == 3:
            return "float3"
        if n == 4:
            return "float4"
    return "float"


def _coerce_type(inferred_type, value, sd_type_id):
    """Coerce the inferred Python type to match the actual SD property type.
    Prevents SD 15 silent crashes caused by wrong SDValue types.
    sd_type_id: the getId() string of the property's SDType.
    """
    if not sd_type_id:
        return inferred_type
    tid = sd_type_id.lower()

    # Exact primitive types
    if tid == "int":        return "int"
    if tid == "float":      return "float"
    if tid == "bool":       return "bool"
    if tid == "string":     return "string"
    if tid == "float2":     return "float2"
    if tid == "float3":     return "float3"
    if tid == "float4":     return "float4"
    if tid == "int2":       return "int2"
    if tid == "int3":       return "int3"
    if tid == "int4":       return "int4"
    if tid == "colorrgba":  return "color"
    if tid == "colorrgb":   return "float3"

    # SD enum types (sbs::compositing::blendingmode, sbs::compositing::format, etc.)
    # Enums are integer-based — any non-primitive sd type that accepts an int value
    # SD enum types accept SDValueInt. Coerce float → int for these.
    if tid.startswith("sbs::") or "::" in tid:
        if inferred_type in ("float",):
            # Only coerce scalar floats that represent enum/int values
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return "int"
        return inferred_type

    # Fallback: check for int/float keywords in type name
    if "int" in tid and "float" not in tid:
        if inferred_type == "float":
            return "int"
        if inferred_type == "float4" and isinstance(value, (list, tuple)):
            return "int4"
        if inferred_type == "float2" and isinstance(value, (list, tuple)):
            return "int2"

    return inferred_type


def _sanitize_identifier(name):
    if not name:
        return "MCP_Graph"
    sanitized = re.sub(r'[^A-Za-z0-9_]', '_', name)
    if sanitized and not sanitized[0].isalpha():
        sanitized = "G_" + sanitized
    return sanitized or "MCP_Graph"


# ════════════════════════════════════════════════════════════════════════════
# COMMAND HANDLER — the brain of the plugin
# ════════════════════════════════════════════════════════════════════════════
class CommandHandler:

    def __init__(self):
        self.HANDLERS = {
            # ── Core scene ──
            "get_scene_info":         self.get_scene_info,
            "create_package":         self.create_package,
            "create_graph":           self.create_graph,
            "delete_graph":           self.delete_graph,
            "open_graph":             self.open_graph,
            "get_graph_info":         self.get_graph_info,
            "save_package":           self.save_package,
            "graph_snapshot":         self.graph_snapshot,
            "diagnostic":             self.diagnostic,
            # ── Node operations ──
            "list_node_definitions":  self.list_node_definitions,
            "create_node":            self.create_node,
            "create_instance_node":   self.create_instance_node,
            "create_output_node":     self.create_output_node,
            "delete_node":            self.delete_node,
            "move_node":              self.move_node,
            "duplicate_node":         self.duplicate_node,
            "get_node_info":          self.get_node_info,
            "get_library_nodes":      self.get_library_nodes,
            # ── Connection ──
            "connect_nodes":          self.connect_nodes,
            "disconnect_nodes":       self.disconnect_nodes,
            # ── Parameters ──
            "set_parameter":          self.set_parameter,
            "set_graph_output_size":  self.set_graph_output_size,
            # ── Batch builders ──
            "create_batch_graph":     self.create_batch_graph,
            "build_material_graph":   self.build_material_graph,
            "build_heightmap_graph":  self.build_heightmap_graph,
            # ── Recipe engine ──
            "list_recipes":           self.list_recipes,
            "get_recipe_info":        self.get_recipe_info,
            "apply_recipe":           self.apply_recipe,
            # ── Utilities ──
            "smart_connect":          self.smart_connect,
            "arrange_nodes":          self.arrange_nodes,
            "execute_code":           self.execute_code,
        }
        # Library node URL cache (populated lazily, session-lifetime)
        self._lib_url_cache = {}  # lower-case identifier -> url string

    def dispatch(self, cmd_type, params):
        handler = self.HANDLERS.get(cmd_type)
        if not handler:
            raise ValueError("Unknown command: '{}'. Available: {}".format(
                cmd_type, sorted(self.HANDLERS.keys())))
        return handler(**params)

    # ═══════════════════════════════════════════════════════════════════════
    # ── SD API helpers ──────────────────────────────────────────────────
    # ═══════════════════════════════════════════════════════════════════════

    def _app(self):
        return sd.getContext().getSDApplication()

    def _pkg_mgr(self):
        return self._app().getPackageMgr()

    def _ui_mgr(self):
        return self._app().getUIMgr()

    def _get_sd_version(self):
        try:
            return self._app().getVersion()
        except Exception:
            return "unknown"

    def _resolve_package(self, package_index=0, package_path=None):
        pkgs = list(self._pkg_mgr().getUserPackages())
        if package_path:
            for pkg in pkgs:
                if pkg.getFilePath() == package_path:
                    return pkg
            raise ValueError("Package '{}' not found.".format(package_path))
        if not pkgs:
            raise ValueError("No user packages loaded. Open a .sbs file first.")
        if package_index < 0:
            raise ValueError("package_index must be >= 0 (got {}).".format(package_index))
        if package_index >= len(pkgs):
            raise ValueError("Package index {} out of range (have {}).".format(
                package_index, len(pkgs)))
        return pkgs[package_index]

    def _resolve_graph(self, graph_identifier=None):
        if graph_identifier:
            for pkg in list(self._pkg_mgr().getUserPackages()):
                for res in list(pkg.getChildrenResources(False)):
                    try:
                        if res.getIdentifier() == graph_identifier:
                            return res
                    except Exception:
                        continue
            raise ValueError("Graph '{}' not found.".format(graph_identifier))

        try:
            g = self._ui_mgr().getCurrentGraph()
            if g is not None:
                return g
        except Exception:
            pass

        for pkg in list(self._pkg_mgr().getUserPackages()):
            for res in list(pkg.getChildrenResources(False)):
                try:
                    if "SDSBSCompGraph" in res.getClassName():
                        return res
                except Exception:
                    continue
        raise ValueError(
            "No graph available. Open a package/graph in SD, or pass graph_identifier.")

    def _find_node(self, graph, node_id):
        try:
            n = graph.getNodeFromId(node_id)
            if n is not None:
                return n
        except Exception:
            pass
        for node in list(graph.getNodes()):
            if node.getIdentifier() == node_id:
                return node
        raise ValueError("Node '{}' not found in graph '{}'.".format(
            node_id, graph.getIdentifier()))

    def _get_node_def_id(self, node):
        try:
            defn = node.getDefinition()
            if defn is not None:
                return defn.getId()
        except Exception:
            pass
        return "unknown"

    def _is_instance_node(self, node):
        defn_id = self._get_node_def_id(node)
        return (defn_id == "unknown" or
                defn_id.startswith("pkg://") or
                "?dependency=" in defn_id)

    def _get_node_pos(self, node):
        try:
            p = node.getPosition()
            return [p.x, p.y]
        except Exception:
            return [0.0, 0.0]

    def _make_sd_value(self, value_type, value):
        t = value_type.lower()
        if t == "float":
            return SDValueFloat.sNew(float(value))
        if t == "int":
            return SDValueInt.sNew(int(value))
        if t == "bool":
            return SDValueBool.sNew(bool(value))
        if t == "string":
            return SDValueString.sNew(str(value))
        if t == "float2":
            v = value if isinstance(value, (list, tuple)) else [value, value]
            return SDValueFloat2.sNew(float2(float(v[0]), float(v[1])))
        if t == "float3":
            v = value if isinstance(value, (list, tuple)) else [value] * 3
            return SDValueFloat3.sNew(float3(float(v[0]), float(v[1]), float(v[2])))
        if t == "float4":
            v = value if isinstance(value, (list, tuple)) else [value] * 4
            return SDValueFloat4.sNew(float4(
                float(v[0]), float(v[1]), float(v[2]), float(v[3])))
        if t in ("color", "colorrgba"):
            v = value if isinstance(value, (list, tuple)) else [value] * 3 + [1.0]
            a = float(v[3]) if len(v) > 3 else 1.0
            return SDValueColorRGBA.sNew(ColorRGBA(
                float(v[0]), float(v[1]), float(v[2]), a))
        if t == "int2":
            v = value if isinstance(value, (list, tuple)) else [value, value]
            return SDValueInt2.sNew(int2(int(v[0]), int(v[1])))
        if t == "int3":
            v = value if isinstance(value, (list, tuple)) else [value] * 3
            return SDValueInt3.sNew(int3(int(v[0]), int(v[1]), int(v[2])))
        if t == "int4":
            v = value if isinstance(value, (list, tuple)) else [value] * 4
            return SDValueInt4.sNew(int4(int(v[0]), int(v[1]), int(v[2]), int(v[3])))
        raise ValueError(
            "Unknown value_type '{}'. Valid: float, int, bool, string, "
            "float2, float3, float4, color, int2, int3, int4".format(value_type))

    def _resolve_lib_url(self, keyword):
        """Find a library node URL by keyword (case-insensitive). Cached."""
        key = keyword.lower()
        if key in self._lib_url_cache:
            return self._lib_url_cache[key]
        for pkg in list(self._pkg_mgr().getPackages()):
            try:
                fp = pkg.getFilePath()
                if not fp:
                    continue
                for recursive in (True, False):
                    try:
                        children = list(pkg.getChildrenResources(recursive))
                        if not children:
                            continue
                        for res in children:
                            try:
                                if "SDSBSCompGraph" not in res.getClassName():
                                    continue
                                rid = res.getIdentifier()
                                if key in rid.lower():
                                    url = None
                                    try:
                                        url = res.getUrl()
                                    except Exception:
                                        pass
                                    if url:
                                        self._lib_url_cache[key] = url
                                        # also cache by exact identifier
                                        self._lib_url_cache[rid.lower()] = url
                                        return url
                            except Exception:
                                pass
                        break
                    except Exception:
                        continue
            except Exception:
                pass
        return None

    def _create_library_node(self, graph, keyword, position=None):
        """Create a library node from a keyword, auto-resolving URL."""
        url = self._resolve_lib_url(keyword)
        if not url:
            raise ValueError(
                "Library node '{}' not found. "
                "Use get_library_nodes(filter_text='{}') to verify.".format(keyword, keyword))
        resource = None
        for pkg in list(self._pkg_mgr().getPackages()):
            try:
                r = pkg.findResourceFromUrl(url)
                if r is not None:
                    resource = r
                    break
            except Exception:
                pass
        if not resource:
            raise ValueError("Resource URL not found: {}".format(url))
        node = graph.newInstanceNode(resource)
        if not node:
            raise RuntimeError("newInstanceNode failed for '{}'.".format(url))
        if position and len(position) >= 2:
            node.setPosition(float2(float(position[0]), float(position[1])))
        return node

    def _set_node_params(self, node, params):
        """Apply parameter dict to a node. Type-safe: reads actual SD property type
        and coerces before setting to prevent SD 15 silent crashes."""
        if not params:
            return {}
        results = {}

        # Build property type maps: id -> SDType id string
        input_type_map  = {}   # param_id -> sd_type_id
        annot_type_map  = {}
        try:
            for p in list(node.getProperties(SDPropertyCategory.Input)):
                pid = p.getId()
                try:
                    t = p.getType()
                    input_type_map[pid] = t.getId() if t else ""
                except Exception:
                    input_type_map[pid] = ""
        except Exception:
            pass
        try:
            for p in list(node.getProperties(SDPropertyCategory.Annotation)):
                pid = p.getId()
                try:
                    t = p.getType()
                    annot_type_map[pid] = t.getId() if t else ""
                except Exception:
                    annot_type_map[pid] = ""
        except Exception:
            pass

        for param_id, param_spec in params.items():
            # Skip system params — they cannot be set as node inputs safely
            if param_id.startswith("$"):
                results[param_id] = "skipped_system"
                continue
            try:
                if isinstance(param_spec, dict) and "value" in param_spec:
                    pval  = param_spec["value"]
                    ptype = param_spec.get("type", _infer_type(pval))
                else:
                    pval  = param_spec
                    ptype = _infer_type(pval)

                # Coerce ptype to match actual SD property type (prevents silent crash)
                sd_type_id = (input_type_map.get(param_id)
                              or annot_type_map.get(param_id) or "")
                ptype = _coerce_type(ptype, pval, sd_type_id)

                sd_val = self._make_sd_value(ptype, pval)
                set_ok = False
                if param_id in input_type_map:
                    try:
                        node.setInputPropertyValueFromId(param_id, sd_val)
                        set_ok = True
                    except Exception:
                        pass
                if not set_ok and param_id in annot_type_map:
                    try:
                        node.setAnnotationPropertyValueFromId(param_id, sd_val)
                        set_ok = True
                    except Exception:
                        pass
                results[param_id] = "ok" if set_ok else "skipped"
            except Exception as e:
                results[param_id] = "error: {}".format(e)
        return results

    def _safe_connect(self, graph, from_node, from_out, to_node, to_in):
        """Connect nodes with port validation. Returns True on success."""
        out_ids = set()
        in_ids  = set()
        try:
            for p in list(from_node.getProperties(SDPropertyCategory.Output)):
                out_ids.add(p.getId())
        except Exception:
            pass
        try:
            for p in list(to_node.getProperties(SDPropertyCategory.Input)):
                pid = p.getId()
                if pid not in _SYSTEM_PARAMS:
                    in_ids.add(pid)
        except Exception:
            pass

        if out_ids and from_out not in out_ids:
            raise ValueError(
                "Output port '{}' not found on node '{}'. "
                "Available: {}".format(from_out, from_node.getIdentifier(), sorted(out_ids)))
        if in_ids and to_in not in in_ids:
            raise ValueError(
                "Input port '{}' not found on node '{}'. "
                "Available: {}".format(to_in, to_node.getIdentifier(), sorted(in_ids)))

        conn = from_node.newPropertyConnectionFromId(from_out, to_node, to_in)
        if conn is None:
            raise RuntimeError(
                "Connection failed: {}.{} -> {}.{}".format(
                    from_node.getIdentifier(), from_out,
                    to_node.getIdentifier(), to_in))
        return True

    # ═══════════════════════════════════════════════════════════════════════
    # ── CORE SCENE TOOLS ────────────────────────────────────────────────
    # ═══════════════════════════════════════════════════════════════════════

    def get_scene_info(self):
        pkg_mgr = self._pkg_mgr()
        try:
            current_graph = self._ui_mgr().getCurrentGraph()
            current_graph_id = current_graph.getIdentifier() if current_graph else None
        except Exception:
            current_graph = None
            current_graph_id = None

        pkg_list = []
        for pkg in list(pkg_mgr.getUserPackages()):
            try:
                graphs = []
                for res in list(pkg.getChildrenResources(False)):
                    try:
                        cname = res.getClassName()
                        rid   = res.getIdentifier()
                        nc    = 0
                        if "CompGraph" in cname or "SDGraph" in cname:
                            try:
                                nc = len(list(res.getNodes()))
                            except Exception:
                                pass
                        graphs.append({"identifier": rid, "type": cname, "node_count": nc})
                    except Exception:
                        pass
                pkg_list.append({"file_path": pkg.getFilePath(), "graphs": graphs})
            except Exception as e:
                pkg_list.append({"error": str(e)})

        current_nc = 0
        if current_graph is not None:
            try:
                current_nc = len(list(current_graph.getNodes()))
            except Exception:
                pass

        return {
            "packages": pkg_list,
            "package_count": len(pkg_list),
            "current_graph": current_graph_id,
            "current_graph_node_count": current_nc,
            "sd_version": self._get_sd_version(),
            "plugin_version": ".".join(map(str, PLUGIN_VERSION)),
        }

    def create_package(self, file_path=None):
        pkg = self._pkg_mgr().newUserPackage()
        return {
            "file_path": pkg.getFilePath(),
            "message": "New package created. Use save_package to save it.",
        }

    def create_graph(self, package_index=0, graph_name="MCP_Graph", package_path=None):
        safe_name = _sanitize_identifier(graph_name)
        pkg = self._resolve_package(package_index, package_path)
        new_graph = SDSBSCompGraph.sNew(pkg)
        new_graph.setIdentifier(safe_name)
        actual_id = new_graph.getIdentifier()
        return {
            "identifier": actual_id,
            "requested_name": graph_name,
            "sanitized_name": safe_name,
            "type": new_graph.getClassName(),
            "package": pkg.getFilePath(),
        }

    def delete_graph(self, graph_identifier, package_index=0):
        pkg = self._resolve_package(package_index)
        for res in list(pkg.getChildrenResources(False)):
            try:
                if res.getIdentifier() == graph_identifier:
                    res.delete()
                    return {"deleted": graph_identifier}
            except Exception:
                pass
        raise ValueError("Graph '{}' not found.".format(graph_identifier))

    def open_graph(self, graph_identifier):
        graph = self._resolve_graph(graph_identifier)
        try:
            self._ui_mgr().openResourceInEditor(graph)
            return {"opened": graph_identifier, "success": True}
        except Exception as e:
            return {"opened": graph_identifier, "warning": str(e)}

    def get_graph_info(self, graph_identifier=None, node_limit=100, include_connections=True):
        graph = self._resolve_graph(graph_identifier)
        all_nodes = list(graph.getNodes())
        total = len(all_nodes)
        to_detail = all_nodes[:node_limit] if node_limit > 0 else []

        node_list = []
        for node in to_detail:
            try:
                info = {
                    "identifier": node.getIdentifier(),
                    "definition":  self._get_node_def_id(node),
                    "position":    self._get_node_pos(node),
                    "connections": [],
                }
                if include_connections:
                    try:
                        for prop in list(node.getProperties(SDPropertyCategory.Input)):
                            pid   = prop.getId()
                            conns = node.getPropertyConnections(prop)
                            if conns is None:
                                continue
                            for conn in list(conns):
                                try:
                                    sn = conn.getInputPropertyNode()
                                    sp = conn.getInputProperty()
                                    if sn and sp:
                                        info["connections"].append({
                                            "input":       pid,
                                            "from_node":   sn.getIdentifier(),
                                            "from_output": sp.getId(),
                                        })
                                except Exception:
                                    pass
                    except Exception:
                        pass
                node_list.append(info)
            except Exception:
                pass

        return {
            "identifier":  graph.getIdentifier(),
            "node_count":  total,
            "nodes":       node_list,
            "truncated":   total > node_limit,
            "node_limit":  node_limit,
        }

    def save_package(self, package_index=0, file_path=None, package_path=None):
        pkg_mgr = self._pkg_mgr()
        pkg = self._resolve_package(package_index, package_path)
        if file_path:
            target_dir = os.path.dirname(os.path.abspath(file_path))
            if not os.path.exists(target_dir):
                try:
                    os.makedirs(target_dir, exist_ok=True)
                except Exception as e:
                    raise ValueError("Cannot create directory '{}': {}".format(target_dir, e))
            pkg_mgr.savePackageAs(pkg, file_path)
            return {"saved_to": file_path}
        else:
            current_path = pkg.getFilePath()
            if not current_path:
                raise ValueError(
                    "Package has no file path. Use file_path parameter to specify.")
            pkg_mgr.savePackage(pkg)
            return {"saved_to": current_path}

    def graph_snapshot(self, graph_identifier=None):
        """Export full graph structure as JSON snapshot (nodes + connections)."""
        graph = self._resolve_graph(graph_identifier)
        all_nodes = list(graph.getNodes())
        snapshot = {
            "graph_identifier": graph.getIdentifier(),
            "node_count": len(all_nodes),
            "nodes": [],
            "connections": [],
        }
        for node in all_nodes:
            nid  = node.getIdentifier()
            defn = self._get_node_def_id(node)
            pos  = self._get_node_pos(node)
            snapshot["nodes"].append({
                "id": nid, "definition": defn, "position": pos,
                "is_library": self._is_instance_node(node),
            })
            try:
                for prop in list(node.getProperties(SDPropertyCategory.Input)):
                    pid   = prop.getId()
                    conns = node.getPropertyConnections(prop)
                    if conns is None:
                        continue
                    for conn in list(conns):
                        try:
                            sn = conn.getInputPropertyNode()
                            sp = conn.getInputProperty()
                            if sn and sp:
                                snapshot["connections"].append({
                                    "from_node": sn.getIdentifier(),
                                    "from_output": sp.getId(),
                                    "to_node": nid,
                                    "to_input": pid,
                                })
                        except Exception:
                            pass
            except Exception:
                pass
        return snapshot

    def diagnostic(self):
        """Full health check of SD environment."""
        results = {}
        # SD running?
        try:
            ver = self._get_sd_version()
            results["sd_running"] = True
            results["sd_version"] = ver
        except Exception as e:
            results["sd_running"] = False
            results["sd_version_error"] = str(e)

        # Qt binding
        results["qt_binding"] = _QT_BINDING_USED or "NONE"
        results["pyside_path"] = _pyside_path or "NOT FOUND"

        # Invoker
        inv = _Invoker.instance()
        results["qt_invoker_ok"] = inv is not None

        # Packages
        try:
            pkgs = list(self._pkg_mgr().getUserPackages())
            results["user_packages"] = len(pkgs)
            results["package_files"] = [p.getFilePath() for p in pkgs]
        except Exception as e:
            results["packages_error"] = str(e)

        # Library cache
        results["library_cache_entries"] = len(self._lib_url_cache)

        # Current graph
        try:
            g = self._ui_mgr().getCurrentGraph()
            if g:
                results["current_graph"] = g.getIdentifier()
                results["current_graph_nodes"] = len(list(g.getNodes()))
            else:
                results["current_graph"] = None
        except Exception as e:
            results["current_graph_error"] = str(e)

        return results

    # ═══════════════════════════════════════════════════════════════════════
    # ── NODE TOOLS ──────────────────────────────────────────────────────
    # ═══════════════════════════════════════════════════════════════════════

    def list_node_definitions(self, filter_text="", graph_identifier=None, limit=500):
        temp_pkg = None
        try:
            if graph_identifier:
                graph = self._resolve_graph(graph_identifier)
            else:
                graph = None
                try:
                    graph = self._ui_mgr().getCurrentGraph()
                except Exception:
                    pass
                if not graph:
                    pkgs = list(self._pkg_mgr().getUserPackages())
                    if pkgs:
                        rs = list(pkgs[0].getChildrenResources(False))
                        for r in rs:
                            try:
                                if "SDSBSCompGraph" in r.getClassName():
                                    graph = r
                                    break
                            except Exception:
                                pass
                if not graph:
                    temp_pkg = self._pkg_mgr().newUserPackage()
                    graph = SDSBSCompGraph.sNew(temp_pkg)
                    graph.setIdentifier("_TempDefQuery")

            definitions = graph.getNodeDefinitions()
            result = []
            for defn in list(definitions):
                try:
                    did = defn.getId()
                    if filter_text and filter_text.lower() not in did.lower():
                        continue
                    result.append(did)
                    if len(result) >= limit:
                        break
                except Exception:
                    pass

            return {
                "count":       len(result),
                "definitions": result,
                "truncated":   len(result) >= limit,
                "filter":      filter_text,
            }
        finally:
            if temp_pkg is not None:
                try:
                    self._pkg_mgr().unloadUserPackage(temp_pkg)
                except Exception:
                    pass

    def create_node(self, definition_id, graph_identifier=None, position=None):
        graph = self._resolve_graph(graph_identifier)
        # Validate before calling newNode — unknown defs HANG SD 15
        try:
            known = {d.getId() for d in list(graph.getNodeDefinitions())}
            if definition_id not in known:
                raise ValueError(
                    "Unknown definition '{}'. "
                    "Library nodes require create_instance_node with pkg:// URL.".format(
                        definition_id))
        except ValueError:
            raise
        except Exception:
            pass

        node = graph.newNode(definition_id)
        if not node:
            raise RuntimeError("newNode('{}') returned None.".format(definition_id))
        if position and len(position) >= 2:
            node.setPosition(float2(float(position[0]), float(position[1])))
        return {
            "node_id":    node.getIdentifier(),
            "definition": self._get_node_def_id(node),
            "position":   list(position) if position else [0.0, 0.0],
        }

    def create_instance_node(self, resource_url, graph_identifier=None, position=None):
        graph = self._resolve_graph(graph_identifier)
        resource = None
        for pkg in list(self._pkg_mgr().getPackages()):
            try:
                r = pkg.findResourceFromUrl(resource_url)
                if r is not None:
                    resource = r
                    break
            except Exception:
                pass
        if not resource:
            raise ValueError("Resource '{}' not found.".format(resource_url))
        node = graph.newInstanceNode(resource)
        if not node:
            raise RuntimeError("newInstanceNode failed for '{}'.".format(resource_url))
        if position and len(position) >= 2:
            node.setPosition(float2(float(position[0]), float(position[1])))
        return {
            "node_id":      node.getIdentifier(),
            "resource_url": resource_url,
            "position":     list(position) if position else [0.0, 0.0],
            "note":         "Call get_node_info to find exact port IDs before connecting.",
        }

    def create_output_node(self, usage="baseColor", label=None,
                           graph_identifier=None, position=None):
        if label is None:
            label = usage
        graph = self._resolve_graph(graph_identifier)
        node = graph.newNode('sbs::compositing::output')
        if not node:
            raise RuntimeError("Failed to create output node.")
        if position and len(position) >= 2:
            node.setPosition(float2(float(position[0]), float(position[1])))
        label_set = False
        try:
            node.setAnnotationPropertyValueFromId("label", SDValueString.sNew(label))
            label_set = True
        except Exception as e:
            _log("Warning: label set failed: {}".format(e))
        return {
            "node_id":    node.getIdentifier(),
            "definition": "sbs::compositing::output",
            "usage":      usage,
            "label":      label,
            "label_set":  label_set,
        }

    def delete_node(self, node_id, graph_identifier=None):
        graph = self._resolve_graph(graph_identifier)
        node  = self._find_node(graph, node_id)
        graph.deleteNode(node)
        return {"deleted": node_id}

    def move_node(self, node_id, position, graph_identifier=None):
        graph = self._resolve_graph(graph_identifier)
        node  = self._find_node(graph, node_id)
        node.setPosition(float2(float(position[0]), float(position[1])))
        return {"node_id": node_id, "position": position}

    def duplicate_node(self, node_id, offset=None, graph_identifier=None):
        graph = self._resolve_graph(graph_identifier)
        node  = self._find_node(graph, node_id)
        if self._is_instance_node(node):
            raise ValueError(
                "Cannot duplicate library node '{}' via duplicate_node. "
                "Use create_instance_node with the same resource_url.".format(node_id))
        defn_id = self._get_node_def_id(node)
        pos     = self._get_node_pos(node)
        off     = offset or [100, 0]
        new_node = graph.newNode(defn_id)
        if not new_node:
            raise RuntimeError("Failed to duplicate node '{}'.".format(node_id))
        new_pos = [pos[0] + off[0], pos[1] + off[1]]
        new_node.setPosition(float2(float(new_pos[0]), float(new_pos[1])))
        return {
            "original_node_id": node_id,
            "new_node_id":      new_node.getIdentifier(),
            "definition":       defn_id,
            "position":         new_pos,
        }

    def get_node_info(self, node_id, graph_identifier=None):
        graph = self._resolve_graph(graph_identifier)
        node  = self._find_node(graph, node_id)

        inputs = []
        try:
            for prop in list(node.getProperties(SDPropertyCategory.Input)):
                pid = prop.getId()
                if pid in _SYSTEM_PARAMS:
                    continue
                info = {"id": pid}
                try:
                    val_obj = node.getPropertyValue(prop)
                    if val_obj is not None:
                        info["value"] = self._serialize_sd_value(val_obj)
                except Exception:
                    pass
                try:
                    conns = node.getPropertyConnections(prop)
                    if conns is not None:
                        cl = list(conns)
                        if cl:
                            info["connected_from"] = []
                            for conn in cl:
                                try:
                                    sn = conn.getInputPropertyNode()
                                    sp = conn.getInputProperty()
                                    if sn and sp:
                                        info["connected_from"].append(
                                            "{}.{}".format(sn.getIdentifier(), sp.getId()))
                                except Exception:
                                    pass
                except Exception:
                    pass
                inputs.append(info)
        except Exception:
            pass

        outputs = []
        try:
            for prop in list(node.getProperties(SDPropertyCategory.Output)):
                outputs.append({"id": prop.getId()})
        except Exception:
            pass

        annotations = []
        try:
            for prop in list(node.getProperties(SDPropertyCategory.Annotation)):
                pid = prop.getId()
                info = {"id": pid}
                try:
                    val_obj = node.getPropertyValue(prop)
                    if val_obj is not None:
                        info["value"] = self._serialize_sd_value(val_obj)
                except Exception:
                    pass
                annotations.append(info)
        except Exception:
            pass

        is_lib = self._is_instance_node(node)
        return {
            "node_id":        node_id,
            "definition":     self._get_node_def_id(node),
            "is_library_node": is_lib,
            "position":       self._get_node_pos(node),
            "inputs":         inputs,
            "outputs":        outputs,
            "annotations":    annotations,
            "note": (
                "Library node: use output IDs listed above, NOT 'unique_filter_output'"
                if is_lib else ""
            ),
        }

    def _serialize_sd_value(self, val):
        if val is None:
            return None
        try:
            raw = val.get()
        except Exception:
            return str(val)
        if hasattr(raw, 'x') and hasattr(raw, 'y'):
            d = {"x": raw.x, "y": raw.y}
            if hasattr(raw, 'z'):
                d["z"] = raw.z
            if hasattr(raw, 'w'):
                d["w"] = raw.w
            return d
        if hasattr(raw, 'r') and hasattr(raw, 'g'):
            return {"r": raw.r, "g": raw.g, "b": raw.b, "a": raw.a}
        if hasattr(raw, 'getSize') and hasattr(raw, 'getItem'):
            items = []
            try:
                for i in range(raw.getSize()):
                    item = raw.getItem(i)
                    items.append(str(item.get()) if hasattr(item, 'get') else str(item))
            except Exception:
                return str(raw)
            return items
        return str(raw)

    def get_library_nodes(self, filter_text="", limit=200):
        pkg_mgr = self._pkg_mgr()
        results = []
        for pkg in list(pkg_mgr.getPackages()):
            try:
                fp = pkg.getFilePath()
                if not fp:
                    continue
                children = None
                for recursive in (True, False):
                    try:
                        c = list(pkg.getChildrenResources(recursive))
                        if c:
                            children = c
                            break
                    except Exception:
                        continue
                if not children:
                    continue
                for res in children:
                    try:
                        if "SDSBSCompGraph" not in res.getClassName():
                            continue
                        rid = res.getIdentifier()
                        if filter_text and filter_text.lower() not in rid.lower():
                            continue
                        url = None
                        try:
                            url = res.getUrl()
                        except Exception:
                            pass
                        if not url:
                            continue
                        # Update cache
                        self._lib_url_cache[rid.lower()] = url
                        results.append({
                            "identifier": rid,
                            "url":        url,
                            "package":    os.path.basename(fp),
                        })
                        if len(results) >= limit:
                            break
                    except Exception:
                        pass
                if len(results) >= limit:
                    break
            except Exception:
                pass
        return {
            "count":     len(results),
            "nodes":     results,
            "truncated": len(results) >= limit,
            "filter":    filter_text,
        }

    # ═══════════════════════════════════════════════════════════════════════
    # ── CONNECTION TOOLS ────────────────────────────────────────────────
    # ═══════════════════════════════════════════════════════════════════════

    def connect_nodes(self, from_node_id, to_node_id,
                      from_output="unique_filter_output",
                      to_input="input1",
                      graph_identifier=None):
        graph     = self._resolve_graph(graph_identifier)
        from_node = self._find_node(graph, from_node_id)
        to_node   = self._find_node(graph, to_node_id)
        self._safe_connect(graph, from_node, from_output, to_node, to_input)
        return {
            "from_node":   from_node_id,
            "from_output": from_output,
            "to_node":     to_node_id,
            "to_input":    to_input,
            "success":     True,
        }

    def disconnect_nodes(self, node_id, input_id, graph_identifier=None):
        graph = self._resolve_graph(graph_identifier)
        node  = self._find_node(graph, node_id)
        prop  = node.getPropertyFromId(input_id, SDPropertyCategory.Input)
        if not prop:
            raise ValueError(
                "Property '{}' not found on node '{}'.".format(input_id, node_id))
        node.deletePropertyConnections(prop)
        return {"disconnected": "{}:{}".format(node_id, input_id)}

    def smart_connect(self, from_node_id, to_node_id,
                      from_output=None, to_input=None,
                      graph_identifier=None):
        """
        Auto-detect port names if not specified.
        Uses ATOMIC_PORTS registry for known node types.
        Falls back to get_node_info for library nodes.
        """
        graph     = self._resolve_graph(graph_identifier)
        from_node = self._find_node(graph, from_node_id)
        to_node   = self._find_node(graph, to_node_id)

        from_defn = self._get_node_def_id(from_node)
        to_defn   = self._get_node_def_id(to_node)

        # Determine from_output
        if not from_output:
            if from_defn in ATOMIC_PORTS:
                outs = ATOMIC_PORTS[from_defn]["outputs"]
                from_output = outs[0] if outs else "unique_filter_output"
            else:
                # Library node — query
                try:
                    outs = [p.getId() for p in
                            list(from_node.getProperties(SDPropertyCategory.Output))]
                    from_output = outs[0] if outs else "unique_filter_output"
                except Exception:
                    from_output = "unique_filter_output"

        # Determine to_input
        if not to_input:
            if to_defn in ATOMIC_PORTS:
                ins = ATOMIC_PORTS[to_defn]["inputs"]
                to_input = ins[0] if ins else "input1"
            else:
                try:
                    ins = [p.getId() for p in
                           list(to_node.getProperties(SDPropertyCategory.Input))
                           if p.getId() not in _SYSTEM_PARAMS]
                    to_input = ins[0] if ins else "input1"
                except Exception:
                    to_input = "input1"

        self._safe_connect(graph, from_node, from_output, to_node, to_input)
        return {
            "from_node":   from_node_id,
            "from_output": from_output,
            "to_node":     to_node_id,
            "to_input":    to_input,
            "success":     True,
        }

    # ═══════════════════════════════════════════════════════════════════════
    # ── PARAMETER TOOLS ─────────────────────────────────────────────────
    # ═══════════════════════════════════════════════════════════════════════

    def set_parameter(self, node_id, parameter_id, value, value_type="float",
                      graph_identifier=None):
        graph = self._resolve_graph(graph_identifier)
        node  = self._find_node(graph, node_id)
        sd_value = self._make_sd_value(value_type, value)

        input_ids  = set()
        annot_ids  = set()
        try:
            for p in list(node.getProperties(SDPropertyCategory.Input)):
                input_ids.add(p.getId())
        except Exception:
            pass
        try:
            for p in list(node.getProperties(SDPropertyCategory.Annotation)):
                annot_ids.add(p.getId())
        except Exception:
            pass

        if (input_ids or annot_ids) and \
           parameter_id not in input_ids and parameter_id not in annot_ids:
            all_ids = sorted(input_ids | annot_ids)
            raise ValueError(
                "Property '{}' not found on node '{}'. Available: {}".format(
                    parameter_id, node_id, all_ids))

        set_ok = False
        last_err = None
        for setter in [node.setInputPropertyValueFromId,
                       node.setAnnotationPropertyValueFromId]:
            try:
                setter(parameter_id, sd_value)
                set_ok = True
                break
            except Exception as e:
                last_err = e

        if not set_ok:
            raise RuntimeError("Failed to set '{}' on node '{}': {}".format(
                parameter_id, node_id, last_err))

        return {
            "node_id":      node_id,
            "parameter_id": parameter_id,
            "value":        value,
            "value_type":   value_type,
        }

    def set_graph_output_size(self, width_log2=11, height_log2=11, graph_identifier=None):
        graph = self._resolve_graph(graph_identifier)
        graph.setInputPropertyValueFromId(
            "$outputsize",
            SDValueInt2.sNew(int2(int(width_log2), int(height_log2)))
        )
        return {
            "graph":       graph.getIdentifier(),
            "width_log2":  width_log2,
            "height_log2": height_log2,
            "size":        "{}x{}".format(2 ** width_log2, 2 ** height_log2),
        }

    # ═══════════════════════════════════════════════════════════════════════
    # ── BATCH GRAPH BUILDER ─────────────────────────────────────────────
    # ═══════════════════════════════════════════════════════════════════════

    def create_batch_graph(self, graph_name, package_index=0, package_path=None,
                           nodes=None, connections=None, output_size_log2=11,
                           open_in_editor=True):
        """
        Create a complete graph in one call.
        Supports atomic nodes, library nodes (via resource_url or keyword),
        output nodes, and full connection wiring.
        """
        if nodes is None:
            nodes = []
        if connections is None:
            connections = []

        safe_name = _sanitize_identifier(graph_name)
        pkg   = self._resolve_package(package_index, package_path)
        graph = SDSBSCompGraph.sNew(pkg)
        graph.setIdentifier(safe_name)

        try:
            graph.setInputPropertyValueFromId(
                "$outputsize",
                SDValueInt2.sNew(int2(int(output_size_log2), int(output_size_log2))))
        except Exception as e:
            _log("Warning: Could not set graph output size: {}".format(e))

        try:
            _known_defs = {d.getId() for d in list(graph.getNodeDefinitions())}
        except Exception:
            _known_defs = set()

        alias_map = {}       # alias -> (node_obj, node_id_str)
        created   = []
        failed    = []

        for spec in nodes:
            defn_id  = spec.get("definition_id", "sbs::compositing::uniform")
            pos      = spec.get("position", [0, 0])
            params   = spec.get("parameters", {})
            alias    = (spec.get("id_alias") or spec.get("alias")
                        or defn_id.split("::")[-1])
            orig_alias = alias
            usage    = spec.get("usage")
            label    = spec.get("label")
            res_url  = spec.get("resource_url")
            lib_kw   = spec.get("library_keyword")

            try:
                node = None

                if defn_id == "sbs::compositing::output":
                    lv = label or usage or "output"
                    node = graph.newNode("sbs::compositing::output")
                    if node:
                        try:
                            node.setAnnotationPropertyValueFromId(
                                "label", SDValueString.sNew(lv))
                        except Exception:
                            pass

                elif res_url:
                    resource = None
                    for p in list(self._pkg_mgr().getPackages()):
                        try:
                            r = p.findResourceFromUrl(res_url)
                            if r is not None:
                                resource = r
                                break
                        except Exception:
                            pass
                    node = graph.newInstanceNode(resource) if resource else None
                    if not node:
                        raise ValueError("Resource '{}' not found.".format(res_url))

                elif lib_kw:
                    node = self._create_library_node(graph, lib_kw)

                else:
                    if _known_defs and defn_id not in _known_defs:
                        raise ValueError("Unknown definition '{}'. "
                                         "Use library_keyword for library nodes.".format(defn_id))
                    node = graph.newNode(defn_id)

                if not node:
                    raise RuntimeError("newNode returned None for '{}'.".format(defn_id))

                node.setPosition(float2(float(pos[0]), float(pos[1])))
                self._set_node_params(node, params)

                node_id = node.getIdentifier()
                # deduplicate aliases
                counter = 0
                while alias in alias_map:
                    counter += 1
                    alias = "{}_{}".format(orig_alias, counter)

                alias_map[alias] = (node, node_id)
                actual_def = self._get_node_def_id(node)
                created.append({
                    "alias": alias, "node_id": node_id, "definition": actual_def})

            except Exception as e:
                _log("Error creating node '{}': {}".format(alias, e))
                failed.append({"alias": alias, "error": str(e)})

        conn_results = []
        for conn in connections:
            fa  = conn.get("from") or conn.get("from_alias")
            ta  = conn.get("to") or conn.get("to_alias")
            fo  = conn.get("from_output", "unique_filter_output")
            ti  = conn.get("to_input", "input1")

            if fa not in alias_map:
                conn_results.append({"error": "from '{}' not found".format(fa), "conn": conn})
                continue
            if ta not in alias_map:
                conn_results.append({"error": "to '{}' not found".format(ta), "conn": conn})
                continue

            fn, _ = alias_map[fa]
            tn, _ = alias_map[ta]
            try:
                self._safe_connect(graph, fn, fo, tn, ti)
                conn_results.append({"from": fa, "to": ta, "success": True})
            except Exception as e:
                conn_results.append({"from": fa, "to": ta, "success": False, "error": str(e)})

        if open_in_editor:
            try:
                self._ui_mgr().openResourceInEditor(graph)
            except Exception as e:
                _log("Warning: openResourceInEditor failed: {}".format(e))

        return {
            "graph_identifier":  graph.getIdentifier(),
            "requested_name":    graph_name,
            "nodes_created":     len(created),
            "nodes_failed":      len(failed),
            "connections_ok":    sum(1 for c in conn_results if c.get("success")),
            "connections_failed": sum(1 for c in conn_results if not c.get("success")),
            "node_map":          {a: nid for a, (_, nid) in alias_map.items()},
            "nodes":             created,
            "failed_nodes":      failed,
            "connections":       conn_results,
        }

    # ═══════════════════════════════════════════════════════════════════════
    # ── SMART MATERIAL GRAPH BUILDER ────────────────────────────────────
    # ═══════════════════════════════════════════════════════════════════════

    def build_material_graph(self, graph_name, recipe_name,
                              package_index=0, package_path=None,
                              overrides=None, output_size_log2=11,
                              open_in_editor=True):
        """
        Build a complete PBR material graph from a named recipe.
        overrides: dict of parameter overrides applied on top of recipe defaults.
        """
        from .recipes import RECIPE_REGISTRY
        recipe_name_key = recipe_name.lower().replace(" ", "_").replace("-", "_")
        recipe = RECIPE_REGISTRY.get(recipe_name_key)
        if not recipe:
            available = sorted(RECIPE_REGISTRY.keys())
            raise ValueError(
                "Recipe '{}' not found. Available: {}".format(recipe_name, available))

        # Apply overrides
        if overrides:
            import copy
            recipe = copy.deepcopy(recipe)
            for node_alias, node_overrides in overrides.items():
                for spec in recipe.get("nodes", []):
                    if spec.get("id_alias") == node_alias:
                        spec.setdefault("parameters", {}).update(node_overrides)

        nodes       = recipe.get("nodes", [])
        connections = recipe.get("connections", [])

        return self.create_batch_graph(
            graph_name       = graph_name,
            package_index    = package_index,
            package_path     = package_path,
            nodes            = nodes,
            connections      = connections,
            output_size_log2 = output_size_log2,
            open_in_editor   = open_in_editor,
        )

    def build_heightmap_graph(self, graph_name, style,
                               package_index=0, package_path=None,
                               output_size_log2=11, open_in_editor=True,
                               detail_level=2, scale=5.0, disorder=0.5):
        """
        Build a heightmap graph for terrain/rock/cliff styles.
        style: 'cliff', 'rock', 'cracked', 'sand', 'mud', 'mountain', 'cobblestone'
        detail_level: 1=basic, 2=standard, 3=high detail
        """
        from .recipes import HEIGHTMAP_RECIPES
        style_key = style.lower().replace(" ", "_")
        builder   = HEIGHTMAP_RECIPES.get(style_key)
        if not builder:
            available = sorted(HEIGHTMAP_RECIPES.keys())
            raise ValueError(
                "Heightmap style '{}' not found. Available: {}".format(style, available))

        recipe = builder(detail_level=detail_level, scale=scale, disorder=disorder)
        nodes       = recipe.get("nodes", [])
        connections = recipe.get("connections", [])
        return self.create_batch_graph(
            graph_name       = graph_name,
            package_index    = package_index,
            package_path     = package_path,
            nodes            = nodes,
            connections      = connections,
            output_size_log2 = output_size_log2,
            open_in_editor   = open_in_editor,
        )

    # ═══════════════════════════════════════════════════════════════════════
    # ── RECIPE ENGINE ───────────────────────────────────────────────────
    # ═══════════════════════════════════════════════════════════════════════

    def list_recipes(self):
        """List all available material recipes."""
        try:
            from .recipes import RECIPE_REGISTRY, HEIGHTMAP_RECIPES
            recipes = []
            for key, recipe in RECIPE_REGISTRY.items():
                recipes.append({
                    "key":         key,
                    "name":        recipe.get("name", key),
                    "category":    recipe.get("category", "unknown"),
                    "description": recipe.get("description", ""),
                    "node_count":  len(recipe.get("nodes", [])),
                    "outputs":     recipe.get("outputs", []),
                })
            heightmaps = sorted(HEIGHTMAP_RECIPES.keys())
            return {
                "material_recipes": recipes,
                "heightmap_styles": heightmaps,
                "total_recipes": len(recipes),
                "total_heightmap_styles": len(heightmaps),
            }
        except ImportError as e:
            return {"error": "Recipes module not loaded: {}".format(e)}

    def get_recipe_info(self, recipe_name):
        """Get detailed info about a specific recipe."""
        try:
            from .recipes import RECIPE_REGISTRY
            key = recipe_name.lower().replace(" ", "_").replace("-", "_")
            recipe = RECIPE_REGISTRY.get(key)
            if not recipe:
                return {"error": "Recipe '{}' not found.".format(recipe_name)}
            return {
                "key":          key,
                "name":         recipe.get("name", key),
                "category":     recipe.get("category", "unknown"),
                "description":  recipe.get("description", ""),
                "outputs":      recipe.get("outputs", []),
                "node_count":   len(recipe.get("nodes", [])),
                "nodes_preview": [
                    {
                        "alias": s.get("id_alias", "?"),
                        "type":  s.get("definition_id", s.get("library_keyword", "?")),
                    }
                    for s in recipe.get("nodes", [])[:20]
                ],
            }
        except ImportError as e:
            return {"error": "Recipes module not loaded: {}".format(e)}

    def apply_recipe(self, recipe_name, graph_identifier=None, position_offset=None,
                     overrides=None):
        """
        Apply a recipe to an EXISTING graph (add nodes + connections to current graph).
        Useful for combining multiple recipes or adding detail passes to existing work.
        """
        try:
            from .recipes import RECIPE_REGISTRY
        except ImportError as e:
            raise RuntimeError("Recipes module not loaded: {}".format(e))

        key    = recipe_name.lower().replace(" ", "_").replace("-", "_")
        recipe = RECIPE_REGISTRY.get(key)
        if not recipe:
            raise ValueError("Recipe '{}' not found.".format(recipe_name))

        import copy
        recipe = copy.deepcopy(recipe)

        # Apply position offset
        if position_offset:
            ox, oy = float(position_offset[0]), float(position_offset[1])
            for spec in recipe.get("nodes", []):
                p = spec.get("position", [0, 0])
                spec["position"] = [p[0] + ox, p[1] + oy]

        # Apply overrides
        if overrides:
            for node_alias, node_overrides in overrides.items():
                for spec in recipe.get("nodes", []):
                    if spec.get("id_alias") == node_alias:
                        spec.setdefault("parameters", {}).update(node_overrides)

        graph     = self._resolve_graph(graph_identifier)
        nodes     = recipe.get("nodes", [])
        conns     = recipe.get("connections", [])

        try:
            _known_defs = {d.getId() for d in list(graph.getNodeDefinitions())}
        except Exception:
            _known_defs = set()

        alias_map = {}
        created   = []
        failed    = []

        for spec in nodes:
            defn_id    = spec.get("definition_id", "sbs::compositing::uniform")
            pos        = spec.get("position", [0, 0])
            params     = spec.get("parameters", {})
            alias      = spec.get("id_alias") or defn_id.split("::")[-1]
            orig_alias = alias
            res_url    = spec.get("resource_url")
            lib_kw     = spec.get("library_keyword")
            label      = spec.get("label")
            usage      = spec.get("usage")

            try:
                node = None
                if defn_id == "sbs::compositing::output":
                    lv = label or usage or "output"
                    node = graph.newNode("sbs::compositing::output")
                    if node:
                        try:
                            node.setAnnotationPropertyValueFromId(
                                "label", SDValueString.sNew(lv))
                        except Exception:
                            pass
                elif res_url:
                    resource = None
                    for p in list(self._pkg_mgr().getPackages()):
                        try:
                            r = p.findResourceFromUrl(res_url)
                            if r is not None:
                                resource = r
                                break
                        except Exception:
                            pass
                    node = graph.newInstanceNode(resource) if resource else None
                    if not node:
                        raise ValueError("Resource '{}' not found.".format(res_url))
                elif lib_kw:
                    node = self._create_library_node(graph, lib_kw)
                else:
                    if _known_defs and defn_id not in _known_defs:
                        raise ValueError("Unknown definition '{}'.".format(defn_id))
                    node = graph.newNode(defn_id)

                if not node:
                    raise RuntimeError("newNode returned None.")

                node.setPosition(float2(float(pos[0]), float(pos[1])))
                self._set_node_params(node, params)

                nid = node.getIdentifier()
                counter = 0
                while alias in alias_map:
                    counter += 1
                    alias = "{}_{}".format(orig_alias, counter)
                alias_map[alias] = (node, nid)
                created.append({"alias": alias, "node_id": nid})

            except Exception as e:
                _log("Error creating node '{}': {}".format(alias, e))
                failed.append({"alias": alias, "error": str(e)})

        conn_results = []
        for conn in conns:
            fa = conn.get("from") or conn.get("from_alias")
            ta = conn.get("to") or conn.get("to_alias")
            fo = conn.get("from_output", "unique_filter_output")
            ti = conn.get("to_input", "input1")
            if fa not in alias_map or ta not in alias_map:
                conn_results.append({"error": "alias not found", "conn": conn})
                continue
            fn, _ = alias_map[fa]
            tn, _ = alias_map[ta]
            try:
                self._safe_connect(graph, fn, fo, tn, ti)
                conn_results.append({"from": fa, "to": ta, "success": True})
            except Exception as e:
                conn_results.append({"from": fa, "to": ta, "success": False, "error": str(e)})

        return {
            "graph_identifier":  graph.getIdentifier(),
            "recipe":            recipe_name,
            "nodes_added":       len(created),
            "nodes_failed":      len(failed),
            "connections_ok":    sum(1 for c in conn_results if c.get("success")),
            "connections_failed": sum(1 for c in conn_results if not c.get("success")),
            "node_map":          {a: nid for a, (_, nid) in alias_map.items()},
        }

    # ═══════════════════════════════════════════════════════════════════════
    # ── UTILITIES ───────────────────────────────────────────────────────
    # ═══════════════════════════════════════════════════════════════════════

    def arrange_nodes(self, graph_identifier=None, start_x=-1000, start_y=0,
                      node_spacing_x=200, node_spacing_y=150):
        """
        WARNING: DESTROYS all connections in SD 15. Use move_node() instead.
        Only use when connections don't matter.
        """
        graph = self._resolve_graph(graph_identifier)
        nodes = list(graph.getNodes())
        if not nodes:
            return {"graph": graph.getIdentifier(), "arranged_nodes": 0,
                    "warning": "No nodes to arrange."}

        per_row = max(1, int(len(nodes) ** 0.5) + 1)
        x, y = float(start_x), float(start_y)
        for i, node in enumerate(nodes):
            try:
                node.setPosition(float2(x, y))
            except Exception:
                pass
            x += node_spacing_x
            if (i + 1) % per_row == 0:
                x = float(start_x)
                y += node_spacing_y

        return {
            "graph":          graph.getIdentifier(),
            "arranged_nodes": len(nodes),
            "warning":        "arrange_nodes DESTROYS all connections in SD 15.",
        }

    def execute_code(self, code):
        """Execute arbitrary Python on the SD main thread. Keep it short."""
        stdout_cap = io.StringIO()
        stderr_cap = io.StringIO()
        app_obj    = sd.getContext().getSDApplication()

        def _open_in_editor_safe(g):
            try:
                app_obj.getUIMgr().openResourceInEditor(g)
            except Exception as e:
                print("[MCP] open_in_editor warning: {}".format(e))

        namespace = {
            "sd": sd, "app": app_obj,
            "pkg_mgr": app_obj.getPackageMgr(),
            "ui_mgr":  app_obj.getUIMgr(),
            "open_in_editor": _open_in_editor_safe,
        }
        error = None
        try:
            with redirect_stdout(stdout_cap), redirect_stderr(stderr_cap):
                exec(compile(code, "<mcp_execute>", "exec"), namespace)
        except Exception as e:
            error = "{}: {}".format(type(e).__name__, e)
            stderr_cap.write(traceback.format_exc())

        return {
            "executed": error is None,
            "stdout":   stdout_cap.getvalue(),
            "stderr":   stderr_cap.getvalue(),
            "error":    error,
        }


# ════════════════════════════════════════════════════════════════════════════
# Plugin entry points
# ════════════════════════════════════════════════════════════════════════════

def initializeSDPlugin():
    global _server
    _log("Initializing v{}".format(".".join(map(str, PLUGIN_VERSION))))

    if _pyside_path:
        _log("PySide path injected: {}".format(_pyside_path))
    else:
        _log("Warning: PySide6 path not found")

    if _QT_BINDING_USED:
        _log("Qt binding: {}".format(_QT_BINDING_USED))
    else:
        _log("FATAL: No Qt binding. All MCP calls will fail.")

    inv = _Invoker.instance()
    if inv is not None:
        _log("Qt invoker ready (Signal/Slot dispatch)")
    else:
        _log("FATAL: Qt invoker creation failed")

    try:
        _server = SDMCPServer(ports=DEFAULT_PORTS)
        _server.start()
        _log("Plugin v{} ready! Port: {}".format(
            ".".join(map(str, PLUGIN_VERSION)), DEFAULT_PORTS))
    except Exception as e:
        _log("FATAL: Failed to start server: {}".format(e))
        traceback.print_exc()


def uninitializeSDPlugin():
    global _server
    _log("Uninitializing")
    if _server:
        _server.stop()
        _server = None
