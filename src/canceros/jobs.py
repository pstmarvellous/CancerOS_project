"""One harmless engineering digest workflow; not medical processing or publication."""

import hashlib
import json
from uuid import UUID, uuid4

from redis import Redis
from sqlalchemy import text

from canceros.persistence import canonical_bytes, science_hash
from canceros.settings import Settings
from canceros.storage import PrivateStorage

READY = "canceros:engineering:ready"
PROCESSING = "canceros:engineering:processing"


def queue_for(config: Settings):
    if not config.queue_url:
        raise ValueError("Queue configuration required")
    return Redis.from_url(
        config.queue_url.get_secret_value(),
        socket_connect_timeout=3,
        socket_timeout=3,
        decode_responses=True,
    )


def enqueue(engine, project_id, patient_id, label="engineering-only"):
    if len(label) > 100:
        raise ValueError("Engineering payload limit exceeded")
    identity = uuid4()
    manifest = {
        "fixture_origin": "ENGINEERING_ONLY_NONCLINICAL",
        "label": label,
        "schema_version": "digest/1",
    }
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO ops.jobs(id,project_id,patient_id,kind,input_manifest,input_hash,status) VALUES(:id,:p,:u,'engineering.digest',CAST(:m AS jsonb),:h,'queued')"
            ),
            {
                "id": identity,
                "p": project_id,
                "u": patient_id,
                "m": canonical_bytes(manifest).decode(),
                "h": science_hash(manifest),
            },
        )
        connection.execute(
            text("INSERT INTO ops.outbox(id,job_id) VALUES(:event,:job)"),
            {"event": uuid4(), "job": identity},
        )
        connection.execute(
            text(
                "INSERT INTO ops.audit_events(id,project_id,event_code,target_id) VALUES(:id,:p,'ENGINEERING_JOB_ENQUEUED',:target)"
            ),
            {"id": uuid4(), "p": project_id, "target": identity},
        )
    return identity


def dispatch(engine, queue, project_id=None):
    with engine.begin() as connection:
        clause = " AND j.project_id=:project" if project_id is not None else ""
        events = connection.execute(
            text(
                "SELECT o.id,o.job_id FROM ops.outbox o JOIN ops.jobs j ON j.id=o.job_id WHERE o.delivered_at IS NULL AND j.kind='engineering.digest'"
                + clause
                + " ORDER BY o.created_at FOR UPDATE OF o SKIP LOCKED LIMIT 25"
            ),
            {"project": project_id} if project_id is not None else {},
        ).all()
        for event in events:
            queue.lpush(READY, str(event.job_id))
            connection.execute(
                text("UPDATE ops.outbox SET delivered_at=now() WHERE id=:id"), {"id": event.id}
            )
    return len(events)


def recover(engine, queue):
    # SQL decides recoverability. Redis processing IDs are transport bookkeeping.
    recovered = 0
    for identity in queue.lrange(PROCESSING, 0, -1):
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT kind,status,leased_until IS NULL OR leased_until<now() AS expired FROM ops.jobs WHERE id=:id"
                ),
                {"id": UUID(identity)},
            ).one_or_none()
        if (
            row is None
            or row.kind != "engineering.digest"
            or row.status in ("succeeded", "failed", "cancelled")
        ):
            queue.lrem(PROCESSING, 0, identity)
        elif row.status == "queued" or row.expired:
            queue.lrem(PROCESSING, 0, identity)
            queue.lpush(READY, identity)
            recovered += 1
    return recovered


