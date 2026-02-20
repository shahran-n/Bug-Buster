"""
Pipeline Runner - Fully conversational agent runner.
The LLM drives everything. We load relevant file context and pass the
full conversation history on every turn.
"""
import os
import re

from pipeline.rtl_parser import parse_verilog
from pipeline.vcd_parser import parse_vcd, find_mismatches
from pipeline.log_parser import parse_log
from pipeline.llm_engine import chat, parse_bug_blocks


LATEST_KEYWORDS = ["latest", "last", "recent", "newest", "current"]
ALL_KEYWORDS    = ["all", "every", "each"]
DEBUG_KEYWORDS  = ["debug", "bug", "fix", "error", "fail", "check", "analyze",
                   "analyse", "find", "issue", "problem", "wrong", "broken"]
FILE_EXTENSIONS = [".v", ".sv", ".vcd", ".log", ".txt"]


def run_pipeline(prompt, indexer, config, history=None):
    """
    Main entry point — fully conversational.
    prompt:  current user message
    history: list of {role, content} from previous turns
    Returns response dict.
    """
    history = history or []
    response = {
        "prompt": prompt,
        "status": "ok",
        "messages": [],
        "bug_reports": [],
        "files_used": [],
        "plain_text": "",
        "summary": "",
    }

    # --- Resolve any files mentioned in the prompt ---
    file_context, files_used, load_msgs = _load_relevant_files(prompt, indexer)
    response["files_used"] = files_used
    response["messages"]   = load_msgs

    # --- Build conversation for LLM ---
    # Inject indexed file list so LLM knows what's available
    all_files = indexer.get_all()
    file_list_str = ""
    if all_files:
        names = [f["filename"] for f in all_files]
        file_list_str = f"\n\n[Indexed project files: {', '.join(names)}]"

    # Augment the user message with file list context (invisible tag)
    augmented_prompt = prompt + file_list_str

    messages = history + [{"role": "user", "content": augmented_prompt}]

    # --- Call LLM ---
    raw = chat(messages, config, file_context)

    # --- Parse bug blocks out of the response ---
    plain_text, bug_reports = parse_bug_blocks(raw)
    response["plain_text"] = plain_text
    response["bug_reports"] = bug_reports

    if bug_reports:
        response["summary"] = f"⚠️ Found {len(bug_reports)} issue(s)."
    else:
        response["summary"] = ""

    return response


def _load_relevant_files(prompt, indexer):
    """
    Detect if the prompt references any files and load their contents.
    Returns (file_context_string, files_used_list, messages_list)
    """
    prompt_lower = prompt.lower()
    files_used = []
    messages   = []
    contexts   = []

    wants_latest = any(k in prompt_lower for k in LATEST_KEYWORDS)
    wants_all    = any(k in prompt_lower for k in ALL_KEYWORDS)
    wants_debug  = any(k in prompt_lower for k in DEBUG_KEYWORDS)

    # Check if any indexed filenames are mentioned
    matched = indexer.resolve(prompt)
    verilog  = [m for m in matched if m["type"] in ("verilog", "systemverilog")]
    waveform = [m for m in matched if m["type"] == "waveform"]
    logs     = [m for m in matched if m["type"] == "log"]

    # Determine which files to load
    to_load = []

    if wants_all and wants_debug:
        to_load += indexer.get_by_type("verilog") + indexer.get_by_type("systemverilog")
    elif verilog:
        to_load.append(verilog[0])
    
    if waveform:
        to_load.append(waveform[0])
    elif wants_latest or (wants_debug and not verilog):
        latest_vcd = indexer.get_latest("waveform")
        if latest_vcd:
            to_load.append(latest_vcd)

    if logs:
        to_load.append(logs[0])
    elif wants_latest or any(k in prompt_lower for k in ["log", "simulation", "failed"]):
        latest_log = indexer.get_latest("log")
        if latest_log:
            to_load.append(latest_log)

    # Load file contents
    for entry in to_load:
        try:
            with open(entry["path"], "r", errors="replace") as f:
                content = f.read()

            files_used.append(entry["filename"])
            messages.append(f"📄 Loaded: {entry['filename']}")

            # For Verilog, also run static analysis and include results
            if entry["type"] in ("verilog", "systemverilog"):
                analysis = parse_verilog(entry["path"])
                suspicious = analysis.get("suspicious_lines", [])
                analysis_summary = (
                    f"Modules: {', '.join(analysis['modules']) or 'none'} | "
                    f"Signals: {len(analysis['signals'])} | "
                    f"Always blocks: {len(analysis['always_blocks'])} | "
                    f"Static issues found: {len(suspicious)}"
                )
                contexts.append(
                    f"=== {entry['filename']} ===\n{content[:3000]}\n\n"
                    f"[Static analysis: {analysis_summary}]\n"
                    + (f"[Suspicious lines: {suspicious}]\n" if suspicious else "")
                )
            elif entry["type"] == "waveform":
                vcd = parse_vcd(entry["path"])
                issues = find_mismatches(vcd)
                sig_names = [s["name"] for s in vcd["signals"].values()]
                contexts.append(
                    f"=== {entry['filename']} (VCD) ===\n"
                    f"Signals: {', '.join(sig_names)}\n"
                    f"Max time: {vcd['max_time']} {vcd['timescale']}\n"
                    f"Waveform anomalies: {len(issues)}\n"
                    + (f"Issues: {issues[:5]}\n" if issues else "")
                )
            elif entry["type"] == "log":
                log = parse_log(entry["path"])
                contexts.append(
                    f"=== {entry['filename']} (Log) ===\n"
                    f"Pass: {log['pass_count']} | Fail: {log['fail_count']}\n"
                    f"Failures:\n" +
                    "\n".join(f["text"] for f in log["failures"][:10])
                )
        except Exception as e:
            messages.append(f"⚠️ Could not load {entry['filename']}: {e}")

    return "\n\n".join(contexts), files_used, messages
