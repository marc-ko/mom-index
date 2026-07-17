import json
import sys
from pathlib import Path
from typing import Dict, Iterable, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analyzer.semantic_classifier import classify_semantic


def predicted_label(row: Dict) -> str:
    result = classify_semantic(row["post"], row.get("sector", "unknown"))
    if result.spam_or_marketing >= 50:
        return "marketing_or_creator_content"
    if result.author_is_beginner >= 50 and (result.basic_knowledge_gap >= 40 or result.decision_dependence >= 40):
        return "actual_beginner_question"
    if result.targets_beginners >= 60 and result.author_is_beginner < 40:
        return "beginner_education"
    if abs(result.fomo_or_panic) >= 50:
        return "emotional_retail_post"
    if result.professional_depth >= 50:
        return "professional_or_data_driven"
    return "normal_discussion"


def evaluate_rows(rows: Iterable[Dict]) -> Dict[str, float]:
    rows = list(rows)
    predictions = [(row["expected_label"], predicted_label(row)) for row in rows]
    true_positive = sum(1 for expected, predicted in predictions if expected == predicted == "actual_beginner_question")
    predicted_positive = sum(1 for _, predicted in predictions if predicted == "actual_beginner_question")
    actual_positive = sum(1 for expected, _ in predictions if expected == "actual_beginner_question")
    precision = true_positive / max(predicted_positive, 1)
    recall = true_positive / max(actual_positive, 1)
    accuracy = sum(1 for expected, predicted in predictions if expected == predicted) / max(len(predictions), 1)
    return {
        "actual_beginner_question_precision": round(precision, 3),
        "actual_beginner_question_recall": round(recall, 3),
        "accuracy": round(accuracy, 3),
    }


def load_jsonl(path: Path) -> List[Dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


if __name__ == "__main__":
    rows = load_jsonl(Path("data/labeled_posts.example.jsonl"))
    print(json.dumps(evaluate_rows(rows), ensure_ascii=False, indent=2))
