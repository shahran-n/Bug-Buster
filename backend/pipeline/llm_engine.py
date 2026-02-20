"""
LLM Engine - Fully conversational agent.
The LLM sees the full conversation history, indexed file list, and any
loaded file content. It decides what to do — debug, explain, write code,
answer follow-ups, anything.
"""
import json
import urllib.request
import urllib.error

SYSTEM_PROMPT = """You are FABB (Full-Auto Bug Buster), an expert RTL/Verilog verification engineer and AI coding assistant built into a debugging tool.

You have access to the user's project folder which has been indexed. File contents will be provided to you when relevant.

You can do ANYTHING the user asks:
- Debug and explain Verilog/SystemVerilog bugs in detail
- Suggest and write synthesizable RTL fixes
- Answer follow-up questions about a previous bug or fix
- Explain RTL concepts (FSMs, timing, resets, handshakes, etc.)
- Write new Verilog modules from scratch
- Review code for best practices
- Compare two implementations
- Answer general hardware/HDL questions
- Have a normal conversation

When you detect bugs or suggest fixes, structure your response using these XML tags so the UI can render them nicely:

<bug>
  <label>Short bug title</label>
  <severity>high|medium|low</severity>
  <signal>signal_name (if applicable)</signal>
  <cycle>cycle number (if applicable)</cycle>
  <line>line number (if applicable)</line>
  <description>Plain English explanation of the bug</description>
  <root_cause>The specific technical root cause</root_cause>
  <patch_original>the exact buggy line(s) from the RTL</patch_original>
  <patch_fixed>the corrected line(s)</patch_fixed>
  <patch_explanation>Why this fix works</patch_explanation>
</bug>

You can include multiple <bug> blocks. Outside of bug blocks, respond normally in plain text — explain your reasoning, answer questions, write code, etc.

If the user asks something not related to RTL at all, just answer helpfully as a general assistant. You are not limited to only RTL topics."""


def chat(messages, config, file_context=""):
    """
    Send a full conversation to the LLM and get a response.
    messages: list of {role, content} dicts (full history)
    file_context: string of loaded file contents to inject
    Returns: raw text response from LLM
    """
    api_key = config.get("api_key", "").strip()
    provider = config.get("api_provider", "openai")

    # Build system prompt with file context if available
    system = SYSTEM_PROMPT
    if file_context:
        system += f"\n\n--- LOADED FILE CONTEXT ---\n{file_context}\n--- END FILE CONTEXT ---"

    if not api_key:
        return _no_key_response(messages[-1]["content"] if messages else "")

    try:
        if provider == "anthropic":
            return _call_anthropic(messages, system, api_key)
        else:
            return _call_openai(messages, system, api_key)
    except Exception as e:
        return f"⚠️ API error: {str(e)}\n\nMake sure your API key is correct in Settings."


def _call_openai(messages, system, api_key):
    payload = json.dumps({
        "model": "gpt-4o",
        "messages": [{"role": "system", "content": system}] + messages,
        "max_tokens": 2000,
        "temperature": 0.3,
    }).encode()

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]


def _call_anthropic(messages, system, api_key):
    payload = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 2000,
        "system": system,
        "messages": messages,
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    return data["content"][0]["text"]


def _no_key_response(prompt):
    """Minimal rule-based response when no API key is set."""
    p = prompt.lower()
    if any(k in p for k in ["debug", "bug", "fix", "error", "fail"]):
        return (
            "I can see you want to debug some RTL. To get full AI-powered analysis, "
            "please add your OpenAI or Anthropic API key in ⚙ Settings.\n\n"
            "Without an API key I can still run static analysis — try asking me to "
            "debug a specific file and I'll do rule-based detection."
        )
    return (
        "I'm FABB, your RTL debugging assistant! To unlock full conversational AI, "
        "add your API key in ⚙ Settings.\n\n"
        "You can still use me to index files and run static analysis without a key."
    )


def parse_bug_blocks(text):
    """Parse <bug>...</bug> blocks from LLM response into structured dicts."""
    import re
    bugs = []
    for block in re.finditer(r'<bug>(.*?)</bug>', text, re.DOTALL):
        b = block.group(1)
        def tag(name):
            m = re.search(rf'<{name}>(.*?)</{name}>', b, re.DOTALL)
            return m.group(1).strip() if m else ""
        bugs.append({
            "label":             tag("label") or "Bug Detected",
            "severity":          tag("severity") or "medium",
            "signal":            tag("signal"),
            "cycle":             tag("cycle"),
            "line":              tag("line"),
            "description":       tag("description"),
            "root_cause":        tag("root_cause"),
            "llm_explanation":   tag("description"),
            "patch": {
                "original":    tag("patch_original"),
                "fixed":       tag("patch_fixed"),
                "explanation": tag("patch_explanation"),
            },
            "confidence": "high",
            "note": "",
        })
    # Remove bug blocks from plain text
    plain = re.sub(r'<bug>.*?</bug>', '', text, flags=re.DOTALL).strip()
    return plain, bugs
