"""The linked public template is deliverable; private runtime files never are."""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'prepare_pack.py'
spec = importlib.util.spec_from_file_location('prepare_pack', SCRIPT)
pack = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pack)


@pytest.fixture
def repository(tmp_path, monkeypatch):
    monkeypatch.setattr(pack, 'ROOT', tmp_path)
    return tmp_path


def test_explicit_public_root_template_accepts_blank_credentials(repository):
    template = repository / '.env.example'
    template.write_text('# Public example\nNAGARSEVA_OFFICER_KEY=\nNAGARSEVA_MODE=pilot-prototype\nAPI_TOKEN=""\n')
    assert pack.public_file(template)


@pytest.mark.parametrize('assignment', ['NAGARSEVA_OFFICER_KEY=private-value', 'API_TOKEN=private-value', 'DB_PASSWORD=private-value', 'export API_TOKEN='])
def test_populated_credentials_and_shell_assignments_fail_closed(repository, assignment):
    template = repository / '.env.example'
    template.write_text(assignment + '\n')
    with pytest.raises(ValueError, match='template'):
        pack.public_file(template)


@pytest.mark.parametrize('name', ['.env', '.env.local', '.env.production', 'nested/.env.example', '.aws/credentials', '.runtime/data.json', '.env.backup/config.txt'])
def test_other_environment_and_private_paths_are_never_packaged(repository, name):
    private = repository / name
    private.parent.mkdir(parents=True, exist_ok=True)
    private.write_text('private-value')
    assert not pack.public_file(private)


def test_symlink_cannot_pull_external_material_into_archive(repository, tmp_path_factory):
    secret = tmp_path_factory.mktemp('external') / 'private.txt'
    secret.write_text('private-value')
    alias = repository / 'public.txt'
    alias.symlink_to(secret)
    with pytest.raises(ValueError, match='inside the repository'):
        pack.public_file(alias)
