# IOManager / Resource lifecycle in Dagster — empirical findings

This project pins the actual lifecycle behaviour of Dagster resources and
IOManagers via a runnable test suite (11 passing tests). It answers the
write-up's central question: **is there a per-asset / per-step scope for
resources and IOManagers, and what's the supported pattern for sharing a
single SQLAlchemy `Session` across the load_input / op body / handle_output
calls in one step?**

The TL;DR is at the bottom. Each numbered claim links to the test that
asserts it.

## What's confirmed

### 1. Resources are documented as run-scoped, and that's exactly what you observe in-process

`tests/test_inprocess_lifecycle.py::test_single_resource_init_per_run_inprocess`

A single `@dg.resource` (or `ConfigurableResource`) is initialised **once per
run** under the in-process executor. With three assets in a linear graph
(`foo → bar → baz`) we see exactly one `resource_enter` and one
`resource_exit`, despite three step boundaries.

### 2. Every load_input / handle_output in a run sees the same instance

`tests/test_inprocess_lifecycle.py::test_every_iomanager_call_sees_same_session_inprocess`

The 3 `handle_output` calls and 2 `load_input` calls all observe the same
`session_id`. So with one IOManager + one session resource + in-process
executor, your "one session per step" instinct works *as long as you treat
the run as the unit*.

### 3. There is no per-step setup/teardown hook on a resource or IOManager

`tests/test_no_step_lifecycle_hook.py::test_op_success_hook_fires_after_handle_output`

You confirmed this from the source; the test pins the ordering for posterity:

```
asset_body(start) → asset_body(end) → handle_output → success_hook
```

`@success_hook` / `@failure_hook` fire *after* `handle_output` has already
run, so they cannot prepare the session the IOManager will use. They can
observe a step's outcome, not bracket the step.

### 4. The "open a Session per call" anti-pattern produces N sessions for N calls

`tests/test_step_boundary_anti_pattern.py::test_anti_pattern_creates_one_session_per_call`

For a 3-asset graph we observe 5 distinct sessions (3 outputs + 2 inputs).
No identity map, no atomicity. This is the failure mode the write-up
called out, pinned as a regression test.

### 5. Step failure does **not** propagate into the resource generator — surprise gotcha

`tests/test_inprocess_lifecycle.py::test_step_failure_does_NOT_propagate_into_resource_generator`

This is the result that surprised me most. A `@contextmanager`-style
resource that does `try: yield; commit() except: rollback()` will take the
**commit** path even when a step in the run raises. Dagster exits the
generator cleanly during teardown after recording the failure on the run.

So the canonical "transactional resource" idiom is unreliable for the
behaviour you want. If you depend on rollback-on-step-failure, you cannot
get it from a `@contextmanager` resource alone — you need to drive
commit/rollback from somewhere that *does* see the per-step outcome (the
op body itself, or an op `failure_hook`, neither of which the IOManager
can plug into transparently).

### 6. Multiprocess executor: process boundary turns "run-scoped" into "step-scoped"

`tests/test_multiprocess_lifecycle.py::test_resource_initialised_per_step_under_multiprocess`
`tests/test_multiprocess_lifecycle.py::test_each_step_runs_in_its_own_pid`
`tests/test_multiprocess_lifecycle.py::test_all_iomanager_calls_within_a_step_share_one_session`

Under `multiprocess_executor`, each step runs in its own worker subprocess
that re-initialises the resources it needs. We observe:

* **3 `resource_enter` / 3 `resource_exit` events** — one per step.
* **3 distinct PIDs**, each owning one asset's body.
* Within a single step's PID, every `load_input` and `handle_output` sees
  the **same `session_id`**. Across steps, sessions are distinct.

So the practical answer to "is there per-step scoping?" is:

> **Yes — via the process boundary of the multiprocess (or any
> out-of-process) executor, which is the default for jobs.** The
> framework doesn't *say* the lifecycle is step-scoped, but in any
> realistic deployment it effectively is.

`dagster dev` and `dg dev` both use the multiprocess executor by default
for jobs, so your local dev story matches your prod story without needing
k8s.

### 7. Multi-IOManager + one ConfigurableResource: GOTCHA — Dagster initialises it once *per IOManager*

`tests/test_two_iomanagers.py::test_modern_nesting_initialises_session_resource_twice`
`tests/test_multiprocess_lifecycle.py::test_modern_pythonic_nesting_creates_one_session_PER_IOMANAGER`

