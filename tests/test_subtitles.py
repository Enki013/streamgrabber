from streamgrabber.subtitles import (
    build_opensubtitles_search_url,
    language_to_opensubtitles_id,
    srt_to_vtt,
    choose_best_subtitle,
)


def test_language_to_opensubtitles_id_accepts_tr_and_turkish():
    assert language_to_opensubtitles_id('tr') == 'tur'
    assert language_to_opensubtitles_id('turkish') == 'tur'
    assert language_to_opensubtitles_id('tur') == 'tur'


def test_build_search_url_for_movie():
    assert build_opensubtitles_search_url('tt0096895', 'tur') == (
        'https://rest.opensubtitles.org/search/imdbid-0096895/sublanguageid-tur'
    )


def test_build_search_url_for_tv_episode():
    assert build_opensubtitles_search_url('tt3032476', 'tur', season=1, episode=2) == (
        'https://rest.opensubtitles.org/search/episode-2/imdbid-3032476/season-1/sublanguageid-tur'
    )


def test_srt_to_vtt_converts_timestamps():
    srt = '1\n00:00:01,000 --> 00:00:02,500\nMerhaba\n'
    assert srt_to_vtt(srt).startswith('WEBVTT\n\n00:00:01.000 --> 00:00:02.500\nMerhaba')


def test_choose_best_subtitle_prefers_matching_episode_and_downloads():
    subs = [
        {'SubFileName': 'Random.Show.S01E03.srt', 'SubDownloadsCnt': '999'},
        {'SubFileName': 'Better.Call.Saul.S01E02.720p.BluRay.x264-DEFLATE.srt', 'SubDownloadsCnt': '10'},
    ]
    assert choose_best_subtitle(subs, title='Better Call Saul 2015', season=1, episode=2)['SubFileName'].endswith('S01E02.720p.BluRay.x264-DEFLATE.srt')
