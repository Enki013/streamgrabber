from streamgrabber.vaplayer import build_streamdata_url, episode_output_name, parse_media_id_from_url


def test_parse_media_id_from_streamimdb_embed_url():
    media_type, media_id = parse_media_id_from_url('https://streamimdb.ru/embed/tv/tt3032476')
    assert media_type == 'tv'
    assert media_id == 'tt3032476'


def test_build_streamdata_url_for_episode():
    assert build_streamdata_url('tt3032476', 'tv', season=1, episode=2) == (
        'https://streamdata.vaplayer.ru/api.php?imdb=tt3032476&type=tv&season=1&episode=2'
    )


def test_episode_output_name_uses_file_name_season_episode():
    assert episode_output_name(
        title='Better Call Saul 2015',
        season=1,
        episode=2,
        file_name='Better.Call.Saul.S01.1080p.BluRay.x264-Scene/better.call.saul.s01e02.1080p.bluray.x264.mkv',
    ) == 'Better Call Saul 2015 S01E02.mkv'
