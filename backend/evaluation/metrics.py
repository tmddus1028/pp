from collections.abc import Iterable


def set_metrics(predicted: Iterable, expected: Iterable) -> dict[str, float | int]:
    predicted, expected = set(predicted), set(expected)
    tp = len(predicted & expected)
    precision = tp / len(predicted) if predicted else (1.0 if not expected else 0.0)
    recall = tp / len(expected) if expected else (1.0 if not predicted else 0.0)
    return {
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "true_positives": tp,
        "predicted": len(predicted),
        "expected": len(expected),
        "exact_match": float(predicted == expected),
    }


def classification_metrics(predicted: list[str], expected: list[str]) -> dict[str, float]:
    """Aligned labels only; caller is responsible for aligning items by ground-truth IDs."""
    if len(predicted) != len(expected):
        raise ValueError("Predictions and labels must have equal lengths and aligned item IDs")
    labels = set(predicted) | set(expected)
    f1s = [
        set_metrics(
            [i for i, p in enumerate(predicted) if p == label],
            [i for i, e in enumerate(expected) if e == label],
        )["f1"]
        for label in labels
    ]
    return {
        "accuracy": sum(p == e for p, e in zip(predicted, expected)) / len(expected)
        if expected
        else 1.0,
        "macro_f1": sum(f1s) / len(f1s) if f1s else 1.0,
    }
