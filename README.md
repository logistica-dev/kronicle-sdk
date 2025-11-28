# Kronicle SDK

Python-based Software Development Kit to fetch and push information to a Kronicle.

examples in [README.ipynb](README.ipynb)

# use in an other project

1 - build the package

```bash
python -m build
```

> creates a dist dir

2 - pip install

within the venv of the other package, run :

```bash
pip install kronicle-sdk

pip install kronicle-sdk[pandas]

```

Then

```python
from kronicle import KronicleWriter
```

should work.
