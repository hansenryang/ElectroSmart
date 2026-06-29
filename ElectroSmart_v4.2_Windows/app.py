import streamlit as st
import io
import zipfile
import pandas as pd
import matplotlib.pyplot as plt
from galvani import BioLogic

from plotting import (
    plot_all_EIS_precond,
    semiellipse_fit,
    get_current_from_mpr,
    plot_cp_ewe,
    analyze_sand_and_polarization,
    plot_limiting_peis_fit,
    plot_all_CP_LC,
    plot_sands_analysis,
    analyze_current_fraction_mpr,
    analyze_diffusion_coefficient,
)


# --- Helper Functions ---
def get_discard_parameters():
    col1, col2 = st.columns(2)
    with col1:
        left = st.number_input(
            "Points to discard (left):", min_value=0, value=2, key="left_input"
        )
    with col2:
        right = st.number_input(
            "Points to discard (right):", min_value=0, value=2, key="right_input"
        )
    return left, right


def single_or_dual_ellipse(key=None):
    return st.radio(
        "Fit Choice:",
        ["Single Ellipse", "Two Ellipse (Recommended)", "Single/Two Ellipse"],
        horizontal=True,
        index=1,
        key=key,
    )


def impedance_technique_radio(key):
    return st.radio(
        "Technique:",
        ["Linear fit", "Semi-ellipse fit"],
        horizontal=True,
        index=1,
        key=key,
    )


def process_limiting_current_bundles(files, area_cm2):
    # Updated pattern: We just need to identify the Run Type (CP, OCV, PEIS)
    # This assumes the prefix is everything before the first underscore
    grouped_data = {}

    # 1. Group files by prefix while maintaining their relative upload/discovery order
    for f in files:
        parts = f.name.split("_")
        if len(parts) < 2:
            continue

        prefix = parts[0]
        # Identify type by checking for keywords in the filename
        run_type = None
        if "CP" in f.name.upper():
            run_type = "CP"
        elif "OCV" in f.name.upper():
            run_type = "OCV"
        elif "PEIS" in f.name.upper():
            run_type = "PEIS"

        if run_type:
            if prefix not in grouped_data:
                grouped_data[prefix] = []
            grouped_data[prefix].append({"name": f.name, "type": run_type, "obj": f})

    results = []
    for prefix, file_list in grouped_data.items():
        # 2. Iterate through the files as they were provided (Date Modified order)
        i = 0
        while i < len(file_list) - 2:
            f_cp = file_list[i]
            if f_cp["type"] == "CP":
                f_ocv = file_list[i + 1]
                f_peis = file_list[i + 2]

                # Check if the next two files complete the triplet
                if f_ocv["type"] == "OCV" and f_peis["type"] == "PEIS":
                    current_mA = get_current_from_mpr(f_cp["obj"])
                    density = current_mA / area_cm2 if area_cm2 > 0 else 0
                    results.append(
                        {
                            "prefix": prefix,
                            "Bundled Files": f"{f_cp['name']}\n{f_ocv['name']}\n{f_peis['name']}",
                            "Current Density (mA/cm²)": density,
                            "Applied Current (mA)": current_mA,
                            "f_cp": f_cp["obj"],
                            "f_peis": f_peis["obj"],
                        }
                    )
                    i += 3  # Move to next possible triplet
                    continue
            i += 1
    return results


def fit_current_fraction_eis_resistances(
    cell_label, pos_eis_file, neg_eis_file, discard_left, discard_right, fit_choice
):
    resistances = {}
    fit_tables = []

    for resistance_key, run_label, f_obj in [
        ("R_pos", "Positive", pos_eis_file),
        ("R_neg", "Negative", neg_eis_file),
    ]:
        fit_df, trend_buf, _, _ = semiellipse_fit(
            "Current Fraction",
            cell_label,
            discard_left,
            discard_right,
            f_obj,
            run_label,
            fit_choice == "Two Ellipse (Recommended)",
            fit_choice == "Single Ellipse",
        )
        fit_df = fit_df.sort_values("Cycle").reset_index(drop=True)
        first_cycle = fit_df.iloc[0]
        last_cycle = fit_df.iloc[-1]

        resistances[resistance_key] = [
            first_cycle["R_bulk"],
            first_cycle["R_i"],
            last_cycle["R_bulk"],
            last_cycle["R_i"],
        ]

        fit_table = fit_df.copy()
        fit_table.insert(0, "Polarity", run_label)
        fit_table["EIS File"] = f_obj.name
        fit_tables.append(fit_table)

    return resistances, pd.concat(fit_tables, ignore_index=True)


def build_preconditioning_analysis_zip(cell_label):
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        for key in ["Positive", "Negative"]:
            plot_key = f"data_{key}"
            if plot_key in st.session_state:
                zf.writestr(
                    st.session_state[f"fname_{key}"],
                    st.session_state[plot_key].getvalue(),
                )

            if f"fit_df_{key}" in st.session_state:
                zf.writestr(
                    f"{key}_summary.csv",
                    st.session_state[f"fit_csv_{key}"].getvalue(),
                )
                zf.writestr(
                    f"{key}_trend.png",
                    st.session_state[f"fit_fig_{key}"].getvalue(),
                )
                for fname, buf in st.session_state[f"fit_cycles_{key}"]:
                    zf.writestr(f"{key}_{fname}", buf.getvalue())

    return zip_buf.getvalue()


