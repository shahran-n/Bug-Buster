# FABB — Full-Auto Bug Buster

An AI-powered RTL debugging agent that runs as a chat window in your browser.
Point it at a folder of Verilog files and ask it to find bugs in plain English.

---

## Requirements

- Python 3.8+ (no external packages needed — pure stdlib)
- A modern web browser (Chrome, Firefox, Safari, Edge)
- Optional: OpenAI or Anthropic API key for AI-powered explanations

---

## Run

```bash
python3 fabb.py
```

This starts the backend server and opens the UI in your browser automatically.

---

## First-Time Setup

1. Click **⚙ Settings** in the top-right corner
2. Set your **Project Folder** to the folder containing your `.v` / `.sv` / `.vcd` files
3. (Optional) Add your **OpenAI or Anthropic API key** for AI explanations
4. Click **Save & Index**

---

## Example Prompts

| Prompt | What FABB does |
|--------|----------------|
| `debug counter.v` | Parses counter.v + newest VCD, runs full pipeline |
| `check latest simulation` | Loads newest .log + .vcd, reports failures |
| `find all reset logic bugs` | Scans all .v files for reset issues |
| `what files are indexed?` | Lists all files FABB knows about |
| `debug fsm_traffic.v` | Analyzes FSM module for stuck states |

---

## Project Structure

```
fabb/
├── fabb.py                   ← LAUNCHER (run this)
├── frontend/
│   └── index.html            ← Chat UI (opens in browser)
├── backend/
│   ├── server.py             ← HTTP API server
│   ├── file_index/
│   │   └── indexer.py        ← Folder scanner + fuzzy resolver
│   └── pipeline/
│       ├── runner.py         ← Orchestrates all stages
│       ├── rtl_parser.py     ← Verilog static analysis
│       ├── vcd_parser.py     ← Waveform parsing
│       ├── log_parser.py     ← Simulation log parsing
│       ├── bug_classifier.py ← Bug pattern classification
│       └── llm_engine.py     ← OpenAI / Anthropic integration
└── sample_project/           ← Demo files to test with
    ├── counter.v             ← Buggy counter (3 injected bugs)
    ├── fsm_traffic.v         ← FSM with missing default state
    ├── counter.vcd           ← Sample waveform
    └── counter_sim.log       ← Sample simulation log
```

---

## Without an API Key

FABB still works without an API key — it uses rule-based analysis to detect and
classify bugs from static RTL patterns and VCD anomalies. Add an API key to get
full AI-generated explanations and synthesizable patch suggestions.

---

## Stopping FABB

Press `Ctrl+C` in the terminal where you ran `python3 fabb.py`.
