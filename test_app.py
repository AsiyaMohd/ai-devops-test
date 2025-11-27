# test_app.py

def test_basic_math():
    """A simple test to ensure pytest is working."""
    assert 1 + 1 == 2

def test_app_import():
    """Optional: Try to import app to ensure no syntax errors in app.py."""
    try:
        import app
        assert True
    except ImportError:
        # If app.py isn't a module or has errors, this might fail
        assert False, "Could not import app.py"