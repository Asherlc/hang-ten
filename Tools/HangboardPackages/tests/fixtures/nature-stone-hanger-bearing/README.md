# Stone Hanger bearing fixtures

These native CAD face measurements support the reverse 6 mm pose regression
in `test_pose_camera_facing.py`. They are display geometry measurements, not
manufacturer angle specifications.

`display-bearing.json` contains the independently measured bearing normals.
`contact-preservation.json` proves that the granite seat revision preserved
the seven measured wood contact surfaces. `runtime-validation.json` binds
that proof to the generated model and descriptor. The test checks the fixture
hashes, preserved surface areas, current model hashes, and current CAD-bound
suspension before using the normals.

For a change to these contact surfaces, replace the measurements and
preservation proof with a new independent CAD check, then review the pose
against the resulting geometry. Metadata-only changes do not justify changing
the measured normals.
