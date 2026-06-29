"""Optional GeoIP resolution (MaxMind GeoLite2-City).

If no database is configured or a lookup fails, geo is simply unknown — geo predicates
then fail closed (DESIGN §6). The raw IP is used only to derive coarse geo here; it is
never persisted.
"""

from __future__ import annotations

import os

try:
    import geoip2.database
    import geoip2.errors

    _HAVE_GEOIP2 = True
except ImportError:  # pragma: no cover - geoip2 is a declared dep, guard is defensive
    _HAVE_GEOIP2 = False


class GeoResolver:
    def __init__(self, db_path: str | None) -> None:
        self._reader = None
        if _HAVE_GEOIP2 and db_path and os.path.isfile(db_path):
            self._reader = geoip2.database.Reader(db_path)

    def __call__(self, ip: str | None) -> tuple[str | None, str | None]:
        if self._reader is None or not ip:
            return (None, None)
        try:
            resp = self._reader.city(ip)
        except Exception:
            return (None, None)
        return (resp.country.iso_code, resp.city.name)

    def close(self) -> None:
        if self._reader is not None:
            self._reader.close()
            self._reader = None
