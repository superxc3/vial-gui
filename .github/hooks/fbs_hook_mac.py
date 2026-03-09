import importlib, os, sys
module = importlib.import_module('fbs_runtime._frozen')
module.BUILD_SETTINGS = {'app_name': 'Vial', 'version': '0.7.5', 'author': 'xcmkb'}
# fbs looks in Contents/Resources/ but PyInstaller puts files in Contents/MacOS/
# Patch get_resource_dirs to check both locations.
_orig = module.get_resource_dirs
def _patched():
    dirs = _orig()
    dirs.append(os.path.dirname(sys.executable))
    return dirs
module.get_resource_dirs = _patched
