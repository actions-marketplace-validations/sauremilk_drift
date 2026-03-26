"""Synthetic repo builders and repair functions for the repair benchmark.

Each builder creates a repo with known drift patterns modeled after
real findings in flask_full.json / httpx_full.json.  Each repair
function modifies the repo in-place and returns a description string.
"""

from __future__ import annotations

from pathlib import Path

# =========================================================================
# webapp (Flask-like) — MDS + PFS
# =========================================================================

_MAKE_TIMEDELTA_BODY = (
    "def _make_timedelta(value):\n"
    '    """Convert value to timedelta if not already one."""\n'
    "    if value is None or isinstance(value, timedelta):\n"
    "        return value\n"
    "    return timedelta(seconds=value)\n"
)


def create_webapp(d: Path) -> dict[str, list[str]]:
    """Create webapp repo.  Returns {signal: [mutation_descriptions]}."""
    src = d / "src" / "webapp"
    for p in [src, src / "handlers", src / "models", src / "utils", d / "tests"]:
        p.mkdir(parents=True, exist_ok=True)
        (p / "__init__.py").write_text("")

    # MDS: exact duplicate _make_timedelta
    (src / "app.py").write_text(
        '"""Main application module."""\n'
        "from datetime import timedelta\n\n" + _MAKE_TIMEDELTA_BODY + "\n\n"
        "class App:\n"
        "    def __init__(self, name: str):\n"
        "        self.name = name\n"
        "        self.config: dict = {}\n\n"
        "    def configure(self, **kwargs):\n"
        '        """Configure the application."""\n'
        "        for k, v in kwargs.items():\n"
        '            if k == "timeout": v = _make_timedelta(v)\n'
        "            self.config[k] = v\n"
        "        return self\n"
    )
    (src / "base_app.py").write_text(
        '"""Base application module."""\n'
        "from datetime import timedelta\n\n" + _MAKE_TIMEDELTA_BODY + "\n\n"
        "class BaseApp:\n"
        "    def __init__(self):\n"
        "        self.defaults: dict = {}\n\n"
        "    def set_default(self, key: str, value):\n"
        '        if key.endswith("_timeout"): value = _make_timedelta(value)\n'
        "        self.defaults[key] = value\n"
    )

    # PFS: 4 error-handling variants
    (src / "handlers" / "auth.py").write_text(
        "import logging\nlogger = logging.getLogger(__name__)\n\n"
        "def authenticate(u: str, p: str) -> dict:\n"
        "    try:\n"
        "        if not u or not p: raise ValueError('Missing')\n"
        "        return {'token': 'abc', 'user': u}\n"
        "    except ValueError as e:\n"
        "        logger.error(f'Auth failed: {e}')\n"
        "        raise\n"
        "    except Exception as e:\n"
        "        logger.exception('Unexpected')\n"
        "        raise RuntimeError('Internal') from e\n"
    )
    (src / "handlers" / "orders.py").write_text(
        "class OrderError(Exception): pass\n\n"
        "def create_order(items: list) -> dict:\n"
        "    if not items: raise OrderError('No items')\n"
        "    try:\n"
        "        total = sum(i['price'] for i in items)\n"
        "    except (KeyError, TypeError):\n"
        "        raise OrderError('Bad format')\n"
        "    return {'order_id': 1, 'total': total}\n"
    )
    (src / "handlers" / "payments.py").write_text(
        "def process_payment(amount: float) -> dict:\n"
        "    result: dict = {'success': False, 'error': None}\n"
        "    if amount <= 0:\n"
        "        result['error'] = 'Invalid amount'\n"
        "        return result\n"
        "    if amount > 10000:\n"
        "        result['error'] = 'Exceeds limit'\n"
        "        return result\n"
        "    result['success'] = True\n"
        "    result['transaction_id'] = 'txn_123'\n"
        "    return result\n"
    )
    (src / "handlers" / "notifications.py").write_text(
        "def send_notification(uid: int, msg: str) -> bool:\n"
        "    assert uid > 0, 'uid must be positive'\n"
        "    assert msg, 'msg required'\n"
        "    return len(msg) <= 1000\n"
    )

    (d / "README.md").write_text(
        "# Webapp\n\nBenchmark web app.\n\n"
        "- `src/webapp/` — App code\n"
        "- `src/webapp/handlers/` — Handlers\n"
        "- `src/webapp/models/` — Models\n"
        "- `tests/` — Tests\n"
    )

    return {
        "mutant_duplicate": ["Exact duplicate: _make_timedelta in app.py and base_app.py"],
        "pattern_fragmentation": [
            "error_handling: 4 variants in handlers/ (try/except, custom exc, result-dict, assert)"
        ],
    }


