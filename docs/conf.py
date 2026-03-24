from __future__ import annotations

import importlib
import inspect
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from sphinx import addnodes
from sphinx.domains.python._annotations import _parse_annotation
from sphinx.errors import ExtensionError
from sphinx.util import inspect as sphinx_inspect
from sphinx.util.typing import stringify_annotation

DOCS_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = DOCS_ROOT.parent
SRC_ROOT = PROJECT_ROOT / "src"
PACKAGE_ROOT = SRC_ROOT / "eolib"

sys.path.insert(0, str(DOCS_ROOT))
sys.path.insert(0, str(SRC_ROOT))

from generated_protocol_typehints import GeneratedProtocolModuleFixer
from eolib.__about__ import __version__


REFERENCE_TITLE_SUFFIX_RE = re.compile(r"(eolib(?:\.[A-Za-z0-9_]+)*) (package|module)")
GENERATED_PROTOCOL_ANNOTATION_RE = re.compile(
    r"(?P<prefix>~?)"
    r"(?P<module>eolib\.protocol\._generated(?:\.[a-z_][a-z0-9_]*)+)"
    r"\.(?P<qualname>[A-Z][A-Za-z0-9_]*(?:\.[A-Z][A-Za-z0-9_]*)*)"
)
AUTODOC_TYPEHINTS_BUILTINS = (
    "bool",
    "bytearray",
    "bytes",
    "dict",
    "float",
    "int",
    "list",
    "object",
    "set",
    "str",
    "tuple",
)
BUILTIN_TYPE_ALIASES = {
    builtin: f":external+python:py:class:`{builtin}`" for builtin in AUTODOC_TYPEHINTS_BUILTINS
}
BUILTIN_TYPE_NAME_RE = re.compile(
    r"(?<![A-Za-z0-9_.])"
    r"(?P<name>bool|bytearray|bytes|dict|float|int|list|object|set|str|tuple)"
    r"(?![A-Za-z0-9_])"
)


def rewrite_public_protocol_paths(text: str) -> str:
    return text.replace("eolib.protocol._generated", "eolib.protocol").replace(
        r"eolib.protocol.\_generated", "eolib.protocol"
    )


def qualify_builtin_type_names(annotation: str) -> str:
    def replace(match: re.Match[str]) -> str:
        return BUILTIN_TYPE_ALIASES[match.group("name")]

    return BUILTIN_TYPE_NAME_RE.sub(replace, annotation)


def get_render_mode(typehints_format: str) -> str:
    if typehints_format == "short":
        return "smart"
    return "fully-qualified-except-typing"


def rewrite_public_protocol_annotation(annotation: str, fixer) -> str:
    def replace(match: re.Match[str]) -> str:
        fixed_module = fixer(match.group("module"))
        return f"{match.group('prefix')}{fixed_module}.{match.group('qualname')}"

    return GENERATED_PROTOCOL_ANNOTATION_RE.sub(replace, annotation)


def rewrite_annotation_targets(annotation: str, fixer) -> str:
    annotation = qualify_builtin_type_names(annotation)
    return rewrite_public_protocol_annotation(annotation, fixer)


def simplify_reference_labels(text: str) -> str:
    return REFERENCE_TITLE_SUFFIX_RE.sub(r"\1", text)


def package_dir_for(package_name: str) -> Path:
    return PACKAGE_ROOT.joinpath(*package_name.split(".")[1:])


def iter_public_packages() -> list[str]:
    packages: list[str] = []

    def walk(package_name: str, package_dir: Path) -> None:
        packages.append(package_name)
        for child in sorted(package_dir.iterdir()):
            if not child.is_dir() or child.name.startswith("_"):
                continue
            if not (child / "__init__.py").exists():
                continue
            walk(f"{package_name}.{child.name}", child)

    walk("eolib", PACKAGE_ROOT)
    return packages


def immediate_public_subpackages(package_name: str) -> list[str]:
    package_dir = package_dir_for(package_name)
    result: list[str] = []
    for child in sorted(package_dir.iterdir()):
        if not child.is_dir() or child.name.startswith("_"):
            continue
        if (child / "__init__.py").exists():
            result.append(f"{package_name}.{child.name}")
    return result


def immediate_public_module_names(package_name: str) -> list[str]:
    package_dir = package_dir_for(package_name)
    result: list[str] = []
    for child in sorted(package_dir.glob("*.py")):
        if child.stem in {"__init__", "__about__"} or child.stem.startswith("_"):
            continue
        result.append(f"{package_name}.{child.stem}")
    return result


