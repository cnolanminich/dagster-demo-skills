"""Auto code_version utilities for Dagster assets.

Provides helpers that derive `code_version` strings by hashing asset function
source code at import time. This gives ZenML-style automatic cache
invalidation when code changes, without requiring manual version bumps.

CAVEATS — read before using:
  - Only hashes the decorated function body (via inspect.getsource).
  - Does NOT detect changes in imported helpers, utility modules, or
    third-party package upgrades.
  - Cosmetic changes (whitespace, comments, docstrings) WILL change the hash
    and trigger unnecessary re-materialization.
  - If the function is defined dynamically (e.g. inside a factory), the hash
    may be unstable across interpreter restarts.
  - For production ML pipelines, consider `auto_code_version_deep` which
    also hashes explicitly declared dependencies.

See dagster-io/dagster#15242 for why Dagster chose not to build this in.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import textwrap
from typing import Callable, Sequence


# ---------------------------------------------------------------------------
# Strategy 1: Shallow hash (function body only)
# ---------------------------------------------------------------------------

def auto_code_version(fn: Callable) -> str:
    """Hash the source code of *fn* and return a short hex digest.

    This is the simplest approach — equivalent to what ZenML does for step
    source code — but limited to the single function body.

    Caveats:
      * Whitespace and comment changes produce a new hash (false positive).
      * Changes to called helpers are invisible (false negative).

    Example::

        def _train_impl(features):
            ...

        @dg.asset(code_version=auto_code_version(_train_impl))
        def trained_model(features):
            return _train_impl(features)
    """
    source = inspect.getsource(fn)
    return hashlib.md5(source.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Strategy 2: Normalized hash (strips comments & whitespace)
# ---------------------------------------------------------------------------

def auto_code_version_normalized(fn: Callable) -> str:
    """Hash a normalized AST of *fn*, ignoring whitespace and comments.

    Parses the function source into an AST, strips docstrings, then dumps
    the tree back to a canonical string. This avoids false positives from
    formatting-only changes while still catching logic changes.

    Caveats:
      * Still only covers the single function body.
      * Changes to called helpers are invisible (false negative).
      * Renaming local variables WILL change the hash (correct behavior).

    Example::

        @dg.asset(code_version=auto_code_version_normalized(my_func))
        def my_asset(): ...
    """
    source = textwrap.dedent(inspect.getsource(fn))
    tree = ast.parse(source)

    # Strip docstrings from function defs
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, (ast.Constant, ast.Str))
            ):
                node.body.pop(0)

    canonical = ast.dump(tree)
    return hashlib.md5(canonical.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Strategy 3: Deep hash (function + explicit deps)
# ---------------------------------------------------------------------------

def auto_code_version_deep(
    fn: Callable,
    deps: Sequence[Callable] = (),
    extra: str = "",
) -> str:
    """Hash *fn* plus every callable in *deps* and an optional *extra* salt.

    This is the closest analog to ZenML's full cache key, which hashes step
    source + input artifact IDs + parameters. Here you explicitly list the
    helper functions and can add a salt for package versions, config, etc.

    Args:
        fn: The primary asset function.
        deps: Additional callables whose source should be included in the
            hash (imported helpers, transformers, model classes, etc.).
        extra: Arbitrary string folded into the hash — use for package
            versions, config hashes, or feature-flag state.

    Caveats:
      * You must manually list deps — nothing is auto-discovered.
      * C-extension functions (e.g. numpy ufuncs) have no inspectable source
        and will raise TypeError; pass their __version__ in *extra* instead.

    Example::

        from mylib import preprocess, build_features
        import sklearn

        @dg.asset(
            code_version=auto_code_version_deep(
                _train_impl,
                deps=[preprocess, build_features],
                extra=sklearn.__version__,
            )
        )
        def trained_model(features):
            return _train_impl(features)
    """
    h = hashlib.md5()
    h.update(inspect.getsource(fn).encode("utf-8"))

    for dep in deps:
        try:
            h.update(inspect.getsource(dep).encode("utf-8"))
        except (TypeError, OSError):
            # Built-in or C-extension — include repr as best-effort fallback
            h.update(repr(dep).encode("utf-8"))

    if extra:
        h.update(extra.encode("utf-8"))

    return h.hexdigest()[:12]
