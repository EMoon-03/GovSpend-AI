import pandas as pd
import pytest

from govspend.rag.corpus import award_chunks, parse_data_dictionary, parse_far_html
from govspend.rag.embed import HashingEmbedder
from govspend.rag.evaluate import evaluate, score_query
from govspend.rag.index import VectorIndex
from govspend.rag.retrieve import peer_summary, retrieve_peers, retrieve_references

from rag_fixtures import DATA_DICTIONARY_PAYLOAD, FAR_PART_6_HTML, make_awards


@pytest.fixture(scope="module")
def embedder():
    return HashingEmbedder()


@pytest.fixture(scope="module")
def awards(embedder):
    return VectorIndex.build(award_chunks(pd.DataFrame(make_awards())), embedder)


@pytest.fixture(scope="module")
def references(embedder):
    chunks = parse_far_html(FAR_PART_6_HTML, 6) + parse_data_dictionary(DATA_DICTIONARY_PAYLOAD)
    return VectorIndex.build(chunks, embedder)


def test_index_save_load_round_trip(tmp_path, awards):
    awards.save(tmp_path / "award")
    loaded = VectorIndex.load(tmp_path / "award")
    assert len(loaded) == len(awards) and loaded.embedder_name == awards.embedder_name
    assert (loaded.vectors == awards.vectors).all()


def test_mismatched_embedder_fails_loudly(awards):
    with pytest.raises(ValueError, match="rebuild"):
        awards.search_text(HashingEmbedder(n_features=2**10), "cloud", 3)


def test_peer_summary_uses_same_naics_and_agency(awards):
    s = peer_summary(awards.get("CONT_AWD_BIG"), awards, min_group=20)
    assert s.n == 24 and "Department of Defense" in s.group
    assert s.median_amount == pytest.approx(1_250_000.0)
    assert s.ratio == pytest.approx(76.0)
    assert "76.0 times" in s.describe()


def test_peer_summary_unavailable_when_group_too_small(awards):
    assert peer_summary(awards.get("CONT_AWD_HHS_1"), awards, min_group=20) is None


def test_peers_exclude_target_and_prefer_similar_descriptions(awards):
    peers = retrieve_peers(awards.get("CONT_AWD_BIG"), awards, k=5)
    ids = [p.hit.chunk.chunk_id for p in peers]
    assert "CONT_AWD_BIG" not in ids and len(ids) == 5
    assert all(p.level == "same NAICS" for p in peers)
    assert all("CLOUD HOSTING" in p.hit.chunk.text for p in peers)


def test_peers_fall_back_beyond_naics(awards):
    peers = retrieve_peers(awards.get("CONT_AWD_HHS_1"), awards, k=3)
    assert len(peers) == 3 and {p.level for p in peers} == {"any"}


def test_reference_retrieval_returns_far_then_dictionary(awards, references, embedder):
    hits = retrieve_references(awards.get("CONT_AWD_BIG"), references, embedder, k_far=2, k_dd=1)
    assert [h.chunk.source for h in hits] == ["far", "far", "data_dictionary"]


def test_score_query_counts_windows_as_their_section():
    recall, rr = score_query(["FAR-6.000", "FAR-6.302-1#2", "FAR-6.303-2"], {"FAR-6.302-1"})
    assert recall == 1.0 and rr == pytest.approx(0.5)


def test_evaluate_reports_per_index(references, embedder):
    queries = [{"query": "only one responsible source sole source authority", "index": "reference",
                "relevant": ["FAR-6.302-1"]}]
    result = evaluate(queries, {"reference": references}, embedder, k=3)
    assert result["reference"]["queries"] == 1
    assert result["reference"]["recall@3"] == 1.0