def process_one(engine, queue, storage: PrivateStorage, config: Settings):
    raw = queue.rpoplpush(READY, PROCESSING)
    if raw is None:
        return None
    identity = UUID(raw)
    token = uuid4()
    with engine.begin() as connection:
        row = connection.execute(
            text(
                "SELECT *,leased_until IS NULL OR leased_until<now() AS expired FROM ops.jobs WHERE id=:id FOR UPDATE"
            ),
            {"id": identity},
        ).one_or_none()
        if (
            row is None
            or row.kind != "engineering.digest"
            or row.status in ("succeeded", "failed", "cancelled")
        ):
            queue.lrem(PROCESSING, 0, raw)
            return identity
        if row.cancel_requested:
            connection.execute(
                text("UPDATE ops.jobs SET status='cancelled',finished_at=now() WHERE id=:id"),
                {"id": identity},
            )
            queue.lrem(PROCESSING, 0, raw)
            return identity
        if row.status == "running" and not row.expired:
            return None
        if row.attempt_count >= config.job_max_attempts:
            connection.execute(
                text("UPDATE ops.jobs SET status='failed',finished_at=now() WHERE id=:id"),
                {"id": identity},
            )
            queue.lrem(PROCESSING, 0, raw)
            return identity
        manifest = row.input_manifest
        if (
            science_hash(manifest) != row.input_hash
            or manifest.get("fixture_origin") != "ENGINEERING_ONLY_NONCLINICAL"
        ):
            connection.execute(
                text("UPDATE ops.jobs SET status='failed',finished_at=now() WHERE id=:id"),
                {"id": identity},
            )
            queue.lrem(PROCESSING, 0, raw)
            return identity
        attempt = row.attempt_count + 1
        project_id = row.project_id
        patient_id = row.patient_id
        connection.execute(
            text(
                "UPDATE ops.jobs SET status='running',lease_token=:t,leased_until=now()+interval '120 seconds',attempt_count=:attempt WHERE id=:id"
            ),
            {"id": identity, "t": token, "attempt": attempt},
        )
        connection.execute(
            text(
                "INSERT INTO ops.job_attempts(job_id,attempt_number,lease_token,outcome) VALUES(:id,:a,:t,'running')"
            ),
            {"id": identity, "a": attempt, "t": token},
        )
    try:
        result_hash = hashlib.sha256(canonical_bytes(manifest)).hexdigest()
        artifact = storage.write_verified(
            project_id,
            json.dumps(
                {"fixture_origin": "ENGINEERING_ONLY_NONCLINICAL", "digest": result_hash},
                sort_keys=True,
            ).encode(),
        )
        artifact_id = uuid4()
        with engine.begin() as connection:
            current = connection.execute(
                text(
                    "SELECT lease_token,cancel_requested,status FROM ops.jobs WHERE id=:id FOR UPDATE"
                ),
                {"id": identity},
            ).one()
            if current.lease_token != token or current.status != "running":
                raise ValueError("STALE_WORKER_LEASE")
            if current.cancel_requested:
                connection.execute(
                    text("UPDATE ops.jobs SET status='cancelled',finished_at=now() WHERE id=:id"),
                    {"id": identity},
                )
            else:
                connection.execute(
                    text(
                        "INSERT INTO ops.artifacts(id,project_id,patient_id,object_key,object_version,byte_size,sha256,provenance,availability) VALUES(:id,:p,:u,:key,:version,:size,:hash,'SYNTHETIC_GENERATED','verified')"
                    ),
                    {
                        "id": artifact_id,
                        "p": project_id,
                        "u": patient_id,
                        "key": artifact.key,
                        "version": artifact.version,
                        "size": artifact.byte_size,
                        "hash": artifact.sha256,
                    },
                )
                connection.execute(
                    text(
                        "UPDATE ops.jobs SET status='succeeded',result_hash=:h,result_artifact_id=:a,publication_status='ready',finished_at=now() WHERE id=:id"
                    ),
                    {"h": result_hash, "a": artifact_id, "id": identity},
                )
                connection.execute(
                    text(
                        "INSERT INTO ops.audit_events(id,project_id,event_code,target_id) VALUES(:id,:p,'ENGINEERING_RESULT_READY',:target)"
                    ),
                    {"id": uuid4(), "p": project_id, "target": identity},
                )
            connection.execute(
                text(
                    "UPDATE ops.job_attempts SET outcome='completed' WHERE job_id=:id AND attempt_number=:a"
                ),
                {"id": identity, "a": attempt},
            )
        queue.lrem(PROCESSING, 0, raw)
    except Exception:
        # Keep transport processing entry for bounded recovery; never log input or SDK errors.
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE ops.jobs SET leased_until=now()-interval '1 second' WHERE id=:id AND lease_token=:t AND status='running'"
                ),
                {"id": identity, "t": token},
            )
        raise RuntimeError("ENGINEERING_JOB_FAILED; retry via bounded recovery") from None
    return identity
