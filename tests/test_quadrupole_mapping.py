import numpy as np
from tskb.barbell import Q_of_barbell


def test_quadrupole_mapping():
    Q = Q_of_barbell(2.0, 2.0, np.array([1.0, 0.0, 0.0]))
    assert np.allclose(np.diag(Q), [4.0, -2.0, -2.0])
    assert np.isclose(np.trace(Q), 0.0)
