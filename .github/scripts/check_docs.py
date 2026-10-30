"""Check published Markdown links against Git's tree, not local runtime files."""
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
ENTRY_POINTS = {
    'README.md', 'nagarseva/README.md', 'prototype/README.md',
    'deploy/aws/README.md', 'deploy/vercel/README.md',
}


def documents(tracked):
    return sorted(name for name in tracked if name in ENTRY_POINTS or
                  (name.startswith('research/') and name.endswith('.md')))


def check_links(root, tracked, selected=None):
    root = Path(root).resolve()
    errors = []
    for name in documents(tracked) if selected is None else selected:
        file = root / name
        if not file.is_file():
            errors.append(f'{name}: document is missing')
            continue
        # Code examples are not rendered links. Validate actual Markdown links.
        text = re.sub(r'^```[^\n]*\n.*?^```\s*$', '', file.read_text(),
                      flags=re.MULTILINE | re.DOTALL)
        for target in re.findall(r'\]\(([^)]+)\)', text):
            target = target.split(' "', 1)[0].strip().strip('<>')
            if target.startswith(('http://', 'https://', 'mailto:', '#', '//')):
                continue
            location = unquote(target.split('#', 1)[0])
            try:
                resolved = (file.parent / location).resolve()
                relative = resolved.relative_to(root).as_posix()
            except ValueError:
                errors.append(f'{name}: link leaves repository: {target}')
                continue
            if relative not in tracked or not resolved.is_file():
                errors.append(f'{name}: link target is not a published file: {target}')
    return errors


def main():
    tracked = set(subprocess.check_output(
        ['git', 'ls-files', '-z'], cwd=ROOT).decode().rstrip('\0').split('\0'))
    errors = check_links(ROOT, tracked)
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        raise SystemExit(1)
    print(f'Checked {len(documents(tracked))} Markdown documents; '
          'all relative file links point to tracked files.')


if __name__ == '__main__':
    main()