def build_limiting_impedance_zip(cell_label, include_summary=True, include_individual=True):
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        if include_summary:
            if "img_LC_PEIS_all" in st.session_state:
                zf.writestr(
                    st.session_state["fname_png_LC_PEIS_all"],
                    st.session_state["img_LC_PEIS_all"].getvalue(),
                )
            if "peis_summary_all" in st.session_state:
                zf.writestr(
                    st.session_state["fname_csv_LC_PEIS_all"],
                    st.session_state["peis_summary_all"].to_csv(index=False),
                )

        if include_individual and "lim_bundles_peis" in st.session_state:
            for idx, bundle in enumerate(st.session_state["lim_bundles_peis"]):
                fit_buf = bundle.get("fig_peis")
                if fit_buf:
                    zf.writestr(
                        f"{cell_label}_Run_{idx + 1}_PEIS_Plot.png",
                        fit_buf.getvalue(),
                    )

    return zip_buf.getvalue()


def prepare_limiting_current_runs(bundles, cell_label):
    cp_summaries = []
    all_cp_raw_data = []

    for i, b in enumerate(bundles):
        if "df_cp" not in b or "img_cp" not in b:
            buf_cp, df_cp = plot_cp_ewe(
                b["f_cp"], cell_label, b["Current Density (mA/cm²)"]
            )
            b["img_cp"] = buf_cp
            b["df_cp"] = df_cp

        cp_summaries.append((b["df_cp"], b["Current Density (mA/cm²)"]))

        df_cp_export = b["df_cp"].copy()
        df_cp_export["density_mA_cm2"] = b["Current Density (mA/cm²)"]
        df_cp_export["Run_no"] = i + 1
        all_cp_raw_data.append(df_cp_export)

    cp_raw_combined = (
        pd.concat(all_cp_raw_data, ignore_index=True)
        if all_cp_raw_data
        else pd.DataFrame()
    )
    return bundles, cp_summaries, cp_raw_combined


