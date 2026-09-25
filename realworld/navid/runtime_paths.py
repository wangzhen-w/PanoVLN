"""Load this method's official model packages, without importing another baseline."""
from pathlib import Path
import sys

MODEL_CODE = Path(__file__).resolve().parent / 'model_code'
PACKAGES = ('navid',)

def activate_model_code():
    # NaVILA and StreamVLN both vendor llava, with incompatible implementations.
    # Separate model processes/environments are intentional; never silently reuse
    # an already-imported package belonging to a different method.
    for name in PACKAGES:
        loaded = sys.modules.get(name)
        if loaded is None:
            continue
        paths = list(getattr(loaded, '__path__', []))
        if getattr(loaded, '__file__', None):
            paths.append(loaded.__file__)
        if not paths or any(MODEL_CODE not in Path(path).resolve().parents for path in paths):
            raise RuntimeError(f'{name} is already loaded from another project; start a separate model process')
    path = str(MODEL_CODE)
    if path in sys.path:
        sys.path.remove(path)
    sys.path.insert(0, path)
