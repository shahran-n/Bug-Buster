"""
RTL Parser - Parses Verilog/SystemVerilog files using regex.
Extracts modules, ports, signals, FSMs, always blocks, arithmetic ops.
"""
import re
import os


def parse_verilog(filepath):
    """Parse a Verilog file and return structured analysis."""
    with open(filepath, "r", errors="replace") as f:
        content = f.read()

    result = {
        "filepath": filepath,
        "filename": os.path.basename(filepath),
        "modules": [],
        "signals": [],
        "fsm_states": [],
        "always_blocks": [],
        "arithmetic_ops": [],
        "reset_signals": [],
        "clock_signals": [],
        "raw_lines": content.splitlines(),
    }

    # Remove comments
    clean = re.sub(r'//[^\n]*', '', content)
    clean = re.sub(r'/\*.*?\*/', '', clean, flags=re.DOTALL)

    # Extract modules
    for m in re.finditer(r'\bmodule\s+(\w+)\s*[#(]?', clean):
        result["modules"].append(m.group(1))

    # Extract ports and signals
    port_patterns = [
        r'\b(input|output|inout)\s+(?:wire|reg)?\s*(?:\[[\d\s:]+\])?\s*(\w+)',
        r'\b(wire|reg)\s+(?:\[[\d\s:]+\])?\s*(\w+)',
    ]
    for pat in port_patterns:
        for m in re.finditer(pat, clean):
            direction = m.group(1)
            name = m.group(2)
            if name not in ('begin', 'end', 'if', 'else', 'case', 'endcase'):
                result["signals"].append({"direction": direction, "name": name})

    # Detect FSM state parameters/localparams
    for m in re.finditer(r'\b(?:parameter|localparam)\s+(\w+)\s*=\s*(\d+|\'[bhdBHD][0-9a-fA-F_xXzZ]+)', clean):
        name = m.group(1)
        if any(kw in name.upper() for kw in ["STATE", "ST_", "_ST", "IDLE", "INIT", "WAIT", "BUSY", "DONE", "RUN", "FETCH", "EXEC", "DECODE"]):
            result["fsm_states"].append({"name": name, "value": m.group(2)})

    # Extract always blocks
    always_pattern = re.compile(r'always\s*@\s*\(([^)]*)\)(.*?)(?=always\s*@|\bendmodule\b)', re.DOTALL)
    for m in always_pattern.finditer(clean):
        sensitivity = m.group(1).strip()
        body = m.group(2).strip()[:300]  # limit size
        block_type = "sequential" if "posedge" in sensitivity or "negedge" in sensitivity else "combinational"
        result["always_blocks"].append({
            "sensitivity": sensitivity,
            "type": block_type,
            "body_preview": body,
        })

    # Detect arithmetic operations
    arith_ops = []
    for op, name in [(r'\+', "addition"), (r'-', "subtraction"), (r'\*', "multiplication"),
                     (r'/', "division"), (r'%', "modulo"), (r'<<', "left_shift"), (r'>>', "right_shift")]:
        if re.search(op, clean):
            arith_ops.append(name)
    result["arithmetic_ops"] = arith_ops

    # Detect clock and reset signals
    for sig in result["signals"]:
        name = sig["name"].lower()
        if any(kw in name for kw in ["clk", "clock", "ck"]):
            result["clock_signals"].append(sig["name"])
        if any(kw in name for kw in ["rst", "reset", "rstn", "nrst"]):
            result["reset_signals"].append(sig["name"])

    # Line-level analysis for potential bugs
    result["suspicious_lines"] = find_suspicious_patterns(content)

    return result


def find_suspicious_patterns(content):
    """Find potentially buggy patterns in Verilog."""
    issues = []
    lines = content.splitlines()

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Both edges sensitivity (common bug)
        if re.search(r'always\s*@\s*\(\s*(?:posedge|negedge)\s+\w+\s*,?\s*(?:posedge|negedge)\s+\w+', stripped):
            issues.append({"line": i, "text": stripped, "issue": "Dual-edge sensitivity — may cause double-triggering"})

        # Missing posedge (bare clock in sensitivity list)
        if re.search(r'always\s*@\s*\(\s*\w+\s*\)', stripped) and "posedge" not in stripped and "negedge" not in stripped:
            if re.search(r'always', stripped):
                issues.append({"line": i, "text": stripped, "issue": "Missing posedge/negedge in sensitivity list"})

        # Blocking assignment in sequential block
        if re.search(r'always\s*@.*posedge', stripped):
            pass  # will check next lines — simplified

        # Non-blocking in combinational
        if re.search(r'always\s*@\s*\(\s*\*', stripped):
            pass

        # Potential reset polarity issue: active-high reset used with negedge
        if "negedge" in stripped and "rst" in stripped.lower() and "n" not in stripped.lower().split("rst")[0][-3:]:
            issues.append({"line": i, "text": stripped, "issue": "Possible reset polarity mismatch (negedge with active-high reset name)"})

    return issues
