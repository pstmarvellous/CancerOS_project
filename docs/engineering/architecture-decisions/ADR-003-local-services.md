# ADR-003: native private local services

COS-012/013; selected for development, not production deployment.
Use existing PostgreSQL15 binaries with a new isolated cluster. Use SeaweedFS4.51
mini (one native process) for versioned private S3; official MinIO download returned
410. Redis Windows port8.10.3 provides native Redis transport; no service installed
globally and no original system service modified. All data/tools/config remain ignored.

Upstream actually inspected: SeaweedFS tag4.51 LICENSE (Apache2.0) and
weed/command/mini.go startup/auth/bind/port options. Supported S3 adapter API is
boto3 put/get/copy/versioning/presign. Actual version/privacy compatibility is checked
against the installed service. AWS S3 versioning documentation was read for explicit
bucket enablement and version-specific reads. No upstream source was copied.

References:
https://raw.githubusercontent.com/seaweedfs/seaweedfs/4.51/LICENSE
https://raw.githubusercontent.com/seaweedfs/seaweedfs/4.51/weed/command/mini.go
https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html
https://github.com/redis-windows/redis-windows/releases/tag/8.10.3

Redis port wrapper LICENSE is Apache2.0; this does not establish all bundled upstream
server/dependency redistribution rights. Local binaries are not vendored or published;
full license inventory and production platform review remain release work. Download
version/URLs/hashes are recorded by the bootstrap tool; artifacts fetched over official
HTTPS release URLs, not arbitrary mirrors. No models/datasets are included.

Academic/empirical medical reading is not applicable to infrastructure; no medical
algorithm is selected. Standards→inspected tagged interface→actual private service
test is the engineering decision chain. Domain scientific evidence remains absent.
