from tskb.barbell import DualBarbell


def test_tension_constraints():
    craft = DualBarbell(1000.0, min_length=1.0, max_length=2.0)
    assert craft.tension_ok(1.5)
    assert not craft.tension_ok(0.5)
    assert not craft.tension_ok(2.5)
