from streamgrabber.subtitles import (
    build_opensubtitles_search_url,
    choose_best_subtitle,
    language_to_opensubtitles_id,
    parse_release,
    srt_to_vtt,
    streamimdb_match_score,
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


def test_parse_release_matches_streamimdb_ptt_fields():
    info = parse_release('Better.Call.Saul.S01.1080p.BluRay.x264-Scene/better.call.saul.s01e02.1080p.bluray.x264-shortbrehd.mkv')
    assert info is not None
    assert info.title == 'better call saul s01'
    assert info.season == 1
    assert info.episode == 2
    assert info.resolution == '1080p'
    assert info.quality == 'BluRay'
    assert info.codec == 'x264'
    assert info.release_group == 'shortbrehd'


def test_streamimdb_match_score_rewards_exact_release_metadata():
    video = parse_release('Better.Call.Saul.S01.1080p.BluRay.x264-Scene/better.call.saul.s01e02.1080p.bluray.x264-shortbrehd.mkv')
    matching = 'better.call.saul.s01e02.1080p.bluray.x264-shortbrehd.srt'
    mismatching = 'Better.Call.Saul.S01E03.720p.NF.WEBRip.DD5.1.x264-NTb.srt'
    assert streamimdb_match_score(video, matching) >= 80
    assert streamimdb_match_score(video, mismatching) < 50


def test_choose_best_subtitle_prefers_streamimdb_ptt_match_over_downloads():
    subs = [
        {'SubFileName': 'Better.Call.Saul.S01E02.Mijo.720p.NF.WEBRip.DD5.1.x264-NTb.srt', 'SubDownloadsCnt': '99999'},
        {'SubFileName': 'better.call.saul.s01e02.1080p.bluray.x264-shortbrehd.srt', 'SubDownloadsCnt': '10'},
    ]
    selected = choose_best_subtitle(
        subs,
        title='Better Call Saul 2015',
        file_name='Better.Call.Saul.S01.1080p.BluRay.x264-Scene/better.call.saul.s01e02.1080p.bluray.x264-shortbrehd.mkv',
        season=1,
        episode=2,
    )
    assert selected['SubFileName'] == 'better.call.saul.s01e02.1080p.bluray.x264-shortbrehd.srt'


def test_choose_best_subtitle_prefers_bluray_over_high_download_webrip_for_bluray_video():
    subs = [
        {'SubFileName': 'Better.Call.Saul.S01E02.Mijo.720p.NF.WEBRip.DD5.1.x264-NTb.srt', 'SubDownloadsCnt': '13512'},
        {'SubFileName': 'Better.Call.Saul.S01E02.720p.Bluray.x264.srt', 'SubDownloadsCnt': '1709'},
    ]
    selected = choose_best_subtitle(
        subs,
        title='Better Call Saul 2015',
        file_name='Better.Call.Saul.S01.1080p.BluRay.x264-Scene/better.call.saul.s01e02.1080p.bluray.x264-shortbrehd.mkv',
        season=1,
        episode=2,
    )
    assert selected['SubFileName'] == 'Better.Call.Saul.S01E02.720p.Bluray.x264.srt'


def test_choose_best_subtitle_falls_back_to_downloads_without_any_release_info():
    subs = [
        {'SubFileName': 'Random.Show.S01E03.srt', 'SubDownloadsCnt': '999'},
        {'SubFileName': 'Better.Call.Saul.S01E02.720p.BluRay.x264-DEFLATE.srt', 'SubDownloadsCnt': '10'},
    ]
    assert choose_best_subtitle(subs)['SubFileName'] == 'Random.Show.S01E03.srt'
