"""Saved cases in PostgreSQL. Plain SQL, no ORM; config.py stays untouched on purpose."""

import os

import psycopg
from dotenv import dotenv_values
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

DEFAULT_URL = "postgresql://patent:patent@127.0.0.1:5432/patent_review"
STATUSES = ("open", "in_progress", "responded", "closed")
META = "id, analysis_id, title, jurisdiction, status, deadline, created_at"

# ponytail: CREATE IF NOT EXISTS instead of migrations; add Alembic on the first schema change.
SCHEMA = f"""
CREATE TABLE IF NOT EXISTS cases (
  id bigserial PRIMARY KEY,
  analysis_id text NOT NULL,
  title text NOT NULL,
  jurisdiction text NOT NULL CHECK (jurisdiction IN ('US', 'KR')),
  status text NOT NULL DEFAULT 'open' CHECK (status IN {STATUSES}),
  deadline date,
  created_at timestamptz NOT NULL DEFAULT now(),
  result jsonb NOT NULL,
  review jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS case_files (
  case_id bigint NOT NULL REFERENCES cases ON DELETE CASCADE,
  document_id text NOT NULL,
  filename text NOT NULL,
  data bytea NOT NULL,
  PRIMARY KEY (case_id, document_id)
);
"""
_ready = False


def connect():
    # ponytail: one connection per request; add psycopg_pool when concurrent users arrive.
    global _ready
    url = os.getenv("DATABASE_URL") or dotenv_values(".env").get("DATABASE_URL") or DEFAULT_URL
    conn = psycopg.connect(url, row_factory=dict_row)
    if not _ready:
        with conn.transaction():
            conn.execute(SCHEMA)
        _ready = True
    return conn


def create_case(analysis_id, title, jurisdiction, result, review, files):
    with connect() as conn:
        case_id = conn.execute(
            "INSERT INTO cases (analysis_id, title, jurisdiction, result, review)"
            " VALUES (%s, %s, %s, %s, %s) RETURNING id",
            [analysis_id, title, jurisdiction, Jsonb(result), Jsonb(review)],
        ).fetchone()["id"]
        for document_id, (filename, data) in files.items():
            conn.execute(
                "INSERT INTO case_files VALUES (%s, %s, %s, %s)",
                [case_id, document_id, filename, data],
            )
    return case_id


def list_cases():
    with connect() as conn:
        return conn.execute(
            f"SELECT {META}, jsonb_array_length("
            "coalesce(result->'claim_summary'->'direct_rejected_claims', '[]')) AS direct_count,"
            " jsonb_array_length(result->'rejections') AS rejection_count"
            " FROM cases ORDER BY deadline ASC NULLS LAST, created_at DESC"
        ).fetchall()


def get_case(case_id):
    with connect() as conn:
        return conn.execute(
            f"SELECT {META}, result, review FROM cases WHERE id = %s", [case_id]
        ).fetchone()


def update_case(case_id, fields):
    if not fields:
        return get_meta(case_id)
    columns = ", ".join(f"{name} = %s" for name in fields)  # names come from a Pydantic model
    with connect() as conn:
        return conn.execute(
            f"UPDATE cases SET {columns} WHERE id = %s RETURNING {META}",
            [*fields.values(), case_id],
        ).fetchone()


def get_meta(case_id):
    with connect() as conn:
        return conn.execute(f"SELECT {META} FROM cases WHERE id = %s", [case_id]).fetchone()


def delete_case(case_id):
    with connect() as conn:
        return conn.execute("DELETE FROM cases WHERE id = %s", [case_id]).rowcount > 0


def get_file(case_id, document_id):
    with connect() as conn:
        return conn.execute(
            "SELECT filename, data FROM case_files WHERE case_id = %s AND document_id = %s",
            [case_id, document_id],
        ).fetchone()


def get_files(case_id):
    with connect() as conn:
        rows = conn.execute(
            "SELECT document_id, data FROM case_files WHERE case_id = %s", [case_id]
        ).fetchall()
    return {row["document_id"]: row["data"] for row in rows}