def repair_webapp_mds_correct(d: Path) -> str:
    """Consolidate _make_timedelta into utils/timedelta.py."""
    src = d / "src" / "webapp"
    (src / "utils" / "timedelta.py").write_text(
        "from datetime import timedelta\n\n"
        "def make_timedelta(value):\n"
        '    """Convert value to timedelta if not already one."""\n'
        "    if value is None or isinstance(value, timedelta):\n"
        "        return value\n"
        "    return timedelta(seconds=value)\n"
    )
    (src / "app.py").write_text(
        '"""Main application module."""\n'
        "from src.webapp.utils.timedelta import make_timedelta\n\n"
        "class App:\n"
        "    def __init__(self, name: str):\n"
        "        self.name = name\n"
        "        self.config: dict = {}\n\n"
        "    def configure(self, **kwargs):\n"
        "        for k, v in kwargs.items():\n"
        '            if k == "timeout": v = make_timedelta(v)\n'
        "            self.config[k] = v\n"
        "        return self\n"
    )
    (src / "base_app.py").write_text(
        '"""Base application module."""\n'
        "from src.webapp.utils.timedelta import make_timedelta\n\n"
        "class BaseApp:\n"
        "    def __init__(self):\n"
        "        self.defaults: dict = {}\n\n"
        "    def set_default(self, key: str, value):\n"
        '        if key.endswith("_timeout"): value = make_timedelta(value)\n'
        "        self.defaults[key] = value\n"
    )
    return "Consolidated _make_timedelta into utils/timedelta.py"


def repair_webapp_mds_incorrect(d: Path) -> str:
    """Rename one copy but keep identical body — should still detect."""
    src = d / "src" / "webapp"
    (src / "base_app.py").write_text(
        '"""Base application module."""\n'
        "from datetime import timedelta\n\n"
        "def _convert_to_timedelta(value):\n"
        '    """Convert value to timedelta if not already one."""\n'
        "    if value is None or isinstance(value, timedelta):\n"
        "        return value\n"
        "    return timedelta(seconds=value)\n\n\n"
        "class BaseApp:\n"
        "    def __init__(self):\n"
        "        self.defaults: dict = {}\n\n"
        "    def set_default(self, key: str, value):\n"
        '        if key.endswith("_timeout"): value = _convert_to_timedelta(value)\n'
        "        self.defaults[key] = value\n"
    )
    return "Renamed to _convert_to_timedelta (body unchanged — duplication persists)"


# =========================================================================
# datalib (httpx-like) — MDS + EDS + SMS
# =========================================================================

_FLUSH_BODY = (
    "    def flush(self) -> bytes:\n"
    '        """Flush remaining buffered data."""\n'
    "        if self._finished:\n"
    '            return b""\n'
    "        self._finished = True\n"
    "        remaining = self._buffer\n"
    '        self._buffer = b""\n'
    "        return remaining\n"
)


