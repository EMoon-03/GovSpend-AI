"""Checks for pagination, record caps and request building — no network needed."""

import json

import pytest

from govspend import collect as c


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


class FakeSession:
    """Serves `total` fake awards in pages, honouring each request's page/limit."""

    def __init__(self, total):
        self.total = total
        self.bodies = []

    def post(self, url, json, timeout):
        self.bodies.append(json)
        start = (json["page"] - 1) * json["limit"]
        end = min(start + json["limit"], self.total)
        results = [{"internal_id": i, "generated_internal_id": f"CONT_AWD_{i}"}
                   for i in range(start, end)]
        return FakeResponse({"results": results,
                             "page_metadata": {"page": json["page"], "hasNext": end < self.total}})


def test_request_body_shape():
    body = c.build_request_body(page=2, limit=50)
    assert body["filters"]["award_type_codes"] == ["A", "B", "C", "D"]
    assert body["filters"]["naics_codes"] == {"require": ["5415"]}
    assert body["filters"]["time_period"] == [{"start_date": "2024-10-01", "end_date": "2025-09-30"}]
    assert body["page"] == 2 and body["limit"] == 50
    assert body["sort"] in body["fields"]


@pytest.mark.parametrize("limit", [0, 101])
def test_request_body_rejects_bad_limit(limit):
    with pytest.raises(ValueError):
        c.build_request_body(page=1, limit=limit)


def test_stops_at_record_cap(tmp_path):
    session = FakeSession(total=1000)
    run_dir = c.collect(250, session=session, out_root=tmp_path, pause=0)
    notes = json.loads((run_dir / "collection_notes.json").read_text())
    assert notes["records_collected"] == 250
    assert [b["limit"] for b in session.bodies] == [100, 100, 50]
    assert notes["stop_reason"].startswith("record cap")
    assert len(list(run_dir.glob("page_*.json"))) == 3


def test_stops_at_last_page(tmp_path):
    run_dir = c.collect(500, session=FakeSession(total=130), out_root=tmp_path, pause=0)
    notes = json.loads((run_dir / "collection_notes.json").read_text())
    assert notes["records_collected"] == 130
    assert "hasNext" in notes["stop_reason"]


def test_non_retryable_error_raises(tmp_path):
    class BadSession:
        def post(self, url, json, timeout):
            return FakeResponse({"detail": "bad filter"}, status=422)

    with pytest.raises(RuntimeError, match="422"):
        c.collect(10, session=BadSession(), out_root=tmp_path, pause=0)
