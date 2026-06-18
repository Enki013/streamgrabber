from streamgrabber.resolver import extract_imdb_id, normalize_input_url, playimdb_url


def test_extract_imdb_id_from_bare_id():
    assert extract_imdb_id('tt0096895') == 'tt0096895'


def test_extract_imdb_id_from_imdb_title_url():
    assert extract_imdb_id('https://www.imdb.com/title/tt0096895/?ref_=fn_all_ttl_1') == 'tt0096895'


def test_playimdb_url_from_id():
    assert playimdb_url('tt0096895') == 'https://www.playimdb.com/title/tt0096895'


def test_normalize_imdb_url_uses_playimdb_redirect_resolver():
    assert normalize_input_url(
        'https://www.imdb.com/title/tt0096895',
        redirect_resolver=lambda url: 'https://streamimdb.ru/embed/movie/tt0096895',
    ) == 'https://streamimdb.ru/embed/movie/tt0096895'


def test_normalize_streamimdb_url_keeps_url():
    url = 'https://streamimdb.ru/embed/tv/tt3032476'
    assert normalize_input_url(url, redirect_resolver=lambda _: 'SHOULD_NOT_BE_USED') == url