def protocol_generated_package_name(package_name: str) -> str | None:
    if package_name == "eolib.protocol":
        return "eolib.protocol._generated"
    if package_name.startswith("eolib.protocol."):
        suffix = package_name.removeprefix("eolib.protocol.")
        return f"eolib.protocol._generated.{suffix}"
    return None


def immediate_generated_module_names(package_name: str) -> list[str]:
    generated_package_name = protocol_generated_package_name(package_name)
    if generated_package_name is None:
        return []

    generated_dir = PACKAGE_ROOT / "protocol" / "_generated"
    if package_name != "eolib.protocol":
        suffix_parts = package_name.split(".")[2:]
        generated_dir = generated_dir.joinpath(*suffix_parts)

    if not generated_dir.exists():
        return []

    result: list[str] = []
    for child in sorted(generated_dir.glob("*.py")):
        if child.stem == "__init__" or child.stem.startswith("_"):
            continue
        result.append(f"{generated_package_name}.{child.stem}")
    return result


def source_module_names_for(package_name: str) -> list[str]:
    module_names = immediate_public_module_names(package_name)
    module_names.extend(immediate_generated_module_names(package_name))
    return module_names


def is_public_export(module_name: str, name: str, obj: object) -> bool:
    if name.startswith("_") or inspect.ismodule(obj):
        return False

    if inspect.isclass(obj) or inspect.isfunction(obj) or inspect.isbuiltin(obj):
        return getattr(obj, "__module__", None) == module_name

    object_module = getattr(obj, "__module__", None)
    return object_module is None or object_module == module_name


def collect_package_export_names(package_name: str) -> list[str]:
    export_names: list[str] = []
    seen: set[str] = set()

    for module_name in source_module_names_for(package_name):
        module = importlib.import_module(module_name)
        public_names = getattr(module, "__all__", None)
        if public_names is None:
            public_names = [name for name in module.__dict__ if not name.startswith("_")]

        for name in public_names:
            if name in seen or not hasattr(module, name):
                continue

            if not is_public_export(module_name, name, getattr(module, name)):
                continue

            seen.add(name)
            export_names.append(name)

    return export_names


def prepare_package_exports() -> None:
    for package_name in iter_public_packages():
        if package_name == "eolib":
            continue

        package = importlib.import_module(package_name)
        package.__all__ = collect_package_export_names(package_name)


def collect_public_type_aliases() -> dict[str, str]:
    alias_targets: dict[str, set[str]] = {}

    for package_name in iter_public_packages():
        if package_name == "eolib":
            continue

        package = importlib.import_module(package_name)
        for name in getattr(package, "__all__", []):
            if not hasattr(package, name):
                continue

            obj = getattr(package, name)
            if not inspect.isclass(obj):
                continue

            alias_targets.setdefault(name, set()).add(f"~{package_name}.{name}")

    return {
        name: next(iter(targets)) for name, targets in alias_targets.items() if len(targets) == 1
    }


def write_heading(lines: list[str], title: str, adornment: str = "=") -> None:
    lines.extend([title, adornment * len(title), ""])


def write_directive(
    lines: list[str], directive: str, target: str, options: list[str] | None = None
) -> None:
    lines.append(f".. {directive}:: {target}")
    if options:
        for option in options:
            lines.append(f"   {option}")
    lines.append("")


def nav_label_for_package(package_name: str) -> str:
    if package_name == "eolib":
        return "eolib"
    return package_name.rsplit(".", 1)[-1]


def build_package_page(package_name: str) -> str:
    lines: list[str] = []
    subpackages = immediate_public_subpackages(package_name)

    write_heading(lines, package_name)
    if package_name == "eolib":
        write_directive(
            lines,
            "automodule",
            package_name,
            options=[
                ":no-members:",
                ":no-undoc-members:",
                ":no-special-members:",
            ],
        )
    else:
        write_directive(
            lines,
            "automodule",
            package_name,
            options=[
                ":members:",
                ":imported-members:",
                ":undoc-members:",
                ":show-inheritance:",
            ],
        )

    if subpackages:
        lines.extend([".. toctree::", "   :hidden:", "   :maxdepth: 1", ""])
        lines.extend(
            f"   {nav_label_for_package(subpackage)} <{subpackage}>" for subpackage in subpackages
        )
        lines.append("")

    return "\n".join(lines) + "\n"


def generate_reference_pages(output_dir: Path) -> None:
    package_names = iter_public_packages()

    for package_name in package_names:
        page_path = output_dir / f"{package_name}.rst"
        page_path.write_text(build_package_page(package_name), encoding="utf-8")


