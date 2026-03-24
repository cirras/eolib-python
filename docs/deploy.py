from __future__ import annotations

import argparse
import gzip
import importlib.metadata
import json
import posixpath
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath


DOCS_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = DOCS_ROOT.parent
BUILD_ROOT = DOCS_ROOT / "_build"
HTML_ROOT = BUILD_ROOT / "deploy-html"
PAGES_WORKTREE = BUILD_ROOT / "gh-pages"
SRC_ROOT = PROJECT_ROOT / "src"
PACKAGE_ROOT = SRC_ROOT / "eolib"

MKDOCS_BUILDER = "mkdocs"
SPHINX_BUILDER = "sphinx"
SITE_URL = "https://cirras.github.io/eolib-python"


def run(*args: str, cwd: Path | None = None) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def capture(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(
        args,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def write_redirect(path: Path, target: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "<!DOCTYPE html>",
                "<html lang=\"en\">",
                "  <head>",
                "    <meta charset=\"utf-8\">",
                "    <script>",
                f"      const target = new URL({json.dumps(target)}, window.location.href);",
                "      if (window.location.hash) {",
                "        target.hash = window.location.hash;",
                "      }",
                "      window.location.replace(target.toString());",
                "    </script>",
                f"    <meta http-equiv=\"refresh\" content=\"0; url={target}\">",
                f"    <link rel=\"canonical\" href=\"{target}\">",
                "    <title>Redirecting...</title>",
                "  </head>",
                "  <body>",
                f"    <p>Redirecting to <a href=\"{target}\">{target}</a>.</p>",
                "  </body>",
                "</html>",
                "",
            ]
        ),
        encoding="utf-8",
    )


def infer_builder(version: str, path: Path) -> str:
    if (path / version / "reference" / "eolib.html").exists():
        return SPHINX_BUILDER
    return MKDOCS_BUILDER


def load_versions(path: Path) -> list[dict[str, object]]:
    versions_path = path / "versions.json"
    if not versions_path.exists():
        return []

    try:
        data = json.loads(versions_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list):
        return []

    versions: list[dict[str, object]] = []
    for item in data:
        if not isinstance(item, dict):
            continue

        version = item.get("version")
        title = item.get("title")
        aliases = item.get("aliases", [])
        builder = item.get("builder")

        if (
            not isinstance(version, str)
            or not isinstance(title, str)
            or not isinstance(builder, str)
            or not isinstance(aliases, list)
            or builder not in {MKDOCS_BUILDER, SPHINX_BUILDER}
            or not all(isinstance(alias, str) for alias in aliases)
        ):
            continue

        versions.append(
            {"version": version, "title": title, "aliases": aliases, "builder": builder}
        )

    return versions


def write_versions(path: Path, versions: list[dict[str, object]]) -> None:
    (path / "versions.json").write_text(json.dumps(versions, indent=2) + "\n", encoding="utf-8")


