"""Exercise the saved models without the API loader's heuristic fallback."""
from pathlib import Path
import warnings

import joblib
import numpy as np
import pytest
from sklearn.exceptions import InconsistentVersionWarning


ARTIFACTS = Path(__file__).resolve().parents[1] / 'artifacts'


@pytest.mark.parametrize('name', ['priority', 'intervention', 'service_gap', 'cost', 'grievance'])
def test_saved_models_are_compatible_with_the_installed_runtime(name):
    with warnings.catch_warnings():
        warnings.simplefilter('error', InconsistentVersionWarning)
        model = joblib.load(ARTIFACTS / f'{name}_model.joblib')
    assert model is not None
    if name == 'grievance':
        probabilities = model.predict_proba(['Water supply has stopped in this area.'])
        assert probabilities.shape == (1, len(model.classes_))
        assert np.isfinite(probabilities).all()
        assert np.isclose(probabilities.sum(), 1.0)
