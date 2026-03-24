# Default ICC Gamut Mesh Profiles

This directory contains precomputed gamut boundary meshes in JSON format.

Each mesh file stores a convex hull representation of a standard output
condition's gamut in CIELab space, including:

- **vertices**: Lab points on the hull surface
- **equations**: Half-space inequalities for fast in-gamut testing
- **volume**: Total gamut volume in Lab^3 units

## Generating Meshes

Meshes are built from CGATS characterization data using
`gamut_boundary.build_gamut_boundary_from_lab_points()` and saved with
`gamut_boundary.save_gamut_boundary()`.

## Available Conditions

See `conditions.json` in the parent directory for the registry of
supported output conditions and their corresponding mesh files.
