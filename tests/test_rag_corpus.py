import pandas as pd

from govspend.rag.corpus import (Chunk, award_chunks, parse_data_dictionary, parse_far_html,
                                 read_jsonl, write_jsonl)

from rag_fixtures import DATA_DICTIONARY_PAYLOAD, FAR_PART_6_HTML, make_awards


def test_far_sections_are_parsed_with_ids_titles_and_anchors():
    chunks = parse_far_html(FAR_PART_6_HTML, 6)
    sections = {c.metadata["section"] for c in chunks}
    assert sections == {"6.000", "6.302-1", "6.303-2"}  # 16.505 and the <script> ignored

    sole = next(c for c in chunks if c.chunk_id == "FAR-6.302-1")
    assert sole.title.startswith("FAR 6.302-1 Only one responsible source")
    assert "(a) Authority. When the supplies" in sole.text
    assert "(b) Application." in sole.text
    assert "only one responsible source, full and open" in sole.text  # source line wrap joined
    assert len(sole.text.split("\n")) == 3  # title + one line per paragraph
    assert sole.url.endswith("/far/part-6#FAR_6_302_1")


def test_heading_text_is_not_repeated_in_body():
    sole = next(c for c in parse_far_html(FAR_PART_6_HTML, 6) if c.chunk_id == "FAR-6.302-1")
    body = sole.text.split("\n", 1)[1]
    assert "will satisfy agency requirements" not in body


def test_long_sections_split_into_numbered_windows():
    windows = [c for c in parse_far_html(FAR_PART_6_HTML, 6, max_chars=800)
               if c.metadata["section"] == "6.303-2"]
    assert len(windows) > 1
    assert windows[0].chunk_id == "FAR-6.303-2" and windows[1].chunk_id == "FAR-6.303-2#2"
    assert all(len(c.text.split("\n", 1)[1]) <= 800 for c in windows)
    assert all(c.text.startswith("FAR 6.303-2 Content") for c in windows)  # every window keeps its title


def test_data_dictionary_rows_become_chunks():
    chunks = parse_data_dictionary(DATA_DICTIONARY_PAYLOAD)
    assert [c.chunk_id for c in chunks] == ["DD-total-obligated-amount", "DD-type-of-contract-pricing"]
    assert "Domain values: J: Firm Fixed Price" in chunks[1].text


def test_award_chunks_keep_metadata_and_leave_recipient_out_of_text():
    chunks = award_chunks(pd.DataFrame(make_awards(n_same=2)))
    big = next(c for c in chunks if c.chunk_id == "CONT_AWD_BIG")
    assert "Award amount: $95,000,000" in big.text
    assert "NAICS: 541512 COMPUTER SYSTEMS DESIGN SERVICES" in big.text
    assert "Vendor X" not in big.text and big.metadata["recipient_name"] == "Vendor X"

    hhs = next(c for c in chunks if c.chunk_id == "CONT_AWD_HHS_1")
    assert hhs.text.startswith("(no description)")
    assert hhs.metadata["has_description"] is False and hhs.metadata["start_date"] is None


def test_jsonl_round_trip(tmp_path):
    chunks = [Chunk("x", "far", "t", "body", "u", {"part": 6})]
    write_jsonl(chunks, tmp_path / "c.jsonl")
    assert read_jsonl(tmp_path / "c.jsonl") == chunks
