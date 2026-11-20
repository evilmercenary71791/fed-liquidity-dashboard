# Fed Liquidity Dashboard

An interactive Fed balance-sheet and reserve-attribution dashboard. Data are sourced from the Federal Reserve's H.4.1 release through FRED's public CSV exports.

## Publish and initialize

1. Under **Settings → Actions → General → Workflow permissions**, select **Read and write permissions**, then Save. The weekly workflow writes CSV observations and source metadata to the repository.
2. Under **Actions → Refresh Federal Reserve H.4.1 data**, select **Run workflow** once. Check that the run succeeds and creates `data/weekly.csv`, `data/status.json`, `data/money_supply.csv` and `data/money_status.json`.
3. Under **Settings → Pages**, select **Deploy from a branch**, branch **main**, folder **/(root)**, then Save.
4. Dashboard URL: https://evilmercenary71791.github.io/fed-liquidity-dashboard/

The workflow also runs Fridays at **12:15 UTC (14:15 South African time)**. Scheduled GitHub Actions may be delayed, particularly on busy days, and might be disabled following prolonged repository inactivity.

## H.4.1 Wednesday-level series, USD millions in FRED

| Dashboard measure | FRED ID |
| --- | --- |
| Total assets | WALCL |
| Treasury holdings | WSHOTSL |
| Agency MBS holdings | WSHOMCB |
| Treasury General Account | WDTGAL |
| Reverse repurchase agreements (total H.4.1 category) | WLRRAL |
| Reserve balances, Wednesday level | WRBWFRBL |
| Primary credit | WLCFLPCL |
| Bank Term Funding Program, discontinued | H41RESPPALDKNWW |

The downloaded H.4.1 data are converted to USD billions. H.6 monthly money stocks M1SL and M2SL are downloaded in USD billions as published. Discontinued M3SL is retained as historical data only (through March 2006). M1 was redefined in May 2020; comparisons across the redefinition need care. The public dashboard loads official CSV files automatically and no longer displays manual import controls. Required core fields must exist for every displayed observation; optional lending fields are blank when unavailable. No simulated observations are published.

**Reserve attribution:** Δreserves = Δtotal Fed assets − ΔTGA − Δreverse repos + residual. The residual includes other Fed liabilities and capital. The net liquidity proxy (assets − TGA − reverse repos) is analytical and not an official Fed statistic.

The first historical date is determined by overlapping available sources, normally starting in December 2002. Extending to 2000 requires a separate documented backfill. The current deployment contains no verified market-transmission correlations.

To test the update script locally: `python update_data.py`. To serve the dashboard locally: `python -m http.server 8000`. Visit http://localhost:8000.
