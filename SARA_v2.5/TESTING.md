# SARA v2.5 Test Environment

## Supported test environment

- Python: 3.12
- Test dependency: pinned in the repository-root `requirements-test.txt`.
- Live model/provider credentials are not required for deterministic contract tests.

## Local setup

From the repository root:

```sh
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: . .venv/bin/activate
python -m pip install -r requirements-test.txt
python -m pytest SARA_v2.5/tests/test_executor.py SARA_v2.5/tests/test_executor_nested_status.py -q
python -m pytest SARA_v2.5/tests/test_dialogue_runtime.py SARA_v2.5/tests/test_inference_pipeline.py SARA_v2.5/tests/test_inference_trigger.py SARA_v2.5/tests/test_internal_judgment_model.py -q
```

Run all contract tests with:

```sh
python -m pytest tests SARA_v2.3/07_SYSTEM/test_sara_callable.py SARA_v2.4/tests SARA_v2.5/tests -q
```

## Validation boundary

Passing deterministic tests covers only the behavior asserted by those tests
and their test doubles. It does not establish live provider configuration,
semantic judgment accuracy, independent verification quality, or integration
with the current ChatGPT application. A CI job with no runner steps has not
executed the tests and is neither a test pass nor a code-level test failure.

Configure live provider credentials through deployment secrets, never in the
repository. Record the provider and model revisions when conducting a live
integration evaluation.
