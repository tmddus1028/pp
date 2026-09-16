"""Stream downloaded CSVs into the same local document schema with explicit column mapping."""

import csv
from pathlib import Path

from backend.errors import DocumentError
from backend.ingestion.adapters import from_text
from backend.schemas import Document


def claims_from_csv(
    path: Path, application_id: str, *, id_column: str, number_column: str, text_column: str
) -> Document:
    """Column names vary by USPTO release; require a verified mapping, not guessed fields."""
    rows = []
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        required = {id_column, number_column, text_column}
        if not required <= set(reader.fieldnames or []):
            raise DocumentError(
                f"CSV 열이 없습니다: {sorted(required - set(reader.fieldnames or []))}"
            )
        for row in reader:
            if row[id_column] != application_id:
                continue
            try:
                number = int(row[number_column])
            except ValueError as exc:
                raise DocumentError("CSV 청구항 번호는 정수여야 합니다.") from exc
            rows.append((number, row[text_column]))
    if not rows:
        raise DocumentError("선택한 application/patent ID의 청구항 데이터가 없습니다.")
    text = "Claims\n" + "\n".join(f"{number}. {text}" for number, text in sorted(rows))
    return from_text(text, f"{application_id}.txt", "patent")
