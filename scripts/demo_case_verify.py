"""Verify one BreastDCEDL demonstration case offline (read-only, no DB writes).

Checks file identity, checksums, image/mask alignment, parser compatibility,
and pipeline staging limits for a paired subject, then writes a verification
record to docs/engineering/testing/browser-e2e/. Source files are never
modified. This script never provisions patient records: see the E2E-002 report
for why real bytes stay out of the dev database (bounded staging contract +
unconfirmed public-demo rights) and which explicitly synthetic fixture carries
the rendered browser demonstration.
"""

import argparse
import gzip
import hashlib
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Data_folder" / "Demo_data" / "BreastDCEDL_demo_data"

SUBJECTS = {
    "ISPY1_1001": ("ISPY1_1001_spy1_vis1_dce_aqc_0.nii.gz", "ISPY1_1001_spy1_vis1_mask.nii.gz"),
    "ISPY1_1002": ("ISPY1_1002_spy1_vis1_dce_aqc_0.nii.gz", "ISPY1_1002_spy1_vis1_mask.nii.gz"),
    "ISPY1_1003": ("ISPY1_1003_spy1_vis1_dce_aqc_0.nii.gz", "ISPY1_1003_spy1_vis1_mask.nii.gz"),
    "ACRIN-6698-102212": (
        "ACRIN-6698-102212_spy2_vis1_dce_aqc_0.nii.gz",
        "ACRIN-6698-102212_spy2_vis1_mask.nii.gz",
    ),
    "ACRIN-6698-103939": (
        "ACRIN-6698-103939_spy2_vis1_dce_aqc_0.nii.gz",
        "ACRIN-6698-103939_spy2_vis1_mask.nii.gz",
    ),
}

PUBLISHED_TARBALL_MD5 = "5b7d870130c9c3807f8d126f7ddcede"
STAGE_CONTRACT_CHARS = 900000


def read_header(raw: bytes) -> dict:
    return {
        "magic": raw[344:348].decode("latin1"),
        "extension": raw[348:352].hex(),
        "xyzt_units_code": raw[123],
        "vox_offset": struct.unpack("<f", raw[108:112])[0],
        "datatype": struct.unpack("<h", raw[70:72])[0],
        "bitpix": struct.unpack("<h", raw[72:74])[0],
    }


def main(subject: str) -> int:
    if subject not in SUBJECTS:
        print(f"unknown subject {subject}; choose from {sorted(SUBJECTS)}")
        return 2
    dce_name, mask_name = SUBJECTS[subject]
    dce_path, mask_path = DATA / "dce" / dce_name, DATA / "mask" / mask_name
    dce_gz, mask_gz = dce_path.read_bytes(), mask_path.read_bytes()
    dce_raw = gzip.decompress(dce_gz)
    mask_raw = gzip.decompress(mask_gz)

    import nibabel as nib
    import numpy as np

    dce_img = nib.Nifti1Image.from_bytes(dce_raw)
    mask_img = nib.Nifti1Image.from_bytes(mask_raw)
    dce_data = np.asarray(dce_img.dataobj)
    mask_data = np.asarray(mask_img.dataobj)
    labels = sorted(float(v) for v in np.unique(mask_data))
    voxels = int((mask_data > 0).sum())

    record = {
        "subject": subject,
        "files": {"dce": dce_name, "mask": mask_name},
        "sha256": {
            "dce_gz": hashlib.sha256(dce_gz).hexdigest(),
            "mask_gz": hashlib.sha256(mask_gz).hexdigest(),
        },
        "sizes": {"dce_gz": len(dce_gz), "mask_gz": len(mask_gz)},
        "geometry": {
            "dce_shape": list(dce_img.shape),
            "mask_shape": list(mask_img.shape),
            "shapes_match": dce_img.shape == mask_img.shape,
            "affine_match": bool(np.allclose(dce_img.affine, mask_img.affine)),
            "affine": dce_img.affine.tolist(),
            "mask_labels": labels,
            "mask_foreground_voxels": voxels,
        },
        "parser_compatibility": {
            "dce_header": read_header(dce_raw),
            "mask_header": read_header(mask_raw),
        },
        "staging_contract": {
            "contract_base64_char_limit": STAGE_CONTRACT_CHARS,
            "dce_base64_chars": (len(dce_gz) * 4 + 2) // 3,
            "mask_base64_chars": (len(mask_gz) * 4 + 2) // 3,
            "dce_fits_contract": (len(dce_gz) * 4 + 2) // 3 <= STAGE_CONTRACT_CHARS,
            "mask_fits_contract": (len(mask_gz) * 4 + 2) // 3 <= STAGE_CONTRACT_CHARS,
        },
        "rights": {
            "distribution_license": "CC BY-NC 4.0 as distributed in BreastDCEDL_demo_data.tar.gz",
            "tarball_md5_verified": hashlib.md5(
                (ROOT / "Data_folder" / "BreastDCEDL_demo_data.tar.gz").read_bytes()
            ).hexdigest()
            == PUBLISHED_TARBALL_MD5,
            "deidentification_report_found": False,
            "public_demo_permission_found": False,
        },
    }
    out = ROOT / "docs" / "engineering" / "testing" / "browser-e2e" / f"E2E-002-case-{subject}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(json.dumps(record, indent=2)[:1500])
    print(f"record={out}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", default="ISPY1_1001")
    sys.exit(main(parser.parse_args().subject))
