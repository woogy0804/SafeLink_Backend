# Backlink data contract

## Provider

The default provider is DataForSEO Backlinks API, using:

`POST /v3/backlinks/bulk_referring_domains/live`

It supports up to 1,000 targets per request and returns counts from its latest
live backlink index. Credentials are read only from `DATAFORSEO_LOGIN` and
`DATAFORSEO_PASSWORD`.

## Count definition

`count` means the DataForSEO `referring_main_domains` value for a registered
domain target:

- target scope: the registered/root domain and all its subdomains;
- time scope: links considered live during the provider's latest check;
- uniqueness: one count per referring root domain;
- link attributes: all live external backlink types, including nofollow, UGC,
  sponsored, and noreferrer links;
- missing provider result: unknown (`0` feature value), never an inferred zero;
- explicit provider count of zero: phishing signal (`-1` feature value).

Using referring root domains avoids inflating the signal when one site creates
many site-wide links. Raw backlink URL counts and all-time/historical counts
must not be mixed into the same snapshot.

## Classification

| Provider count | Feature value |
| ---: | ---: |
| 0 | -1 |
| 1-2 | 0 |
| 3 or more | 1 |
| missing/unavailable | 0 |

## Refresh

Build a dated, immutable snapshot and refresh it at most once every 24 hours.
Run-time URL analysis reads the local CSV/SQLite snapshot and does not call the
paid provider directly.

```powershell
$env:DATAFORSEO_LOGIN='...'
$env:DATAFORSEO_PASSWORD='...'
python -m scripts.update_backlinks_dataforseo domains.csv
```

Generated CSV and SQLite files are ignored by Git. Store provider name,
observation time, and `live_referring_main_domains` in snapshot metadata.
