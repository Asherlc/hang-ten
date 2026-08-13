"""Explicit static UI asset manifest for the Hangboard Workbench."""

from __future__ import annotations


STATIC_ASSET_ROUTES = (
    ("/", "index.html"),
    ("/index.html", "index.html"),
    ("/styles.css", "styles.css"),
    ("/editor-model.js", "editor-model.js"),
    ("/curve-gesture-model.js", "curve-gesture-model.js"),
    ("/editor-interaction-model.js", "editor-interaction-model.js"),
    ("/workbench-client.js", "workbench-client.js"),
    ("/workbench-controller.js", "workbench-controller.js"),
    ("/workbench-model.js", "workbench-model.js"),
    ("/workbench-suite-model.js", "workbench-suite-model.js"),
    ("/workbench-suite-controller.js", "workbench-suite-controller.js"),
    ("/validation-view.js", "validation-view.js"),
    ("/vector-path-model.js", "vector-path-model.js"),
    ("/app.js", "app.js"),
)

STATIC_ASSETS = tuple(dict.fromkeys(asset for _route, asset in STATIC_ASSET_ROUTES))
