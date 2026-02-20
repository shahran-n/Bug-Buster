"""
Bug Classifier - Classifies detected issues into known bug patterns.
"""


BUG_PATTERNS = {
    "fsm_stuck": {
        "label": "FSM Stuck State",
        "keywords": ["state", "fsm", "idle", "stuck", "transition"],
        "description": "Finite state machine is not transitioning between states correctly.",
        "fix_hint": "Check state transition conditions and default state assignments.",
    },
    "arithmetic_overflow": {
        "label": "Arithmetic Overflow/Underflow",
        "keywords": ["overflow", "underflow", "addition", "multiplication", "carry", "count"],
        "description": "An arithmetic operation exceeds the bit-width of the register.",
        "fix_hint": "Widen the register or add overflow detection logic.",
    },
    "off_by_one": {
        "label": "Off-By-One Error",
        "keywords": ["counter", "count", "index", "off", "one", "boundary"],
        "description": "A counter or index is off by one cycle or value.",
        "fix_hint": "Check <= vs < comparisons and initial values.",
    },
    "reset_polarity": {
        "label": "Reset Polarity Mismatch",
        "keywords": ["reset", "rst", "polarity", "active", "high", "low", "negedge", "posedge"],
        "description": "Reset signal polarity does not match the logic (active-high vs active-low).",
        "fix_hint": "Invert the reset condition or rename rstn vs rst consistently.",
    },
    "clock_domain": {
        "label": "Clock Domain / Timing Issue",
        "keywords": ["clock", "clk", "domain", "timing", "setup", "hold", "metastable"],
        "description": "Signal crosses clock domains without proper synchronization.",
        "fix_hint": "Add a 2-FF synchronizer on any signal crossing clock domains.",
    },
    "mux_select": {
        "label": "Mux Select Error",
        "keywords": ["select", "mux", "sel", "case", "condition"],
        "description": "An incorrect mux select signal drives the wrong data path.",
        "fix_hint": "Verify select signal encoding matches case statement branches.",
    },
    "handshake": {
        "label": "Handshake Protocol Violation",
        "keywords": ["valid", "ready", "ack", "req", "handshake", "fifo", "full", "empty"],
        "description": "A valid/ready or request/acknowledge handshake protocol is violated.",
        "fix_hint": "Ensure valid is not deasserted before ready is seen.",
    },
    "width_mismatch": {
        "label": "Width Mismatch",
        "keywords": ["width", "bit", "truncat", "extend", "sign", "port"],
        "description": "Signal width mismatch causes truncation or unintended sign extension.",
        "fix_hint": "Explicitly cast or zero-extend signals to match target width.",
    },
    "xz_propagation": {
        "label": "X/Z Propagation",
        "keywords": ["x", "z", "unknown", "high_impedance", "uninitialized"],
        "description": "Uninitialized or high-impedance values are propagating through the design.",
        "fix_hint": "Ensure all registers are reset to a known value in the reset condition.",
    },
    "stuck_signal": {
        "label": "Stuck Signal",
        "keywords": ["stuck", "never", "change", "constant", "static"],
        "description": "A signal never changes value during simulation.",
        "fix_hint": "Verify the signal is being driven and not accidentally disconnected.",
    },
}


def classify_bugs(rtl_analysis, vcd_issues, log_issues):
    """Classify all detected issues into bug categories."""
    classified = []

    all_issues = vcd_issues + log_issues

    for issue in all_issues:
        issue_text = (issue.get("description", "") + " " + issue.get("type", "")).lower()
        best_match = None
        best_score = 0

        for bug_id, pattern in BUG_PATTERNS.items():
            score = sum(1 for kw in pattern["keywords"] if kw in issue_text)
            # Also match against signal name
            sig = issue.get("signal", "").lower()
            score += sum(1 for kw in pattern["keywords"] if kw in sig)
            if score > best_score:
                best_score = score
                best_match = bug_id

        if best_match is None:
            best_match = "xz_propagation" if issue.get("type") == "xz_propagation" else "stuck_signal"

        pattern = BUG_PATTERNS[best_match]
        classified.append({
            "bug_type": best_match,
            "label": pattern["label"],
            "description": pattern["description"],
            "fix_hint": pattern["fix_hint"],
            "source_issue": issue,
            "severity": issue.get("severity", "medium"),
        })

    # Also check RTL suspicious lines
    for line_issue in rtl_analysis.get("suspicious_lines", []):
        text = line_issue["issue"].lower()
        classified.append({
            "bug_type": "reset_polarity" if "reset" in text else "clock_domain" if "edge" in text else "off_by_one",
            "label": "RTL Static Analysis Finding",
            "description": line_issue["issue"],
            "fix_hint": "Review the flagged line in the RTL source.",
            "source_issue": {"line": line_issue["line"], "text": line_issue["text"]},
            "severity": "medium",
        })

    return classified


def summarize_bugs(classified_bugs):
    """Create a short summary of all bugs found."""
    if not classified_bugs:
        return "No bugs detected."

    counts = {}
    for bug in classified_bugs:
        label = bug["label"]
        counts[label] = counts.get(label, 0) + 1

    parts = [f"{v}x {k}" for k, v in counts.items()]
    return f"Found {len(classified_bugs)} issue(s): " + ", ".join(parts)
