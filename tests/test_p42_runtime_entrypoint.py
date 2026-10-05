from pathlib import Path
import importlib.util
import json
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "sara_runtime.py"
SPEC = importlib.util.spec_from_file_location("sara_runtime", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _request():
    return {
        "request_id": "P42-REQ-1",
        "capability": "verify_claim",
        "claim": {
            "id": "C-P42",
            "text": "A bounded runtime claim.",
            "inference_level": "FACT",
        },
        "evidence": [],
        "provenance_ids": ["INPUT-P42"],
        "adapter_revision": "p42",
        "requested_at": "2026-10-05T00:00:00Z",
        "environment": {"test": True},
    }


def test_p42_runtime_executes_through_production_backend_and_preserves_boundary():
    def provider(request):
        assert request["claim"]["id"] == "C-P42"
        return {
            "status": "SUCCEEDED",
            "external_result_id": "P42-RESULT-1",
            "external_result_provenance_ids": ["P42-RESULT-PROV-1"],
            "verification_status": "VERIFIED",
            "findings": ["P42_PROVIDER_VERIFIED"],
        }

    result = MODULE.execute_request(_request(), provider)

    assert result.status == "SUCCEEDED"
    assert result.verification_status == "VERIFIED"
    assert result.external_result_provenance_ids == ("P42-RESULT-PROV-1",)
    assert result.truthfulness_status == "UNASSESSED"


def test_p42_runtime_provider_failure_is_fail_closed():
    def provider(_request):
        return {
            "status": "FAILED",
            "failure": {"code": "P42_PROVIDER_FAILURE"},
        }

    result = MODULE.execute_request(_request(), provider)

    assert result.status == "FAILED"
    assert result.verification_status == "UNVERIFIED"
    assert result.truthfulness_status == "UNASSESSED"


def test_p42_cli_invokes_provider_module(tmp_path):
    provider_module = tmp_path / "p42_provider.py"
    provider_module.write_text(
        "def verify(request):\n"
        "    return {\n"
        "        'status': 'SUCCEEDED',\n"
        "        'external_result_id': 'CLI-1',\n"
        "        'external_result_provenance_ids': ['CLI-PROV-1'],\n"
        "        'verification_status': 'UNVERIFIED',\n"
        "    }\n",
        encoding="utf-8",
    )
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(_request()), encoding="utf-8")

    env = dict(__import__("os").environ)
    env["PYTHONPATH"] = str(tmp_path)

    completed = subprocess.run(
        [
            sys.executable,
            str(MODULE_PATH),
            "--provider",
            "p42_provider:verify",
            "--request",
            str(request_path),
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert completed.returncode == 0
    output = json.loads(completed.stdout)
    assert output["status"] == "SUCCEEDED"
    assert output["verification_status"] == "UNVERIFIED"
    assert output["truthfulness_status"] == "UNASSESSED"
