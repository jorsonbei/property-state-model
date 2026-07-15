from __future__ import annotations

import json
import os
import secrets
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
PROTOCOL_PATH = PSM_ROOT / "benchmarks" / "v0_262_invite_only_external_trial_protocol.json"
CONTRACT_PATH = PSM_ROOT / "benchmarks" / "v0_263_three_participant_enrollment_contract.json"
PRIVATE_STATE_PATH = PSM_ROOT / "private_runtime" / "v0_263" / "enrollment_state.json"
CHECKPOINT_PATH = PSM_ROOT / "runtime" / "v0_263_participant_enrollment_checkpoint.json"
KEYCHAIN_SERVICE = "com.property-state-model.v0-263-invite-binding"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_or_create_binding_secret() -> bytes:
    supplied = os.environ.get("PSM_V0_263_BINDING_SECRET", "").strip()
    if supplied:
        secret = _decode_secret(supplied)
        if len(secret) < 32:
            raise SystemExit("PSM_V0_263_BINDING_SECRET must contain at least 32 bytes.")
        return secret

    account = os.environ.get("USER", "psm-local-operator")
    lookup = subprocess.run(
        ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", account, "-w"],
        capture_output=True,
        text=True,
        check=False,
    )
    if lookup.returncode == 0 and lookup.stdout.strip():
        return _decode_secret(lookup.stdout.strip())

    encoded = secrets.token_hex(32)
    stored = subprocess.run(
        [
            "security",
            "add-generic-password",
            "-U",
            "-s",
            KEYCHAIN_SERVICE,
            "-a",
            account,
            "-w",
            encoded,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if stored.returncode != 0:
        raise SystemExit(stored.stderr.strip() or "Unable to store V0.263 binding secret in Keychain.")
    return bytes.fromhex(encoded)


def _decode_secret(value: str) -> bytes:
    try:
        return bytes.fromhex(value)
    except ValueError:
        return value.encode("utf-8")


def validate_contract(contract: dict, protocol: dict) -> None:
    from psm_v0.external_trial_protocol import canonical_sha256

    if contract.get("schema_version") != "psm_v0_263_three_participant_enrollment_contract_v1":
        raise SystemExit("V0.263 enrollment contract schema is invalid.")
    authorization = contract.get("authorization") or {}
    if (
        authorization.get("participant_count_selected_by_user") is not True
        or authorization.get("selection_text") != "3人"
        or authorization.get("selected_participant_count") != 3
        or authorization.get("does_not_assert_adulthood_presence_or_consent") is not True
    ):
        raise SystemExit("V0.263 three-participant authorization is incomplete.")
    if (contract.get("parent_protocol") or {}).get("sha256") != canonical_sha256(protocol):
        raise SystemExit("V0.263 contract references a different V0.262 protocol.")
    if (contract.get("cohort") or {}).get("direct_identity_collection_allowed") is not False:
        raise SystemExit("V0.263 contract permits direct identity collection.")
    boundary = contract.get("release_boundary") or {}
    still_closed = (
        "adult_verification_completed",
        "notice_acknowledgment_completed",
        "explicit_consent_completed",
        "supervised_trial_active",
        "public_service_allowed",
        "privacy_compliance_claimed",
        "training_on_trial_data_allowed",
        "rule_replacement_allowed",
        "external_release_authority",
    )
    if any(boundary.get(name) is not False for name in still_closed):
        raise SystemExit("V0.263 pre-enrollment contract opens an unearned authority.")


def main() -> None:
    from psm_v0.external_trial_protocol import load_protocol, validate_protocol
    from psm_v0.participant_enrollment import (
        build_enrollment_checkpoint,
        initialize_enrollment,
        load_private_state,
        write_public_checkpoint,
        write_private_state,
    )

    protocol = load_protocol(PROTOCOL_PATH)
    protocol_errors = validate_protocol(protocol)
    if protocol_errors:
        raise SystemExit("Frozen V0.262 protocol is invalid: " + "; ".join(protocol_errors))
    contract = read_json(CONTRACT_PATH)
    validate_contract(contract, protocol)

    if PRIVATE_STATE_PATH.exists():
        state = load_private_state(PRIVATE_STATE_PATH, protocol)
        if state.get("participant_count") != 3:
            raise SystemExit("Existing private enrollment state has a different participant count.")
        created = False
    else:
        state = initialize_enrollment(
            participant_count=3,
            protocol=protocol,
            binding_secret=load_or_create_binding_secret(),
        )
        write_private_state(PRIVATE_STATE_PATH, state, protocol)
        created = True

    checkpoint = build_enrollment_checkpoint(state)
    write_public_checkpoint(CHECKPOINT_PATH, state)
    print(f"private_state_created: {created}")
    print("participant_count: 3")
    print("pseudonymous_ids: P01,P02,P03")
    print("invitation_codes_printed: false")
    print(f"trial_active: {str(checkpoint['trial_active']).lower()}")
    print(f"checkpoint: {CHECKPOINT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
