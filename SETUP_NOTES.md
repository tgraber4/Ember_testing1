# EMBER2024 on HPC: Apptainer setup and code changes

## Apptainer

### Problem 1: LightGBM would not import
The original `python310.sif` is a minimal Python image without the OpenMP runtime
(`libgomp.so.1`). LightGBM's compiled library needs it, so `import lightgbm` failed with
`OSError: libgomp.so.1: cannot open shared object file`. Because `thrember/__init__.py`
imports `model.py`, which imports LightGBM, `import thrember` failed too.

The failing `lightgbm` was also being loaded from the host's `~/.local`, because Apptainer
mounts the home directory by default.

### Fix: rebuild the image (`ember.def`)
- Base: `docker://python:3.10-slim`
- Installs the OS package `libgomp1`.
- Installs the Python dependencies into the image: `lightgbm>=4.6.0`, `pefile`, `polars`,
  `scikit-learn`, `tqdm`, `signify>=0.9.1,<0.10`, `shap>=0.46.0`, `huggingface_hub`,
  `matplotlib`.
- Sets `PYTHONNOUSERSITE=1` so packages in the host's `~/.local` are ignored.
- `thrember` itself is not installed in the image. It is used from source via `PYTHONPATH`.

Build (Apptainer 1.5.4), from the project directory on the cluster:

```bash
export APPTAINER_CACHEDIR=/cluster/pixstor/euh46-lab/EmberEnsemble/Tyler/apptainer_cache
export APPTAINER_TMPDIR=/cluster/pixstor/euh46-lab/EmberEnsemble/Tyler/apptainer_tmp
mkdir -p $APPTAINER_CACHEDIR $APPTAINER_TMPDIR
apptainer build --fakeroot ember.sif ember.def
```

### Running the container
```bash
export HF_HOME=/cluster/pixstor/euh46-lab/EmberEnsemble/Tyler/hf_cache
mkdir -p $HF_HOME

apptainer exec --bind /cluster/pixstor/euh46-lab \
    --env PYTHONPATH=/cluster/pixstor/euh46-lab/EmberEnsemble/Tyler/EMBER2024/src \
    ember.sif python <your_script>.py
```

- `--bind /cluster/pixstor/euh46-lab` makes the lab storage visible and writable inside
  the container (the `.sif` itself is read-only).
- `--env PYTHONPATH=.../EMBER2024/src` makes `import thrember` use the source on lab storage.
- `HF_HOME` moves the HuggingFace cache off the small home directory onto lab storage.

### Download notes
- The download was killed (`Killed` during "reconstructing file") on a session with limited
  RAM. Run it on a compute node with a memory allocation (for example `--mem=16G`) instead
  of the login node.
- `HF_HUB_DISABLE_XET=1` can be set to lower memory use during file reconstruction.
- The HuggingFace cache keeps a copy of each downloaded zip, so disk use is roughly doubled
  until `hf_cache` is deleted. It can be removed once the extracted data is verified.

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
