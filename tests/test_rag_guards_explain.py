import pandas as pd

from govspend.rag import explain, guards
from govspend.rag.corpus import award_chunks, parse_data_dictionary, parse_far_html
from govspend.rag.embed import HashingEmbedder
from govspend.rag.index import VectorIndex

from rag_fixtures import DATA_DICTIONARY_PAYLOAD, FAR_PART_6_HTML, make_awards

ALLOWED = {"CONT_AWD_BIG", "CONT_AWD_DOD_1", "FAR-6.302-1"}


def test_clean_explanation_passes():
    text = ("The award is 76.0 times the peer median [A:CONT_AWD_BIG]. "
            "Comparable cloud awards were far smaller [A:CONT_AWD_DOD_1]. "
            "Sole-source authority applies when only one source exists [R:FAR-6.302-1].")
    report = guards.check(text, ALLOWED)
    assert report.passed and not report.uncited_claims and len(report.citations) == 3


def test_fabricated_citation_fails():
    report = guards.check("Similar awards exist [A:CONT_AWD_NOT_RETRIEVED].", ALLOWED)
    assert not report.passed and report.unknown_citations == ["CONT_AWD_NOT_RETRIEVED"]


def test_accusatory_wording_fails_but_ordinary_waste_does_not():
    assert guards.check("This looks fraudulent [A:CONT_AWD_BIG].", ALLOWED).accusatory_terms == ["fraudulent"]
    assert guards.check("Possible kickbacks [A:CONT_AWD_BIG].", ALLOWED).accusatory_terms == ["kickbacks"]
    assert guards.check("Covers hazardous waste removal [A:CONT_AWD_BIG].", ALLOWED).passed


def test_uncited_figures_are_reported():
    report = guards.check("The award is $95 million. It is larger than peers [A:CONT_AWD_BIG].", ALLOWED)
    assert report.uncited_claims == ["The award is $95 million."]


def test_no_citations_fails():
    assert not guards.check("The award is unusual.", ALLOWED).passed


def _indexes():
    emb = HashingEmbedder()
    awards = VectorIndex.build(award_chunks(pd.DataFrame(make_awards())), emb)
    refs = VectorIndex.build(parse_far_html(FAR_PART_6_HTML, 6) + parse_data_dictionary(DATA_DICTIONARY_PAYLOAD), emb)
    return awards, refs, emb


def test_prompt_contains_only_retrieved_ids_and_rules():
    awards, refs, emb = _indexes()
    ctx = explain.gather_context("CONT_AWD_BIG", awards, refs, emb, k_peers=3, k_far=2, k_dd=1)
    p = ctx.prompt
    assert "[A:CONT_AWD_BIG]" in p.user and "76.0 times" in p.user
    assert len(p.allowed_ids) == 1 + 3 + 3
    for cid in p.allowed_ids:
        assert f":{cid}]" in p.user
    assert "Never invent an ID" in p.system and "not a finding" in p.system


def test_end_to_end_with_stub_model(tmp_path, monkeypatch):
    awards, refs, emb = _indexes()
    awards.save(tmp_path / "award")
    refs.save(tmp_path / "reference")

    def fake_generate(system, user, **kwargs):
        peer = next(line for line in user.splitlines() if line.startswith("[A:CONT_AWD_DOD"))
        peer_id = peer.split("]")[0][3:]
        return (f"The award is 76.0 times the peer median [A:CONT_AWD_BIG]. "
                f"A comparable cloud award was much smaller [A:{peer_id}].")

    monkeypatch.setattr(explain, "generate", fake_generate)
    monkeypatch.setattr(explain, "get_embedder", lambda name: emb)
    explain.main(["CONT_AWD_BIG", "--index-dir", str(tmp_path), "--out-dir", str(tmp_path / "out")])

    md = (tmp_path / "out" / "CONT_AWD_BIG.md").read_text()
    assert "Guard result: PASS" in md
    assert "not a finding of wrongdoing" in md
    assert "https://www.usaspending.gov/award/CONT_AWD_BIG" in md
