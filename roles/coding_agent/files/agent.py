#!/usr/bin/env python3
"""Minimal autonomous coding agent for small local models via Ollama.

Loop: (1) model writes pytest tests for the task (or you supply them),
(2) model writes solution, (3) run tests, (4) feed failures back, repeat.

Usage:
  python agent.py "Write a function slugify(s) that ..." --model qwen2.5-coder:3b
  python agent.py "task..." --tests my_tests.py
Output goes to $AGENT_WORKSPACES/<timestamp>/ (default ./workspaces/).

Environment: OLLAMA_URL, AGENT_MODEL, AGENT_WORKSPACES.
"""
import argparse, os, re, resource, subprocess, sys, time
from pathlib import Path
import requests

OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")

SYSTEM = """You are a careful Python programmer. Reply ONLY with files in this exact format, no prose:

### FILE: solution.py
```python
<code>
```

Rules: standard library only unless told otherwise. Put the solution in solution.py.
Tests import from solution (e.g. `from solution import slugify`)."""

FILE_RE = re.compile(r"###\s*FILE:\s*(\S+)\s*\n```[\w+-]*\n(.*?)```", re.DOTALL)


def chat(model, messages):
    r = requests.post(
        OLLAMA,
        json={"model": model, "messages": messages, "stream": False,
              "options": {"temperature": 0.2, "num_ctx": 8192}},
        timeout=1800,
    )
    r.raise_for_status()
    return r.json()["message"]["content"]


def parse_files(text):
    out = {}
    for path, code in FILE_RE.findall(text):
        p = Path(path)
        if p.is_absolute() or ".." in p.parts:  # keep writes inside workdir
            continue
        out[path] = code
    return out


def write_files(workdir, files):
    for path, code in files.items():
        dest = workdir / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(code)


def limits():
    resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (50 * 1024**2, 50 * 1024**2))


def run_tests(workdir):
    try:
        p = subprocess.run(
            [sys.executable, "-m", "pytest", "-x", "-q", "--tb=short"],
            cwd=workdir, capture_output=True, text=True, timeout=60,
            preexec_fn=limits,
        )
        return p.returncode == 0, (p.stdout + p.stderr)[-3000:]
    except subprocess.TimeoutExpired:
        return False, "Tests timed out after 60s (infinite loop or too slow?)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("task")
    ap.add_argument("--model", default=os.environ.get("AGENT_MODEL", "qwen2.5-coder:3b"))
    ap.add_argument("--tests", help="path to your own pytest file (recommended)")
    ap.add_argument("--max-iters", type=int, default=6)
    a = ap.parse_args()

    root = Path(os.environ.get("AGENT_WORKSPACES", "workspaces"))
    workdir = root / time.strftime("%Y%m%d-%H%M%S")
    workdir.mkdir(parents=True)

    # Step 1: tests
    if a.tests:
        (workdir / "test_solution.py").write_text(Path(a.tests).read_text())
    else:
        print("Generating tests...")
        out = chat(a.model, [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content":
                f"Task:\n{a.task}\n\nWrite ONLY pytest tests as test_solution.py "
                "(5-8 focused tests incl. edge cases). Do not write the solution."},
        ])
        write_files(workdir, {k: v for k, v in parse_files(out).items()
                              if k == "test_solution.py"})
        if not (workdir / "test_solution.py").exists():
            sys.exit("Model did not produce test_solution.py")

    tests = (workdir / "test_solution.py").read_text()
    solution, feedback = "", ""

    # Step 2: solve / test / repair loop
    for i in range(1, a.max_iters + 1):
        prompt = f"Task:\n{a.task}\n\nTests (test_solution.py):\n```python\n{tests}\n```\n"
        if solution:
            prompt += f"\nYour previous solution.py:\n```python\n{solution}\n```\n"
            prompt += f"\nIt FAILED with:\n{feedback}\n\nFix solution.py. Output the full file."
        else:
            prompt += "\nWrite solution.py so these tests pass."
        print(f"[iter {i}] asking {a.model}...")
        out = chat(a.model, [{"role": "system", "content": SYSTEM},
                             {"role": "user", "content": prompt}])
        files = parse_files(out)
        if "solution.py" not in files:
            feedback = "Your reply had no '### FILE: solution.py' block. Follow the format exactly."
            continue
        files.pop("test_solution.py", None)  # model may not edit the tests
        write_files(workdir, files)
        solution = files["solution.py"]
        ok, feedback = run_tests(workdir)
        print(feedback.strip().splitlines()[-1] if feedback.strip() else "")
        if ok:
            print(f"\nPASSED on iteration {i}. Output: {workdir}/solution.py")
            return
    print(f"\nGave up after {a.max_iters} iterations. Last attempt in {workdir}/")
    sys.exit(1)


if __name__ == "__main__":
    main()
