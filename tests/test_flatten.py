"""Checks for amount parsing, nested code fields and duplicate handling."""

from govspend.flatten import flatten, split_code


def rec(gid, amount, naics=None, **extra):
    base = {"internal_id": 1, "generated_internal_id": gid, "Award ID": gid,
            "Award Amount": amount, "NAICS": naics, "Start Date": "2025-01-15"}
    base.update(extra)
    return base


def test_split_code_handles_dict_string_and_none():
    assert split_code({"code": "541511", "description": "Custom Programming"}) == ("541511", "Custom Programming")
    assert split_code("541512") == ("541512", None)
    assert split_code(None) == (None, None)


def test_amounts_parse_including_negative_and_bad_values():
    df = flatten([rec("a", 1500.5), rec("b", "-200"), rec("c", "n/a"), rec("d", None)])
    assert df["award_amount"].tolist()[:2] == [1500.5, -200.0]
    assert df["award_amount"].isna().sum() == 2  # kept as missing, not silently zeroed


def test_duplicates_dropped_by_generated_internal_id():
    df = flatten([rec("a", 1), rec("a", 1), rec("b", 2)])
    assert len(df) == 2
    assert df.attrs["duplicates_dropped"] == 1


def test_dates_and_naics_columns():
    df = flatten([rec("a", 1, naics={"code": "541511", "description": "Custom Programming"},
                      **{"Start Date": "not a date"})])
    assert df.loc[0, "naics_code"] == "541511"
    assert df["start_date"].isna().all()
