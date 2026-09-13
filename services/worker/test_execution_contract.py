from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from all12_executor import _artifact_is_valid

def test_empty_artifact_is_not_verifiable(tmp_path):
    empty = tmp_path / "empty.json"
    empty.write_text("")
    assert _artifact_is_valid(empty) is False

def test_nonempty_artifact_is_verifiable(tmp_path):
    output = tmp_path / "result.json"
    output.write_text("{\"executed\": true}")
    assert _artifact_is_valid(output) is True

def test_nonempty_directory_is_verifiable(tmp_path):
    folder = tmp_path / "artifact"
    folder.mkdir()
    (folder / "output.bin").write_bytes(b"real output")
    assert _artifact_is_valid(folder) is True
