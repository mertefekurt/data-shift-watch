# Data Shift Watch

A small CLI for detecting distribution shift between baseline and current CSV datasets. The idea is simple: give Data Shift Watch the local file or fixture, get a readable result, and decide what needs attention before the next handoff.

## A quick look

![Data Shift Watch cover](assets/readme-cover.svg)

## Start here

```bash
git clone https://github.com/mertefekurt/data-shift-watch.git
cd data-shift-watch
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Run:

```bash
data-shift-watch examples/current.csv
```

## Files with the most context

```text
.github/        CI workflow
examples/       sample inputs
src/            package source
tests/          test coverage
.gitignore      project file
pyproject.toml  package metadata
```
