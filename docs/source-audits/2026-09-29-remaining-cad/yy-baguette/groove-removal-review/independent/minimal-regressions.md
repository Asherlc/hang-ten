# Minimal retained regression candidates

No code edits; source geometry/package only. Actual package validation plus independent USD material/binding import and target-specific staging equality should be prioritized. No broad unchanged suite required.

Python narrow tests:
- Tools/HangboardCAD/tests/test_board_manifest.py::test_round_trip_regenerates_board_json_and_leaves_geometry_untouched
- Tools/HangboardCAD/tests/test_cad_sidecars.py::test_matching_native_authoring_graph_merges_without_runtime_solver_settings
- Tools/HangboardPackages/tests/test_board_catalog.py::test_a_cad_backed_package_validates_its_generated_board_json
- Tools/HangboardPackages/tests/test_model_first_packages.py::test_model_display_surface_finish_applies_without_node_inventory
- Tools/HangboardPackages/tests/test_board_package_staging.py::test_staging_preserves_package_authored_surface_finishes_without_model_edits
- Tools/HangboardPackages/tests/test_cad_routed_cord.py (5 cases)

Swift fixture-focused:
- BoardPackageStoreTests/testModelBoardFinishDecodesWithoutPerMeshSelections
- BoardModelRealityTests/testWoodFinishHighlightsAndRestoresEveryContactWithoutChangingPicking (Mammut wood fixture; renderer behavior only)
- SuspendedBoardPresentationTests/testNativeCADRoutesKeepTheWorldSupportAndExactBodyPose

Actual yy.baguette RealityKit load/contact collision/selection/cord-nonpickability is covered by BoardModelRealityTests/testNativeCADModelsCreateNonPickableCordSegmentsInEveryPosition, but this existing test loops all 21 boards, so it is not a narrow package-specific test.
