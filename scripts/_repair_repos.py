"""Synthetic repo builders and repair functions for the repair benchmark.

Each builder creates a repo with known drift patterns modeled after
real findings in flask_full.json / httpx_full.json.  Each repair
function modifies the repo in-place and returns a description string.
"""

from __future__ import annotations

import os
import subprocess
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

    # SMS: novel third-party deps (stdlib is ignored by SMS)
    (src / "native_optimizer.py").write_text(
        "import numpy as np  # noqa: F401\n"
        "import pandas as pd  # noqa: F401\n"
        "import pyarrow as pa  # noqa: F401\n\n\n"
        "def optimize_records(records: list) -> list:\n"
        '    """Vectorized record optimization."""\n'
        "    df = pd.DataFrame(records)\n"
        "    arr = pa.array(df.values.flatten())\n"
        "    return np.where(arr.is_valid, arr.to_pylist(), []).tolist()\n"
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
            "Novel deps: native_optimizer.py uses numpy/pandas/pyarrow in data lib"
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


# =========================================================================
# Helper: git commit with explicit date
# =========================================================================


def _commit_dated(d: Path, msg: str, date_str: str) -> None:
    """Create a git commit with a specific author+committer date."""
    env = {
        **os.environ,
        "GIT_AUTHOR_DATE": date_str,
        "GIT_COMMITTER_DATE": date_str,
    }
    subprocess.run(["git", "add", "."], cwd=d, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", msg, "--allow-empty"],
        cwd=d, capture_output=True, env=env,
    )


# =========================================================================
# apiserver — AVS (architecture_violation) repo
# =========================================================================


def create_apiserver(d: Path) -> dict[str, list[str]]:
    """Create API server repo with layering violations.

    Structure:
      api/       (layer 0)  - presentation
      services/  (layer 1)  - business logic
      db/        (layer 2)  - data access
      utils/     (omnilayer) - crosscutting

    Violation: db/user_repo.py imports from api/serializers.py (layer 2 -> 0).
    """
    src = d / "src" / "apiserver"
    for p in [
        src / "api", src / "services", src / "db",
        src / "utils", d / "tests",
    ]:
        p.mkdir(parents=True, exist_ok=True)
        (p / "__init__.py").write_text("")
    (src / "__init__.py").write_text("")

    # Layer 0 — API
    (src / "api" / "serializers.py").write_text(
        '"""API serialization helpers."""\n\n'
        "def serialize_user(user: dict) -> dict:\n"
        '    """Convert internal user dict to API response format."""\n'
        "    return {\n"
        "        'id': user['id'],\n"
        "        'name': user.get('name', ''),\n"
        "        'email': user.get('email', ''),\n"
        "    }\n\n\n"
        "def serialize_error(code: int, msg: str) -> dict:\n"
        '    """Format error response."""\n'
        "    return {'error': {'code': code, 'message': msg}}\n"
    )
    (src / "api" / "routes.py").write_text(
        '"""API route definitions."""\n\n'
        "from src.apiserver.services.user_service import get_user\n"
        "from src.apiserver.api.serializers import serialize_user, serialize_error\n\n\n"
        "def handle_get_user(user_id: int) -> dict:\n"
        "    user = get_user(user_id)\n"
        "    if user is None:\n"
        "        return serialize_error(404, 'Not found')\n"
        "    return serialize_user(user)\n"
    )

    # Layer 1 — Services
    (src / "services" / "user_service.py").write_text(
        '"""User business logic."""\n\n'
        "from src.apiserver.db.user_repo import find_user_by_id\n\n\n"
        "def get_user(user_id: int) -> dict | None:\n"
        '    """Get user by ID."""\n'
        "    return find_user_by_id(user_id)\n\n\n"
        "def create_user(name: str, email: str) -> dict:\n"
        '    """Create a new user."""\n'
        "    return {'id': 1, 'name': name, 'email': email}\n"
    )
    (src / "services" / "order_service.py").write_text(
        '"""Order business logic."""\n\n'
        "from src.apiserver.db.order_repo import find_orders\n\n\n"
        "def get_orders(user_id: int) -> list:\n"
        "    return find_orders(user_id)\n"
    )

    # Layer 2 — DB *with layering violation*
    (src / "db" / "user_repo.py").write_text(
        '"""User repository — data access layer."""\n\n'
        "# VIOLATION: layer 2 importing from layer 0\n"
        "from src.apiserver.api.serializers import serialize_user\n\n"
        "_USERS = [\n"
        "    {'id': 1, 'name': 'Alice', 'email': 'alice@example.com'},\n"
        "    {'id': 2, 'name': 'Bob', 'email': 'bob@example.com'},\n"
        "]\n\n\n"
        "def find_user_by_id(uid: int) -> dict | None:\n"
        "    for u in _USERS:\n"
        "        if u['id'] == uid:\n"
        "            return serialize_user(u)\n"
        "    return None\n"
    )
    (src / "db" / "order_repo.py").write_text(
        '"""Order repository."""\n\n\n'
        "def find_orders(user_id: int) -> list:\n"
        "    return [{'id': 1, 'user_id': user_id, 'total': 99.99}]\n"
    )

    # Omnilayer — utils
    (src / "utils" / "validation.py").write_text(
        '"""Shared validation utilities."""\n\n\n'
        "def validate_email(email: str) -> bool:\n"
        "    return '@' in email and '.' in email.split('@')[1]\n"
    )

    (d / "README.md").write_text(
        "# API Server\n\nBenchmark API server.\n\n"
        "- `src/apiserver/api/` — HTTP routes & serialization\n"
        "- `src/apiserver/services/` — Business logic\n"
        "- `src/apiserver/db/` — Data access\n"
        "- `tests/` — Tests\n"
    )

    return {
        "architecture_violation": [
            "Upward layer import: db/user_repo.py imports from "
            "api/serializers.py (layer 2 -> layer 0)"
        ],
    }


def repair_apiserver_avs_correct(d: Path) -> str:
    """Fix layering violation by removing upward import from DB layer."""
    src = d / "src" / "apiserver"
    (src / "db" / "user_repo.py").write_text(
        '"""User repository — data access layer."""\n\n'
        "_USERS = [\n"
        "    {'id': 1, 'name': 'Alice', 'email': 'alice@example.com'},\n"
        "    {'id': 2, 'name': 'Bob', 'email': 'bob@example.com'},\n"
        "]\n\n\n"
        "def find_user_by_id(uid: int) -> dict | None:\n"
        "    for u in _USERS:\n"
        "        if u['id'] == uid:\n"
        "            return dict(u)\n"
        "    return None\n"
    )
    return "Removed upward import from DB layer — returns raw data"


def repair_apiserver_avs_incorrect(d: Path) -> str:
    """Rename the import but keep the upward dependency."""
    src = d / "src" / "apiserver"
    (src / "db" / "user_repo.py").write_text(
        '"""User repository — data access layer."""\n\n'
        "# Still importing from layer 0 — just aliased\n"
        "from src.apiserver.api.serializers import serialize_user as format_user\n\n"
        "_USERS = [\n"
        "    {'id': 1, 'name': 'Alice', 'email': 'alice@example.com'},\n"
        "    {'id': 2, 'name': 'Bob', 'email': 'bob@example.com'},\n"
        "]\n\n\n"
        "def find_user_by_id(uid: int) -> dict | None:\n"
        "    for u in _USERS:\n"
        "        if u['id'] == uid:\n"
        "            return format_user(u)\n"
        "    return None\n"
    )
    return "Aliased import (serialize_user -> format_user) — violation persists"


# =========================================================================
# churnapp — TVS (temporal_volatility) repo
# =========================================================================


def create_churnapp(d: Path) -> dict[str, list[str]]:
    """Create app with high-churn file to trigger TVS.

    One file (config_loader.py) is modified many times in 30 days.
    Other files have minimal changes, creating a z-score outlier.
    """
    src = d / "src" / "churnapp"
    for p in [src, src / "core", d / "tests"]:
        p.mkdir(parents=True, exist_ok=True)
        (p / "__init__.py").write_text("")

    # Stable files — 1 commit each
    (src / "core" / "engine.py").write_text(
        '"""Core engine — stable module."""\n\n\n'
        "def run_pipeline(data: list) -> list:\n"
        "    return [x * 2 for x in data]\n"
    )
    (src / "core" / "cache.py").write_text(
        '"""Cache layer — stable module."""\n\n'
        "_CACHE: dict = {}\n\n\n"
        "def get(key: str):\n"
        "    return _CACHE.get(key)\n\n\n"
        "def put(key: str, val):\n"
        "    _CACHE[key] = val\n"
    )
    (src / "models.py").write_text(
        '"""Data models — stable module."""\n\n\n'
        "class Record:\n"
        "    def __init__(self, key: str, value: float):\n"
        "        self.key = key\n"
        "        self.value = value\n"
    )
    (d / "tests" / "test_basic.py").write_text(
        "def test_placeholder():\n    assert True\n"
    )

    (d / "README.md").write_text(
        "# ChurnApp\n\nBenchmark app for TVS testing.\n"
    )

    return {
        "temporal_volatility": [
            "High churn: config_loader.py modified 8+ times in 30 days "
            "while other files have 1-2 commits"
        ],
    }


def init_churnapp_history(d: Path) -> None:
    """Create git history with churn pattern for TVS detection.

    Must be called AFTER create_churnapp and _init_git.
    Creates 8 additional commits touching config_loader.py over 20 days.
    Uses real past dates so TVS z-score computation works correctly.
    """
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    src = d / "src" / "churnapp"
    conf = src / "config_loader.py"

    # Generate 8 commits spread over the last 25 days
    base_days_ago = 25
    versions = [
        (
            base_days_ago,
            "Add config_loader v1",
            '"""Configuration loader."""\n\n'
            "def load_config(path: str) -> dict:\n"
            "    with open(path) as f:\n"
            "        return eval(f.read())  # noqa: S307\n",
        ),
        (
            base_days_ago - 2,
            "fix: config_loader add default",
            '"""Configuration loader."""\n\nimport json\n\n'
            "def load_config(path: str = 'config.json') -> dict:\n"
            "    with open(path) as f:\n"
            "        return json.load(f)\n",
        ),
        (
            base_days_ago - 5,
            "fix: config_loader add env override",
            '"""Configuration loader."""\n\nimport json\nimport os\n\n'
            "def load_config(path: str = 'config.json') -> dict:\n"
            "    env_path = os.environ.get('CONFIG_PATH', path)\n"
            "    with open(env_path) as f:\n"
            "        return json.load(f)\n",
        ),
        (
            base_days_ago - 8,
            "fix: config_loader add caching",
            '"""Configuration loader."""\n\nimport json\nimport os\n\n'
            "_CACHED: dict | None = None\n\n\n"
            "def load_config(path: str = 'config.json') -> dict:\n"
            "    global _CACHED  # noqa: PLW0603\n"
            "    if _CACHED is not None:\n        return _CACHED\n"
            "    env_path = os.environ.get('CONFIG_PATH', path)\n"
            "    with open(env_path) as f:\n"
            "        _CACHED = json.load(f)\n"
            "    return _CACHED\n",
        ),
        (
            base_days_ago - 11,
            "fix: config_loader add validation",
            '"""Configuration loader."""\n\nimport json\nimport os\n\n'
            "_CACHED: dict | None = None\n"
            "_REQUIRED = ['database_url', 'secret_key']\n\n\n"
            "def load_config(path: str = 'config.json') -> dict:\n"
            "    global _CACHED  # noqa: PLW0603\n"
            "    if _CACHED is not None:\n        return _CACHED\n"
            "    env_path = os.environ.get('CONFIG_PATH', path)\n"
            "    with open(env_path) as f:\n"
            "        cfg = json.load(f)\n"
            "    for k in _REQUIRED:\n"
            "        if k not in cfg:\n"
            "            raise KeyError(f'Missing required config: {k}')\n"
            "    _CACHED = cfg\n    return _CACHED\n",
        ),
        (
            base_days_ago - 14,
            "fix: config_loader merge env vars",
            '"""Configuration loader."""\n\nimport json\nimport os\n\n'
            "_CACHED: dict | None = None\n"
            "_REQUIRED = ['database_url', 'secret_key']\n\n\n"
            "def load_config(path: str = 'config.json') -> dict:\n"
            "    global _CACHED  # noqa: PLW0603\n"
            "    if _CACHED is not None:\n        return _CACHED\n"
            "    env_path = os.environ.get('CONFIG_PATH', path)\n"
            "    with open(env_path) as f:\n"
            "        cfg = json.load(f)\n"
            "    for k in list(cfg):\n"
            "        env_val = os.environ.get(k.upper())\n"
            "        if env_val is not None:\n            cfg[k] = env_val\n"
            "    for k in _REQUIRED:\n"
            "        if k not in cfg:\n"
            "            raise KeyError(f'Missing required config: {k}')\n"
            "    _CACHED = cfg\n    return _CACHED\n",
        ),
        (
            base_days_ago - 17,
            "fix: config_loader add reload",
            '"""Configuration loader."""\n\nimport json\nimport os\n\n'
            "_CACHED: dict | None = None\n"
            "_REQUIRED = ['database_url', 'secret_key']\n\n\n"
            "def load_config(path: str = 'config.json', *, force: bool = False) -> dict:\n"
            "    global _CACHED  # noqa: PLW0603\n"
            "    if _CACHED is not None and not force:\n        return _CACHED\n"
            "    env_path = os.environ.get('CONFIG_PATH', path)\n"
            "    with open(env_path) as f:\n"
            "        cfg = json.load(f)\n"
            "    for k in list(cfg):\n"
            "        env_val = os.environ.get(k.upper())\n"
            "        if env_val is not None:\n            cfg[k] = env_val\n"
            "    for k in _REQUIRED:\n"
            "        if k not in cfg:\n"
            "            raise KeyError(f'Missing required config: {k}')\n"
            "    _CACHED = cfg\n    return _CACHED\n",
        ),
        (
            base_days_ago - 20,
            "fix: config_loader add logging",
            '"""Configuration loader."""\n\nimport json\nimport logging\nimport os\n\n'
            "logger = logging.getLogger(__name__)\n"
            "_CACHED: dict | None = None\n"
            "_REQUIRED = ['database_url', 'secret_key']\n\n\n"
            "def load_config(path: str = 'config.json', *, force: bool = False) -> dict:\n"
            "    global _CACHED  # noqa: PLW0603\n"
            "    if _CACHED is not None and not force:\n        return _CACHED\n"
            "    env_path = os.environ.get('CONFIG_PATH', path)\n"
            "    logger.info('Loading config from %s', env_path)\n"
            "    with open(env_path) as f:\n"
            "        cfg = json.load(f)\n"
            "    for k in list(cfg):\n"
            "        env_val = os.environ.get(k.upper())\n"
            "        if env_val is not None:\n            cfg[k] = env_val\n"
            "    for k in _REQUIRED:\n"
            "        if k not in cfg:\n"
            "            raise KeyError(f'Missing required config: {k}')\n"
            "    _CACHED = cfg\n"
            "    logger.info('Config loaded: %d keys', len(_CACHED))\n"
            "    return _CACHED\n",
        ),
    ]

    for days_ago, msg, content in versions:
        date_str = (now - timedelta(days=days_ago)).strftime(
            "%Y-%m-%dT%H:%M:%S+00:00"
        )
        conf.write_text(content)
        _commit_dated(d, msg, date_str)


def repair_churnapp_tvs_correct(d: Path) -> str:
    """Delete high-churn config_loader and replace with focused modules."""
    src = d / "src" / "churnapp"

    # Delete the high-churn file entirely
    (src / "config_loader.py").unlink()

    (src / "config.py").write_text(
        '"""Configuration loader — simplified replacement."""\n\n'
        "import json\nimport logging\nimport os\n\n"
        "from src.churnapp.config_schema import validate\n"
        "from src.churnapp.config_env import overlay_env\n\n"
        "logger = logging.getLogger(__name__)\n"
        "_CACHED: dict | None = None\n\n\n"
        "def load_config(path: str = 'config.json', *, force: bool = False) -> dict:\n"
        '    """Load, validate, and cache configuration."""\n'
        "    global _CACHED  # noqa: PLW0603\n"
        "    if _CACHED is not None and not force:\n        return _CACHED\n"
        "    env_path = os.environ.get('CONFIG_PATH', path)\n"
        "    logger.info('Loading config from %s', env_path)\n"
        "    with open(env_path) as f:\n"
        "        cfg = json.load(f)\n"
        "    cfg = overlay_env(cfg)\n"
        "    validate(cfg)\n"
        "    _CACHED = cfg\n"
        "    logger.info('Config loaded: %d keys', len(_CACHED))\n"
        "    return _CACHED\n"
    )
    (src / "config_schema.py").write_text(
        '"""Configuration schema — validation rules."""\n\n'
        "_REQUIRED = ['database_url', 'secret_key']\n\n\n"
        "def validate(cfg: dict) -> None:\n"
        '    """Validate configuration has all required keys."""\n'
        "    for k in _REQUIRED:\n"
        "        if k not in cfg:\n"
        "            raise KeyError(f'Missing required config: {k}')\n"
    )
    (src / "config_env.py").write_text(
        '"""Environment variable overlay for config."""\n\nimport os\n\n\n'
        "def overlay_env(cfg: dict) -> dict:\n"
        '    """Merge environment variables into config dict."""\n'
        "    for k in list(cfg):\n"
        "        env_val = os.environ.get(k.upper())\n"
        "        if env_val is not None:\n"
        "            cfg[k] = env_val\n"
        "    return cfg\n"
    )
    return "Deleted config_loader.py, split into config.py + config_schema + config_env"


def repair_churnapp_tvs_incorrect(d: Path) -> str:
    """Add comments but do not split the high-churn file."""
    src = d / "src" / "churnapp"
    content = (src / "config_loader.py").read_text()
    content = content.replace(
        '"""Configuration loader."""',
        '"""Configuration loader — refactored for clarity.\n\n'
        'This module handles config loading, validation and caching.\n"""',
    )
    (src / "config_loader.py").write_text(content)
    return "Updated docstring only — file remains monolithic high-churn target"


# =========================================================================
# datalib — SMS (system_misalignment) setup + repairs
# =========================================================================


def init_datalib_sms_history(d: Path) -> None:
    """Set up git history so SMS detection works.

    Moves most files to >=30 days ago, keeps native_optimizer.py recent.
    Must be called INSTEAD of _init_git for SMS testing.
    """
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    old_date = (now - timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    new_date = (now - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S+00:00")

    novel_file = d / "src" / "datalib" / "native_optimizer.py"
    novel_content = novel_file.read_text()
    novel_file.unlink()

    # Init + commit base files with old date
    subprocess.run(["git", "init"], cwd=d, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "bench@drift.dev"],
        cwd=d, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Drift Bench"],
        cwd=d, capture_output=True,
    )
    _commit_dated(d, "init: baseline files", old_date)

    # Re-add novel-dep file with recent date
    novel_file.write_text(novel_content)
    _commit_dated(d, "add: native optimizer", new_date)


def repair_datalib_sms_correct(d: Path) -> str:
    """Remove novel third-party deps — align with module conventions."""
    (d / "src" / "datalib" / "native_optimizer.py").write_text(
        '"""Data optimizer using pure-Python approach."""\n\n\n'
        "def optimize_records(records: list) -> list:\n"
        '    """Optimize records using list comprehension."""\n'
        "    return [r for r in records if r is not None]\n"
    )
    return "Replaced numpy/pandas/pyarrow with pure-Python — aligns with module conventions"


def repair_datalib_sms_incorrect(d: Path) -> str:
    """Add justification comments but keep novel deps — SMS should persist."""
    (d / "src" / "datalib" / "native_optimizer.py").write_text(
        '"""Data optimizer using vectorized operations.\n\n'
        "Note: numpy/pandas/pyarrow are required for performance.\n"
        '"""\n'
        "import numpy as np  # required for vectorization\n"
        "import pandas as pd  # required for dataframes\n"
        "import pyarrow as pa  # required for arrow format\n\n\n"
        "def optimize_records(records: list) -> list:\n"
        '    """Vectorized record optimization."""\n'
        "    df = pd.DataFrame(records)\n"
        "    arr = pa.array(df.values.flatten())\n"
        "    return np.where(arr.is_valid, arr.to_pylist(), []).tolist()\n"
    )
    return "Added justification comments (novel deps unchanged — SMS persists)"


# =========================================================================
# Variant repos for n-scaling
# =========================================================================


def create_webapp_v2(d: Path) -> dict[str, list[str]]:
    """Variant webapp with different MDS duplicate + DIA pattern."""
    src = d / "src" / "webapp2"
    for p in [src, src / "handlers", src / "utils", d / "tests"]:
        p.mkdir(parents=True, exist_ok=True)
        (p / "__init__.py").write_text("")

    # MDS: duplicate _format_size in two modules (same pattern as _make_timedelta)
    format_size_body = (
        "def _format_size(value):\n"
        '    """Convert byte count to human-readable size string."""\n'
        "    if value is None or isinstance(value, str):\n"
        "        return value\n"
        "    for unit in ('B', 'KB', 'MB', 'GB'):\n"
        "        if abs(value) < 1024:\n"
        "            return f'{value:.1f} {unit}'\n"
        "        value /= 1024\n"
        "    return f'{value:.1f} TB'\n"
    )
    (src / "handlers" / "uploads.py").write_text(
        '"""Upload handling."""\n\n' + format_size_body + "\n\n"
        "def handle_upload(data: bytes, name: str) -> dict:\n"
        "    return {'name': name, 'size': _format_size(len(data))}\n"
    )
    (src / "utils" / "display.py").write_text(
        '"""Display utilities."""\n\n' + format_size_body + "\n\n"
        "def render_stats(files: list) -> list:\n"
        "    return [{'name': f['name'], 'size': _format_size(f['bytes'])} for f in files]\n"
    )

    # DIA: README mentions nonexistent dirs (≥3 phantom refs for reliable detection)
    (d / "README.md").write_text(
        "# Webapp V2\n\nVariant benchmark web app.\n\n"
        "- `src/webapp2/handlers/` — Request handlers\n"
        "- `src/webapp2/utils/` — Utilities\n"
        "- `src/webapp2/middleware/` — Request middleware\n"
        "- `src/webapp2/plugins/` — Plugin system\n"
        "- `docs/` — Documentation\n"
        "- `tests/` — Tests\n"
    )

    return {
        "mutant_duplicate": [
            "Exact duplicate: _format_size in uploads.py and display.py"
        ],
        "doc_impl_drift": [
            "Phantom dirs: middleware/, plugins/, docs/ referenced in README"
        ],
    }


def repair_webapp_v2_mds_correct(d: Path) -> str:
    """Consolidate _format_size into utils/display.py."""
    src = d / "src" / "webapp2"
    (src / "handlers" / "uploads.py").write_text(
        '"""Upload handling."""\n\n'
        "from src.webapp2.utils.display import _format_size\n\n\n"
        "def handle_upload(data: bytes, name: str) -> dict:\n"
        "    return {'name': name, 'size': _format_size(len(data))}\n"
    )
    return "Consolidated _format_size into utils/display.py"


def repair_webapp_v2_mds_incorrect(d: Path) -> str:
    """Rename duplicate but keep body unchanged."""
    src = d / "src" / "webapp2"
    (src / "handlers" / "uploads.py").write_text(
        '"""Upload handling."""\n\n'
        "def _human_size(value):\n"
        '    """Convert byte count to human-readable size string."""\n'
        "    if value is None or isinstance(value, str):\n"
        "        return value\n"
        "    for unit in ('B', 'KB', 'MB', 'GB'):\n"
        "        if abs(value) < 1024:\n"
        "            return f'{value:.1f} {unit}'\n"
        "        value /= 1024\n"
        "    return f'{value:.1f} TB'\n\n\n"
        "def handle_upload(data: bytes, name: str) -> dict:\n"
        "    return {'name': name, 'size': _human_size(len(data))}\n"
    )
    return "Renamed to _human_size (body identical — MDS persists)"


def repair_webapp_v2_dia_correct(d: Path) -> str:
    """Fix README to only reference existing directories."""
    (d / "README.md").write_text(
        "# Webapp V2\n\nVariant benchmark web app.\n\n"
        "- `src/` — Source code\n"
        "- `tests/` — Tests\n"
    )
    return "Fixed README: removed phantom middleware/ and docs/ refs"


def repair_webapp_v2_dia_incorrect(d: Path) -> str:
    """Remove some phantom refs and add new ones — still phantom."""
    (d / "README.md").write_text(
        "# Webapp V2\n\nVariant benchmark web app.\n\n"
        "- `src/webapp2/handlers/` — Request handlers\n"
        "- `src/webapp2/utils/` — Utilities\n"
        "- `deploy/` — Deployment configs\n"
        "- `scripts/` — Build scripts\n"
        "- `monitoring/` — Monitoring setup\n"
        "- `infra/` — Infrastructure\n"
        "- `tests/` — Tests\n"
    )
    return "Swapped phantom refs (deploy/, scripts/, monitoring/, infra/) — DIA still triggers"


def create_datalib_v2(d: Path) -> dict[str, list[str]]:
    """Variant datalib with different EDS + MDS pattern."""
    src = d / "src" / "datalib2"
    for p in [src, src / "parsers", src / "formatters", d / "tests"]:
        p.mkdir(parents=True, exist_ok=True)
        (p / "__init__.py").write_text("")

    # MDS: duplicate _parse_header in two parser files
    header_body = (
        "def _parse_header(raw: bytes) -> dict:\n"
        '    """Parse binary header into field dict."""\n'
        "    if len(raw) < 8:\n"
        "        raise ValueError('Header too short')\n"
        "    return {\n"
        "        'version': raw[0],\n"
        "        'flags': raw[1],\n"
        "        'length': int.from_bytes(raw[2:6], 'big'),\n"
        "        'checksum': raw[6:8],\n"
        "    }\n"
    )
    (src / "parsers" / "binary.py").write_text(
        '"""Binary format parser."""\n\n' + header_body + "\n\n"
        "def parse_binary(data: bytes) -> list:\n"
        "    hdr = _parse_header(data[:8])\n"
        "    return [hdr]\n"
    )
    (src / "parsers" / "streaming.py").write_text(
        '"""Streaming format parser."""\n\n' + header_body + "\n\n"
        "def parse_stream(chunks: list[bytes]) -> list:\n"
        "    results = []\n"
        "    for c in chunks:\n"
        "        if len(c) >= 8:\n"
        "            results.append(_parse_header(c[:8]))\n"
        "    return results\n"
    )

    # EDS: complex undocumented formatter
    (src / "formatters" / "report.py").write_text(
        '"""Report formatter."""\n\n\n'
        "def format_report(data, cols, groups, sorts, limits, style):\n"
        "    rows = []\n"
        "    for d in data:\n"
        "        row = {}\n"
        "        for c in cols:\n"
        "            val = d.get(c['field'])\n"
        "            if c.get('transform') == 'upper': val = str(val).upper()\n"
        "            elif c.get('transform') == 'lower': val = str(val).lower()\n"
        "            elif c.get('transform') == 'round':\n"
        "                val = round(float(val or 0), c.get('digits', 2))\n"
        "            elif c.get('transform') == 'truncate':\n"
        "                val = str(val)[:c.get('max_len', 50)]\n"
        "            elif c.get('transform') == 'currency':\n"
        "                val = f'${float(val or 0):,.2f}'\n"
        "            row[c['name']] = val\n"
        "        skip = False\n"
        "        for g in groups:\n"
        "            if row.get(g['key']) is None: skip = True\n"
        "        if not skip: rows.append(row)\n"
        "    if sorts:\n"
        "        for s in reversed(sorts):\n"
        "            rev = s.get('desc', False)\n"
        "            rows.sort(key=lambda r: r.get(s['field'], ''), reverse=rev)\n"
        "    if limits:\n"
        "        offset = limits.get('offset', 0)\n"
        "        count = limits.get('count', len(rows))\n"
        "        rows = rows[offset:offset+count]\n"
        "    return rows\n"
    )

    (d / "README.md").write_text(
        "# DataLib V2\n\nVariant data library.\n\n"
        "- `src/datalib2/parsers/` — Data parsers\n"
        "- `src/datalib2/formatters/` — Output formatters\n"
        "- `tests/` — Tests\n"
    )

    return {
        "mutant_duplicate": [
            "Exact duplicate: _parse_header in binary.py and streaming.py"
        ],
        "explainability_deficit": [
            "Unexplained complexity: format_report (CC>=10, 6 params, no docstring)"
        ],
    }


def repair_datalib_v2_mds_correct(d: Path) -> str:
    """Consolidate _parse_header into shared module."""
    src = d / "src" / "datalib2"
    (src / "parsers" / "common.py").write_text(
        '"""Shared parser utilities."""\n\n\n'
        "def parse_header(raw: bytes) -> dict:\n"
        '    """Parse binary header into field dict."""\n'
        "    if len(raw) < 8:\n"
        "        raise ValueError('Header too short')\n"
        "    return {\n"
        "        'version': raw[0],\n"
        "        'flags': raw[1],\n"
        "        'length': int.from_bytes(raw[2:6], 'big'),\n"
        "        'checksum': raw[6:8],\n"
        "    }\n"
    )
    (src / "parsers" / "binary.py").write_text(
        '"""Binary format parser."""\n\n'
        "from src.datalib2.parsers.common import parse_header\n\n\n"
        "def parse_binary(data: bytes) -> list:\n"
        "    hdr = parse_header(data[:8])\n"
        "    return [hdr]\n"
    )
    (src / "parsers" / "streaming.py").write_text(
        '"""Streaming format parser."""\n\n'
        "from src.datalib2.parsers.common import parse_header\n\n\n"
        "def parse_stream(chunks: list[bytes]) -> list:\n"
        "    results = []\n"
        "    for c in chunks:\n"
        "        if len(c) >= 8:\n"
        "            results.append(parse_header(c[:8]))\n"
        "    return results\n"
    )
    return "Extracted _parse_header into parsers/common.py"


def repair_datalib_v2_mds_incorrect(d: Path) -> str:
    """Rename duplicate, body unchanged."""
    src = d / "src" / "datalib2"
    content = (src / "parsers" / "streaming.py").read_text()
    content = content.replace("_parse_header", "_read_header")
    (src / "parsers" / "streaming.py").write_text(content)
    return "Renamed to _read_header (body unchanged — MDS persists)"


def repair_datalib_v2_eds_correct(d: Path) -> str:
    """Split complex format_report into helpers with docs."""
    src = d / "src" / "datalib2"
    (src / "formatters" / "report.py").write_text(
        '"""Report formatter — refactored."""\n\n\n'
        "def _transform(val, spec: dict):\n"
        '    """Apply column transformation."""\n'
        "    t = spec.get('transform')\n"
        "    if t == 'upper': return str(val).upper()\n"
        "    if t == 'lower': return str(val).lower()\n"
        "    if t == 'round': return round(float(val or 0), spec.get('digits', 2))\n"
        "    if t == 'truncate': return str(val)[:spec.get('max_len', 50)]\n"
        "    if t == 'currency': return f'${float(val or 0):,.2f}'\n"
        "    return val\n\n\n"
        "def _build_row(record: dict, cols: list) -> dict:\n"
        '    """Build output row from record using column specs."""\n'
        "    return {c['name']: _transform(record.get(c['field']), c) for c in cols}\n\n\n"
        "def format_report(\n"
        "    data: list, cols: list, groups: list,\n"
        "    sorts: list, limits: dict | None, style: str,\n"
        ") -> list:\n"
        '    """Format data into report rows with sorting and pagination."""\n'
        "    rows = [_build_row(d, cols) for d in data]\n"
        "    if groups:\n"
        "        rows = [r for r in rows\n"
        "                if all(r.get(g['key']) is not None for g in groups)]\n"
        "    if sorts:\n"
        "        for s in reversed(sorts):\n"
        "            rows.sort(key=lambda r: r.get(s['field'], ''),\n"
        "                      reverse=s.get('desc', False))\n"
        "    if limits:\n"
        "        o, c = limits.get('offset', 0), limits.get('count', len(rows))\n"
        "        rows = rows[o:o+c]\n"
        "    return rows\n"
    )
    return "Split format_report into _transform + _build_row helpers with docs"


def repair_datalib_v2_eds_incorrect(d: Path) -> str:
    """Add trivial docstring to complex function — EDS persists."""
    src = d / "src" / "datalib2"
    content = (src / "formatters" / "report.py").read_text()
    content = content.replace(
        "def format_report(data, cols, groups, sorts, limits, style):\n"
        "    rows = []",
        "def format_report(data, cols, groups, sorts, limits, style):\n"
        '    """Generate formatted report."""\n'
        "    rows = []",
    )
    (src / "formatters" / "report.py").write_text(content)
    return "Added trivial docstring (complexity unchanged — EDS persists)"
