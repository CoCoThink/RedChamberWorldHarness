from pathlib import Path

import pytest

from rcwh.candidate_reviews import digest
from rcwh.delivery import BundleDelivery

ROOT = Path(__file__).resolve().parents[1]


def test_removed_copy_bindings_reconstruct_exact_original_bytes(tmp_path):
    service = BundleDelivery(ROOT)
    summary = service.summary()
    assert summary["removed_duplicate_bytes"] == 32551643
    for bundle in service.config["bundles"]:
        destination = tmp_path/bundle["id"]
        result = service.materialize(bundle["id"], destination)
        assert result["status"] == "PASS"
        for row in service.config["removed_copies"]:
            if row["bundle"] == bundle["id"] and row["member"]:
                assert digest((destination/row["member"]).read_bytes()) == row["sha256"]
        with pytest.raises(ValueError, match="new"): service.materialize(bundle["id"], destination)


def test_prepared_attachments_keep_registered_bytes_and_do_not_publish(tmp_path):
    service = BundleDelivery(ROOT)
    result = service.attachments(tmp_path/"attachments")
    assert result["publication"] == "NOT_PUBLISHED"
    for row in result["files"]:
        assert digest((tmp_path/"attachments"/row["filename"]).read_bytes()) == row["sha256"]
