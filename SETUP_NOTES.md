# EMBER2024 on HPC: Apptainer setup

Instructions for running EMBER2024 (`thrember`) on the cluster with Apptainer 1.5.4.

> **Note:** do not use the original `python310.sif`. It is missing a system library that
> LightGBM needs, so `import thrember` fails. Build a new image from `ember.def` instead.
> The reason is explained in [Why we use a definition file](#why-we-use-a-definition-file) at
> the bottom.

## 1. Build the image

Copy `ember.def` (provided as a separate file) to the project folder on the cluster, then build. `--fakeroot` lets
us build without root access. The two exports keep the build cache and temporary files off
the small home directory.

```bash
export APPTAINER_CACHEDIR=/cluster/pixstor/euh46-lab/EmberEnsemble/Tyler/apptainer_cache
export APPTAINER_TMPDIR=/cluster/pixstor/euh46-lab/EmberEnsemble/Tyler/apptainer_tmp
mkdir -p $APPTAINER_CACHEDIR $APPTAINER_TMPDIR
apptainer build --fakeroot ember.sif ember.def
```

The `%test` section of `ember.def` runs at the end of the build and imports every dependency,
so a missing library shows up during the build.

## 2. Apply the code changes

Make the `features.py` edits in [Changes to the original EMBER2024
code](#changes-to-the-original-ember2024-code) below. The image installs `signify` 0.9.x, and
the original code does not work with it.

## 3. Run the container

```bash
apptainer exec --bind /cluster/pixstor/euh46-lab \
    --env PYTHONPATH=/cluster/pixstor/euh46-lab/EmberEnsemble/Tyler/EMBER2024/src \
    ember.sif python <your_script>.py
```

- `--bind /cluster/pixstor/euh46-lab` makes the lab storage visible and writable inside the
  container. The `.sif` file itself is read-only.
- `--env PYTHONPATH=.../EMBER2024/src` makes `import thrember` use the source on lab storage.
  `thrember` is not installed in the image, so code changes do not need a rebuild.

## Changes to the original EMBER2024 code

### `src/thrember/features.py`
The original code targets an older `signify` API. With `signify` 0.9.x (0.9.3 in the image),
the import failed with `ImportError: cannot import name 'SignedPEFile' from
'signify.authenticode'`. Three edits:

| Location | Original | Changed to |
|---|---|---|
| Import (line 28) | `from signify.authenticode import SignedPEFile` | `from signify.authenticode.signed_file import SignedPEFile` |
| Signature loop (line 935) | `signed_pe.iter_signed_datas()` | `signed_pe.iter_embedded_signatures()` |
| Certificate list (line 955) | `certs = signed_data.certificates` | `certs = list(signed_data.certificates)` |

The `list(...)` is needed because `len(certs)` and `certs[:-1]` are used afterwards.

### Dependency pins
The original `pyproject.toml` has `signify>=0.7.1`, which is unbounded, so a fresh install
picks up a version where the code above no longer works. The working setup pins
`signify>=0.9.1,<0.10` and adds `shap>=0.46.0`. These pins are applied in `ember.def` for the
image. They were also made in the `pyproject.toml` and `setup.cfg` of the alternative copy of
the repository, but not in this folder's `pyproject.toml`.

The `features.py` edits and the `signify` version must stay matched: the changed code does
not work with `signify` 0.7.x.

## Why we use a definition file

We first tried the existing `python310.sif` (Python 3.10) on the cluster. A `.sif` file is a
read-only image, and we have no root access on the cluster, so we cannot install system
packages into it afterwards. Any missing system library has to be added by building a new
image.

### The problem: LightGBM would not import

```
OSError: libgomp.so.1: cannot open shared object file: No such file or directory
```

- LightGBM contains a compiled library that needs the OpenMP runtime, `libgomp.so.1`.
- `libgomp` is a system library (the `libgomp1` package on Debian/Ubuntu), not a Python
  package, so `pip` does not install it.
- `python310.sif` is a minimal Python image and does not include it.
- `thrember/__init__.py` imports `model.py`, which imports `lightgbm`, so `import thrember`
  failed too, even for a script that only downloads data.
- The failing `lightgbm` was also being loaded from the host's `~/.local`. Apptainer mounts
  the home directory by default, so packages installed with `pip install --user` on the host
  were visible inside the container. That mixes host packages with the container's system
  libraries.

### The fix: build a new image from `ember.def`

The definition file records every step used to build the image, so the container can be
rebuilt the same way at any time. It does three things the old image could not:

1. Starts from the official `python:3.10-slim` image.
2. Installs the missing system library, `libgomp1`, with `apt-get`.
3. Installs the Python dependencies of `thrember` inside the image, so nothing depends on the
   host's `~/.local`. `signify` is pinned to `>=0.9.1,<0.10` to match the code changes above.

It also sets `PYTHONNOUSERSITE=1` so Python ignores the host's `~/.local` packages.
