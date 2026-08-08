from pathlib import Path

from app.blockchain.consensus_poa import PoAConsensus
from app.blockchain.ledger import Ledger
from app.blockchain.transaction import Transaction


def _make_ledger(tmp_path: Path) -> Ledger:
    consensus = PoAConsensus(["validator-1"])
    ledger = Ledger(consensus=consensus, storage_path=str(tmp_path / "ledger.json"))
    ledger.initialize()
    return ledger


def test_ledger_initializes_with_genesis_block(tmp_path: Path) -> None:
    ledger = _make_ledger(tmp_path)
    assert len(ledger.chain) == 1
    assert ledger.chain[0].index == 0
    assert ledger.chain[0].previous_hash == "0"
    assert ledger.is_chain_valid()


def test_commit_pending_transactions_creates_new_block(tmp_path: Path) -> None:
    ledger = _make_ledger(tmp_path)
    tx = Transaction(
        tx_type="register",
        domain="example.bd",
        payload={"ip": "192.168.1.10"},
        owner_public_key="owner-pub-key",
        signature="signed-payload",
    )
    ledger.add_transaction(tx)
    new_block = ledger.commit_pending_transactions("validator-1")

    assert new_block.index == 1
    assert len(new_block.transactions) == 1
    assert len(ledger.chain) == 2
    assert ledger.is_chain_valid()


def test_chain_validation_detects_tampering(tmp_path: Path) -> None:
    ledger = _make_ledger(tmp_path)
    tx = Transaction(
        tx_type="register",
        domain="tamper.bd",
        payload={"ip": "10.1.1.1"},
        owner_public_key="owner-pub-key",
        signature="signed-payload",
    )
    ledger.add_transaction(tx)
    ledger.commit_pending_transactions("validator-1")

    ledger.chain[1].transactions[0].payload["ip"] = "8.8.8.8"
    assert not ledger.is_chain_valid()


def test_ledger_persistence_loads_existing_chain(tmp_path: Path) -> None:
    storage = tmp_path / "ledger.json"
    consensus = PoAConsensus(["validator-1"])

    first_ledger = Ledger(consensus=consensus, storage_path=str(storage))
    first_ledger.initialize()
    first_ledger.add_transaction(
        Transaction(
            tx_type="register",
            domain="persist.bd",
            payload={"ip": "10.0.0.1"},
            owner_public_key="owner-pub-key",
            signature="signed-payload",
        )
    )
    first_ledger.commit_pending_transactions()

    second_ledger = Ledger(consensus=consensus, storage_path=str(storage))
    second_ledger.initialize()
    assert second_ledger.get_chain_height() == 2
    assert second_ledger.chain[1].transactions[0].domain == "persist.bd"
    assert second_ledger.is_chain_valid()
