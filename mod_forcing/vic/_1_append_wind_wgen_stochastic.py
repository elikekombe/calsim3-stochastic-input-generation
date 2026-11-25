# -*- coding: utf-8 -*-
"""Append historical wind to Product B WGEN met files for VIC forcing.

Product B's source sequence uses a leap day every four source years, while its
Gregorian processing calendar can omit leap days at non-leap century years.
Rows are aligned to the requested start year before wind is merged so each
weather record and its historical-date mapping stay together.
"""

import argparse
import calendar
import os
import sys
from pathlib import Path

import pandas as pd


WGEN_COLUMNS = ["source_year", "source_month", "source_day", "pr", "tmax", "tmin"]
CLIMATE_COLUMNS = ["pr", "tmax", "tmin"]
OUTPUT_COLUMNS = ["pr", "tmax", "tmin", "wind"]
DEFAULT_START_YEAR = 2028


def align_wgen_calendar(data_wgen, sampled_dates, start_year=DEFAULT_START_YEAR):
    """Align WGEN rows to Gregorian years, keeping each CSV mapping attached.

    When a target year has no Feb 29, the source Feb 29 row is removed. When
    the target year is leap but the source year has no Feb 29, a row is inserted
    using the Feb 28 / Mar 1 mean for precipitation and temperatures; its
    historical-date mapping is left empty so wind can be interpolated after the
    historical wind merge.
    """
    if not isinstance(start_year, int) or start_year < 1:
        raise ValueError("start_year must be a positive integer")
    if len(data_wgen) != len(sampled_dates):
        raise ValueError(
            "WGEN/CSV row-count mismatch: "
            f"{len(data_wgen)} WGEN rows vs {len(sampled_dates)} CSV date rows"
        )
    missing = set(WGEN_COLUMNS).difference(data_wgen.columns)
    if missing:
        raise ValueError(f"WGEN file is missing required columns: {sorted(missing)}")
    if "resmplDatesLoc" not in sampled_dates.columns:
        raise ValueError("CSV is missing required 'resmplDatesLoc' column")

    data_wgen = data_wgen.copy()
    data_wgen["resmplDatesLoc"] = pd.to_datetime(
        sampled_dates["resmplDatesLoc"], errors="raise"
    ).to_numpy()

    data_wgen = data_wgen.reset_index(drop=True)
    for column in WGEN_COLUMNS[:3]:
        data_wgen[column] = pd.to_numeric(data_wgen[column], errors="raise").astype(int)
    source_years = data_wgen["source_year"].dropna().astype(int).drop_duplicates().tolist()
    if not source_years or source_years != list(range(source_years[0], source_years[-1] + 1)):
        raise ValueError("WGEN source years must be present and consecutive")

    leap_mask = data_wgen["source_month"].eq(2) & data_wgen["source_day"].eq(29)
    leap_counts = data_wgen.loc[leap_mask].groupby("source_year").size()
    row_counts = data_wgen.groupby("source_year", sort=False).size()
    source_leap_years = set(leap_counts.index.astype(int))
    if (leap_counts > 1).any():
        raise ValueError("A WGEN source year contains more than one Feb 29 row")
    if data_wgen.duplicated(["source_year", "source_month", "source_day"]).any():
        raise ValueError("A WGEN source year contains duplicate calendar dates")
    month = data_wgen["source_month"]
    day = data_wgen["source_day"]
    month_max_day = month.map({1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
                               7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31})
    source_leap_by_row = data_wgen["source_year"].isin(source_leap_years)
    february_max = month.eq(2) & source_leap_by_row
    month_max_day = month_max_day.where(~february_max, 29)
    if month_max_day.isna().any() or day.lt(1).any() or day.gt(month_max_day).any():
        raise ValueError("WGEN source dates contain an invalid month/day")
    day_key = month * 100 + day
    same_year = data_wgen["source_year"].eq(data_wgen["source_year"].shift())
    if (same_year & day_key.le(day_key.shift())).any():
        raise ValueError("WGEN dates are not in calendar order within each source year")
    for source_year, count in row_counts.items():
        expected = 366 if int(source_year) in source_leap_years else 365
        if count != expected:
            raise ValueError(
                f"WGEN source year {source_year} has {count} rows; expected {expected}"
            )

    target_years = {
        source_year: start_year + offset
        for offset, source_year in enumerate(source_years)
    }
    if max(target_years.values()) > 9999:
        raise ValueError("Aligned target calendar would exceed year 9999")
    target_leap = {year: calendar.isleap(target) for year, target in target_years.items()}
    target_leap_by_row = data_wgen["source_year"].map(target_leap)
    drop_mask = leap_mask & ~target_leap_by_row
    kept = data_wgen.loc[~drop_mask].copy()
    kept["_source_position"] = kept.index.astype(float)
    kept["_inserted_leap_day"] = False

    # Only years where the target is leap and source is not need inserted rows.
    insert_years = [
        year for year, is_leap in target_leap.items()
        if is_leap and year not in source_leap_years
    ]
    inserted_rows = []
    if insert_years:
        source_rows = data_wgen.set_index(
            ["source_year", "source_month", "source_day"]
        )
        for source_year in insert_years:
            feb28 = source_rows.loc[(source_year, 2, 28)].copy()
            mar1 = source_rows.loc[(source_year, 3, 1)]
            inserted = feb28.copy()
            inserted["source_year"] = source_year
            inserted["source_month"] = 2
            inserted["source_day"] = 29
            inserted["resmplDatesLoc"] = pd.NaT
            inserted["_inserted_leap_day"] = True
            for column in CLIMATE_COLUMNS:
                inserted[column] = (feb28[column] + mar1[column]) / 2
            mar1_position = int(data_wgen.index[
                data_wgen["source_year"].eq(source_year)
                & data_wgen["source_month"].eq(3)
                & data_wgen["source_day"].eq(1)
            ][0])
            inserted["_source_position"] = mar1_position - 0.5
            inserted_rows.append(inserted)

    if inserted_rows:
        aligned = pd.concat([kept, pd.DataFrame(inserted_rows)], ignore_index=True)
        aligned.sort_values("_source_position", kind="stable", inplace=True)
    else:
        aligned = kept
    aligned.reset_index(drop=True, inplace=True)
    aligned.drop(columns=["_source_position"], inplace=True)
    expected_rows = sum(365 + int(is_leap) for is_leap in target_leap.values())
    if len(aligned) != expected_rows:
        raise ValueError(
            f"Calendar alignment produced {len(aligned)} rows; expected {expected_rows}"
        )
    aligned["resmplDatesLoc"] = pd.to_datetime(
        aligned["resmplDatesLoc"], errors="coerce"
    )
    return aligned


