from streamgrabber.doctor import check_binary, check_url_like


def test_check_url_like_accepts_http_urls():
    assert check_url_like("https://example.com/video") is True
    assert check_url_like("http://example.com/video") is True


def test_check_url_like_rejects_doctor_command_word():
    assert check_url_like("doctor") is False


def test_check_binary_reports_missing_binary():
    result = check_binary("definitely-not-a-real-streamgrabber-binary")
    assert result.name == "definitely-not-a-real-streamgrabber-binary"
    assert result.ok is False
    assert result.path is None
