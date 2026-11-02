# EMBER2024 download and duplicate check

## 1. Download

We downloaded the dataset from HuggingFace (`joyce8/EMBER2024`, repo type `dataset`) with the
`thrember` package from the EMBER2024 GitHub repository:

```python
from thrember import download_dataset
download_dataset("ember_data_full", split="all", file_type="all")
```

This downloads the train and test zip files for Win32, Win64, Dot_Net, APK, ELF and PDF, plus
`challenge.zip`. Each zip is fetched with `hf_hub_download` and unzipped with
`zipfile.ZipFile.extractall`. The download code does not copy or modify any records.

## 2. Duplicate check

We checked the first train week of each file type (2023-09-24 to 2023-09-30). We read each
`.jsonl` file, grouped the records by `sha256`, and compared the records in each group.

- Every `sha256` appears exactly twice, in all six file types.
- The number of unique `sha256` values matches the README's weekly counts: Win32 30,000,
  Win64 10,000, Dot_Net 5,000, APK 4,000, PDF 1,000, ELF 500.
- The two copies of a sample are either identical or differ only in the `caps`, `ttps` and
  `mbc` fields. All other fields are the same.

## Not checked

- Other weeks, the test files and the challenge files were not inspected record by record.
- We did not open the zip files before extracting them, so we cannot say whether the
  duplicates are in the zips on HuggingFace or are created during extraction.
