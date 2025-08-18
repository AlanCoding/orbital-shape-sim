from tskb.barbell import DualBarbell


def test_tension_constraints():
    craft = DualBarbell(1000.0)
    craft.update(1.0)
    assert craft.tension_ok()
    craft.update(-1.0)
    assert not craft.tension_ok()
