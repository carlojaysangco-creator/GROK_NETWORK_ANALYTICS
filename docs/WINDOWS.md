# Windows run notes

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[test,rpa]"
pytest -q
network-analytics check
network-analytics publish-sample
network-analytics serve
```

Open `http://127.0.0.1:8050`.

Topology HTML opens in a new tab via `/artifacts/...`.

If Pyvis is missing: `pip install pyvis` or `pip install -e ".[rpa]"`.

Data directories `data\`, `runtime\`, `artifacts\`, `logs\` are created under the project root and are gitignored.