def create_datalib(d: Path) -> dict[str, list[str]]:
    """Create datalib repo.  Returns {signal: [mutation_descriptions]}."""
    src = d / "src" / "datalib"
    for p in [src, src / "decoders", src / "transforms", d / "tests"]:
        p.mkdir(parents=True, exist_ok=True)
        (p / "__init__.py").write_text("")

    # MDS: duplicate flush()
    (src / "decoders" / "compression.py").write_text(
        '"""Compression decoders."""\n\n'
        "class DeflateDecoder:\n"
        "    def __init__(self):\n"
        '        self._buffer = b""\n'
        "        self._finished = False\n\n"
        "    def decode(self, data: bytes) -> bytes:\n"
        "        self._buffer += data\n"
        "        return data\n\n" + _FLUSH_BODY + "\n\nclass GZipDecoder:\n"
        "    def __init__(self):\n"
        '        self._buffer = b""\n'
        "        self._finished = False\n\n"
        "    def decode(self, data: bytes) -> bytes:\n"
        "        self._buffer += data\n"
        "        return data\n\n" + _FLUSH_BODY
    )

    # EDS: complex undocumented function
    (src / "transforms" / "pipeline.py").write_text(
        '"""Data transformation pipeline."""\n\n'
        "def transform_records(records, schema, mappings, filters, aggregations, opts):\n"
        "    result = []\n"
        "    for rec in records:\n"
        "        t = {}\n"
        "        for field, spec in schema.items():\n"
        "            src_f = mappings.get(field, field)\n"
        "            val = rec.get(src_f)\n"
        '            if spec.get("type") == "int":\n'
        "                try: val = int(val) if val is not None else spec.get('default', 0)\n"
        "                except (ValueError, TypeError): val = spec.get('default', 0)\n"
        '            elif spec.get("type") == "float":\n'
        "                try: val = float(val) if val is not None else spec.get('default', 0.0)\n"
        "                except (ValueError, TypeError): val = spec.get('default', 0.0)\n"
        '            elif spec.get("type") == "str":\n'
        "                val = str(val) if val is not None else spec.get('default', '')\n"
        "                if spec.get('max_length'): val = val[:spec['max_length']]\n"
        '            elif spec.get("type") == "bool":\n'
        "                val = bool(val) if val is not None else spec.get('default', False)\n"
        "            t[field] = val\n"
        "        skip = False\n"
        "        for f in filters:\n"
        "            fv = t.get(f['field'])\n"
        "            if f['op'] == 'eq' and fv != f['value']: skip = True\n"
        "            elif f['op'] == 'gt' and (fv is None or fv <= f['value']): skip = True\n"
        "            elif f['op'] == 'lt' and (fv is None or fv >= f['value']): skip = True\n"
        "            elif f['op'] == 'in' and fv not in f['value']: skip = True\n"
        "        if not skip: result.append(t)\n"
        "    if aggregations:\n"
        "        agg = {}\n"
        "        for a in aggregations:\n"
        "            fld = a['field']\n"
        "            vs = [r.get(fld, 0) for r in result if r.get(fld) is not None]\n"
        "            if a['func'] == 'sum': agg[f'{fld}_sum'] = sum(vs)\n"
        "            elif a['func'] == 'avg': agg[f'{fld}_avg'] = sum(vs)/len(vs) if vs else 0\n"
        "            elif a['func'] == 'count': agg[f'{fld}_count'] = len(vs)\n"
        "        return agg\n"
        "    return result\n"
    )

    # SMS: novel system-level deps
    (src / "native_optimizer.py").write_text(
        "import ast, ctypes, dis, mmap, struct  # noqa: F401,E401\n\n"
        "def optimize_bytecode(code: str) -> bytes:\n"
        "    tree = ast.parse(code)\n"
        '    compiled = compile(tree, "<string>", "exec")\n'
        "    bytecode = dis.Bytecode(compiled)\n"
        "    return struct.pack('I', len(list(bytecode)))\n"
    )

    (d / "README.md").write_text(
        "# DataLib\n\nBenchmark data lib.\n\n"
        "- `src/datalib/` — Core\n"
        "- `src/datalib/decoders/` — Decoders\n"
        "- `src/datalib/transforms/` — Transforms\n"
        "- `tests/` — Tests\n"
    )

    return {
        "mutant_duplicate": ["Exact duplicate: DeflateDecoder.flush and GZipDecoder.flush"],
        "explainability_deficit": [
            "Unexplained complexity: transform_records (CC>=12, 6 params, no docstring)"
        ],
        "system_misalignment": [
            "Novel deps: native_optimizer.py uses ctypes/struct/mmap in data lib"
        ],
    }


