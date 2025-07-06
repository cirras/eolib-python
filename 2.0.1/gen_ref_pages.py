"""Generate the code reference pages and navigation."""

from pathlib import Path

import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()

for path in sorted(Path("src").rglob("*.py")):
    module_path = path.relative_to("src").with_suffix("")
    doc_path = path.relative_to("src").with_suffix(".md")
    full_doc_path = Path("reference", doc_path)

    reference_parts = tuple(module_path.parts)
    nav_key = reference_parts[1:]

    if reference_parts[-1] in ["__main__", "__about__"]:
        continue

    if reference_parts[-1] == "__init__":
        reference_parts = reference_parts[:-1]
        nav_key = nav_key[:-1]
        doc_path = doc_path.with_name("index.md")
        full_doc_path = full_doc_path.with_name("index.md")

    if not nav_key:
        continue

    nav[nav_key] = doc_path.as_posix()

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        ident = ".".join(reference_parts)
        fd.write(f"::: {ident}")

with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())
