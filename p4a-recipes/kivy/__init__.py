"""Local override of the Kivy recipe for python-for-android.

The stock recipe pulls in requests, which pulls in charset-normalizer. The Android
wheel of charset-normalizer cannot be installed by the build machine's pip, so the
whole APK build fails. Pseudo Clinic never uses requests (it updates with urllib),
so it is dropped here. Everything else in the stock recipe is kept as it is.

Because this recipe lives in our own folder, python-for-android would look for the
stock recipe's patch files in our folder too. get_recipe_dir sends it back to the
stock folder, where those files really are.
"""

import inspect
import os

from pythonforandroid.recipes.kivy import KivyRecipe as _KivyRecipe

_DROP = {"requests"}
_STOCK_DIR = os.path.dirname(os.path.abspath(inspect.getfile(_KivyRecipe)))


def _strip(items):
    return [item for item in items if item not in _DROP]


class KivyRecipe(_KivyRecipe):
    depends = _strip(getattr(_KivyRecipe, "depends", []))
    python_depends = _strip(getattr(_KivyRecipe, "python_depends", []))
    if "filetype" not in python_depends:
        python_depends.append("filetype")

    def get_recipe_dir(self):
        return _STOCK_DIR


recipe = KivyRecipe()
