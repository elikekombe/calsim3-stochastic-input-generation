# Product A Date Configuration Guide

## Purpose

Product A date ranges are now stored in the repository's configuration instead of being repeated as defaults throughout the Product A pipeline. This makes common date changes easier to manage and keeps scripts that use the same period in sync.

The configuration files are:

- `config_default.json` — tracked example/default values.
- `config.json` — local machine settings. It overrides the default configuration and is normally git-ignored. Keep the existing `data_dir` value when changing dates.

Date settings live under `periods.product_a`. They are separated by purpose because input preparation, training, simulation, validation, climate processing, and analysis can use different windows.

## How a script gets dates from config

`utils/paths.py` loads `config_default.json`, applies values from `config.json`, and provides the `get_periods()` helper. A Product A script can then request the dates it needs, for example:

```python
validation = get_periods("product_a")["validation"]
start_date = validation["start_date"]
end_date = validation["end_date"]
```

I identified command-line date options by checking each script's argument parser for options such as `--start_date`, `--end_date`, `--clip_period`, and `--start_date_vic`, then tracing where the parsed `args` values are used. A command-line option can still exist after this change: for the scripts listed below, the config supplies the default and an explicitly provided command-line value takes precedence for that run.

## Current default periods

The defaults in the current config include:

| Config section | Current default | Used for |
|---|---|---|
| `wind_input` | 1915-01-01 to 2021-12-31 | Historical wind input used when appending wind to WGEN files |
| `wgen_input` | 1915-01-01 to 2018-12-31 | Product A WGEN input range for compilation |
| `training` | 1921-10-01 to 1971-09-30 | Product A training portion of the split-sample period |
| `simulation` | 1971-10-01 to 2018-09-30 | Product A simulation portion |
| `validation` | 1971-10-01 to 2018-09-30; WY 1972-2018 | Product A validation, output clipping, and validation labels |
| `climate_validation` | WY 1922-2018 | Historical climate/WYT validation outputs |
| `input_compilation` | Module-specific | VIC date ranges and optional precipitation clips for each compiler |
| `et_quantile_mapping` | Training WY 1921-1971; simulation WY 1972-2018 | Product A ET quantile mapping |
| `climate_processing` | 1920-10-01 to 2021-09-30 | Climate processing defaults; CLI dates can override |
| `analysis` | 1921-10-01 to 2018-09-30 | Reservoir evaporation analysis windows |
| `oroville_daily_precip` | 1915-10-01 to 2018-09-30 | Product A Oroville daily precipitation window |

The values are separate on purpose. For example, changing `validation` does not automatically change `training`, `wind_input`, or `input_compilation`.

## Example: end validation one water year earlier

If the requested change is to validate through WY 2017 instead of WY 2018, update the relevant entries in `config.json`:

```json
"simulation": {
  "start_date": "1971-10-01",
  "end_date": "2017-09-30"
},
"validation": {
  "start_date": "1971-10-01",
  "end_date": "2017-09-30",
  "start_water_year": 1972,
  "end_water_year": 2017
}
```

This is an example only; it does not change the repository or run a pipeline. Keep the calendar dates and water-year numbers consistent. If a specific input compiler or climate output also needs a shorter period, update its corresponding `input_compilation`, `climate_processing`, or `climate_validation` entry as appropriate. Do not change unrelated periods just because they contain a later year.

For a script that supports a CLI date option, the command can override the config for one run. For example, a compiler with `--start_date` and `--end_date` can be called with:

```powershell
python .\mod_hydrology\calsimhydro\_1_compile_precip.py `
  --product A `
  --start_date 1915-01-01 `
  --end_date 2017-12-31
