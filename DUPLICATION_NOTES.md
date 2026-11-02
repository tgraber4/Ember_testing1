# EMBER2024 duplication

Every sample (`sha256`) appears exactly twice in the `.jsonl` shards, so the files hold about 2x the documented sample count (6,470,315 records vs. 3,238,315 documented). The challenge set is not duplicated. The only fields that ever differ between the two copies are the Capa fields: `caps`, `ttps` and `mbc`.

Results are from the first train shard of each type (2023-09-24 to 2023-09-30).

| Type | Pairs | Identical pairs | Non-identical pairs |
|---|---|---|---|
| Win32 | 30,000 | 5,864 | 24,136 |
| Win64 | 10,000 | 1,994 | 8,006 |
| .NET | 5,000 | 118 | 4,882 |
| ELF | 500 | 429 | 71 |
| APK | 4,000 | 4,000 | 0 |
| PDF | 1,000 | 1,000 | 0 |

**Rows:** one file type each.
- **Pairs:** unique samples in the shard, each stored as two records.
- **Identical pairs:** both copies are exactly the same. In every identical pair, all three Capa fields are empty in both copies.
- **Non-identical pairs:** the copies differ. In each, one copy has Capa results (at least one filled field) and the other has them empty. No pair has Capa results in both copies. Which copy comes first in the file varies.

APK and PDF have only empty Capa fields, so all their pairs are identical. Win32, Win64, .NET and ELF are mixed.

**Empty** means the field is present in the record but blank. Every record has all three fields, none are missing. The check counted `null`, `""`, `[]` and `{}` all as empty, and I did not check which form the files use.

## Capa fields

- `caps`: capabilities found (capability name, namespace, addresses).
- `ttps`: MITRE ATT&CK tactics and techniques.
- `mbc`: Malware Behavior Catalog objectives and behaviors.