def repair_datalib_mds_correct(d: Path) -> str:
    """Extract shared flush into BaseDecoder."""
    (d / "src" / "datalib" / "decoders" / "compression.py").write_text(
        '"""Compression decoders with shared base."""\n\n'
        "class BaseDecoder:\n"
        "    def __init__(self):\n"
        '        self._buffer = b""\n'
        "        self._finished = False\n\n"
        "    def flush(self) -> bytes:\n"
        '        if self._finished: return b""\n'
        "        self._finished = True\n"
        "        remaining = self._buffer\n"
        '        self._buffer = b""\n'
        "        return remaining\n\n\n"
        "class DeflateDecoder(BaseDecoder):\n"
        "    def decode(self, data: bytes) -> bytes:\n"
        "        self._buffer += data\n"
        "        return data\n\n\n"
        "class GZipDecoder(BaseDecoder):\n"
        "    def decode(self, data: bytes) -> bytes:\n"
        "        self._buffer += data\n"
        "        return data\n"
    )
    return "Extracted flush() into BaseDecoder, eliminated duplication"


def repair_datalib_eds_correct(d: Path) -> str:
    """Add docstrings, type hints, split complex function."""
    (d / "src" / "datalib" / "transforms" / "pipeline.py").write_text(
        '"""Data transformation pipeline."""\n\n\n'
        "def _coerce(value, spec: dict):\n"
        '    """Coerce value to schema type."""\n'
        "    t = spec.get('type')\n"
        "    if t == 'int':\n"
        "        try: return int(value) if value is not None else spec.get('default', 0)\n"
        "        except (ValueError, TypeError): return spec.get('default', 0)\n"
        "    if t == 'float':\n"
        "        try: return float(value) if value is not None else spec.get('default', 0.0)\n"
        "        except (ValueError, TypeError): return spec.get('default', 0.0)\n"
        "    if t == 'str':\n"
        "        r = str(value) if value is not None else spec.get('default', '')\n"
        "        ml = spec.get('max_length')\n"
        "        return r[:ml] if ml else r\n"
        "    if t == 'bool':\n"
        "        return bool(value) if value is not None else spec.get('default', False)\n"
        "    return value\n\n\n"
        "def _passes(record: dict, filters: list) -> bool:\n"
        '    """Check if record passes all filters."""\n'
        "    for f in filters:\n"
        "        fv = record.get(f['field'])\n"
        "        op = f['op']\n"
        "        if op == 'eq' and fv != f['value']: return False\n"
        "        if op == 'gt' and (fv is None or fv <= f['value']): return False\n"
        "        if op == 'lt' and (fv is None or fv >= f['value']): return False\n"
        "        if op == 'in' and fv not in f['value']: return False\n"
        "    return True\n\n\n"
        "def _aggregate(records: list, aggs: list) -> dict:\n"
        '    """Compute aggregations."""\n'
        "    out: dict = {}\n"
        "    for a in aggs:\n"
        "        fld = a['field']\n"
        "        vs = [r.get(fld, 0) for r in records if r.get(fld) is not None]\n"
        "        if a['func'] == 'sum': out[f'{fld}_sum'] = sum(vs)\n"
        "        elif a['func'] == 'avg': out[f'{fld}_avg'] = sum(vs)/len(vs) if vs else 0\n"
        "        elif a['func'] == 'count': out[f'{fld}_count'] = len(vs)\n"
        "    return out\n\n\n"
        "def transform_records(\n"
        "    records: list, schema: dict, mappings: dict,\n"
        "    filters: list, aggregations: list, opts: dict | None = None,\n"
        ") -> list | dict:\n"
        '    """Transform, filter, and aggregate records per schema.\n\n'
        "    Args:\n"
        "        records: Input dicts.  schema: Type specs.\n"
        "        mappings: Field name map.  filters: Filter conditions.\n"
        "        aggregations: Aggregation specs.  opts: Reserved.\n"
        '    """\n'
        "    result = []\n"
        "    for rec in records:\n"
        "        t = {f: _coerce(rec.get(mappings.get(f, f)), s) for f, s in schema.items()}\n"
        "        if _passes(t, filters): result.append(t)\n"
        "    return _aggregate(result, aggregations) if aggregations else result\n"
    )
    return "Added docstrings + split into helpers (CC <= 10)"