def sync_reference_pages(source_dir: Path, output_dir: Path) -> None:
    source_pages = {page_path.name: page_path for page_path in source_dir.glob("*.rst")}

    for existing_page in output_dir.glob("*.rst"):
        if existing_page.name not in source_pages:
            existing_page.unlink()

    for page_name, source_page in source_pages.items():
        destination_page = output_dir / page_name
        source_contents = source_page.read_text(encoding="utf-8")
        if destination_page.exists():
            destination_contents = destination_page.read_text(encoding="utf-8")
            if destination_contents == source_contents:
                continue
        destination_page.write_text(source_contents, encoding="utf-8")


def run_reference_generation(app) -> None:
    output_dir = DOCS_ROOT / "reference"
    output_dir.mkdir(exist_ok=True)

    build_root = DOCS_ROOT / "_build"
    build_root.mkdir(exist_ok=True)
    generated_output_dir = Path(tempfile.mkdtemp(prefix="reference-pages-", dir=build_root))

    try:
        generate_reference_pages(generated_output_dir)
        sync_reference_pages(generated_output_dir, output_dir)
    finally:
        shutil.rmtree(generated_output_dir, ignore_errors=True)


# See: https://github.com/pradyunsg/furo/discussions/849
def register_pygments_dark_style(app) -> None:
    original_add_config_value = app.add_config_value

    def add_config_value(name, default, rebuild, types=(), description=""):
        if name == "pygments_dark_style" and name in app.config._options:
            return None
        return original_add_config_value(name, default, rebuild, types, description)

    app.add_config_value = add_config_value

    if "pygments_dark_style" not in app.config._options:
        try:
            original_add_config_value(
                "pygments_dark_style",
                "native",
                "",
                [str],
                "Dark-mode Pygments style name.",
            )
        except ExtensionError:
            pass


def prepare_dynamic_config(app, config) -> None:
    prepare_package_exports()
    config.napoleon_type_aliases = {
        **BUILTIN_TYPE_ALIASES,
        **(config.napoleon_type_aliases or {}),
        **collect_public_type_aliases(),
    }


def process_docstring(
    _: object, __: str, ___: str, ____: object, _____: object, lines: list[str]
) -> None:
    for index, line in enumerate(lines):
        line = rewrite_public_protocol_paths(line)
        for builtin in AUTODOC_TYPEHINTS_BUILTINS:
            line = line.replace(
                f":sphinx_autodoc_typehints_type:`\\:py\\:class\\:\\`{builtin}\\``",
                f":external+python:py:class:`{builtin}`",
            )
        lines[index] = line


def process_bases(_: object, __: str, ___: object, ____: object, bases: list[type]) -> None:
    if not bases:
        return

    filtered_bases = [base for base in bases if base.__name__ != "SimpleSequenceStart"]
    if filtered_bases != bases:
        bases[:] = filtered_bases or [object]


def postprocess_generated_docs(app, exception: Exception | None) -> None:
    if exception is not None:
        return

    output_root = Path(app.outdir)
    candidates = list(output_root.rglob("*.html"))
    search_index_path = output_root / "searchindex.js"
    if search_index_path.exists():
        candidates.append(search_index_path)

    for candidate in candidates:
        if not candidate.exists():
            continue
        contents = candidate.read_text(encoding="utf-8")
        rewritten = rewrite_public_protocol_paths(contents)
        rewritten = simplify_reference_labels(rewritten)
        if rewritten != contents:
            candidate.write_text(rewritten, encoding="utf-8")


def resolve_property_object(signature: addnodes.desc_signature) -> property | None:
    module_name = signature.get("module")
    fullname = signature.get("fullname")
    if not module_name or not fullname or "." not in fullname:
        return None

    module = importlib.import_module(module_name)
    owner_name, property_name = fullname.rsplit(".", 1)
    owner: object = module
    for part in owner_name.split("."):
        owner = getattr(owner, part, None)
        if owner is None:
            return None

    candidate = getattr(owner, property_name, None)
    if isinstance(candidate, property):
        return candidate
    return None


def inject_property_signature_types(app, doctree) -> None:
    for desc in doctree.findall(addnodes.desc):
        if desc.get("objtype") != "property":
            continue

        for signature in desc.findall(addnodes.desc_signature):
            if any(isinstance(child, addnodes.desc_type) for child in signature.children):
                continue

            property_object = resolve_property_object(signature)
            if property_object is None or property_object.fget is None:
                continue

            try:
                property_signature = sphinx_inspect.signature(
                    property_object.fget, type_aliases=app.config.autodoc_type_aliases
                )
            except (TypeError, ValueError):
                continue

            if property_signature.return_annotation is inspect.Signature.empty:
                continue

            mode = get_render_mode(app.config.autodoc_typehints_format)
            short_literals = app.config.python_display_short_literal_types
            annotation = stringify_annotation(
                property_signature.return_annotation, mode, short_literals=short_literals
            )
            annotation = rewrite_public_protocol_annotation(
                annotation, app.config.typehints_fixup_module_name
            )
            type_nodes = _parse_annotation(annotation, app.env)
            signature += addnodes.desc_type(
                "",
                "",
                addnodes.desc_sig_punctuation("", ":"),
                addnodes.desc_sig_space(),
                *type_nodes,
            )