def replace_zero_leap_day_wind(wind):
    """Replace zero historical Feb 29 wind with the neighboring-day mean."""
    wind = wind.copy()
    original_wind = wind.set_index("date")["wind"]
    leap_zero = (
        wind["date"].dt.month.eq(2)
        & wind["date"].dt.day.eq(29)
        & wind["date"].dt.year.between(1948, 2020)
        & wind["wind"].eq(0)
    )
    for date in wind.loc[leap_zero, "date"]:
        before = date - pd.Timedelta(days=1)
        after = date + pd.Timedelta(days=1)
        if before in original_wind.index and after in original_wind.index:
            wind.loc[wind["date"].eq(date), "wind"] = (
                original_wind.loc[before] + original_wind.loc[after]
            ) / 2
    return wind


def add_wind(
    hist_file_name,
    hist_dir,
    wgen_dir,
    wgen_sampled_dates,
    hist_date_start="1/1/1915",
    hist_date_end="12/31/2021",
    start_year=DEFAULT_START_YEAR,
):
    """Return one calendar-aligned Product B VIC met file with historical wind."""
    wind = pd.read_csv(
        os.path.join(hist_dir, hist_file_name), usecols=[3], sep=r"\s+", header=None
    )
    wind.columns = ["wind"]
    wind_dates = pd.date_range(hist_date_start, hist_date_end, freq="D")
    if len(wind) != len(wind_dates):
        raise ValueError(
            f"Historical wind row-count mismatch for {hist_file_name}: "
            f"{len(wind)} values for {len(wind_dates)} dates"
        )
    wind.insert(0, "date", wind_dates)

    # Replace only zero historical wind on leap days within the task period.
    wind = replace_zero_leap_day_wind(wind)

    wgen_name = hist_file_name.replace("data", "meteo", 1)
    wgen = pd.read_csv(
        os.path.join(wgen_dir, wgen_name), usecols=range(6), sep=r"\s+", header=None
    )
    wgen.columns = WGEN_COLUMNS
    if wgen[WGEN_COLUMNS[:3]].isna().any().any():
        raise ValueError(f"WGEN date columns contain missing values in {wgen_name}")
    aligned = align_wgen_calendar(wgen, wgen_sampled_dates, start_year=start_year)
    combined = aligned.merge(
        wind,
        how="left",
        left_on="resmplDatesLoc",
        right_on="date",
        validate="many_to_one",
        sort=False,
    )
    combined.drop(columns=["date"], inplace=True)

    # Newly inserted Feb 29 rows have no CSV sample date; estimate their wind
    # from the already-mapped neighboring days, as specified by the task.
    inserted_positions = combined.index[combined["_inserted_leap_day"]].tolist()
    for position in inserted_positions:
        if position == 0 or position == len(combined) - 1:
            raise ValueError("Cannot interpolate wind for an inserted boundary leap day")
        before = combined.loc[position - 1, "wind"]
        after = combined.loc[position + 1, "wind"]
        if pd.isna(before) or pd.isna(after):
            raise ValueError("Cannot interpolate inserted leap-day wind: neighbor is missing")
        combined.loc[position, "wind"] = (before + after) / 2

    return combined[OUTPUT_COLUMNS]


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Append historical wind to Product B WGEN VIC met files."
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=DEFAULT_START_YEAR,
        help=f"first Gregorian output year (default: {DEFAULT_START_YEAR})",
    )
    args = parser.parse_args(argv)

    # Resolve paths only when executed so importing helpers never starts the job.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from utils.paths import get_base_dir, get_module_generated_dir, get_product_b_chunk_plan

    plan = get_product_b_chunk_plan()
    base_dir = get_base_dir()
    wgen_dir = base_dir / "WGEN" / "Product_B" / "1"
    wind_dir = base_dir / "Historical_Climate_LTO" / "1_Historical"
    output_dir = get_module_generated_dir("mod_forcing/vic") / "input" / "Product_B" / "1"
    date_map_path = base_dir / "WGEN" / f"resampled.dates_Product_B_{plan['wgen_simulation_years']}yr.csv"

    if not date_map_path.is_file():
        raise FileNotFoundError(
            f"No WGEN date map is available for the configured "
            f"{plan['wgen_simulation_years']}-year simulation: {date_map_path}"
        )
    sampled_dates = pd.read_csv(date_map_path)
    if "resmplDatesLoc" not in sampled_dates.columns:
        raise ValueError("Date map is missing required column 'resmplDatesLoc'")
    sampled_dates["resmplDatesLoc"] = pd.to_datetime(
        sampled_dates["resmplDatesLoc"], format="%m/%d/%Y", errors="raise"
    )

    historical_files = sorted(
        path.name for path in wind_dir.iterdir()
        if path.is_file() and path.name.startswith("data_")
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Start year: {args.start_year}")
    print(f"Configured WGEN simulation: {plan['wgen_simulation_years']} years")
    print(f"CalSim chunks: {plan['chunk_count']} x {plan['calsim_chunk_years']} years; "
          f"discarding {plan['discarded_years']} trailing years "
          f"({plan['discarded_months']} months)")
    print(f"Historical wind files: {len(historical_files)}")
    print(f"Date-map rows: {len(sampled_dates)}")

    for index, hist_file_name in enumerate(historical_files, start=1):
        print(f"Processing {index}/{len(historical_files)}: {hist_file_name}")
        processed = add_wind(
            hist_file_name,
            hist_dir=str(wind_dir),
            wgen_dir=str(wgen_dir),
            wgen_sampled_dates=sampled_dates,
            start_year=args.start_year,
        )
        out_name = hist_file_name.replace("data", "meteo", 1)
        processed.to_csv(output_dir / out_name, index=False, header=False, sep="\t")
    print(f"Done: wrote {len(historical_files)} files to {output_dir}")


if __name__ == "__main__":
    main()
