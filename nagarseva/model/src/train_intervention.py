"""Compatibility entry point for the intervention recommender.

The priority training job fits both the priority regressor and the intervention
classifier so their ward split and artifacts remain aligned.
"""

try:
    from .train_priority import train
except ImportError:
    from train_priority import train


if __name__ == "__main__":
    result = train()
    print({key: result[key] for key in ("intervention_macro_f1", "intervention_accuracy", "intervention_labels")})