# =========================================================================
# webapp — DIA (doc_impl_drift) repairs
# =========================================================================


def repair_webapp_dia_correct(d: Path) -> str:
    """Fix README to reference only existing root-level directories."""
    (d / "README.md").write_text(
        "# Webapp\n\nBenchmark web app.\n\n"
        "## Structure\n\n"
        "- `src/` — Application source code\n"
        "- `tests/` — Test suite\n"
    )
    return "Fixed README: removed phantom dir refs (webapp/, handlers/, models/)"


def repair_webapp_dia_incorrect(d: Path) -> str:
    """Fix some phantom refs but introduce new ones (≥3 to equal baseline)."""
    (d / "README.md").write_text(
        "# Webapp\n\nBenchmark web app.\n\n"
        "## Structure\n\n"
        "- `src/` — Source code\n"
        "- `tests/` — Tests\n"
        "- `config/` — Configuration files\n"
        "- `migrations/` — Database migrations\n"
        "- `static/` — Static assets\n"
    )
    return "Removed original phantom refs but added config/, migrations/, static/ (phantom)"


# =========================================================================
# webapp — PFS (pattern_fragmentation) repair
# =========================================================================


def repair_webapp_pfs_correct(d: Path) -> str:
    """Standardize error handling across all handlers.

    All handlers get identical fingerprint: handler_count=1,
    exception_type='Exception', actions=['raise'], no finally/else.
    """
    src = d / "src" / "webapp"
    (src / "handlers" / "auth.py").write_text(
        "class AuthError(Exception): pass\n\n\n"
        "def authenticate(u: str, p: str) -> dict:\n"
        "    try:\n"
        "        if not u or not p:\n"
        "            raise AuthError('Missing credentials')\n"
        "        return {'token': 'abc', 'user': u}\n"
        "    except Exception as e:\n"
        "        raise AuthError('Auth failed') from e\n"
    )
    (src / "handlers" / "orders.py").write_text(
        "class OrderError(Exception): pass\n\n\n"
        "def create_order(items: list) -> dict:\n"
        "    try:\n"
        "        if not items:\n"
        "            raise OrderError('No items')\n"
        "        total = sum(i['price'] for i in items)\n"
        "        return {'order_id': 1, 'total': total}\n"
        "    except Exception as e:\n"
        "        raise OrderError('Order failed') from e\n"
    )
    (src / "handlers" / "payments.py").write_text(
        "class PaymentError(Exception): pass\n\n\n"
        "def process_payment(amount: float) -> dict:\n"
        "    try:\n"
        "        if amount <= 0:\n"
        "            raise PaymentError('Invalid amount')\n"
        "        if amount > 10000:\n"
        "            raise PaymentError('Exceeds limit')\n"
        "        return {'success': True, 'transaction_id': 'txn_123'}\n"
        "    except Exception as e:\n"
        "        raise PaymentError('Payment failed') from e\n"
    )
    (src / "handlers" / "notifications.py").write_text(
        "class NotificationError(Exception): pass\n\n\n"
        "def send_notification(uid: int, msg: str) -> bool:\n"
        "    try:\n"
        "        if uid <= 0:\n"
        "            raise NotificationError('uid must be positive')\n"
        "        if not msg:\n"
        "            raise NotificationError('msg required')\n"
        "        return len(msg) <= 1000\n"
        "    except Exception as e:\n"
        "        raise NotificationError('Notification failed') from e\n"
    )
    return "Standardized all handlers: identical except Exception + raise pattern"


# =========================================================================
# datalib — EDS incorrect repair
# =========================================================================


def repair_datalib_eds_incorrect(d: Path) -> str:
    """Add minimal docstring without reducing complexity — EDS should persist."""
    p = d / "src" / "datalib" / "transforms" / "pipeline.py"
    content = p.read_text()
    content = content.replace(
        "def transform_records(records, schema, mappings, "
        "filters, aggregations, opts):\n"
        "    result = []",
        "def transform_records(records, schema, mappings, "
        "filters, aggregations, opts):\n"
        '    """Process records."""\n'
        "    result = []",
    )
    p.write_text(content)
    return "Added trivial docstring (complexity unchanged — EDS persists)"