```

Only use options that the selected script actually accepts. CLI options shown here are an example and were not executed as part of this documentation.

## Scripts updated to read Product A periods from config

### Forcing

- `mod_forcing/climate/_1_pp_point_locations.py`
- `mod_forcing/climate/_2_uhh_basin_averages.py`
- `mod_forcing/vic/_1_append_wind_wgen_hist.py`
- `mod_forcing/vic/_2_compile_rim_inflows.py`

### Hydrology and water-year types

- `mod_hydrology/calsimhydro/_1_compile_precip.py`
- `mod_hydrology/calsimhydro/_2_compile_et.py`
- `mod_hydrology/calsimhydro/_3_postprocess_product_a.py`
- `mod_hydrology/calsimhydro_ee/_1_compile_precip_EE.py`
- `mod_hydrology/calsimhydro_ee/_2_postprocess_product_a.py`
- `mod_hydrology/delta_channel_depletion/_1_compile_precip_DETAW.py`
- `mod_hydrology/delta_channel_depletion/_2_postprocess_product_a.py`
- `mod_hydrology/rim_inflow/_2_qmap_historical_validation.py`
- `mod_hydrology/small_watersheds/_1_compile_precip_sws.py`
- `mod_hydrology/small_watersheds/_2_postprocess_product_a.py`
- `mod_hydrology/water_year_types/_1_calc_WYTs.py`
- `mod_hydrology/water_year_types/_2_compare_wyts.py`

### Other modules

- `mod_other/instream_flows/_1_min_flow_feather.py`
- `mod_other/instream_flows/_2_sjr_rest_req.py`
- `mod_other/miscellaneous/_2_DeltaAccretionForNDOI.py`
- `mod_other/miscellaneous/_3_hybrid.py`
- `mod_other/miscellaneous/_4_qmap.py`
- `mod_other/upper_watershed/_2_qmap.py`
- `mod_other/upper_watershed/_3_hybrid.py`
- `mod_other/upper_watershed/_4_pge_wy_allocation.py`

### Reservoirs and postprocessing

- `mod_reservoir/evaporation/_2_run_reservoir_evap.py`
- `mod_reservoir/storage_curves/_1_wyt_index_curves.py`
- `mod_reservoir/storage_curves/_2_qmap.py`
- `mod_reservoir/storage_curves/_3_oroville_daily_precip.py`
- `mod_reservoir/storage_curves/_4_oroville_level5.py`
- `postprocessing/calsim_runs/_productA_postproc.py`
- `postprocessing/sv_compile/product_a_historical_validation.py`

### Shared utilities

- `utils/paths.py` — loads config and defines `get_periods()`.
- `utils/qmap_product_a_from_pairs.py` — gets Product A training and simulation dates.
- `utils/wyt_monthlyavg_framework.py` — uses Product A validation dates for default plot windows; callers can still provide explicit plot dates.

## Date options that remain available on the CLI

These scripts now use config values as the Product A default while preserving their date command-line options:

| Script | CLI options that override Product A config |
|---|---|
| `mod_forcing/vic/_2_compile_rim_inflows.py` | `--start_date`, `--end_date` |
| `mod_forcing/climate/_2_uhh_basin_averages.py` | `--start_date`, `--end_date` |
| `mod_hydrology/calsimhydro/_1_compile_precip.py` | `--start_date`, `--end_date`, `--clip_period` |
| `mod_hydrology/calsimhydro/_2_compile_et.py` | `--start_date`, `--end_date` |
| `mod_hydrology/calsimhydro_ee/_1_compile_precip_EE.py` | `--start_date_vic`, `--end_date_vic`, `--clip_period` |
| `mod_hydrology/delta_channel_depletion/_1_compile_precip_DETAW.py` | `--start_date`, `--end_date`, `--clip_period` |
| `mod_hydrology/small_watersheds/_1_compile_precip_sws.py` | `--start_date`, `--end_date`, `--clip_period` |

The postprocessing scripts generally use the configured validation years directly rather than accepting date flags. Check that script's `--help` output before assuming a date option exists.

## Dates not moved to Product A config

This change does not make every date in the repository configurable. The list above is the complete list of scripts updated by this Product A date-config change; the following date uses remain fixed or are handled separately:

- **Product B processing:** Product B scripts, 100-year templates, synthetic year labels, and chunk dates were not changed. These include Product B compiler/postprocessor scripts and `utils/qmap_product_b_from_pairs.py`.
- **Fixed model/template requirements:** Dates used to build Product B calendar templates, initialize historical series, or satisfy model file formats remain fixed by those formats. Changing them would require a separate scientific/workflow decision.
- **External run artifact names:** Some CalSimHydro and related scenario-folder paths contain labels such as `1972-2018`. Those paths refer to existing external model outputs; changing a config date does not rename or regenerate those files.
- **Separate diagnostics and comparison scripts:** `mod_hydrology/calsimhydro/_0_compare_et_cshydro_vic.py` still has its own comparison dates and no config-based date default. `mod_forcing/climate/precip_5way_comparison.py` is also a separate comparison workflow; its dates are not controlled by the new Product A settings.
- **Generic DSS read windows:** `utils/wyt_monthlyavg_framework.py` uses config for Product A plot windows, but its generic historical DSS read defaults remain separately defined. Its callers include `mod_hydrology/tulare_gw_terms/_1_wyt_monthlyavg.py`, `mod_other/upper_watershed/_1_wyt_monthlyavg.py`, and `mod_other/miscellaneous/_1_wyt_monthlyavg.py`.
- **Other fixed historical windows:** `mod_other/closure_terms/_1_ct_calculation.py`, `mod_other/instream_flows/_2_sjr_rest_req.py`'s broad DSS input-read window, and `utils/calculate_correlations_finder.py` still have their own historical date ranges. The SJR script does use config for its Product A plotting and validation period; its broad DSS read window is separate.
- **Product B utilities:** `utils/qmap_product_b_from_pairs.py` and Product B compilation/postprocessing scripts retain their Product B template dates and are not controlled by `periods.product_a`.

Some scripts can therefore use config for their Product A validation output while retaining a broader fixed DSS input-read window. That broader read window is not the same as the period used to clip or validate Product A results.

## Testing status

The added configuration tests check the configured validation years, the training/validation boundary, and the presence of the module-specific input periods. Python syntax and JSON checks were also run. The full Product A workflow was not run, so generated hydrology outputs still need to be validated when the pipeline is run.

## Local workflow and Git status

Edit `config.json` for your machine. `config_default.json` contains the shared starting defaults. The local `config.json` may contain a machine-specific network `data_dir`, so do not replace it with the example config without preserving that path.

The changes described here are local working changes. They have not been committed or pushed.
