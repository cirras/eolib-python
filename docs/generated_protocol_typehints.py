from __future__ import annotations

import hashlib


class GeneratedProtocolModuleFixer:
    def __init__(self, public_packages: list[str]) -> None:
        self._public_packages = frozenset(public_packages)

    def __call__(self, module: str) -> str:
        if not module.startswith("eolib.protocol._generated"):
            return module

        public_module = module.replace("eolib.protocol._generated", "eolib.protocol", 1)
        while public_module not in self._public_packages and "." in public_module:
            public_module = public_module.rsplit(".", 1)[0]
        return public_module

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GeneratedProtocolModuleFixer):
            return NotImplemented
        return self._public_packages == other._public_packages

    def __hash__(self) -> int:
        return hash((self.__class__, self._public_packages))

    def __repr__(self) -> str:
        packages = ",".join(sorted(self._public_packages))
        digest = hashlib.md5(packages.encode(), usedforsecurity=False).hexdigest()[:12]
        return f"{self.__class__.__name__}(packages_hash={digest})"

    __str__ = __repr__
