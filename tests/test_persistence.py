"""PERSISTENCE TESTS: axiom tracker JSONL round-trip, schema stability, and
replay API endpoints reading written data via the Flask test client."""
import os
import json
import uuid
import shutil

import pytest
from flask import Flask

from backend.app.services.axiom_tracker import AxiomTracker
from backend.app.api.replay import replay_bp

SAMPLE_RECORDS = [
    {"simulation_id": "t", "generation": 1,
     "axioms_before": ["survive"], "axioms_after": ["survive", "hoard"]},
    {"simulation_id": "t", "generation": 2,
     "axioms_before": ["survive", "hoard"], "axioms_after": ["hoard"]},
]


@pytest.fixture()
def tracker():
    sim_id = f"test_{uuid.uuid4().hex[:10]}"
    tr = AxiomTracker(sim_id)
    yield tr
    shutil.rmtree(tr.sim_dir, ignore_errors=True)


# ---- AxiomTracker JSONL round-trip ----

def test_jsonl_write_read_round_trip(tracker):
    for rec in SAMPLE_RECORDS:
        tracker.log_compression(rec)
    read = AxiomTracker.read_axioms(tracker.simulation_id)
    assert read == SAMPLE_RECORDS


def test_empty_record_is_ignored(tracker):
    tracker.log_compression({})
    assert AxiomTracker.read_axioms(tracker.simulation_id) == []


def test_read_missing_file_returns_empty_list():
    assert AxiomTracker.read_axioms("no_such_sim_xyz_42") == []


def test_jsonl_schema_stability(tracker):
    """Every line must parse and carry a stable top-level key set."""
    for rec in SAMPLE_RECORDS:
        tracker.log_compression(rec)
    with open(tracker.log_file, encoding='utf-8') as f:
        lines = [json.loads(l) for l in f if l.strip()]
    expected = set(SAMPLE_RECORDS[0].keys())
    for rec in lines:
        assert set(rec.keys()) == expected


def test_multiple_writes_append_not_overwrite(tracker):
    tracker.log_compression(SAMPLE_RECORDS[0])
    tracker.log_compression(SAMPLE_RECORDS[1])
    assert len(AxiomTracker.read_axioms(tracker.simulation_id)) == 2


# ---- Replay API (Flask test client) ----

@pytest.fixture()
def app(tmp_path):
    app = Flask(__name__)
    app.config['OASIS_SIMULATION_DATA_DIR'] = str(tmp_path)
    app.register_blueprint(replay_bp)
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


def _write_run(root, run_id, entries):
    d = root / run_id
    d.mkdir(parents=True)
    p = d / "synthetica_actions.jsonl"
    with open(p, 'w', encoding='utf-8') as f:
        for e in entries:
            f.write(json.dumps(e) + '\n')
    return str(p)


def test_replay_list_reads_written_data(app, client, tmp_path):
    entry = {"run_id": "run1", "turn": 1, "agent": "A-1", "action": "GATHER_LOCAL"}
    _write_run(tmp_path, "run1", [entry])
    resp = client.get('/list')
    assert resp.status_code == 200
    runs = resp.get_json()["runs"]
    assert any("run1" in r for r in runs)


def test_replay_load_returns_trajectory(client, tmp_path):
    entries = [{"run_id": "run2", "turn": g} for g in range(3)]
    path = _write_run(tmp_path, "run2", entries)
    rel = os.path.join("run2", "synthetica_actions.jsonl")
    resp = client.get(f'/load/{rel}')
    assert resp.status_code == 200
    assert resp.get_json()["trajectory"] == entries


def test_replay_list_empty_when_dir_missing(app, client, tmp_path):
    app.config['OASIS_SIMULATION_DATA_DIR'] = str(tmp_path / "nope")
    assert client.get('/list').get_json() == {"runs": []}


def test_replay_load_rejects_path_traversal(client):
    resp = client.get('/load/../../secrets.jsonl')
    assert resp.status_code == 400


def test_replay_load_missing_file_404(client, tmp_path):
    resp = client.get('/load/run_x/missing.jsonl')
    assert resp.status_code == 404
