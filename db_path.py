"""Where Dictionary.db is built and edited.

When this repo is cloned as a sibling folder inside KleiKodeshProject, that is the app's one
working copy: KleiKodeshProject/KitveiHakodesh/CSharpBackend/KitveiHakodesh.Core/Dictionary/Dictionary.db.
Otherwise (e.g. CI, or a stand-alone clone) it is this repo's build/Dictionary.db.
"""

import os

ROOT = os.path.dirname(os.path.abspath(__file__))
APP_DICTIONARY_DIR = os.path.join(os.path.dirname(ROOT), "KitveiHakodesh", "CSharpBackend",
                                  "KitveiHakodesh.Core", "Dictionary")
LOCAL_DB = os.path.join(ROOT, "build", "Dictionary.db")


def dictionary_db():
    if os.path.isdir(APP_DICTIONARY_DIR):
        return os.path.join(APP_DICTIONARY_DIR, "Dictionary.db")
    return LOCAL_DB
