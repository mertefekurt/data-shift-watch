# Data Shift Watch

<p align="center">
  <img src="assets/readme-cover.svg" alt="Data Shift Watch cover" width="100%" />
</p>

A small CLI for detecting distribution shift between baseline and current CSV datasets.

## Working notes

- quick local checks around data quality
- small CI jobs where a readable report is enough
- review workflows that need deterministic output
- examples based on `examples/current.csv`

## Install

```bash
git clone https://github.com/mertefekurt/data-shift-watch.git
cd data-shift-watch
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Use

```bash
data-shift-watch examples/current.csv
```

## Files

```text
.github/        CI workflow
examples/       sample inputs
src/            package source
tests/          test coverage
.gitignore      project file
pyproject.toml  package metadata
```
