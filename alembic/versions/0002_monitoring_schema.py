"""Monitoring catalog, checks, incidents, breaches, and outbox."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_monitoring_schema"
down_revision: str | None = "0001_create_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SERVICE_OVERVIEW = """
CREATE VIEW service_overview AS
SELECT
    services.id AS service_id,
    services.slug,
    services.name,
    services.company_name,
    services.domain,
    COALESCE(service_cards.status, 'unknown') AS status,
    service_cards.status_since,
    service_cards.last_checked_at,
    COALESCE(breach_totals.breach_count, 0) AS breach_count,
    COALESCE(breach_totals.major_breach_count, 0) AS major_breach_count,
    breach_totals.latest_breach_published_at
FROM services
LEFT JOIN service_cards ON service_cards.service_id = services.id
LEFT JOIN (
    SELECT
        breaches.service_id,
        COUNT(*) AS breach_count,
        COUNT(*) FILTER (
            WHERE breaches.severity IN ('high', 'critical')
        ) AS major_breach_count,
        MAX(breaches.published_at) AS latest_breach_published_at
    FROM breaches
    GROUP BY breaches.service_id
) AS breach_totals ON breach_totals.service_id = services.id
"""


def upgrade() -> None:
    op.create_table(
        "services",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("company_name", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("domain", sa.String(length=253), nullable=False),
        sa.Column("homepage_url", sa.String(length=2048), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_services"),
        sa.UniqueConstraint("slug", name="uq_services_slug"),
        sa.UniqueConstraint("domain", name="uq_services_domain"),
        sa.CheckConstraint(
            "slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'",
            name="ck_services_slug",
        ),
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_services_name"),
        sa.CheckConstraint(
            "domain ~ '^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$'",
            name="ck_services_domain",
        ),
        sa.CheckConstraint(
            "homepage_url LIKE 'https://%'",
            name="ck_services_homepage_url",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_services_created_by_users",
            ondelete="SET NULL",
        ),
    )
    op.create_table(
        "checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("purpose", sa.String(length=16), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column(
            "interval_seconds",
            sa.Integer(),
            server_default=sa.text("60"),
            nullable=False,
        ),
        sa.Column(
            "timeout_ms",
            sa.Integer(),
            server_default=sa.text("5000"),
            nullable=False,
        ),
        sa.Column(
            "slow_threshold_ms",
            sa.Integer(),
            server_default=sa.text("2000"),
            nullable=False,
        ),
        sa.Column(
            "failure_threshold",
            sa.SmallInteger(),
            server_default=sa.text("3"),
            nullable=False,
        ),
        sa.Column(
            "recovery_threshold",
            sa.SmallInteger(),
            server_default=sa.text("2"),
            nullable=False,
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "next_run_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_checks"),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["services.id"],
            name="fk_checks_service_id_services",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "kind IN ('http', 'status_page', 'rss', 'breach')",
            name="ck_checks_kind",
        ),
        sa.CheckConstraint(
            "purpose IN ('primary', 'extra', 'breach')",
            name="ck_checks_purpose",
        ),
        sa.CheckConstraint("url IS NULL OR url LIKE 'https://%'", name="ck_checks_url"),
        sa.CheckConstraint(
            "interval_seconds BETWEEN 30 AND 86400",
            name="ck_checks_interval_seconds",
        ),
        sa.CheckConstraint(
            "timeout_ms BETWEEN 100 AND 30000",
            name="ck_checks_timeout_ms",
        ),
        sa.CheckConstraint(
            "slow_threshold_ms > 0 AND slow_threshold_ms < timeout_ms",
            name="ck_checks_slow_threshold_ms",
        ),
        sa.CheckConstraint(
            "failure_threshold BETWEEN 1 AND 20",
            name="ck_checks_failure_threshold",
        ),
        sa.CheckConstraint(
            "recovery_threshold BETWEEN 1 AND 20",
            name="ck_checks_recovery_threshold",
        ),
        sa.CheckConstraint(
            "(kind = 'breach') = (purpose = 'breach')",
            name="ck_checks_breach_purpose",
        ),
        sa.CheckConstraint(
            "(kind = 'breach') = (url IS NULL)",
            name="ck_checks_breach_url",
        ),
        sa.UniqueConstraint(
            "service_id",
            "kind",
            "url",
            name="uq_checks_target",
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.create_index(
        "uq_checks_one_primary",
        "checks",
        ["service_id"],
        unique=True,
        postgresql_where=sa.text("purpose = 'primary'"),
    )
    op.create_index(
        "ix_checks_due",
        "checks",
        ["next_run_at"],
        postgresql_where=sa.text("enabled"),
    )
    op.create_table(
        "check_states",
        sa.Column("check_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "consecutive_failures",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "consecutive_successes",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("last_result", sa.String(length=8), nullable=True),
        sa.Column("last_slot_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("check_id", name="pk_check_states"),
        sa.ForeignKeyConstraint(
            ["check_id"],
            ["checks.id"],
            name="fk_check_states_check_id_checks",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "consecutive_failures >= 0",
            name="ck_check_states_consecutive_failures",
        ),
        sa.CheckConstraint(
            "consecutive_successes >= 0",
            name="ck_check_states_consecutive_successes",
        ),
        sa.CheckConstraint(
            "last_result IN ('success', 'slow', 'failure', 'unknown')",
            name="ck_check_states_last_result",
        ),
        sa.CheckConstraint(
            "consecutive_failures = 0 OR consecutive_successes = 0",
            name="ck_check_states_one_streak",
        ),
    )
    op.create_table(
        "check_attempts",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("check_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slot_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("result", sa.String(length=8), nullable=False),
        sa.Column("http_status", sa.SmallInteger(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("vendor_indicator", sa.String(length=16), nullable=True),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.Column(
            "detail",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_check_attempts"),
        sa.ForeignKeyConstraint(
            ["check_id"],
            ["checks.id"],
            name="fk_check_attempts_check_id_checks",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("check_id", "slot_at", name="uq_check_attempts_slot"),
        sa.CheckConstraint(
            "result IN ('success', 'slow', 'failure', 'unknown')",
            name="ck_check_attempts_result",
        ),
        sa.CheckConstraint(
            "http_status BETWEEN 100 AND 599",
            name="ck_check_attempts_http_status",
        ),
        sa.CheckConstraint("latency_ms >= 0", name="ck_check_attempts_latency_ms"),
        sa.CheckConstraint(
            "vendor_indicator IN ('none', 'minor', 'major', 'critical', 'maintenance')",
            name="ck_check_attempts_vendor_indicator",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(detail) = 'object'",
            name="ck_check_attempts_detail",
        ),
        sa.CheckConstraint(
            "finished_at >= started_at",
            name="ck_check_attempts_finished_at",
        ),
    )
    op.create_table(
        "service_cards",
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.String(length=10),
            server_default=sa.text("'unknown'"),
            nullable=False,
        ),
        sa.Column(
            "status_since",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("service_id", name="pk_service_cards"),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["services.id"],
            name="fk_service_cards_service_id_services",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "status IN ('unknown', 'up', 'degraded', 'down')",
            name="ck_service_cards_status",
        ),
    )
    op.create_table(
        "incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=True),
        sa.Column("vendor_status", sa.String(length=32), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opened_by_attempt_id", sa.BigInteger(), nullable=True),
        sa.Column("resolved_by_attempt_id", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_incidents"),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["services.id"],
            name="fk_incidents_service_id_services",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["opened_by_attempt_id"],
            ["check_attempts.id"],
            name="fk_incidents_opened_by_attempt_id_check_attempts",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by_attempt_id"],
            ["check_attempts.id"],
            name="fk_incidents_resolved_by_attempt_id_check_attempts",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "source IN ('detector', 'status_page')",
            name="ck_incidents_source",
        ),
        sa.CheckConstraint(
            "status IN ('degraded', 'down')",
            name="ck_incidents_status",
        ),
        sa.CheckConstraint(
            "resolved_at IS NULL OR resolved_at >= opened_at",
            name="ck_incidents_resolved_after_opened",
        ),
        sa.CheckConstraint(
            "(source = 'status_page') = (external_id IS NOT NULL)",
            name="ck_incidents_external_id",
        ),
    )
    op.create_index(
        "uq_incidents_one_open_detector",
        "incidents",
        ["service_id"],
        unique=True,
        postgresql_where=sa.text("source = 'detector' AND resolved_at IS NULL"),
    )
    op.create_index(
        "uq_incidents_external",
        "incidents",
        ["service_id", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )
    op.create_index(
        "ix_incidents_service_opened",
        "incidents",
        ["service_id", sa.text("opened_at DESC")],
    )
    op.create_table(
        "breaches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("external_name", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("severity", sa.String(length=10), nullable=False),
        sa.Column("breach_date", sa.Date(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("pwn_count", sa.BigInteger(), nullable=True),
        sa.Column(
            "data_classes",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_breaches"),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["services.id"],
            name="fk_breaches_service_id_services",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "service_id",
            "source",
            "external_name",
            name="uq_breaches_external",
        ),
        sa.CheckConstraint("source IN ('hibp')", name="ck_breaches_source"),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_breaches_severity",
        ),
        sa.CheckConstraint("pwn_count >= 0", name="ck_breaches_pwn_count"),
        sa.CheckConstraint(
            "jsonb_typeof(data_classes) = 'array'",
            name="ck_breaches_data_classes",
        ),
    )
    op.create_index(
        "ix_breaches_service_published",
        "breaches",
        ["service_id", sa.text("published_at DESC")],
    )
    op.create_table(
        "outbox_events",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_outbox_events"),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["services.id"],
            name="fk_outbox_events_service_id_services",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "event_type ~ '^[a-z_]+(\\.[a-z_]+)+$'",
            name="ck_outbox_events_event_type",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(payload) = 'object'",
            name="ck_outbox_events_payload",
        ),
    )
    op.create_index(
        "ix_outbox_events_unpublished",
        "outbox_events",
        ["id"],
        postgresql_where=sa.text("published_at IS NULL"),
    )
    op.execute(_SERVICE_OVERVIEW)


def downgrade() -> None:
    op.execute("DROP VIEW service_overview")
    op.drop_table("outbox_events")
    op.drop_table("breaches")
    op.drop_table("incidents")
    op.drop_table("service_cards")
    op.drop_table("check_attempts")
    op.drop_table("check_states")
    op.drop_table("checks")
    op.drop_table("services")
