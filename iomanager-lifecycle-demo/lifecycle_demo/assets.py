"""Three-step linear asset graph: foo -> bar -> baz.

Each asset records its own start/end with the pid, so tests can correlate
"which step" produced an event without parsing dagster's internal context.
"""

from __future__ import annotations

import dagster as dg

from .tracker import record


@dg.asset
def foo() -> str:
    record("asset_body", asset="foo", phase="start")
    out = "foo-value"
    record("asset_body", asset="foo", phase="end")
    return out


@dg.asset
def bar(foo: str) -> str:
    record("asset_body", asset="bar", phase="start", foo_arg=foo)
    out = "bar-value"
    record("asset_body", asset="bar", phase="end")
    return out


@dg.asset(name="bar", io_manager_key="secondary_io")
def bar_via_secondary(foo: str) -> str:
    record("asset_body", asset="bar", phase="start", foo_arg=foo)
    out = "bar-value"
    record("asset_body", asset="bar", phase="end")
    return out


@dg.asset
def baz(bar: str) -> str:
    record("asset_body", asset="baz", phase="start", bar_arg=bar)
    out = "baz-value"
    record("asset_body", asset="baz", phase="end")
    return out


ALL_ASSETS = [foo, bar, baz]
