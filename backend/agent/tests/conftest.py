"""Shared pytest fixtures for agent tests."""
import pytest


@pytest.fixture(autouse=True)
def _reset_id_counters():
    """agent.state's id counters are module-level itertools.count objects that persist
    across tests in one process. Reset before every test so no test's counter advances
    depend on execution order."""
    from agent.state import reset_counters
    reset_counters()
    yield
