"""A local screenshot must never hide a broken link in the published checkout."""
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/check_docs.py'
spec = importlib.util.spec_from_file_location('check_docs', SCRIPT)
docs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(docs)


def test_ignored_gallery_is_rejected_even_when_it_exists_locally(tmp_path):
    (tmp_path / 'research').mkdir()
    (tmp_path / '.runtime').mkdir()
    (tmp_path / '.runtime/gallery.html').write_text('Local screenshots')
    (tmp_path / 'research/audit.md').write_text('[Gallery](../.runtime/gallery.html)')
    errors = docs.check_links(tmp_path, {'research/audit.md'})
    assert len(errors) == 1 and 'not a published file' in errors[0]


def test_real_relative_link_and_encoded_path_work(tmp_path):
    (tmp_path / 'research').mkdir()
    (tmp_path / 'research/a b.md').write_text('# Findings')
    (tmp_path / 'README.md').write_text('[Findings](research/a%20b.md#findings)')
    assert docs.check_links(tmp_path, {'README.md', 'research/a b.md'}) == []


def test_missing_target_and_repository_escape_are_reported(tmp_path):
    (tmp_path / 'README.md').write_text('[Missing](missing.md) [Escape](../outside.md)')
    errors = docs.check_links(tmp_path, {'README.md', 'missing.md'})
    assert len(errors) == 2
    assert 'not a published file' in errors[0]
    assert 'leaves repository' in errors[1]


def test_external_links_anchors_and_code_examples_are_not_local_files(tmp_path):
    (tmp_path / 'README.md').write_text(
        '[Web](https://example.org/source) [Section](#section)\n'
        '```text\n[Example](untracked.md)\n```\n')
    assert docs.check_links(tmp_path, {'README.md'}) == []


def test_missing_document_is_reported_and_archives_are_selected_explicitly(tmp_path):
    tracked = {'README.md', 'research/audit.md', 'deploy/aws/README.md',
               'nagarseva/README.md', 'unrelated/archive.md'}
    assert docs.documents(tracked) == ['README.md', 'deploy/aws/README.md',
                                      'nagarseva/README.md', 'research/audit.md']
    assert docs.check_links(tmp_path, {'README.md'}) == ['README.md: document is missing']
