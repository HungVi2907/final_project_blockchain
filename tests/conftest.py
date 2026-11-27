from contextlib import closing
import os
from pathlib import Path
import shutil
import socket
import subprocess
from time import monotonic, sleep

import pytest
from web3 import Web3

from credit_audit.chain import compile_registry, deploy


@pytest.fixture(scope="session")
def anvil():
    binary = os.environ.get("ANVIL_BIN") or shutil.which("anvil")
    if not binary:
        pytest.skip("Install Anvil or set ANVIL_BIN to run local chain tests")
    with closing(socket.socket()) as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    process = subprocess.Popen(
        [binary, "--host", "127.0.0.1", "--port", str(port), "--chain-id", "31337", "--silent"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        url = f"http://127.0.0.1:{port}"
        w3 = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": 1}))
        deadline = monotonic() + 10
        while not w3.is_connected():
            if monotonic() >= deadline or process.poll() is not None:
                pytest.fail("Anvil failed to start")
            sleep(0.05)
        yield w3, url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


@pytest.fixture(scope="session")
def compiled_registry():
    path = Path(__file__).resolve().parents[1] / "contracts/DecisionRegistry.vy"
    return compile_registry(path)


@pytest.fixture
def registry(anvil, compiled_registry):
    w3, _ = anvil
    return deploy(w3, compiled_registry, w3.eth.accounts[0])
