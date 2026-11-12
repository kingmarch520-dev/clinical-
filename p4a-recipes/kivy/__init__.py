"""Local override of the Kivy recipe for python-for-android.

The stock recipe pulls in requests, which pulls in charset-normalizer. The Android
wheel of charset-normalizer cannot be installed by the build machine's pip, so the
whole APK build fails. Pseudo Clinic never uses requests (it updates with urllib),
so it is dropped here. Everything else in the stock recipe is kept as it is.
"""

from pythonforandroid.recipes.kivy import KivyRecipe as _KivyRecipe

_DROP = {"requests"}


def _strip(items):
    return [item for item in items if item not in _DROP]


class KivyRecipe(_KivyRecipe):
    depends = _strip(getattr(_KivyRecipe, "depends", []))
    python_depends = _strip(getattr(_KivyRecipe, "python_depends", []))
    if "filetype" not in python_depends:
        python_depends.append("filetype")


recipe = KivyRecipe()