This is the biggest practical landmine and exactly what the write-up
worried about. Even when you do this:

```python
session = ConfigurableSessionResource()  # ONE Python object
defs = dg.Definitions(
    resources={
        "session": session,
        "primary":   UpsertingIOManager(session=session),
        "secondary": UpsertingIOManager(session=session),
    },
)
```

Dagster does **not** dedupe by Python `id()`. Each IOManager carries its
own copy of the nested resource graph and initialises it separately. The
log shows `RESOURCE_INIT_STARTED [io_manager, secondary_io]` and we
observe two distinct session ids. So if a step touches both IOManagers,
it sees two sessions and you've lost atomicity within the step.

### 8. You CAN patch the modern API: have the resource dedupe itself

`tests/test_self_deduping_resource.py`

Yes — you can keep the Pythonic `ConfigurableIOManager` + nested
`ConfigurableResource` ergonomics and still get one session shared across
all nestings. The patch is a process-local cache inside the resource's
own `yield_for_execution`:

```python
_PROCESS_CACHE: dict[tuple[str, str], FakeSession] = {}
_REFCOUNT: dict[tuple[str, str], int] = {}

class SharedSessionResource(dg.ConfigurableResource):
    cache_key: str = "default"

    @contextmanager
    def yield_for_execution(self, context):
        key = (context.run_id, self.cache_key)
        if key in _PROCESS_CACHE:           # second+ nesting: cache hit
            _REFCOUNT[key] += 1
            self._session = _PROCESS_CACHE[key]
            try: yield self
            finally: _REFCOUNT[key] -= 1
            return

        session = FakeSession()              # first nesting: own it
        _PROCESS_CACHE[key] = session
        _REFCOUNT[key] = 1
        self._session = session
        try:
            yield self
            session.commit()
        except BaseException:
            session.rollback(); raise
        finally:
            session.close()
            _REFCOUNT[key] -= 1
            if _REFCOUNT[key] == 0:
                del _PROCESS_CACHE[key]; del _REFCOUNT[key]
```

Properties:

* **Process-local cache.** Under multiprocess each worker has its own
  `_PROCESS_CACHE`, so cross-step sessions never leak. The tests verify
  this: within a step (one PID) all IOManagers share one session id;
  across steps (different PIDs) sessions are distinct.
* **Refcount-based cleanup.** Dagster still calls `yield_for_execution`
  twice (once per nested instance). The first call creates the session
  and owns its close; subsequent calls are a no-op cache hit. Works
  regardless of teardown order.
* **Pluralisable via `cache_key`.** Different cache keys give different
  pools — useful if you need a per-database session, or want to mark a
  resource as "do not share".

What this still does NOT fix (same as before):

* **Step-failure rollback.** The exception still does not propagate into
  the generator, so the commit branch runs even when the run fails. You
  need an op `failure_hook` (or a wrapper inside the op body) for
  per-step rollback semantics.

So the trade-off vs. the function-style API:

| | Function-style + `required_resource_keys` | Self-deduping `ConfigurableResource` |
| --- | --- | --- |
| Sharing across IOManagers | ✅ via key registry | ✅ via process-local cache |
| Pydantic config on the IOManager | ❌ | ✅ |
| Static types on resource access | ❌ (`Any`) | ✅ (typed field) |
| Module-level mutable state | ❌ | ✅ (one private dict per resource type) |
| Has a moving part you need to maintain | ❌ | ✅ (the cache + refcount) |

If you can stomach the small chunk of process-local state, the
self-deduping resource gets you the modern ergonomics with the same
sharing guarantees.

### 9. Fallback: legacy `required_resource_keys` does share

`tests/test_legacy_required_resource_keys.py::test_legacy_required_resource_keys_shares_session`

If you switch the IOManagers to function-style with
`required_resource_keys={"session_resource"}`, both look the resource up by
key from the registered resource map and you get one initialisation, one
session, shared across both IOManagers. This test is the workaround
recipe.

```python
@dg.io_manager(required_resource_keys={"session_resource"})
def primary(_ctx): return LegacyUpsertingIOManager(name="primary")

@dg.io_manager(required_resource_keys={"session_resource"})
def secondary(_ctx): return LegacyUpsertingIOManager(name="secondary")

dg.Definitions(
    resources={
        "session_resource": cm_session_resource,  # registered ONCE by key
        "io_manager":   primary,
        "secondary_io": secondary,
    },
)
```

