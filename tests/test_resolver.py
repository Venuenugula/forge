from __future__ import annotations

import json
import os

from forge.envs import create_env
from forge.runtime import resolution_paths


def test_resolution_paths_follow_local_parent_global_order(tmp_path) -> None:
    os.environ["FORGE_HOME"] = str(tmp_path / ".forge")
    try:
        create_env("base")
        create_env("child", parent="base")

        paths = resolution_paths("child")
        as_strings = [str(p) for p in paths]

        assert as_strings[0].endswith("/envs/child/site-packages")
        assert as_strings[1].endswith("/envs/base/site-packages")
        assert as_strings[2].endswith("/store")
    finally:
        os.environ.pop("FORGE_HOME", None)
