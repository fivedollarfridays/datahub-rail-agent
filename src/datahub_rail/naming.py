"""Turn a DataHub dataset name into a safe, flat outbox filename component.

Dataset names in a real estate are frequently path-shaped
(``data/voice/fingerprint.json``) rather than flat table names
(``demo.public.orders_archive``). Interpolating one straight into an outbox
path makes the separators real: the write targets a directory that was never
created and the run dies with ``FileNotFoundError`` after all the probe work
is done but before any of it is printed.

The slug is **identity for any name already built from safe characters**, so
the verified demo estate and the committed ``sample-outputs/`` keep exactly
the filenames they have today.
"""
import hashlib
import re

#: Characters kept verbatim. Everything else is a separator or is unsafe on
#: some filesystem, so it collapses to `_UNSAFE_DELIMITER`.
_UNSAFE_RUN = re.compile(r"[^A-Za-z0-9._-]+")

_UNSAFE_DELIMITER = "-"

#: Leaves room for the ``incident_``/``schema_patch_`` prefix, the run
#: timestamp and the extension inside the common 255-byte filename limit.
_MAX_LENGTH = 120

_FALLBACK = "dataset"


def slugify_dataset_name(name: str) -> str:
    """Return `name` as a single safe path component.

    Each run of unsafe characters becomes one ``-``. Names already composed
    of ``[A-Za-z0-9._-]`` are returned unchanged, which is what keeps the
    demo's committed sample outputs stable. Overlong names are truncated and
    suffixed with a digest of the original so two long names cannot collide
    onto the same report file.
    """
    slug = _UNSAFE_RUN.sub(_UNSAFE_DELIMITER, name)
    if not slug.strip(f"{_UNSAFE_DELIMITER}."):
        return _FALLBACK
    if len(slug) > _MAX_LENGTH:
        digest = hashlib.blake2b(name.encode("utf-8"), digest_size=4).hexdigest()
        keep = _MAX_LENGTH - len(digest) - 1
        slug = f"{slug[:keep]}{_UNSAFE_DELIMITER}{digest}"
    return slug
