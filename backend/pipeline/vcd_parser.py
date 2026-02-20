"""
VCD Parser - Parses Value Change Dump files to extract signal timelines.
Pure Python, no external dependencies.
"""
import os
import re


def parse_vcd(filepath):
    """Parse a VCD file and return signal timeline data."""
    result = {
        "filepath": filepath,
        "filename": os.path.basename(filepath),
        "timescale": "1ns",
        "signals": {},       # id -> {name, width, module}
        "timeline": {},      # id -> [(time, value), ...]
        "max_time": 0,
        "signal_names": [],  # human-readable names
    }

    if not os.path.exists(filepath):
        return result

    with open(filepath, "r", errors="replace") as f:
        content = f.read()

    # Parse header
    ts = re.search(r'\$timescale\s+(.*?)\s*\$end', content, re.DOTALL)
    if ts:
        result["timescale"] = ts.group(1).strip()

    # Parse variable declarations: $var type width id name $end
    var_pattern = re.compile(r'\$var\s+(\w+)\s+(\d+)\s+(\S+)\s+(\S+)(?:\s+\S+)?\s*\$end')
    module_stack = []
    current_module = "top"

    for line in content.splitlines():
        line = line.strip()
        if "$scope" in line:
            m = re.search(r'\$scope\s+\w+\s+(\w+)', line)
            if m:
                module_stack.append(m.group(1))
                current_module = ".".join(module_stack)
        elif "$upscope" in line:
            if module_stack:
                module_stack.pop()
            current_module = ".".join(module_stack) if module_stack else "top"

        m = var_pattern.search(line)
        if m:
            vtype, width, vid, vname = m.group(1), int(m.group(2)), m.group(3), m.group(4)
            result["signals"][vid] = {
                "name": vname,
                "width": width,
                "type": vtype,
                "module": current_module,
                "full_name": f"{current_module}.{vname}" if current_module else vname,
            }
            result["timeline"][vid] = []

    # Parse value changes
    current_time = 0
    in_dumpvars = False

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("$comment") or line.startswith("$end"):
            if "$dumpvars" in line:
                in_dumpvars = True
            if "$end" in line:
                in_dumpvars = False
            continue

        # Timestamp
        if line.startswith("#"):
            try:
                current_time = int(line[1:])
                result["max_time"] = max(result["max_time"], current_time)
            except ValueError:
                pass
            continue

        # Scalar value change: 0id, 1id, xid, zid
        m = re.match(r'^([01xXzZ])(\S+)$', line)
        if m:
            val, vid = m.group(1), m.group(2)
            if vid in result["timeline"]:
                result["timeline"][vid].append((current_time, val))
            continue

        # Vector value change: b0101 id or B0101 id
        m = re.match(r'^[bBrR](\S+)\s+(\S+)$', line)
        if m:
            val, vid = m.group(1), m.group(2)
            if vid in result["timeline"]:
                result["timeline"][vid].append((current_time, val))

    result["signal_names"] = [s["name"] for s in result["signals"].values()]
    return result


def find_mismatches(vcd_data, expected_signals=None):
    """
    Find signals that have unexpected transitions, X/Z values, or anomalies.
    expected_signals: dict of {signal_name: expected_final_value}
    """
    issues = []

    for vid, events in vcd_data["timeline"].items():
        sig = vcd_data["signals"].get(vid, {})
        name = sig.get("name", vid)

        # Check for X/Z propagation
        xz_events = [(t, v) for t, v in events if v.lower() in ('x', 'z') or 'x' in v.lower() or 'z' in v.lower()]
        if xz_events:
            issues.append({
                "type": "xz_propagation",
                "signal": name,
                "cycles": [t for t, v in xz_events[:3]],
                "severity": "high",
                "description": f"Signal '{name}' has X/Z values at cycles {[t for t, v in xz_events[:3]]}",
            })

        # Check for no transitions (stuck signal)
        if len(events) <= 1 and sig.get("type") not in ("parameter", "real"):
            issues.append({
                "type": "stuck_signal",
                "signal": name,
                "severity": "medium",
                "description": f"Signal '{name}' never changes — may be stuck",
            })

        # Check for expected vs actual
        if expected_signals and name in expected_signals:
            if events:
                final_val = events[-1][1]
                expected = expected_signals[name]
                if str(final_val) != str(expected):
                    issues.append({
                        "type": "value_mismatch",
                        "signal": name,
                        "expected": expected,
                        "actual": final_val,
                        "at_time": events[-1][0],
                        "severity": "high",
                        "description": f"Signal '{name}': expected {expected}, got {final_val} at t={events[-1][0]}",
                    })

    return issues


def get_signal_at_time(vcd_data, signal_name, time):
    """Get the value of a signal at a specific simulation time."""
    for vid, sig in vcd_data["signals"].items():
        if sig["name"] == signal_name:
            events = vcd_data["timeline"].get(vid, [])
            val = "x"
            for t, v in events:
                if t <= time:
                    val = v
                else:
                    break
            return val
    return None
