import pytest

from data.constants import DRIFT_LOT_IDS, WO388_DATE
from agent.tools.charts import render_reflow_chart
from agent.tools.storage import get_local_path, put_bytes

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def test_put_bytes_round_trips_through_get_local_path_and_returns_the_url_shape():
    url = put_bytes(b"hello world", "tests/roundtrip.bin", "text/plain")
    assert url == "/api/files/tests/roundtrip.bin"
    assert get_local_path("tests/roundtrip.bin").read_bytes() == b"hello world"


def test_get_local_path_rejects_a_literal_traversal_key():
    with pytest.raises(ValueError):
        get_local_path("../../../etc/passwd")


def test_get_local_path_rejects_a_percent_decoded_traversal_key():
    """The exploit this guards against: FastAPI/Starlette decodes a request path like
    `/api/files/%2e%2e/%2e%2e/%2e%2e/pyproject.toml` before routing it to this
    function's `key` argument as `../../../pyproject.toml` -- i.e. by the time `key`
    reaches get_local_path, percent-encoding has already been stripped, so the
    traversal shows up here as a perfectly ordinary-looking `..` string. This test
    calls get_local_path with that already-decoded string directly -- the same value
    the percent-encoded request produces -- to prove the resolve()/is_relative_to
    check catches it regardless of how the `..` got there. The end-to-end version,
    hitting the route with the literal percent-encoded URL, lives in
    test_api_contract.py."""
    key = "%2e%2e/%2e%2e/%2e%2e/pyproject.toml".replace("%2e", ".")
    with pytest.raises(ValueError):
        get_local_path(key)


def test_render_reflow_chart_produces_a_real_png():
    url = render_reflow_chart(DRIFT_LOT_IDS, WO388_DATE, "WO-388 maintenance")
    key = url.removeprefix("/api/files/")
    path = get_local_path(key)
    data = path.read_bytes()
    assert data[:8] == PNG_MAGIC
    assert len(data) > 10_000  # a blank/failed render is well under this


def test_render_reflow_chart_is_content_addressed():
    """Same arguments -> same cache key -> same URL, so repeated calls for the same
    evidence (e.g. across hypotheses in one investigation) don't pile up duplicate
    files under different names."""
    url_a = render_reflow_chart(DRIFT_LOT_IDS, WO388_DATE, "WO-388 maintenance")
    url_b = render_reflow_chart(DRIFT_LOT_IDS, WO388_DATE, "WO-388 maintenance")
    assert url_a == url_b

    url_c = render_reflow_chart(DRIFT_LOT_IDS)  # different arguments -> different key
    assert url_c != url_a
