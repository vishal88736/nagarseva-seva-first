"""The restrictive CI fixture keeps every current module and runtime dependency."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('permission_fixture', ROOT / '.github/scripts/build_permission_fixture.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


def test_only_readability_repair_is_removed_from_complete_current_dockerfile():
    production = (ROOT / 'deploy/aws/Dockerfile').read_text()
    broken = fixture.restrictive_fixture(production)
    assert broken != production
    assert production == broken.replace('USER 10001:10001\n', fixture.REPAIR + 'USER 10001:10001\n', 1)
    for dependency in ('COPY nagarseva/model/api/ ./model/api/', 'requirements-urban.txt'):
        assert dependency in broken
    assert 'USER 10001:10001' in broken


@pytest.mark.parametrize('source', ['FROM scratch\nUSER 10001:10001\n', fixture.REPAIR * 2 + 'USER 10001:10001\n', 'USER 10001:10001\n' + fixture.REPAIR])
def test_unexpected_permission_repair_layout_fails_closed(source):
    with pytest.raises(ValueError):
        fixture.restrictive_fixture(source)