def prune_builtin_named_generated_protocol_objects(app, env) -> None:
    python_objects = env.domaindata["py"]["objects"]
    names_to_prune: list[str] = []
    for name, obj in python_objects.items():
        if obj.objtype != "property":
            continue
        if not name.startswith("eolib.protocol."):
            continue
        if name.rsplit(".", 1)[-1] not in AUTODOC_TYPEHINTS_BUILTINS:
            continue
        names_to_prune.append(name)

    for name in names_to_prune:
        del python_objects[name]


def normalize_property_signature_types(app, doctree) -> None:
    for desc in doctree.findall(addnodes.desc):
        if desc.get("objtype") != "property":
            continue

        for signature in desc.findall(addnodes.desc_signature):
            children = list(signature.children)
            for index, child in enumerate(children):
                if not isinstance(child, addnodes.desc_annotation):
                    continue
                if index == 0:
                    continue

                signature[index] = addnodes.desc_type("", "", *child.children)


def setup(app) -> dict[str, bool]:
    register_pygments_dark_style(app)
    app.connect("config-inited", prepare_dynamic_config)
    app.connect("builder-inited", run_reference_generation)
    app.connect("env-updated", prune_builtin_named_generated_protocol_objects)
    app.connect("doctree-read", inject_property_signature_types, priority=600)
    app.connect("doctree-read", normalize_property_signature_types)
    app.connect("autodoc-process-docstring", process_docstring)
    app.connect("autodoc-process-bases", process_bases)
    app.connect("build-finished", postprocess_generated_docs)
    app.add_css_file("localtoc.css", priority=800)
    app.add_css_file("brand.css", priority=800)
    app.add_css_file("api.css", priority=800)
    app.add_css_file("version-picker.css", priority=800)
    app.add_css_file("version-warning.css", priority=800)
    app.add_js_file("version-picker.js", priority=800)
    app.add_js_file("sidebar-nav.js", priority=800)
    return {"parallel_read_safe": True, "parallel_write_safe": True}


project = "EOLib"
author = "Jonah Jeleniewski"
copyright = f"{datetime.now().year}, {author}"
version = __version__
release = __version__

keep_warnings = True
nitpicky = True

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.githubpages",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

source_suffix = {
    ".md": "markdown",
    ".rst": "restructuredtext",
}

root_doc = "index"

autosummary_generate = True
autodoc_member_order = "bysource"
autoclass_content = "class"
autodoc_typehints = "none"
autodoc_class_signature = "separated"
autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__all__, __repr__, __new__",
}

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_preprocess_types = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_rtype = False
napoleon_use_ivar = True

typehints_document_rtype = False
typehints_use_rtype = False
typehints_use_signature_return = True
typehints_defaults = "comma"
typehints_fixup_module_name = GeneratedProtocolModuleFixer(iter_public_packages())
always_use_bars_union = True

myst_heading_anchors = 3
add_module_names = False
toc_object_entries_show_parents = "hide"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

html_theme = "furo"
html_theme_options = {
    "announcement": " ",
    "source_repository": "https://github.com/cirras/eolib-python/",
    "source_branch": "master",
    "source_directory": "docs/",
    "navigation_with_keys": True,
    "top_of_page_buttons": [],
    "footer_icons": [
        {
            "name": "GitHub",
            "url": "https://github.com/cirras/eolib-python",
            "html": """
                <svg stroke="currentColor" fill="currentColor" stroke-width="0" viewBox="0 0 16 16">
                    <path fill-rule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38
                    0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01
                    1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95
                    0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27
                    2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82
                    1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2
                    0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"></path>
                </svg>
            """,
            "class": "",
        }
    ],
}
html_title = f"{project} {release}"
html_logo = "assets/logo.svg"
html_favicon = "assets/logo.svg"
html_static_path = ["assets", "_static"]
html_sidebars = {
    "**": [
        "sidebar/brand.html",
        "sidebar/search.html",
        "sidebar/scroll-start.html",
        "sidebar/navigation.html",
        "sidebar/ethical-ads.html",
        "sidebar/scroll-end.html",
        "sidebar/variant-selector.html",
    ]
}
pygments_style = "default"
pygments_dark_style = "monokai"
