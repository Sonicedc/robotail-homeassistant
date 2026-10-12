"""Cat association is based on record IDs, never inferred from weight."""

from custom_components.robotail.visit import last_cat_name


def test_profile_lookup_accepts_string_record_id():
    assert (
        last_cat_name(
            {
                "latest_visit": {"catInfoId": "12", "weight": 4.2},
                "cats": [{"catInfoId": 12, "nickname": "Milo"}],
            }
        )
        == "Milo"
    )


def test_unassociated_visit_is_unknown_even_with_matching_weight():
    assert (
        last_cat_name(
            {
                "latest_visit": {"catInfoId": 0, "weight": 4.2},
                "cats": [{"catInfoId": 0, "nickname": "Milo", "weight": 4.2}],
            }
        )
        is None
    )


def test_missing_profile_does_not_display_another_cat():
    assert (
        last_cat_name(
            {
                "latest_visit": {"catInfoId": 12},
                "cats": [{"catInfoId": 13, "nickname": "Milo"}],
            }
        )
        is None
    )


def test_no_visit_is_unknown():
    assert last_cat_name({"cats": [{"catInfoId": 12, "nickname": "Milo"}]}) is None
