from streamgrabber.naming import output_path_from_title, sanitize_filename


def test_sanitize_filename_removes_forbidden_characters():
    assert sanitize_filename('Better Call Saul: S01/E01? "Uno"') == 'Better Call Saul S01_E01 Uno'


def test_sanitize_filename_collapses_whitespace_and_dots():
    assert sanitize_filename('  ...Better   Call   Saul...  ') == 'Better Call Saul'


def test_output_path_from_title_uses_mkv_extension(tmp_path):
    assert output_path_from_title('Better Call Saul 2015 1-1', tmp_path).name == 'Better Call Saul 2015 1-1.mkv'


def test_output_path_from_title_falls_back_when_empty(tmp_path):
    assert output_path_from_title('', tmp_path).name == 'streamgrabber-output.mkv'