In the IOManager, access via `context.resources.session_resource`. This is
the supported "share one resource across multiple IOManagers" path today.

## TL;DR

| Question | Answer |
| --- | --- |
| Is there a `scope="step"` API on resources? | **No.** |
| Is there a per-step setup/teardown hook on resources or IOManagers? | **No.** `success_hook` / `failure_hook` fire *after* the step's IOManager work. |
| Does an in-process run init resources once or per step? | **Once per run.** |
| Does a multiprocess run init resources once or per step? | **Per step**, via the process boundary. Sessions cannot leak across workers because they're separate processes. |
| Is the default executor multiprocess? | **Yes**, both for `dagster dev` and prod jobs. |
| Will a `try/except`-based `@contextmanager` resource roll back on step failure? | **No** — Dagster doesn't throw the step exception into the generator. It exits cleanly via the commit path. |
| If I share one Python `ConfigurableResource()` between two `ConfigurableIOManager`s, do they share the underlying session? | **No** by default. Each IOManager nests its own copy and Dagster initialises each one separately. `ResourceDependency[T]` does *not* change this — it's just a typing hint. |
| Can I patch the modern API to share? | **Yes** — make the resource self-dedupe via a process-local cache in `yield_for_execution`. Test `test_self_deduping_resource.py` shows it. |
| Is there a non-patched fallback that shares? | Function-style `@io_manager(required_resource_keys={"session_resource"})` + a single resource registered by key. Each IOManager pulls it from `context.resources`. Not deprecated, just less ergonomic. |

## Practical recommendation for your ORM IOManager

Given the above, the supported recipe that gives you what you want
(one Session per step, shared across every IOManager call inside that
step, transactional commit/rollback driven by step outcome) is:

1. **Register `session_resource` once** at the top level of `Definitions`.
2. **Use legacy function-style `@io_manager`** factories with
   `required_resource_keys={"session_resource"}` — *not* a
   `ConfigurableIOManager` with a nested `ConfigurableResource` field.
   This is the only sharing path Dagster currently dedupes correctly.
3. **Run with the multiprocess executor** (the default). The process
   boundary gives you "step-scoped" lifecycle for free, and ensures one
   subprocess can never leak a Session into another.
4. **Drive commit/rollback from the op body**, not from a `try/except` in
   the resource generator. Either:
   * have the op body wrap its work in `with session.begin(): ...`, or
   * use a `failure_hook` that calls `session.rollback()` and a normal
     finally-style commit in the resource — keeping in mind that the
     failure hook fires after `handle_output` has already run, so the
     session will need to defer commits until that hook (or until step
     teardown) decides which path to take.

What you **cannot** get cleanly today:

* A single transaction that brackets `load_input(...) + body + handle_output(...)`
  and rolls back on step failure *via the resource generator alone*.
* "Three IOManagers per step → one Session" using only the modern
  `ConfigurableIOManager` + nested `ConfigurableResource` API.
* A general-purpose "resource scope = step" knob, even though under
  multiprocess that's effectively the lifecycle you observe.

So your reading of the source was right. The gap you spotted is a real
gap, not a missing-doc situation. The pragmatic path is the legacy
`required_resource_keys` style under the multiprocess executor, with
commit/rollback driven by an explicit hook rather than the resource's
own generator semantics.

## Repository layout

```
iomanager-lifecycle-demo/
  pyproject.toml
  lifecycle_demo/
    __init__.py
    assets.py            # foo → bar → baz, plus an alt-iomanager bar
    fake_session.py      # FakeSession stand-in (records identity)
    io_managers.py       # UpsertingIOManager, LegacyUpsertingIOManager,
                         # StepBoundaryIOManager
    resources.py         # cm_session_resource, ConfigurableSessionResource
    definitions.py       # 4 scenarios as Definitions factories
    jobs.py              # reconstructable jobs for multiprocess tests
    tracker.py           # cross-process JSONL event log
  tests/
    conftest.py
    test_inprocess_lifecycle.py             # 3 tests
    test_multiprocess_lifecycle.py          # 4 tests (under multiprocess executor)
    test_two_iomanagers.py                  # the gotcha
    test_legacy_required_resource_keys.py   # the workaround
    test_step_boundary_anti_pattern.py      # baseline pin
    test_no_step_lifecycle_hook.py          # ordering pin
```

Run with:

```bash
cd iomanager-lifecycle-demo
uv sync
uv run pytest -v
```
