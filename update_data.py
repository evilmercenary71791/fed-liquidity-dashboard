#!/usr/bin/env python3
"""Refresh aligned Wednesday H.4.1 observations from FRED graph CSVs."""
import csv
import io
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
SERIES = {
    "total_assets": "WALCL",
    "treasuries": "WSHOTSL",
    "mbs": "WSHOMCB",
    "tga": "WDTGAL",
    "rrp": "WLRRAL",
    "reserves": "WRBWFRBL",
    "primary_credit": "WLCFLPCL",
    "btfp": "H41RESPPALDKNWW",
}
REQUIRED = ("total_assets", "treasuries", "mbs", "tga", "rrp", "reserves")
OPTIONAL = ("primary_credit", "btfp")

def download(code):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={code}&cosd=2002-12-18"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 FedLiquidityLab/1.0", "Accept": "text/csv"})
    with urlopen(req, timeout=50) as response:
        reader = csv.DictReader(io.StringIO(response.read().decode("utf-8-sig")))
        if not reader.fieldnames or code not in reader.fieldnames:
            raise ValueError(f"{code}: CSV columns unexpected: {reader.fieldnames}")
        date_key = next((k for k in ("DATE", "observation_date") if k in reader.fieldnames), None)
        if date_key is None:
            raise ValueError(f"{code}: date column missing")
        result = {}
        for row in reader:
            date = datetime.strptime(row[date_key], "%Y-%m-%d").date()
            if date.weekday() != 2:
                raise ValueError(f"{code}: non-Wednesday observation {date}")
            raw = row[code]
            if raw and raw != ".":
                result[date.isoformat()] = float(raw) / 1000  # millions -> billions
        if not result:
            raise ValueError(f"{code}: no observations")
        return result


MONEY_SERIES = {"m1": "M1SL", "m2": "M2SL", "m3": "M3SL"}

def download_monthly(code):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={code}&cosd=1959-01-01"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 FedLiquidityLab/1.0", "Accept": "text/csv"})
    with urlopen(req, timeout=50) as response:
        reader = csv.DictReader(io.StringIO(response.read().decode("utf-8-sig")))
        if not reader.fieldnames or code not in reader.fieldnames:
            raise ValueError(f"{code}: CSV columns unexpected: {reader.fieldnames}")
        date_key = next((k for k in ("DATE", "observation_date") if k in reader.fieldnames), None)
        if date_key is None:
            raise ValueError(f"{code}: date column missing")
        result = {}
        for row in reader:
            date = datetime.strptime(row[date_key], "%Y-%m-%d").date()
            if date.day != 1:
                raise ValueError(f"{code}: non-monthly observation {date}")
            raw = row[code]
            if raw and raw != ".":
                result[date.isoformat()] = float(raw) # H.6 series already in USD billions
        if not result:
            raise ValueError(f"{code}: no observations")
        return result

def prepare_money_supply():
    stocks = {field: download_monthly(code) for field, code in MONEY_SERIES.items()}
    if len(stocks["m1"]) < 500 or len(stocks["m2"]) < 500 or len(stocks["m3"]) < 100:
        raise RuntimeError("Money supply history is unexpectedly short")
    if max(stocks["m3"]) > "2006-03-01":
        raise RuntimeError("M3 archival series unexpectedly extends past its March 2006 discontinuation")
    now = datetime.now(timezone.utc).date()
    latest_m2 = datetime.strptime(max(stocks["m2"]), "%Y-%m-%d").date()
    if now - latest_m2 > timedelta(days=110):
        raise RuntimeError(f"M2 observations are stale: {latest_m2}")
    dates = sorted(set().union(*[set(series) for series in stocks.values()]))
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["date", "m1", "m2", "m3"], lineterminator="\\n")
    writer.writeheader()
    for day in dates:
        writer.writerow({"date": day, **{k: (round(stocks[k][day], 3) if day in stocks[k] else "") for k in MONEY_SERIES}})
    metadata = {
        "source": "Federal Reserve H.6 money supply via FRED",
        "frequency": "Monthly, seasonally adjusted",
        "unit": "USD billions",
        "refreshed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "first_observation": dates[0],
        "latest_m1": max(stocks["m1"]),
        "latest_m2": max(stocks["m2"]),
        "latest_m3": max(stocks["m3"]),
        "series": MONEY_SERIES,
        "m1_definition_change": "2020-05",
        "m3_discontinued": "2006-03",
    }
    return output.getvalue(), json.dumps(metadata, indent=2) + "\\n"

def main():
    downloaded = {}
    optional_errors = {}
    for field, code in SERIES.items():
        try:
            downloaded[field] = download(code)
            print(field, code, len(downloaded[field]), max(downloaded[field]))
        except Exception as exc:
            if field in REQUIRED:
                raise RuntimeError(f"Required series {code} failed") from exc
            downloaded[field] = {}
            optional_errors[code] = str(exc)
    dates = sorted(set.intersection(*(set(downloaded[k]) for k in REQUIRED)))
    if len(dates) < 100:
        raise RuntimeError(f"Insufficient aligned observations: {len(dates)}")
    last = datetime.strptime(dates[-1], "%Y-%m-%d").date()
    if datetime.now(timezone.utc).date() - last > timedelta(days=21):
        raise RuntimeError(f"Latest complete Wednesday is stale: {last}")
    fields = ["date", *REQUIRED, *OPTIONAL]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for day in dates:
        row = {"date": day}
        for key in REQUIRED:
            row[key] = round(downloaded[key][day], 3)
        for key in OPTIONAL:
            row[key] = round(downloaded[key][day], 3) if day in downloaded[key] else ""
        writer.writerow(row)
    meta = {
        "source": "H.4.1 Wednesday levels via FRED",
        "unit": "USD billions",
        "refreshed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "first_observation": dates[0],
        "latest_observation": dates[-1],
        "observations": len(dates),
        "series": SERIES,
        "optional_series_errors": optional_errors,
        "methodology": "Net liquidity proxy = Fed assets - TGA - reverse repos. Reserve bridge incorporates residual other liabilities and capital.",
    }
    money_csv, money_metadata = prepare_money_supply()
    (DATA / "money_supply.csv").write_text(money_csv, encoding="utf-8")
    (DATA / "money_status.json").write_text(money_metadata, encoding="utf-8")
    (DATA / "weekly.csv").write_text(output.getvalue(), encoding="utf-8")
    (DATA / "status.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {len(dates)} Wednesday observations through {dates[-1]}")

if __name__ == "__main__":
    main()
