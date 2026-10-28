CREATE SCHEMA access;
CREATE SCHEMA source;
CREATE SCHEMA clinical;
CREATE SCHEMA ops;

CREATE TABLE access.projects (
 id uuid PRIMARY KEY, name text NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE access.users (
 id uuid PRIMARY KEY, issuer text NOT NULL, subject text NOT NULL,
 UNIQUE(issuer, subject)
);
CREATE TABLE access.memberships (
 project_id uuid NOT NULL REFERENCES access.projects(id),
 user_id uuid NOT NULL REFERENCES access.users(id),
 role text NOT NULL CHECK(role IN ('viewer','editor','admin')),
 PRIMARY KEY(project_id,user_id)
);
CREATE TABLE source.research_patients (
 id uuid PRIMARY KEY, project_id uuid NOT NULL REFERENCES access.projects(id),
 display_code text NOT NULL, data_revision bigint NOT NULL DEFAULT 1 CHECK(data_revision>0),
 UNIQUE(project_id,id), UNIQUE(project_id,display_code)
);
CREATE TABLE source.timeline_origins (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
 reference_meaning text NOT NULL CHECK(length(reference_meaning)>0),
 time_domain text NOT NULL CHECK(time_domain IN ('source_calendar','source_shifted','source_relative','simulation')),
 recorded_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(project_id,patient_id) REFERENCES source.research_patients(project_id,id),
 UNIQUE(project_id,patient_id,id,time_domain)
);
CREATE TABLE clinical.time_references (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
 basis text NOT NULL CHECK(basis IN ('timestamp','date','relative_day','unknown')),
 time_domain text NOT NULL CHECK(time_domain IN ('source_calendar','source_shifted','source_relative','simulation')),
 timestamp_value timestamptz, date_value date, relative_day numeric(12,4),
 timeline_origin_id uuid, missing_reason text,
 FOREIGN KEY(project_id,patient_id) REFERENCES source.research_patients(project_id,id),
 FOREIGN KEY(project_id,patient_id,timeline_origin_id,time_domain) REFERENCES source.timeline_origins(project_id,patient_id,id,time_domain),
 CHECK((basis='timestamp' AND timestamp_value IS NOT NULL AND date_value IS NULL AND relative_day IS NULL AND timeline_origin_id IS NULL AND missing_reason IS NULL AND time_domain<>'source_relative')
 OR (basis='date' AND date_value IS NOT NULL AND timestamp_value IS NULL AND relative_day IS NULL AND timeline_origin_id IS NULL AND missing_reason IS NULL AND time_domain<>'source_relative')
 OR (basis='relative_day' AND relative_day IS NOT NULL AND timeline_origin_id IS NOT NULL AND timestamp_value IS NULL AND date_value IS NULL AND missing_reason IS NULL AND time_domain IN ('source_relative','simulation') AND relative_day::text NOT IN ('NaN','Infinity','-Infinity'))
 OR (basis='unknown' AND timestamp_value IS NULL AND date_value IS NULL AND relative_day IS NULL AND timeline_origin_id IS NULL AND missing_reason IS NOT NULL AND missing_reason IN ('unknown','not_recorded','not_collected','not_applicable','below_detection','withheld')))
);
CREATE TABLE source.patient_revisions (
 project_id uuid NOT NULL, patient_id uuid NOT NULL, revision bigint NOT NULL CHECK(revision>0),
 input_manifest jsonb NOT NULL CHECK(jsonb_typeof(input_manifest)='object'),
 input_hash text NOT NULL CHECK(input_hash ~ '^[0-9a-f]{64}$'),
 recorded_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(project_id,patient_id,revision),
 FOREIGN KEY(project_id,patient_id) REFERENCES source.research_patients(project_id,id)
);
CREATE TABLE ops.artifacts (
 id uuid PRIMARY KEY, project_id uuid NOT NULL REFERENCES access.projects(id), patient_id uuid,
 object_key text NOT NULL UNIQUE, object_version text NOT NULL, byte_size bigint NOT NULL CHECK(byte_size>=0),
 sha256 text NOT NULL CHECK(sha256 ~ '^[0-9a-f]{64}$'),
 provenance text NOT NULL CHECK(provenance IN ('REAL_OBSERVED','REAL_DERIVED','SYNTHETIC_GENERATED','INTERPOLATED','MODEL_PREDICTED')),
 availability text NOT NULL CHECK(availability IN ('quarantined','verified','unavailable')),
 fixture_origin text NOT NULL DEFAULT 'ENGINEERING_ONLY_NONCLINICAL' CHECK(fixture_origin='ENGINEERING_ONLY_NONCLINICAL'),
 recorded_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(project_id,id),
 FOREIGN KEY(project_id,patient_id) REFERENCES source.research_patients(project_id,id)
);
CREATE TABLE ops.jobs (
 id uuid PRIMARY KEY, project_id uuid NOT NULL REFERENCES access.projects(id), patient_id uuid,
 kind text NOT NULL CHECK(kind='engineering.digest'),
 input_manifest jsonb NOT NULL, input_hash text NOT NULL CHECK(input_hash ~ '^[0-9a-f]{64}$'),
 status text NOT NULL CHECK(status IN ('queued','running','succeeded','failed','cancelled')),
 cancel_requested boolean NOT NULL DEFAULT false, lease_token uuid,
 attempt_count integer NOT NULL DEFAULT 0 CHECK(attempt_count BETWEEN 0 AND 3),
 result_hash text CHECK(result_hash ~ '^[0-9a-f]{64}$'), result_artifact_id uuid,
 publication_status text NOT NULL DEFAULT 'draft' CHECK(publication_status IN ('draft','ready')),
 created_at timestamptz NOT NULL DEFAULT now(), finished_at timestamptz,
 UNIQUE(project_id,id),
 FOREIGN KEY(project_id,patient_id) REFERENCES source.research_patients(project_id,id),
 FOREIGN KEY(project_id,result_artifact_id) REFERENCES ops.artifacts(project_id,id)
);
CREATE TABLE ops.job_attempts (
 job_id uuid NOT NULL REFERENCES ops.jobs(id), attempt_number integer NOT NULL,
 lease_token uuid NOT NULL, outcome text NOT NULL,
 PRIMARY KEY(job_id,attempt_number)
);
CREATE TABLE ops.outbox (
 id uuid PRIMARY KEY, job_id uuid NOT NULL UNIQUE REFERENCES ops.jobs(id),
 delivered_at timestamptz, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE ops.audit_events (
 id uuid PRIMARY KEY, project_id uuid NOT NULL REFERENCES access.projects(id),
 event_code text NOT NULL, target_id uuid NOT NULL, recorded_at timestamptz NOT NULL DEFAULT now()
);
CREATE FUNCTION source.reject_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'APPEND_ONLY'; END $$;
CREATE TRIGGER revisions_append_only BEFORE UPDATE OR DELETE ON source.patient_revisions
 FOR EACH ROW EXECUTE FUNCTION source.reject_mutation();
CREATE TRIGGER origins_immutable BEFORE UPDATE OR DELETE ON source.timeline_origins
 FOR EACH ROW EXECUTE FUNCTION source.reject_mutation();
CREATE TRIGGER times_immutable BEFORE UPDATE OR DELETE ON clinical.time_references
 FOR EACH ROW EXECUTE FUNCTION source.reject_mutation();
CREATE TRIGGER audit_append_only BEFORE UPDATE OR DELETE ON ops.audit_events
 FOR EACH ROW EXECUTE FUNCTION source.reject_mutation();
CREATE FUNCTION source.reject_owner_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN IF NEW.project_id IS DISTINCT FROM OLD.project_id OR NEW.id IS DISTINCT FROM OLD.id
THEN RAISE EXCEPTION 'IMMUTABLE_OWNERSHIP'; END IF; RETURN NEW; END $$;
CREATE TRIGGER patient_owner_immutable BEFORE UPDATE ON source.research_patients
 FOR EACH ROW EXECUTE FUNCTION source.reject_owner_change();
CREATE FUNCTION ops.protect_job_input() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN IF NEW.input_manifest IS DISTINCT FROM OLD.input_manifest OR NEW.input_hash IS DISTINCT FROM OLD.input_hash
 OR NEW.project_id IS DISTINCT FROM OLD.project_id OR NEW.patient_id IS DISTINCT FROM OLD.patient_id
THEN RAISE EXCEPTION 'IMMUTABLE_JOB_INPUT'; END IF; RETURN NEW; END $$;
CREATE TRIGGER immutable_job_input BEFORE UPDATE ON ops.jobs FOR EACH ROW EXECUTE FUNCTION ops.protect_job_input();
CREATE INDEX jobs_status ON ops.jobs(status,created_at);
CREATE INDEX outbox_pending ON ops.outbox(created_at) WHERE delivered_at IS NULL;