def remove_path(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def replace_directory(source: Path, destination: Path) -> None:
    remove_path(destination)
    shutil.copytree(source, destination)


def version_base_url(version_name: str) -> str:
    return f"{SITE_URL}/{version_name}/"


def html_file_url(relative_path: PurePosixPath, base_url: str) -> str:
    if relative_path == PurePosixPath("index.html"):
        return base_url
    if relative_path.name == "index.html":
        return f"{base_url}{relative_path.parent.as_posix().rstrip('/')}/"
    return f"{base_url}{relative_path.as_posix()}"


def write_sitemap(version_dir: Path, version_name: str) -> None:
    base_url = version_base_url(version_name)
    html_pages = sorted(
        page.relative_to(version_dir) for page in version_dir.rglob("*.html") if page.is_file()
    )
    lastmod = datetime.now(UTC).date().isoformat()
    urls = [
        "\n".join(
            [
                "    <url>",
                f"         <loc>{html_file_url(page, base_url)}</loc>",
                f"         <lastmod>{lastmod}</lastmod>",
                "    </url>",
            ]
        )
        for page in html_pages
    ]
    sitemap = "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
            *urls,
            "</urlset>",
            "",
        ]
    )
    (version_dir / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    with gzip.open(version_dir / "sitemap.xml.gz", "wt", encoding="utf-8", newline="") as handle:
        handle.write(sitemap)


def update_versions(
    existing_versions: list[dict[str, object]], version: str, aliases: list[str], pages_root: Path
) -> list[dict[str, object]]:
    claimed_aliases = set(aliases)
    updated_versions: list[dict[str, object]] = [
        {"version": version, "title": version, "aliases": aliases, "builder": SPHINX_BUILDER},
    ]

    for entry in existing_versions:
        existing_version = entry["version"]
        if existing_version == version:
            continue
        if not (pages_root / existing_version).exists():
            continue

        existing_aliases = [alias for alias in entry["aliases"] if alias not in claimed_aliases]
        updated_versions.append(
            {
                "version": existing_version,
                "title": entry["title"],
                "aliases": existing_aliases,
                "builder": entry.get("builder", infer_builder(existing_version, pages_root)),
            }
        )

    return updated_versions


def head_commit_sha() -> str:
    return capture("git", "rev-parse", "--short", "HEAD", cwd=PROJECT_ROOT)


def sphinx_version() -> str:
    return importlib.metadata.version("sphinx")


def deploy_commit_message(version: str) -> str:
    return f"Deployed {head_commit_sha()} to {version} with Sphinx {sphinx_version()}"


def iter_package_names(root_name: str, root_dir: Path, include_private: bool = False) -> list[str]:
    packages: list[str] = []

    def walk(package_name: str, package_dir: Path) -> None:
        packages.append(package_name)
        for child in sorted(package_dir.iterdir()):
            if not child.is_dir():
                continue
            if child.name.startswith("_") and not include_private:
                continue
            if not (child / "__init__.py").exists():
                continue
            walk(f"{package_name}.{child.name}", child)

    walk(root_name, root_dir)
    return packages


def iter_module_names(root_name: str, root_dir: Path, include_private: bool = False) -> list[str]:
    modules: list[str] = []

    def walk(package_name: str, package_dir: Path) -> None:
        for child in sorted(package_dir.glob("*.py")):
            if child.stem in {"__init__", "__about__"} or child.stem.startswith("_"):
                continue
            modules.append(f"{package_name}.{child.stem}")

        for child in sorted(package_dir.iterdir()):
            if not child.is_dir():
                continue
            if child.name.startswith("_") and not include_private:
                continue
            if not (child / "__init__.py").exists():
                continue
            walk(f"{package_name}.{child.name}", child)

    walk(root_name, root_dir)
    return modules


def public_protocol_name(name: str) -> str:
    return name.replace("eolib.protocol._generated", "eolib.protocol", 1)


def mkdocs_reference_path(name: str) -> PurePosixPath:
    return PurePosixPath("reference", *name.split("."), "index.html")


def sphinx_reference_path(package_name: str) -> PurePosixPath:
    return PurePosixPath("reference", f"{package_name}.html")


def containing_public_package(module_name: str, public_packages: set[str]) -> str | None:
    candidate = public_protocol_name(module_name).rsplit(".", 1)[0]

    while True:
        if candidate in public_packages:
            return candidate
        if "." not in candidate:
            return None
        candidate = candidate.rsplit(".", 1)[0]


def iter_mkdocs_compatibility_redirects() -> list[tuple[PurePosixPath, PurePosixPath]]:
    redirects: dict[PurePosixPath, PurePosixPath] = {
        PurePosixPath("reference", "SUMMARY", "index.html"): PurePosixPath(
            "reference", "eolib.html"
        ),
    }

    public_packages = iter_package_names("eolib", PACKAGE_ROOT)
    public_package_set = set(public_packages)
    generated_root = PACKAGE_ROOT / "protocol" / "_generated"
    generated_packages = iter_package_names("eolib.protocol._generated", generated_root)
    public_modules = iter_module_names("eolib", PACKAGE_ROOT)
    generated_modules = iter_module_names("eolib.protocol._generated", generated_root)

    for package_name in public_packages:
        redirects[mkdocs_reference_path(package_name)] = sphinx_reference_path(package_name)

    for package_name in generated_packages:
        public_name = public_protocol_name(package_name)
        if public_name in public_package_set:
            redirects[mkdocs_reference_path(package_name)] = sphinx_reference_path(public_name)

    for module_name in public_modules + generated_modules:
        package_name = containing_public_package(module_name, public_package_set)
        if package_name is None:
            continue
        redirects[mkdocs_reference_path(module_name)] = sphinx_reference_path(package_name)

    return sorted(redirects.items(), key=lambda item: item[0].as_posix())


def add_mkdocs_compatibility_redirects(output_dir: Path) -> None:
    for legacy_path, target_path in iter_mkdocs_compatibility_redirects():
        destination = output_dir.joinpath(*legacy_path.parts)
        relative_target = posixpath.relpath(target_path.as_posix(), legacy_path.parent.as_posix())
        write_redirect(destination, relative_target)


def ensure_worktree() -> None:
    if PAGES_WORKTREE.exists():
        try:
            run("git", "worktree", "remove", "--force", str(PAGES_WORKTREE), cwd=PROJECT_ROOT)
        except subprocess.CalledProcessError:
            shutil.rmtree(PAGES_WORKTREE, ignore_errors=True)

    has_remote_branch = (
        subprocess.run(
            ["git", "show-ref", "--verify", "--quiet", "refs/remotes/origin/gh-pages"],
            cwd=PROJECT_ROOT,
            check=False,
        ).returncode
        == 0
    )

    if has_remote_branch:
        run(
            "git",
            "worktree",
            "add",
            "--force",
            "-B",
            "gh-pages",
            str(PAGES_WORKTREE),
            "origin/gh-pages",
            cwd=PROJECT_ROOT,
        )
    else:
        run(
            "git",
            "worktree",
            "add",
            "--orphan",
            "-B",
            "gh-pages",
            str(PAGES_WORKTREE),
            cwd=PROJECT_ROOT,
        )


def build_docs(output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)

    run("sphinx-build", "-b", "html", str(DOCS_ROOT), str(output_dir), cwd=PROJECT_ROOT)
    add_mkdocs_compatibility_redirects(output_dir)


def hash_symlink_target(target: str) -> str:
    return subprocess.run(
        ["git", "hash-object", "-w", "--stdin"],
        cwd=PAGES_WORKTREE,
        check=True,
        input=target,
        capture_output=True,
        text=True,
    ).stdout.strip()


def stage_alias_symlink(alias: str, target_version: str) -> None:
    alias_path = PAGES_WORKTREE / alias
    remove_path(alias_path)
    blob = hash_symlink_target(target_version)
    run(
        "git",
        "update-index",
        "--add",
        "--cacheinfo",
        f"120000,{blob},{alias}",
        cwd=PAGES_WORKTREE,
    )
    run("git", "checkout-index", "-f", "--", alias, cwd=PAGES_WORKTREE)


def deploy(version: str, aliases: list[str]) -> None:
    BUILD_ROOT.mkdir(exist_ok=True)
    ensure_worktree()
    build_docs(HTML_ROOT)

    existing_versions = load_versions(PAGES_WORKTREE)
    unique_aliases = list(dict.fromkeys(alias for alias in aliases if alias != version))

    replace_directory(HTML_ROOT, PAGES_WORKTREE / version)
    write_sitemap(PAGES_WORKTREE / version, version)

    for alias in unique_aliases:
        remove_path(PAGES_WORKTREE / alias)

    known_versions = {entry["version"] for entry in existing_versions}
    stale_aliases = {alias for entry in existing_versions for alias in entry["aliases"]} - set(
        unique_aliases
    )
    for stale_alias in stale_aliases:
        if stale_alias in known_versions:
            continue
        remove_path(PAGES_WORKTREE / stale_alias)

    redirect_target = f"{unique_aliases[0]}/" if unique_aliases else f"{version}/"
    write_redirect(PAGES_WORKTREE / "index.html", redirect_target)
    write_versions(
        PAGES_WORKTREE, update_versions(existing_versions, version, unique_aliases, PAGES_WORKTREE)
    )
    (PAGES_WORKTREE / ".nojekyll").write_text("", encoding="utf-8")

    run("git", "add", "--all", cwd=PAGES_WORKTREE)
    for alias in unique_aliases:
        stage_alias_symlink(alias, version)

    has_changes = (
        subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=PAGES_WORKTREE,
            check=False,
        ).returncode
        != 0
    )
    if not has_changes:
        return

    run("git", "commit", "-m", deploy_commit_message(version), cwd=PAGES_WORKTREE)


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description="Build and deploy Sphinx docs to gh-pages.")
    parser.add_argument("version", help="Version directory to publish.")
    parser.add_argument("aliases", nargs="*", help="Alias directories to update, e.g. latest.")
    args = parser.parse_args(argv)

    deploy(args.version, args.aliases)


if __name__ == "__main__":
    main(sys.argv[1:])
