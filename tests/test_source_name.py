from streamgrabber.source_name import choose_source_name, text_candidates


def test_text_candidates_extracts_episode_like_source_line():
    text = "S01\nE01\n0:00\nBetter Call Saul 2015 1-1\nVidAPI"
    assert "Better Call Saul 2015 1-1" in text_candidates(text)


def test_choose_source_name_prefers_visible_episode_name_over_generic_title():
    assert choose_source_name(
        titles=["Player", "Better Call Saul 2015"],
        visible_text="S01\nE01\n0:00\nBetter Call Saul 2015 1-1\nVidAPI",
    ) == "Better Call Saul 2015 1-1"


def test_choose_source_name_falls_back_to_useful_title():
    assert choose_source_name(titles=["Player", "Some Movie 2024"], visible_text="") == "Some Movie 2024"
