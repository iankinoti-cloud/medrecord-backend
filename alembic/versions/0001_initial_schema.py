"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-14 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ─────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id",            postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email",         sa.String(255), nullable=False),
        sa.Column("full_name",     sa.String(255), nullable=False),
        sa.Column("role",          sa.String(50),  nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("avatar_url",    sa.String(500), nullable=True),
        sa.Column("is_active",     sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("google_id",     sa.String(255), nullable=True),
        sa.Column("github_id",     sa.String(255), nullable=True),
        sa.Column("created_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email",     "users", ["email"],     unique=True)
    op.create_index("ix_users_google_id", "users", ["google_id"], unique=True)
    op.create_index("ix_users_github_id", "users", ["github_id"], unique=True)

    # ── patients ──────────────────────────────────────────────
    op.create_table(
        "patients",
        sa.Column("id",                postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id",        sa.String(20),  nullable=False),
        sa.Column("full_name",         sa.String(255), nullable=False),
        sa.Column("date_of_birth",     sa.Date(),      nullable=False),
        sa.Column("gender",            sa.String(50),  nullable=True),
        sa.Column("blood_type",        sa.String(10),  nullable=True),
        sa.Column("contact_phone",     sa.String(50),  nullable=True),
        sa.Column("contact_email",     sa.String(255), nullable=True),
        sa.Column("address",           sa.Text(),      nullable=True),
        sa.Column("emergency_contact", sa.String(255), nullable=True),
        sa.Column("status",            sa.String(50),  nullable=False, server_default="Active"),
        sa.Column("registered_by",     postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_patients_patient_id", "patients", ["patient_id"], unique=True)
    op.create_index("ix_patients_full_name",  "patients", ["full_name"])
    op.create_index("ix_patients_status",     "patients", ["status"])

    # ── medical_records ───────────────────────────────────────
    op.create_table(
        "medical_records",
        sa.Column("id",           postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id",   postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doctor_id",    postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("diagnosis",    sa.Text(),      nullable=False),
        sa.Column("prescription", sa.Text(),      nullable=True),
        sa.Column("notes",        sa.Text(),      nullable=True),
        sa.Column("record_type",  sa.String(50),  nullable=False, server_default="General"),
        sa.Column("created_at",   sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_medical_records_patient_id", "medical_records", ["patient_id"])

    # ── lab_results ───────────────────────────────────────────
    op.create_table(
        "lab_results",
        sa.Column("id",          postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id",  postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("uploader_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("test_type",   sa.String(100), nullable=False),
        sa.Column("report_id",   sa.String(50),  nullable=False),
        sa.Column("file_url",    sa.String(500), nullable=False),
        sa.Column("status",      sa.String(50),  nullable=False, server_default="Pending"),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_lab_results_patient_id", "lab_results", ["patient_id"])
    op.create_unique_constraint("uq_lab_results_report_id", "lab_results", ["report_id"])

    # ── audit_log ─────────────────────────────────────────────
    op.create_table(
        "audit_log",
        sa.Column("id",          postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id",     postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action",      sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=True),
        sa.Column("entity_id",   postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("details",     postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("ip_address",  postgresql.INET(), nullable=True),
        sa.Column("user_agent",  sa.Text(),      nullable=True),
        sa.Column("created_at",  sa.DateTime(timezone=True),
                  server_default=sa.func.now(), index=True),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("lab_results")
    op.drop_table("medical_records")
    op.drop_table("patients")
    op.drop_table("users")
