"""Copy data/precedents/*.jsonl into the PostgreSQL `response_cases` table.

docker compose up -d   # then
uv run python scripts/load_precedents_pg.py

Korean KIPRIS cases only (demo cases stay out). The table mirrors the redesign doc: 사건 · 거절 유형 · 대응 방식 · 다음 조치 · 해소 여부.
Re-running replaces rows of the same source; the JSONL stays the source of truth.
"""

import sys
from pathlib import Path

from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend import store  # noqa: E402
from backend.precedents.repository import KR_PATH, load  # noqa: E402

DDL = """
CREATE TABLE IF NOT EXISTS response_cases (
  case_id text PRIMARY KEY,
  source text NOT NULL,
  jurisdiction text NOT NULL DEFAULT 'KR' CHECK (jurisdiction = 'KR'),
  application text NOT NULL,
  round int NOT NULL,
  category text NOT NULL,
  oa_type text NOT NULL,
  oa_date date,
  response_type text NOT NULL CHECK (response_type IN ('amendment', 'argument_only', 'none', 'unknown')),
  argument_types text[] NOT NULL DEFAULT '{}',
  next_action text NOT NULL,
  outcome text NOT NULL CHECK (outcome IN ('resolved', 'unresolved', 'excluded')),
  examiner_reply text NOT NULL,
  record jsonb NOT NULL
);
CREATE INDEX IF NOT EXISTS response_cases_category ON response_cases (category, outcome);
"""


def main():
    cases = load(KR_PATH)
    with store.connect() as conn, conn.transaction():
        conn.execute(DDL)
        conn.execute("DELETE FROM response_cases WHERE source = %s", ["KIPRIS"])
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO response_cases (case_id, source, application, round, category,"
                " oa_type, oa_date, response_type, argument_types, next_action, outcome,"
                " examiner_reply, record) VALUES"
                " (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                [
                    (
                        c["case_id"],
                        c["source"],
                        c["application"],
                        c["round"],
                        c["category"],
                        c["oa_type"],
                        c["oa_date"] or None,
                        c["response_type"],
                        c["argument_types"],
                        c["next_action"],
                        c["outcome"],
                        c["examiner_reply"],
                        Jsonb(c),
                    )
                    for c in cases
                ],
            )
    print(f"{len(cases)} response cases loaded")


if __name__ == "__main__":
    main()
