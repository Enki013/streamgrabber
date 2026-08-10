from streamgrabber.resolver import extract_imdb_id, normalize_input_url, streamimdb_url


def test_extract_imdb_id_from_bare_id():
    assert extract_imdb_id('tt0096895') == 'tt0096895'


def test_extract_imdb_id_from_imdb_title_url():
    assert extract_imdb_id('https://www.imdb.com/title/tt0096895/?ref_=fn_all_ttl_1') == 'tt0096895'


def test_streamimdb_movie_url_from_id():
    assert streamimdb_url('tt0096895', 'movie') == 'https://streamimdb.ru/embed/movie/tt0096895'


def test_streamimdb_tv_url_from_id():
    assert streamimdb_url('tt3032476', 'tv') == 'https://streamimdb.ru/embed/tv/tt3032476'


def test_normalize_imdb_movie_url_resolves_direct_streamimdb_movie_embed():
    assert normalize_input_url(
        'https://www.imdb.com/title/tt1877830',
        media_type_resolver=lambda imdb_id: 'movie',
    ) == 'https://streamimdb.ru/embed/movie/tt1877830'


def test_normalize_imdb_tv_url_resolves_direct_streamimdb_tv_embed():
    assert normalize_input_url(
        'https://www.imdb.com/title/tt3032476',
        media_type_resolver=lambda imdb_id: 'tv',
    ) == 'https://streamimdb.ru/embed/tv/tt3032476'


def test_normalize_bare_imdb_id_resolves_direct_streamimdb_embed():
    assert normalize_input_url(
        'tt1877830',
        media_type_resolver=lambda imdb_id: 'movie',
    ) == 'https://streamimdb.ru/embed/movie/tt1877830'


def test_normalize_old_playimdb_url_no_longer_requests_playimdb_redirect():
    assert normalize_input_url(
        'https://www.playimdb.com/title/tt3032476',
        media_type_resolver=lambda imdb_id: 'tv',
    ) == 'https://streamimdb.ru/embed/tv/tt3032476'


def test_normalize_streamimdb_url_keeps_url():
    url = 'https://streamimdb.ru/embed/tv/tt3032476'
    assert normalize_input_url(url, media_type_resolver=lambda _: 'movie') == url


def test_normalize_imdb_metadata_failure_falls_back_to_movie():
    assert normalize_input_url(
        'tt1877830',
        media_type_resolver=lambda imdb_id: (_ for _ in ()).throw(RuntimeError('offline')),
    ) == 'https://streamimdb.ru/embed/movie/tt1877830'
