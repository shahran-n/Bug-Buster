"""
Log Parser - Parses simulation log files for assertion failures and errors.
"""
import re
import os


def parse_log(filepath):
    """Parse a simulation log file and extract failures and warnings."""
    result = {
        "filepath": filepath,
        "filename": os.path.basename(filepath),
        "failures": [],
        "warnings": [],
        "errors": [],
        "pass_count": 0,
        "fail_count": 0,
    }

    if not os.path.exists(filepath):
        return result

    with open(filepath, "r", errors="replace") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        line_stripped = line.strip()
        line_lower = line_stripped.lower()

        # Detect failures
        if any(kw in line_lower for kw in ["fail", "error", "assertion", "mismatch", "wrong"]):
            # Try to extract time/cycle info
            time_match = re.search(r'(?:time|cycle|@)\s*[=:]?\s*(\d+)', line_lower)
            signal_match = re.search(r'(?:signal|wire|reg|output)\s+["\']?(\w+)["\']?', line_lower)

            entry = {
                "type": "failure",
                "line_num": i + 1,
                "text": line_stripped,
                "severity": "high",
            }
            if time_match:
                entry["cycle"] = int(time_match.group(1))
            if signal_match:
                entry["signal"] = signal_match.group(1)

            # Classify the failure
            if "mismatch" in line_lower:
                entry["description"] = f"Output mismatch detected: {line_stripped}"
            elif "assertion" in line_lower:
                entry["description"] = f"Assertion failure: {line_stripped}"
            elif "timeout" in line_lower:
                entry["description"] = f"Simulation timeout: {line_stripped}"
            else:
                entry["description"] = f"Error/failure: {line_stripped}"

            result["failures"].append(entry)
            result["fail_count"] += 1

        # Detect warnings
        elif "warning" in line_lower:
            result["warnings"].append({
                "type": "warning",
                "line_num": i + 1,
                "text": line_stripped,
                "severity": "low",
                "description": f"Warning: {line_stripped}",
            })

        # Count passes
        elif any(kw in line_lower for kw in ["pass", "ok", "success", "✓", "passed"]):
            result["pass_count"] += 1

    return result
