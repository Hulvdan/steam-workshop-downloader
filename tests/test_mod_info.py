from src.downloader import ModInfo


def test_mod_info_filename():
    mod_info1 = ModInfo(
        "Sukritact's Simple UI Adjustments", 939149009, last_update_date=""
    )
    assert mod_info1.filename == "939149009_sukritact's_simple_ui_adjustments"

    mod_info2 = ModInfo(
        "CQUI - Community Quick User Interface", 2115302648, last_update_date=""
    )
    assert (
        mod_info2.filename == "2115302648_cqui_-_community_quick_user_interface"
    )

    mod_info3 = ModInfo(
        "Fast Dynamic Timer (Update 3.5)", 1431485535, last_update_date=""
    )
    assert (
        mod_info3.filename == "1431485535_fast_dynamic_timer_update_3.5"
    )