def display_limiting_current_runs(bundles):
    st.write("#### Individual Runs")
    for i in range(0, len(bundles), 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j < len(bundles):
                idx = i + j
                b = bundles[idx]
                with cols[j]:
                    with st.expander(
                        f"Run {idx+1}: {b['Current Density (mA/cm²)']:.3f} mA/cm²"
                    ):
                        st.write("**Files**")
                        st.write(b["Bundled Files"])
                        st.write("**Voltage vs Time**")
                        st.image(b["img_cp"])
    st.success("All Runs are shown!!")


# --- Main App ---
st.set_page_config(
    page_title="ElectroSmart",
    page_icon="Logo.png",
    menu_items={
        "Report a bug": "https://github.com/hansenryang/electrosmart/issues",
        "About": ("ElectroSmart v4.2 — Balsara Lab, UC Berkeley\n\n"
                  "**Contact:** hansenry@berkeley.edu, zironghe@berkeley.edu\n\n"
                  "**Acknowledgements & Credits:** \n - If this software contributes to any " 
                  "publications outside the Balsara Lab, please acknowledge the Balsara Lab, University of California, Berkeley.\n\n"
                  "**References:**\n - Limiting Current: Zach J. Hoffman *et al* 2023 *J. Electrochem. Soc.* **170** 120524 \n"
                  "- Current Fraction/Diffusion Coefficient: Zach J. Hoffman *et al* 2021 *Solid State Ionics* **370** 115751")
    }
)

st.markdown("""
    <style>
    .tooltip {
        position: relative;
        display: inline-block;
        cursor: pointer;
        font-size: 28px;
        vertical-align: middle;
        margin-left: 10px;
    }
    .tooltip .tooltiptext {
        visibility: hidden;
        width: 320px;
        background-color: #1E1E1E;
        color: #FFFFFF;
        text-align: left;
        border-radius: 6px;
        padding: 12px;
        position: absolute;
        z-index: 999;
        top: 125%; /* Position below the star */
        left: 50%;
        margin-left: -160px;
        opacity: 0;
        transition: opacity 0.2s;
        font-size: 14px;
        font-family: sans-serif;
        line-height: 1.4;
        border: 1px solid #444;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.3);
    }
    .tooltip:hover .tooltiptext {
        visibility: visible;
        opacity: 1;
    }
    .title-container {
        display: flex;
        align-items: center;
        margin-bottom: 20px;
    }
    .main-title {
        font-size: 42px;
        font-weight: 700;
        margin: 0;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown(
    """
    <style>
    div[data-testid="stButton"] > button[kind="secondary"],
    div[data-testid="stButton"] > button[kind="secondary"]:hover {
        background-color: #0068c9 !important;
        color: #ffffff !important;
        border-color: #0068c9 !important;
    }

    div[data-testid="stDownloadButton"] > button,
    div[data-testid="stDownloadButton"] > button:hover {
        background-color: #09ab3b !important;
        color: #ffffff !important;
        border-color: #09ab3b !important;
    }

    div[data-testid="stButton"] > button[kind="primary"],
    div[data-testid="stButton"] > button[kind="primary"]:hover {
        background-color: #f63366 !important;
        color: #ffffff !important;
        border-color: #f63366 !important;
    }

    div[data-testid="stButton"] > button p,
    div[data-testid="stDownloadButton"] > button p {
        background-color: transparent !important;
        color: #ffffff !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("ElectroSmart")

st.caption("*Check the ⋮ menu (top right) for app info and acknowledgements.*")

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0
col_a, col_b = st.columns(2)
with col_a:
    cell_type = st.text_input("Cell Type", placeholder="LiIn Trilayer")
with col_b:
    cell_label = st.text_input("Cell Label", placeholder="Cell 53")

uploaded_files = st.file_uploader(
    "Upload .mpr runs",
    type=["mpr"],
    accept_multiple_files=True,
    key=f"up_{st.session_state.uploader_key}",
)

if st.button("Clear files", key="clear_files_button", type="primary"):
    st.session_state.uploader_key += 1
    st.rerun()

if not (cell_type and cell_label and uploaded_files):
    cell_type_indicator = " cell type," if not (cell_type) else ""
    cell_label_indicator = " cell label," if not (cell_label) else ""
    file_indicator = " file upload." if not (uploaded_files) else ""

    st.warning(
        f"Please input{cell_type_indicator}{cell_label_indicator}{file_indicator}"
    )


if cell_type and cell_label and uploaded_files:

    # State cleanup if files change
    curr_fnames = [f.name for f in uploaded_files]
    if (
        "last_fnames" not in st.session_state
        or st.session_state.last_fnames != curr_fnames
    ):
        for k in list(st.session_state.keys()):
            if k.startswith(
                (
                    "fig_",
                    "data_",
                    "fname_",
                    "fit_",
                    "lim_",
                    "peis_",
                    "img_",
                    "sands_",
                    "polarization_",
                    "cf_",
                    "diffusion_",
                )
            ):
                st.session_state.pop(k)
        st.session_state.last_fnames = curr_fnames

    mpr_files = list(uploaded_files)  # uploader already filters to .mpr

    st.divider()
    analysis_type = st.radio(
        "Analysis:",
        [
            "Preconditioning",
            "Limiting Current",
            "Current Fraction",
            "Diffusion Coefficient",
        ],
        horizontal=True,
    )

    if analysis_type == "Preconditioning":
        if not mpr_files:
            st.warning("Please upload .mpr files for Preconditioning analysis.")
            st.stop()

        peis_files = [f for f in mpr_files if "PEIS" in f.name]
        if not peis_files:
            st.warning("No PEIS files detected. Please upload at least two PEIS .mpr files.")
            st.stop()

        peis_file_names = [f.name for f in peis_files]

        st.write("#### Identify PEIS Files")
        p1, p2 = st.columns(2)
        pos_peis_name = p1.selectbox("Positive PEIS file", peis_file_names, key="precond_pos_peis")
        neg_peis_default_idx = 1 if len(peis_file_names) > 1 else 0
        neg_peis_name = p2.selectbox(
            "Negative PEIS file",
            peis_file_names,
            index=neg_peis_default_idx,
            key="precond_neg_peis",
        )

        precond_same_file = pos_peis_name == neg_peis_name
        if precond_same_file:
            st.warning(
                "Positive and Negative PEIS files must be different. "
                "Please select a distinct file for each polarity."
            )
        else:
            selections = {"Positive": pos_peis_name, "Negative": neg_peis_name}
            st.divider()
            tech = impedance_technique_radio("preconditioning_impedance_technique")

            if tech == "Linear fit":
                st.warning("This technique is not yet supported.")

            if tech == "Semi-ellipse fit":
                discard_left, discard_right = get_discard_parameters()
                fit_choice = single_or_dual_ellipse("preconditioning_fit_choice")

                if st.button("Generate EIS Plots"):

                    with st.spinner(
                        f"Analyzing Positive and Negative PEIS for {cell_label}... This may take a moment."
                    ):
                        for key in ["Positive", "Negative"]:
                            f_obj = next(
                                f for f in mpr_files if f.name == selections[key]
                            )
                            img_buf = plot_all_EIS_precond(
                                cell_type, cell_label, f_obj, key
                            )
                            st.session_state[f"data_{key}"] = img_buf
                            st.session_state[f"fname_{key}"] = (
                                f"{cell_label}_{key}_Plot.png"
                            )

                            df, sum_fig, csv_data, cyc_imgs = semiellipse_fit(
                                cell_type,
                                cell_label,
                                discard_left,
                                discard_right,
                                f_obj,
                                key,
                                fit_choice == "Two Ellipse (Recommended)",
                                fit_choice == "Single Ellipse",
                            )

                            st.session_state[f"fit_df_{key}"] = df
                            st.session_state[f"fit_fig_{key}"] = sum_fig
                            st.session_state[f"fit_csv_{key}"] = csv_data
                            st.session_state[f"fit_cycles_{key}"] = cyc_imgs

                        st.session_state["precond_zip"] = build_preconditioning_analysis_zip(cell_label)
                        st.toast("EIS analysis complete!", icon="✅")

                # --- PERSISTENT DISPLAY AREA ---

                has_cycle_plots = (
                    "data_Positive" in st.session_state
                    and "data_Negative" in st.session_state
                )
                has_fit_data = (
                    "fit_df_Positive" in st.session_state
                    or "fit_df_Negative" in st.session_state
                )

                if has_cycle_plots or has_fit_data:

                    st.download_button(
                        "📦 Download All EIS Analysis Files (ZIP)",
                        st.session_state["precond_zip"],
                        f"{cell_label}_Full_Analysis.zip",
                        "application/zip",
                        width="stretch",
                    )

                if has_cycle_plots:
                    c1, c2 = st.columns(2)

                    for i, key in enumerate(["Positive", "Negative"]):
                        with [c1, c2][i]:
                            st.subheader(f"{key} PEIS")
                            st.image(st.session_state[f"data_{key}"])
                            st.download_button(
                                f"Download {key} PNG",
                                st.session_state[f"data_{key}"],
                                st.session_state[f"fname_{key}"],
                                "image/png",
                                key=f"btn_{key}",
                            )

                st.divider()

                # --- PERSISTENT DISPLAY ---

                if has_fit_data:
                    col1, col2 = st.columns(2)
                    for i, key in enumerate(["Positive", "Negative"]):
                        with [col1, col2][i]:
                            if f"fit_df_{key}" in st.session_state:
                                st.subheader(f"{key} Fit")
                                st.image(st.session_state[f"fit_fig_{key}"])

                                # Individual Summary Downloads
                                c_dl1, c_dl2 = st.columns(2)
                                c_dl1.download_button(
                                    f"CSV ({key})",
                                    st.session_state[f"fit_csv_{key}"].getvalue(),
                                    f"{key}_data.csv",
                                )
                                c_dl2.download_button(
                                    f"Trend ({key})",
                                    st.session_state[f"fit_fig_{key}"].getvalue(),
                                    f"{key}_trend.png",
                                )

                                # Expandable Individual Cycles
                                with st.expander(f"Individual Cycle Plots ({key})"):
                                    for fname, img_buf in st.session_state[
                                        f"fit_cycles_{key}"
                                    ]:
                                        st.image(img_buf, caption=fname)
                                        st.download_button(
                                            f"Download {fname}",
                                            img_buf.getvalue(),
                                            f"{key}_{fname}",
                                            key=f"btn_{key}_{fname}",
                                        )

    if analysis_type == "Limiting Current":
        if not mpr_files:
            st.warning("Please upload .mpr files for Limiting Current analysis.")
            st.stop()

        st.write("### Setup")
        c1, c2, c3 = st.columns(3)

        active_area = c1.number_input(
            "Active Area (cm²):", value=0.079170, format="%.6f"
        )

        elyt_thickness = c2.number_input(
            "Electrolyte Thickness (cm):",
            value=0.0500,
            format="%.4f",
            help="1 um = 1e-4 cm",
        )

        diff_coeff = c3.number_input(
            "Diffusion Coefficient (cm²/s):", value=6.9e-8, format="%.4e"
        )

        bundles = process_limiting_current_bundles(mpr_files, active_area)

        st.write("#### A. Confirm Runs")

        if not bundles:
            st.warning("No CP/OCV/PEIS run bundles were detected.")

        if st.button("Confirm", disabled=not bundles):
            with st.spinner("Preparing run confirmation plots ..."):
                confirmed_bundles, _, _ = prepare_limiting_current_runs(
                    bundles, cell_label
                )
                st.session_state["lim_runs_confirmed"] = True
                st.session_state["lim_bundles_confirmed"] = confirmed_bundles

        if st.session_state.get("lim_runs_confirmed"):
            display_limiting_current_runs(st.session_state["lim_bundles_confirmed"])

        st.divider()
        st.write("#### B. Potentiometric Data")

        if st.button("Process Potentiometric Data", disabled=not bundles):
            with st.spinner("Analyzing Potentiometric Data ..."):
                confirmed_bundles, cp_summaries, _ = prepare_limiting_current_runs(
                    bundles, cell_label
                )

                st.session_state["lim_bundles_confirmed"] = confirmed_bundles
                st.session_state["lim_bundles_cp"] = confirmed_bundles
                st.session_state["fname_cp"] = f"{cell_label}_all_CP_plot.png"
                st.session_state["cp_summary"] = cp_summaries
                cp_plot_buf = plot_all_CP_LC(
                    cell_label, elyt_thickness, cp_summaries
                )
                st.session_state["img_all_CP"] = cp_plot_buf
                s_df, p_df = analyze_sand_and_polarization(cp_summaries)
                st.session_state["sands_df"] = s_df
                st.session_state["fname_sands_csv"] = f"{cell_label}_sands_time.csv"
                st.session_state["polarization_df"] = p_df
                st.session_state["fname_polarization"] = (
                    f"{cell_label}_polarization.csv"
                )

                if not s_df.empty:
                    all_currents = sorted([abs(b["Current Density (mA/cm²)"]) for b in confirmed_bundles])
                    diverged_currents = s_df["Current (mA/cm^2)"].tolist()
                    stable_currents = [
                        i for i in all_currents if round(i, 3) not in diverged_currents
                    ]
                    last_stable = max(stable_currents) if stable_currents else 0
                    first_diverge = (
                        min(diverged_currents) if diverged_currents else max(all_currents)
                    )
                    buf_sands, _ = plot_sands_analysis(
                        s_df, cell_label, elyt_thickness, diff_coeff, last_stable, first_diverge
                    )
                    st.session_state["fname_sands_png"] = f"{cell_label}_Sands_Fit.png"
                    st.session_state["img_sands_fit"] = buf_sands

                st.toast("Processing of Potentiometric Data is complete!", icon="✅")

        if "lim_bundles_cp" in st.session_state:

            zip_limcurr_allCP_buf = io.BytesIO()
            sands_csv = st.session_state["sands_df"].to_csv(index=False)
            polarization_csv = st.session_state["polarization_df"].to_csv(index=False)

            with zipfile.ZipFile(zip_limcurr_allCP_buf, "w") as zf:
                zf.writestr(
                    st.session_state["fname_cp"],
                    st.session_state["img_all_CP"].getvalue(),
                )
                zf.writestr(st.session_state["fname_sands_csv"], sands_csv)
                if "img_sands_fit" in st.session_state:
                    zf.writestr(
                        st.session_state["fname_sands_png"],
                        st.session_state["img_sands_fit"].getvalue(),
                    )
                zf.writestr(st.session_state["fname_polarization"], polarization_csv)

            st.download_button(
                "📂 Download Summary Potentiometric Data (ZIP)",
                zip_limcurr_allCP_buf.getvalue(),
                f"{cell_label}_Limiting_Current_Potentiometric_Analysis.zip",
                "application/zip",
                width="stretch",
            )

            # --- Limiting Current Plot ---
            st.write("#### Combined Polarization Plots")
            st.image(st.session_state["img_all_CP"])

            c1, c2 = st.columns(2)

            # --- Display CSV Contents ---
            c1.write("#### Sand's time Data")
            c1.dataframe(st.session_state["sands_df"], width="stretch")

            # --- Display CSV Contents ---
            c2.write("#### Polarization Data")
            c2.dataframe(st.session_state["polarization_df"], width="stretch")

            # --- Sand's time Plot ---
            if "img_sands_fit" in st.session_state:
                st.write("#### Sand's Time Series Fit")
                st.image(st.session_state["img_sands_fit"])

            # --- Summary Download Buttons ---
            c1, c2, c3, c4 = st.columns(4)

            c1.download_button(
                label="Download all CP Plot PNG",
                data=st.session_state["img_all_CP"].getvalue(),
                file_name=st.session_state["fname_cp"],
                mime="image/png",
            )

            if not st.session_state["sands_df"].empty:
                s_csv = st.session_state["sands_df"].to_csv(index=False).encode("utf-8")
                c2.download_button(
                    "Download Sand's Time CSV",
                    s_csv,
                    st.session_state["fname_sands_csv"],
                    "text/csv",
                )

            if "img_sands_fit" in st.session_state:
                c3.download_button(
                    "Download Sand's Fit PNG",
                    st.session_state["img_sands_fit"].getvalue(),
                    st.session_state["fname_sands_png"],
                    "image/png",
                )

            if not st.session_state["polarization_df"].empty:
                p_csv = (
                    st.session_state["polarization_df"]
                    .to_csv(index=False)
                    .encode("utf-8")
                )
                c4.download_button(
                    "Download Polarization CSV",
                    p_csv,
                    st.session_state["fname_polarization"],
                    "text/csv",
                )

        st.divider()
        st.write("#### C. Impedance Data")

        tech = impedance_technique_radio("limiting_current_impedance_technique")

        if tech == "Linear fit":
            st.warning("This technique is not yet supported.")

        if tech == "Semi-ellipse fit":

            discard_left, discard_right = get_discard_parameters()
            fit_choice = single_or_dual_ellipse("limiting_current_fit_choice")

            if st.button("Process Impedance Data", disabled=not bundles):
                with st.spinner("Analyzing Impedance Data ..."):
                    peis_results = []
                    all_peis_raw_data = []

                    for i, b in enumerate(bundles):
                        b["f_peis"].seek(0)
                        mpr_peis = BioLogic.MPRfile(b["f_peis"])
                        df_peis_raw = pd.DataFrame(mpr_peis.data)
                        df_peis_raw["density"] = b["Current Density (mA/cm²)"]
                        all_peis_raw_data.append(df_peis_raw)

                        fit_img_buf, fit_df, fit_csv = plot_limiting_peis_fit(
                            b["f_peis"],
                            cell_label,
                            f"Run {i+1}",
                            discard_left,
                            discard_right,
                            fit_choice == "Two Ellipse (Recommended)",
                            fit_choice == "Single Ellipse",
                        )
                        b["fig_peis"] = fit_img_buf

                        dens = b["Current Density (mA/cm²)"]
                        fit_df["Run_no"] = i + 1
                        fit_df["Current (mA/cm^2)"] = round(dens, 3)
                        fit_df["R_bulk + R_i"] = fit_df["R_bulk"] + fit_df["R_i"]
                        fit_df = fit_df[
                            [
                                "Run_no",
                                "Current (mA/cm^2)",
                                "R_bulk",
                                "R_i",
                                "R_bulk + R_i",
                            ]
                        ]
                        peis_results.append(fit_df)

                    peis_raw_combined = pd.concat(all_peis_raw_data)
                    st.session_state["lim_bundles_peis"] = bundles
                    st.session_state["peis_summary_all"] = pd.concat(
                        peis_results, ignore_index=True
                    )
                    st.session_state["fname_csv_LC_PEIS_all"] = (
                        f"{cell_label}_all_PEIS_fits.csv"
                    )
                    st.session_state["fname_png_LC_PEIS_all"] = (
                        f"{cell_label}_combined_PEIS_plot.png"
                    )

                    # Build combined PEIS plot once here, store in session state
                    fig_peis_all, ax_peis = plt.subplots(figsize=(10, 6))
                    for dens in peis_raw_combined["density"].unique():
                        subset = peis_raw_combined[peis_raw_combined["density"] == dens]
                        ax_peis.scatter(
                            subset["Re(Z)/Ohm"],
                            subset["-Im(Z)/Ohm"],
                            label=f"{abs(dens):.2f} mA/cm²",
                            s=10,
                            alpha=0.7,
                        )
                    ax_peis.set_xlabel("Re(Z)/Ohm")
                    ax_peis.set_ylabel("-Im(Z)/Ohm")
                    ax_peis.set_title(f"Combined PEIS: {cell_label}")
                    ax_peis.grid(True, linestyle=":", alpha=0.6)
                    ax_peis.set_aspect("equal")
                    n_cols = 2 if len(bundles) > 12 else 1
                    ax_peis.legend(
                        loc="upper left",
                        bbox_to_anchor=(1.02, 1),
                        ncol=n_cols,
                        fontsize="x-small",
                    )
                    peis_plot_buf = io.BytesIO()
                    fig_peis_all.savefig(
                        peis_plot_buf, format="png", dpi=300, bbox_inches="tight"
                    )
                    peis_plot_buf.seek(0)
                    plt.close(fig_peis_all)
                    st.session_state["img_LC_PEIS_all"] = peis_plot_buf

                    st.toast("Processing of Impedance Data is complete!", icon="✅")

            if "lim_bundles_peis" in st.session_state:
                bundles_peis = st.session_state["lim_bundles_peis"]

                st.download_button(
                    "📂 Download Summary Impedance Data (ZIP)",
                    build_limiting_impedance_zip(
                        cell_label, include_summary=True, include_individual=True
                    ),
                    f"{cell_label}_Limiting_Current_Impedance_Analysis.zip",
                    "application/zip",
                    width="stretch",
                )

                st.write("### Impedance Analysis")

                # --- Combined PEIS Summary Plot ---
                st.write("#### Combined PEIS Runs")
                st.image(st.session_state["img_LC_PEIS_all"])

                # --- Display CSV Contents ---
                st.write("#### Fit Summary Data")
                st.dataframe(st.session_state["peis_summary_all"], width="stretch")

                peis_all_df = st.session_state["peis_summary_all"]

                c1, c2, c3 = st.columns(3)

                c1.download_button(
                    label=f"Download {cell_label} Combined PEIS Plot (PNG)",
                    data=st.session_state["img_LC_PEIS_all"].getvalue(),
                    file_name=st.session_state["fname_png_LC_PEIS_all"],
                    mime="image/png",
                )

                all_peis_csv = peis_all_df.to_csv(index=False).encode("utf-8")
                c2.download_button(
                    f"Download {cell_label} all PEIS fits (CSV)",
                    all_peis_csv,
                    st.session_state["fname_csv_LC_PEIS_all"],
                    "text/csv",
                )

                c3.download_button(
                    "Download All EIS Individual Run Fits (ZIP)",
                    build_limiting_impedance_zip(
                        cell_label, include_summary=False, include_individual=True
                    ),
                    f"{cell_label}_Individual_PEIS_Fits.zip",
                    "application/zip",
                )

                st.write("#### Individual Runs")
                for i in range(0, len(bundles_peis), 2):
                    cols = st.columns(2)
                    for j in range(2):
                        if i + j < len(bundles_peis):
                            idx = i + j
                            b = bundles_peis[idx]
                            with cols[j]:
                                with st.expander(
                                    f"Run {idx+1}: {b['Current Density (mA/cm²)']:.3f} mA/cm²"
                                ):
                                    st.write("**PEIS Semi-ellipse Fit**")
                                    if b["fig_peis"]:
                                        st.image(b["fig_peis"])

                                    st.download_button(
                                        label="Download PEIS fit (PNG)",
                                        data=b["fig_peis"].getvalue(),
                                        file_name=f"{cell_label}_Run_{idx+1}_PEIS_Plot.png",
                                        mime="image/png",
                                        key=f"dl_img_peis_{idx}",
                                    )

    if analysis_type == "Current Fraction":
        if not mpr_files:
            st.warning("Please upload .mpr files for Current Fraction analysis.")
            st.stop()

        cf_run_files = [
            f
            for f in mpr_files
            if "PEIS" not in f.name.upper() and "EIS" not in f.name.upper()
        ]
        if not cf_run_files:
            st.warning("Please upload CA/OCV .mpr files for Current Fraction analysis.")
            st.stop()

        st.write("### Setup")
        avg_points = st.number_input(
            "Points from the end to average:",
            min_value=1,
            value=5000,
            step=100,
            key="cf_avg_points",
        )

        eis_files = [
            f for f in mpr_files if "PEIS" in f.name.upper() or "EIS" in f.name.upper()
        ]
        if not eis_files:
            st.warning("Please upload positive and negative PEIS .mpr files for EIS resistance fitting.")
            st.stop()

        eis_file_names = [f.name for f in eis_files]

        st.write("#### EIS Resistance Fitting")
        e1, e2 = st.columns(2)
        pos_eis_name = e1.selectbox("Positive PEIS file", eis_file_names, key="cf_pos_eis")
        neg_default_idx = 1 if len(eis_file_names) > 1 else 0
        neg_eis_name = e2.selectbox(
            "Negative PEIS file",
            eis_file_names,
            index=neg_default_idx,
            key="cf_neg_eis",
        )

        eis_same_file = pos_eis_name == neg_eis_name
        if eis_same_file:
            st.warning(
                "Positive and Negative PEIS files must be different. "
                "Please select a distinct file for each polarity."
            )

        discard_left, discard_right = get_discard_parameters()
        fit_choice = single_or_dual_ellipse("current_fraction_fit_choice")

        st.write("#### Uploaded CA/OCV MPR Files")
        st.dataframe(pd.DataFrame({"File": [f.name for f in cf_run_files]}), width="stretch")

        if not eis_same_file and st.button("Analyze Current Fraction"):
            pos_eis_file = next(f for f in eis_files if f.name == pos_eis_name)
            neg_eis_file = next(f for f in eis_files if f.name == neg_eis_name)
            with st.spinner("Analyzing Current Fraction MPR files..."):
                try:
                    resistances, eis_fit_df = fit_current_fraction_eis_resistances(
                        cell_label,
                        pos_eis_file,
                        neg_eis_file,
                        discard_left,
                        discard_right,
                        fit_choice,
                    )
                    summary_df, raw_df, plot_buf, avg_rho = analyze_current_fraction_mpr(
                        cf_run_files, resistances, int(avg_points)
                    )

                    csv_buf = io.StringIO()
                    summary_df.to_csv(csv_buf, index=False)

                    excel_buf = io.BytesIO()
                    with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
                        summary_df.to_excel(writer, sheet_name="Summary", index=False)
                        raw_df.to_excel(writer, sheet_name="Raw_Data", index=False)
                        eis_fit_df.to_excel(writer, sheet_name="EIS_Fits", index=False)
                    excel_buf.seek(0)

                    zip_buf = io.BytesIO()
                    with zipfile.ZipFile(zip_buf, "w") as zf:
                        zf.writestr(f"{cell_label}_current_fraction_summary.csv", csv_buf.getvalue())
                        zf.writestr(f"{cell_label}_current_fraction_results.xlsx", excel_buf.getvalue())
                        zf.writestr(f"{cell_label}_current_fraction_plot.png", plot_buf.getvalue())
                        zf.writestr(
                            f"{cell_label}_current_fraction_eis_fits.csv",
                            eis_fit_df.to_csv(index=False),
                        )

                    st.session_state["cf_summary_df"] = summary_df
                    st.session_state["cf_raw_df"] = raw_df
                    st.session_state["cf_eis_fit_df"] = eis_fit_df
                    st.session_state["cf_plot_buf"] = plot_buf
                    st.session_state["cf_csv"] = csv_buf.getvalue().encode("utf-8")
                    st.session_state["cf_excel"] = excel_buf.getvalue()
                    st.session_state["cf_zip"] = zip_buf.getvalue()
                    st.session_state["cf_avg_rho"] = avg_rho
                    st.toast("Current Fraction analysis complete!", icon="✅")
                except Exception as exc:
                    st.error(f"Current Fraction analysis failed: {exc}")

        if "cf_summary_df" in st.session_state:
            st.write("### Current Fraction Results")
            st.metric("Average rho+", f"{st.session_state['cf_avg_rho']:.6f}")
            st.dataframe(st.session_state["cf_summary_df"], width="stretch")
            st.image(st.session_state["cf_plot_buf"])
            if "cf_eis_fit_df" in st.session_state:
                st.write("#### EIS Fit Resistances")
                st.dataframe(st.session_state["cf_eis_fit_df"], width="stretch")

            d1, d2, d3, d4 = st.columns(4)
            d1.download_button(
                "Download CSV",
                st.session_state["cf_csv"],
                f"{cell_label}_current_fraction_summary.csv",
                "text/csv",
            )
            d2.download_button(
                "Download Excel",
                st.session_state["cf_excel"],
                f"{cell_label}_current_fraction_results.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            d3.download_button(
                "Download Plot",
                st.session_state["cf_plot_buf"].getvalue(),
                f"{cell_label}_current_fraction_plot.png",
                "image/png",
            )
            d4.download_button(
                "Download ZIP",
                st.session_state["cf_zip"],
                f"{cell_label}_current_fraction_analysis.zip",
                "application/zip",
            )

    if analysis_type == "Diffusion Coefficient":
        if not mpr_files:
            st.warning("Please upload OCV relaxation .mpr files for Diffusion Coefficient analysis.")
            st.stop()

        ocv_candidates = [f for f in mpr_files if "OCV" in f.name.upper()] or mpr_files
        file_name_map = {f.name: f for f in ocv_candidates}

        st.write("### Setup")
        selected_ocv_names = st.multiselect(
            "OCV relaxation files",
            list(file_name_map.keys()),
            default=list(file_name_map.keys()),
            key="diffusion_ocv_files",
        )

        d1, d2, d3 = st.columns(3)
        thickness_um = d1.number_input(
            "Thickness (um):",
            min_value=0.001,
            value=500.0,
            step=10.0,
            format="%.3f",
            key="diffusion_thickness_um",
        )
        cutoff_time_h = d2.number_input(
            "Cutoff time (h):",
            min_value=0.0001,
            value=4.0,
            step=0.05,
            format="%.4f",
            key="diffusion_cutoff_time_h",
        )
        alpha = d3.number_input(
            "Alpha:",
            min_value=0.000001,
            value=0.05,
            step=0.005,
            format="%.6f",
            key="diffusion_alpha",
        )

        if st.button("Analyze Diffusion Coefficient"):
            selected_files = [file_name_map[name] for name in selected_ocv_names]
            if not selected_files:
                st.warning("Please select at least one OCV relaxation file.")
            else:
                with st.spinner("Fitting OCV relaxation data..."):
                    try:
                        thickness_cm = thickness_um * 1e-4
                        cutoff_time_s = cutoff_time_h * 3600
                        (
                            results_df,
                            fit_df,
                            original_buf,
                            log_buf,
                        ) = analyze_diffusion_coefficient(
                            selected_files,
                            thickness_cm,
                            cutoff_time_s,
                            alpha,
                        )

                        csv_data = results_df.to_csv(index=False).encode("utf-8")
                        fit_csv_data = fit_df.to_csv(index=False).encode("utf-8")

                        excel_buf = io.BytesIO()
                        with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
                            results_df.to_excel(writer, sheet_name="Summary", index=False)
                            fit_df.to_excel(writer, sheet_name="Fit_Curves", index=False)
                        excel_buf.seek(0)

                        zip_buf = io.BytesIO()
                        with zipfile.ZipFile(zip_buf, "w") as zf:
                            zf.writestr(
                                f"{cell_label}_diffusion_summary.csv",
                                csv_data,
                            )
                            zf.writestr(
                                f"{cell_label}_diffusion_fit_curves.csv",
                                fit_csv_data,
                            )
                            zf.writestr(
                                f"{cell_label}_diffusion_results.xlsx",
                                excel_buf.getvalue(),
                            )
                            zf.writestr(
                                f"{cell_label}_diffusion_original_fit.png",
                                original_buf.getvalue(),
                            )
                            zf.writestr(
                                f"{cell_label}_diffusion_log_fit.png",
                                log_buf.getvalue(),
                            )

                        st.session_state["diffusion_results_df"] = results_df
                        st.session_state["diffusion_fit_df"] = fit_df
                        st.session_state["diffusion_original_buf"] = original_buf
                        st.session_state["diffusion_log_buf"] = log_buf
                        st.session_state["diffusion_csv"] = csv_data
                        st.session_state["diffusion_fit_csv"] = fit_csv_data
                        st.session_state["diffusion_excel"] = excel_buf.getvalue()
                        st.session_state["diffusion_zip"] = zip_buf.getvalue()
                        st.toast("Diffusion coefficient analysis complete!", icon="✅")
                    except Exception as exc:
                        st.error(f"Diffusion coefficient analysis failed: {exc}")

        if "diffusion_results_df" in st.session_state:
            st.write("### Diffusion Coefficient Results")
            st.dataframe(st.session_state["diffusion_results_df"], width="stretch")

            c1, c2 = st.columns(2)
            with c1:
                st.write("#### OCV Fit")
                st.image(st.session_state["diffusion_original_buf"])
            with c2:
                st.write("#### Log |V - V_inf| vs Time")
                st.image(st.session_state["diffusion_log_buf"])

            dl1, dl2, dl3, dl4 = st.columns(4)
            dl1.download_button(
                "Download Summary CSV",
                st.session_state["diffusion_csv"],
                f"{cell_label}_diffusion_summary.csv",
                "text/csv",
            )
            dl2.download_button(
                "Download Excel",
                st.session_state["diffusion_excel"],
                f"{cell_label}_diffusion_results.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            dl3.download_button(
                "Download Plots ZIP",
                st.session_state["diffusion_zip"],
                f"{cell_label}_diffusion_analysis.zip",
                "application/zip",
            )
            dl4.download_button(
                "Download Fit Curve CSV",
                st.session_state["diffusion_fit_csv"],
                f"{cell_label}_diffusion_fit_curves.csv",
                "text/csv",
            )
