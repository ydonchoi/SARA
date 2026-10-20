# SARA v2.5 Test Environment

## Supported test environment

- Python: 3.12
- Test dependency: pinned in the repository-root `requirements-test.txt`
- Live model/provider credentials are **not** required for deterministic contract tests.

## Local setup

From the repository root:

```sh
python3.12 -m venv .venv
# macOS/Linux
. .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-test.txt
python -m pytest SARA_v2.5/tests/test_executor.py -q
python -m pytest SARA_v2.5/tests/test_dialogue_runtime.py SARA_v2.5/tests/test_inference_pipeline.py SARA_v2.5/tests/test_inference_trigger.py SARA_v2.5/tests/test_internal_judgment_model.py -q
```

Run the broader contract suite with:

```sh
python -m pytest tests SARA_v2.4/tests SARA_v2.5/tests -q
```

The broad command may expose tests that depend on additional packages or repository-specific setup. If that happens, record the exact missing dependency and add it to `requirements-test.txt` only after confirming it is a test dependency.

## What this environment does and does not prove

- Passing deterministic tests proves only the behaviors covered by those tests and test doubles.
- It does not prove that a live model provider or external claim verifier is configured.
- It does not prove semantic inference-detection accuracy or independent verification quality.
- It does not connect SARA to the current ChatGPT app.
- A GitHub Actions job with no assigned runner and no steps has not executed these tests; it must not be reported as a test pass or code-level test failure.

## Live provider integration

Live integration is a separate setup step. Implement and configure a provider module satisfying the contract in `SARA_v2.5/EXECUTOR.md`; inject credentials through a secret manager or environment configuration, never by committing secrets. Use a non-production test endpoint or controlled test claims first, then record provider/model revisions and verification evidence.
