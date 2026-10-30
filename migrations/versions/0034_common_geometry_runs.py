"""Allow the common immutable run authority without weakening patient/branch ownership."""

from alembic import op

revision = "0034_common_geometry_runs"
down_revision = "0033_simulation_eligibility"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""ALTER TABLE imaging.synthetic_geometries
      DROP CONSTRAINT synthetic_geometries_project_id_patient_id_run_id_fkey,
      ADD CONSTRAINT synthetic_geometry_run_resource_fk FOREIGN KEY(project_id,patient_id,run_id)
      REFERENCES ops.resource_registry(project_id,patient_id,id)""")
    op.execute("""CREATE FUNCTION imaging.require_geometry_run() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN
        IF NOT EXISTS(SELECT 1 FROM imaging.simulation_fixture_runs
          WHERE id=NEW.run_id AND project_id=NEW.project_id AND patient_id=NEW.patient_id AND branch_id=NEW.branch_id)
          AND NOT EXISTS(SELECT 1 FROM imaging.simulation_runs
          WHERE id=NEW.run_id AND project_id=NEW.project_id AND patient_id=NEW.patient_id AND branch_id=NEW.branch_id)
        THEN RAISE EXCEPTION 'owned immutable geometry run required' USING ERRCODE='23503';
        END IF;
        RETURN NEW;
      END $$""")
    op.execute("""CREATE TRIGGER synthetic_geometry_run_authority BEFORE INSERT ON imaging.synthetic_geometries
      FOR EACH ROW EXECUTE FUNCTION imaging.require_geometry_run()""")


def downgrade():
    raise RuntimeError("Forward-only migration policy")
