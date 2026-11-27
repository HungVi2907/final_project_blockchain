"""Deploy the registry to a local Anvil node and write a deployment manifest."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from credit_audit.chain import DEFAULT_RPC, compile_registry, connect_anvil, deploy

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts/role_c_mvp/deployment.json"


def deploy_local(w3, output):
    compiled = compile_registry(ROOT / "contracts/DecisionRegistry.vy")
    registry = deploy(w3, compiled, w3.eth.accounts[0])
    manifest = {
        "chain_id": w3.eth.chain_id,
        "contract_address": registry.address,
        "min_confirmations": 1,
        "compiler": "vyper 0.4.3",
        "creation_bytecode_sha256": sha256(bytes.fromhex(compiled["bytecode"][2:])).hexdigest(),
        "runtime_bytecode_sha256": sha256(w3.eth.get_code(registry.address)).hexdigest(),
        "abi": compiled["abi"],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return registry


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rpc", default=DEFAULT_RPC)
    parser.add_argument("--output", type=Path, default=MANIFEST)
    options = parser.parse_args()
    contract = deploy_local(connect_anvil(options.rpc), options.output)
    print(f"Anvil registry {contract.address} → {options.output}")
