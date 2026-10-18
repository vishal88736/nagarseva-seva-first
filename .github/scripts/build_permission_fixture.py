"""Build a current, complete Dockerfile fixture containing the original mode bug.

Only remove the application-readability repair. Using a historical Dockerfile with
current source omits modules added later and cannot test a permission-only repair.
"""
from pathlib import Path
import sys

REPAIR = "RUN chmod -R a+rX /app\n"


def restrictive_fixture(dockerfile: str) -> str:
    if dockerfile.splitlines(keepends=True).count(REPAIR) != 1:
        raise ValueError("Expected exactly one application readability repair.")
    if dockerfile.index(REPAIR) > dockerfile.index("USER 10001:10001"):
        raise ValueError("The readability repair must precede the runtime user.")
    return dockerfile.replace(REPAIR, "", 1)


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: build_permission_fixture.py SOURCE_DOCKERFILE OUTPUT_DOCKERFILE")
    source, destination = map(Path, sys.argv[1:])
    if source.resolve() == destination.resolve():
        raise SystemExit("The regression fixture must not overwrite the production Dockerfile.")
    destination.write_text(restrictive_fixture(source.read_text()))


if __name__ == "__main__":
    main()
