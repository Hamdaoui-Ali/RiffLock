import importlib


MODULES = [
    "rifflock",
    "rifflock.config",
    "rifflock.main",
    "rifflock.ui",
    "rifflock.ui.app",
    "rifflock.auth",
    "rifflock.audio",
    "rifflock.crypto",
    "rifflock.files",
    "rifflock.storage",
    "rifflock.models",
    "rifflock.utils",
]


def test_core_modules_import() -> None:
    for module_name in MODULES:
        importlib.import_module(module_name)
