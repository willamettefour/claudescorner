import claudescorner


def test_everything_in_all_is_importable():
    for name in claudescorner.__all__:
        assert hasattr(claudescorner, name), name


def test_version_is_a_non_empty_string():
    assert isinstance(claudescorner.__version__, str)
    assert claudescorner.__version__
