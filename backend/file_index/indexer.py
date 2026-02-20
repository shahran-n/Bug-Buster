"""
File Indexer - recursively scans a folder and builds an index of RTL-related files.
"""
import os
import time

SUPPORTED_EXTENSIONS = {
    ".v": "verilog",
    ".sv": "systemverilog",
    ".vcd": "waveform",
    ".log": "log",
    ".txt": "log",
}

class FileIndexer:
    def __init__(self):
        self._index = {}   # filename (no ext) -> list of {path, ext, type, mtime}
        self._flat = {}    # full filename -> path
        self._folder = ""

    def index(self, folder):
        self._folder = folder
        self._index = {}
        self._flat = {}
        results = []

        for root, dirs, files in os.walk(folder):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in SUPPORTED_EXTENSIONS:
                    continue
                full_path = os.path.join(root, fname)
                stem = os.path.splitext(fname)[0].lower()
                entry = {
                    "path": full_path,
                    "filename": fname,
                    "stem": stem,
                    "ext": ext,
                    "type": SUPPORTED_EXTENSIONS[ext],
                    "mtime": os.path.getmtime(full_path),
                    "rel": os.path.relpath(full_path, folder),
                }
                if stem not in self._index:
                    self._index[stem] = []
                self._index[stem].append(entry)
                self._flat[fname.lower()] = entry
                results.append(entry["rel"])

        return results

    def get_all(self):
        all_files = []
        for entries in self._index.values():
            for e in entries:
                all_files.append({"filename": e["filename"], "type": e["type"], "rel": e["rel"]})
        return all_files

    def resolve(self, query):
        """
        Fuzzy-match a query string against the index.
        Returns list of matching entries sorted by score.
        """
        query_lower = query.lower().strip()

        # Remove common words
        stopwords = ["the", "file", "module", "debug", "check", "analyze", "find", "bugs", "in", "for", "latest", "last"]
        tokens = [t for t in query_lower.split() if t not in stopwords]

        results = []

        for stem, entries in self._index.items():
            for entry in entries:
                score = 0
                # Exact filename match
                if query_lower == entry["filename"].lower():
                    score = 100
                # Exact stem match
                elif query_lower == stem:
                    score = 90
                # Token in stem
                else:
                    for token in tokens:
                        if token in stem:
                            score += 50
                        elif stem in token:
                            score += 30
                        else:
                            # Character overlap score
                            common = sum(1 for c in token if c in stem)
                            if len(token) > 0:
                                score += int(40 * common / max(len(token), len(stem)))

                if score > 20:
                    results.append((score, entry))

        results.sort(key=lambda x: -x[0])
        return [e for _, e in results]

    def get_latest(self, file_type=None):
        """Get the most recently modified file of a given type."""
        candidates = []
        for entries in self._index.values():
            for e in entries:
                if file_type is None or e["type"] == file_type:
                    candidates.append(e)
        if not candidates:
            return None
        return max(candidates, key=lambda e: e["mtime"])

    def get_by_type(self, file_type):
        results = []
        for entries in self._index.values():
            for e in entries:
                if e["type"] == file_type:
                    results.append(e)
        return results
