import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import io
from galvani import BioLogic
from scipy.optimize import fsolve, fmin, curve_fit
from typing import Any, IO, Optional, Union

# Global style updates
plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial"],
        "font.size": 12,
        "figure.dpi": 100,
        "savefig.dpi": 300,
        "legend.framealpha": 0.8,
        "legend.edgecolor": "black",
    }
)


def get_current_from_mpr(file_obj: IO[bytes]) -> float:
    """Read the median current from an MPR file.

    Find the current column in the file. Return its median value.
    If no current column exists, return 0.0.

    Args:
        file_obj: An MPR file object with a seek method.

    Returns:
        The median current in mA, or 0.0 if no current column exists.
    """
    file_obj.seek(0)
    mpr = BioLogic.MPRfile(file_obj)
    df = pd.DataFrame(mpr.data)
    if "I/mA" in df.columns:
        return df["I/mA"].median()
    elif "<I>/mA" in df.columns:
        return df["<I>/mA"].median()
    return 0.0


def plot_all_EIS_precond(
    cell_type: str, cell_label: str, data_filename: IO[bytes], run_label: str
) -> io.BytesIO:
    """Plot all PEIS cycles from one MPR file.

    Read the cycles from the file. Plot each cycle as a scatter series
    on one chart. Save the chart to a PNG buffer.

    Args:
        cell_type: The type of cell under test.
        cell_label: The label of the cell under test.
        data_filename: An MPR file object that contains PEIS data.
        run_label: The label for this run, for example "Positive".

    Returns:
        A PNG image buffer of the combined cycle plot.
    """
    data_filename.seek(0)
    mpr = BioLogic.MPRfile(data_filename)
    df = pd.DataFrame(mpr.data)
    cycle_no = sorted(list(set(df["cycle number"].values)))
    data_list = [df[df["cycle number"] == c] for c in cycle_no]
    range_x_max = max([(max(d["Re(Z)/Ohm"]) - min(d["Re(Z)/Ohm"])) for d in data_list])
    range_y_max = max(
        [(max(d["-Im(Z)/Ohm"]) - min(d["-Im(Z)/Ohm"])) for d in data_list]
    )
    fig = plt.figure(figsize=(5 * range_x_max / range_y_max, 5))
    ax = fig.add_subplot(111)
    for i, df1 in enumerate(data_list):
        ax.scatter(
            df1["Re(Z)/Ohm"], df1["-Im(Z)/Ohm"], label=f"Cycle {int(cycle_no[i])}", s=15
        )
    ax.set_title(f"{cell_label} {run_label} PEIS all cycles")
    ax.set_xlabel("Re(Z)/Ohm")
    ax.set_ylabel("-Im(Z)/Ohm")
    ax.grid(True, linestyle=":", alpha=0.6)
    ncol = 2 if len(data_list) > 12 else 1
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), ncol=ncol)
    img_buffer = io.BytesIO()
    fig.savefig(img_buffer, format="png", dpi=300, bbox_inches="tight")
    img_buffer.seek(0)
    plt.close(fig)
    return img_buffer


def plot_all_CP_LC(
    cell_label: str,
    elyt_thickness: float,
    cp_summaries: list[tuple[pd.DataFrame, float]],
) -> io.BytesIO:
    """Plot the combined CP curves for a Limiting Current run.

    Plot V/L against time for each current density in the run.

    Args:
        cell_label: The label of the cell under test.
        elyt_thickness: The electrolyte thickness, in cm.
        cp_summaries: A list of (dataframe, current density) pairs.

    Returns:
        A PNG image buffer of the combined plot.
    """
    fig_vl, ax_vl = plt.subplots(figsize=(10, 6))
    for df, d in cp_summaries:
        ax_vl.plot(
            df["norm_time_h"],
            df["Ewe/V"].abs() / elyt_thickness,
            label=f"{abs(d):.2f} mA/cm²",
        )

    ax_vl.set_title(f"Limiting Current of {cell_label}")
    ax_vl.set_xlabel("Time (h)")
    ax_vl.set_ylabel("V/L (V/cm)")
    ax_vl.set_xlim(left=0)

    num_items = len(cp_summaries)
    n_cols = (num_items // 20) + (1 if num_items % 20 > 0 else 0)
    ax_vl.legend(
        loc="upper left", bbox_to_anchor=(1.02, 1), ncol=n_cols, fontsize="x-small"
    )

    cp_plot_buf = io.BytesIO()
    fig_vl.savefig(cp_plot_buf, format="png", dpi=300, bbox_inches="tight")
    cp_plot_buf.seek(0)
    plt.close(fig_vl)
    return cp_plot_buf


def semi_ellipse(
    x: np.ndarray, xc: float, yc: float, Rx: float, Ry: float
) -> np.ndarray:
    """Compute the upper half of an ellipse at each x value.

    Args:
        x: The x values to evaluate.
        xc: The x coordinate of the ellipse center.
        yc: The y coordinate of the ellipse center.
        Rx: The x radius of the ellipse.
        Ry: The y radius of the ellipse.

    Returns:
        The y values on the upper half of the ellipse.
    """
    z = (x - xc) / Rx
    return yc + Ry * np.sqrt(np.maximum(1 - z**2, 0))


def solve_ellipse_xints(
    xc: float, yc: float, Rx: float, Ry: float
) -> tuple[float, float]:
    """Find the left and right x-intercepts of an ellipse at y = 0.

    Args:
        xc: The x coordinate of the ellipse center.
        yc: The y coordinate of the ellipse center.
        Rx: The x radius of the ellipse.
        Ry: The y radius of the ellipse.

    Returns:
        The left x-intercept and the right x-intercept.
    """
    term = np.sqrt(abs(1 - (yc / Ry) ** 2))
    return xc - Rx * term, xc + Rx * term


def obj_one_ellipse(params: list[float], x: np.ndarray, y: np.ndarray) -> float:
    """Compute the sum of squared errors for a one-ellipse fit.

    Reject invalid radii with a large penalty value.

    Args:
        params: The fit parameters xc, yc, Rx, Ry.
        x: The measured x values.
        y: The measured y values.

    Returns:
        The sum of squared errors, or 1e12 for invalid radii.
    """
    xc, yc, Rx, Ry = params
    if Rx <= 0 or Ry <= 0:
        return 1e12
    return np.sum((y - semi_ellipse(x, xc, yc, Rx, Ry)) ** 2)


def obj_two_ellipses(params: list[float], x: np.ndarray, y: np.ndarray) -> float:
    """Compute the sum of squared errors for a two-ellipse fit.

    Take the upper envelope of the two ellipses at each x value. Reject
    invalid radii with a large penalty value.

    Args:
        params: The fit parameters for both ellipses.
        x: The measured x values.
        y: The measured y values.

    Returns:
        The sum of squared errors, or 1e12 for invalid radii.
    """
    xc1, yc1, Rx1, Ry1, xc2, yc2, Rx2, Ry2 = params
    if any(p <= 0 for p in [Rx1, Ry1, Rx2, Ry2]):
        return 1e12
    y1 = semi_ellipse(x, xc1, yc1, Rx1, Ry1)
    y2 = semi_ellipse(x, xc2, yc2, Rx2, Ry2)
    return np.sum((y - np.maximum(y1, y2)) ** 2)


def calculate_bic(rss: float, n: int, k: int) -> float:
    """Calculate the Bayesian Information Criterion for a fit.

    Args:
        rss: The residual sum of squares from the fit.
        n: The number of data points.
        k: The number of free parameters in the fit.

    Returns:
        The BIC value. Return 1e12 if rss is not positive.
    """
    if rss <= 0:
        return 1e12
    return n * np.log(rss / n) + k * np.log(n)


def find_both_mins(df: pd.DataFrame, peak_idx: int) -> tuple[int, int]:
    """Find the left and right local minimum points around a peak.

    Search left from the peak for the lowest point. Search right from
    the peak for the lowest point.

    Args:
        df: A dataframe with the imaginary impedance in column 1.
        peak_idx: The row index of the peak.

    Returns:
        The row index of the left minimum and the row index of the
        right minimum.
    """
    Im_Z = df.iloc[:, 1].values
    n_rows = len(Im_Z)
    left_min_idx = 0
    left_min_val = Im_Z[0]
    for i in range(peak_idx):
        if Im_Z[i] < left_min_val:
            left_min_val = Im_Z[i]
            left_min_idx = i
    right_min_idx = peak_idx
    right_min_val = Im_Z[peak_idx]
    for i in range(peak_idx, n_rows):
        if Im_Z[i] < right_min_val:
            right_min_val = Im_Z[i]
            right_min_idx = i
    return left_min_idx, right_min_idx


def semiellipse_fit(
    cell_type: str,
    cell_label: str,
    no_left_idx_to_throw: int,
    no_right_idx_to_throw: int,
    data_filename: IO[bytes],
    run_label: str,
    must_use_dual: bool,
    must_use_single: bool,
) -> tuple[pd.DataFrame, io.BytesIO, io.StringIO, list[tuple[str, io.BytesIO]]]:
    """Fit each PEIS cycle in an MPR file with one or two semi-ellipses.

    For each cycle, trim points near the ends. Fit a single ellipse and
    a two-ellipse model. Choose the model with the lower BIC score,
    unless the caller forces one model. Compute R_bulk and R_i from the
    fit. Plot each cycle fit and the trend across cycles.

    Args:
        cell_type: The type of analysis, for example "Preconditioning".
        cell_label: The label of the cell under test.
        no_left_idx_to_throw: The number of points to discard from the
            left.
        no_right_idx_to_throw: The number of points to discard from the
            right.
        data_filename: An MPR file object that contains PEIS data.
        run_label: The label for this run, for example "Positive".
        must_use_dual: Force the two-ellipse model for every cycle.
        must_use_single: Force the one-ellipse model for every cycle.

    Returns:
        A tuple with the summary dataframe, the trend plot buffer, the
        summary CSV buffer, and a list of (file name, image buffer)
        pairs for each cycle.
    """
    data_filename.seek(0)
    mpr = BioLogic.MPRfile(data_filename)
    df_raw = pd.DataFrame(mpr.data)
    cycle_nums = sorted(list(set(df_raw["cycle number"].values)))
    results_list = []
    cycle_images = []
    for i, c in enumerate(cycle_nums):
        df_cycle = df_raw[df_raw["cycle number"] == c].reset_index(drop=True)
        df_clean = df_cycle[["Re(Z)/Ohm", "-Im(Z)/Ohm"]]
        no_rows = len(df_clean)
        l_idx, r_idx = find_both_mins(df_clean, peak_idx=no_rows // 4)
        if no_rows > 10:
            l_idx += no_left_idx_to_throw
            r_idx -= no_right_idx_to_throw
        l_idx = max(0, l_idx)
        r_idx = min(no_rows - 1, r_idx)
        idx_list = range(l_idx, r_idx + 1)
        df_masked = df_clean.iloc[idx_list, :]
        x_fit = df_masked.iloc[:, 0].values
        y_fit = df_masked.iloc[:, 1].values
        n = len(x_fit)
        start_val, end_val = x_fit[0], x_fit[-1]
        res_one = fmin(
            obj_one_ellipse,
            [(start_val + end_val) / 2, 0, (end_val - start_val) / 2, np.max(y_fit)],
            args=(x_fit, y_fit),
            disp=False,
        )
        bic_one = calculate_bic(obj_one_ellipse(res_one, x_fit, y_fit), n, 4)
        mid_x = (start_val + end_val) / 2
        guess_two = [
            (start_val + mid_x) / 2,
            0,
            (mid_x - start_val) / 2,
            np.max(y_fit) * 0.5,
            (mid_x + end_val) / 2,
            0,
            (end_val - mid_x) / 2,
            np.max(y_fit),
        ]
        res_two = fmin(
            obj_two_ellipses, guess_two, args=(x_fit, y_fit), disp=False, maxiter=2000
        )
        bic_two = calculate_bic(obj_two_ellipses(res_two, x_fit, y_fit), n, 8)
        use_dual = (bic_two < bic_one or must_use_dual) and not must_use_single
        if use_dual:
            xc1, yc1, Rx1, Ry1, xc2, yc2, Rx2, Ry2 = res_two
            l1, r1 = solve_ellipse_xints(xc1, yc1, Rx1, Ry1)
            l2, r2 = solve_ellipse_xints(xc2, yc2, Rx2, Ry2)
            r_bulk_raw = l1 if abs(l1 - start_val) <= abs(l2 - start_val) else l2
            r_total_raw = r1 if abs(r1 - end_val) <= abs(r2 - end_val) else r2
        else:
            xc1, yc1, Rx1, Ry1 = res_one
            r_bulk_raw, r_total_raw = solve_ellipse_xints(xc1, yc1, Rx1, Ry1)
            xc2 = yc2 = Rx2 = Ry2 = np.nan
        r_bulk = r_bulk_raw if r_bulk_raw >= 0 else x_fit[0]
        ri = r_total_raw - r_bulk
        fig_ind = plt.figure(figsize=(8, 4))
        plt.scatter(
            df_clean.iloc[:, 0], df_clean.iloc[:, 1], color="lightgray", alpha=0.3
        )
        plt.scatter(x_fit, y_fit, color="darkblue", s=10)
        x_plot = np.linspace(r_bulk, r_total_raw, 500)
        y_p = (
            np.maximum(
                semi_ellipse(x_plot, xc1, yc1, Rx1, Ry1),
                semi_ellipse(x_plot, xc2, yc2, Rx2, Ry2),
            )
            if use_dual
            else semi_ellipse(x_plot, xc1, yc1, Rx1, Ry1)
        )
        lbl = f"$R_{{bulk}}$: {r_bulk:.1f} Ω\n$R_i$: {ri:.1f} Ω"
        plt.plot(x_plot, y_p, "r-", label=lbl)
        plt.title(f"{cell_label} {run_label} Cycle {int(c)}")
        plt.xlabel("Re(Z)/Ohm")
        plt.ylabel("-Im(Z)/Ohm")
        plt.gca().set_aspect("equal")
        plt.legend(loc="upper left", bbox_to_anchor=(1.05, 1))
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight")
        buf.seek(0)
        cycle_images.append((f"{cell_label}_{run_label}_Cycle_{int(c)}_Fit.png", buf))
        fig_ind.clear()
        plt.close(fig_ind)
        results_list.append(
            {"Cycle": int(c), "R_bulk": r_bulk, "R_i": ri, "R_total": r_total_raw}
        )
    summary_df = pd.DataFrame(results_list).sort_values(by="Cycle")
    fig_sum, ax1 = plt.subplots(figsize=(10, 5))
    ax2 = ax1.twinx()
    ax1.plot(
        summary_df["Cycle"], summary_df["R_i"], "o-", color="crimson", label="$R_i$"
    )
    ax2.plot(
        summary_df["Cycle"],
        summary_df["R_bulk"],
        "s--",
        color="navy",
        label="$R_{bulk}$",
    )
    ax1.set_xlabel("Cycle Number")
    ax1.set_ylabel("$R_i$ / Ohm", color="crimson")
    ax2.set_ylabel("$R_{bulk}$ / Ohm", color="navy")
    ax1.set_title(f"{cell_label} {run_label} PEIS Trend")
    sum_buf = io.BytesIO()
    plt.savefig(sum_buf, format="png", bbox_inches="tight")
    sum_buf.seek(0)
    csv_buf = io.StringIO()
    summary_df.to_csv(csv_buf, index=False)
    csv_buf.seek(0)
    fig_sum.clear()
    plt.close(fig_sum)
    return summary_df, sum_buf, csv_buf, cycle_images


def plot_cp_ewe(
    f_obj: IO[bytes], cell_label: str, density: float
) -> tuple[io.BytesIO, pd.DataFrame]:
    """Plot cell voltage against time for one CP file.

    Args:
        f_obj: An MPR file object that contains CP data.
        cell_label: The label of the cell under test.
        density: The applied current density, in mA/cm².

    Returns:
        A PNG image buffer of the plot, and the dataframe with a
        normalized time column in hours.
    """
    f_obj.seek(0)
    mpr = BioLogic.MPRfile(f_obj)
    df = pd.DataFrame(mpr.data)
    time_s = df["time/s"] - df["time/s"].iloc[0]
    time_h = time_s / 3600
    ewe = df["Ewe/V"]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(time_h, ewe, color="teal")
    ax.set_title(f"{cell_label}: {density:.3f} mA/cm²")
    ax.set_xlabel("Time (h)")
    ax.set_ylabel("Ewe (V)")
    ax.grid(True, linestyle=":", alpha=0.6)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)
    df_norm = df.copy()
    df_norm["norm_time_h"] = time_h
    return buf, df_norm


def plot_limiting_peis_fit(
    f_peis: IO[bytes],
    cell_label: str,
    run_label: str,
    discard_left: int,
    discard_right: int,
    must_use_dual: bool,
    must_use_single: bool,
) -> tuple[Optional[io.BytesIO], pd.DataFrame, io.StringIO]:
    """Fit the PEIS data for one Limiting Current run.

    Call semiellipse_fit and return the first cycle image.

    Args:
        f_peis: An MPR file object that contains PEIS data.
        cell_label: The label of the cell under test.
        run_label: The label for this run, for example "Run 1".
        discard_left: The number of points to discard from the left.
        discard_right: The number of points to discard from the right.
        must_use_dual: Force the two-ellipse model for every cycle.
        must_use_single: Force the one-ellipse model for every cycle.

    Returns:
        The first cycle image buffer, or None if no cycle exists. Also
        return the summary dataframe and the summary CSV buffer.
    """
    summary_df, sum_buf, csv_buf, cycle_imgs = semiellipse_fit(
        "Limiting",
        cell_label,
        discard_left,
        discard_right,
        f_peis,
        run_label,
        must_use_dual,
        must_use_single,
    )
    if cycle_imgs:
        return cycle_imgs[0][1], summary_df, csv_buf
    return None, summary_df, csv_buf


def analyze_sand_and_polarization(
    cp_results: list[tuple[pd.DataFrame, float]]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Find the Sand's time and the steady-state polarization for each run.

    Find the highest voltage across all runs. For each run that reaches
    near this ceiling, record the time it first crosses 99% of the peak
    voltage. For each run with a stable final voltage, record the mean
    voltage over the last two minutes.

    Args:
        cp_results: A list of (dataframe, current density) pairs.

    Returns:
        A dataframe of Sand's times and a dataframe of steady-state
        voltages.
    """
    sands = []
    pols = []

    v_max_list = []

    for df, density in cp_results:
        v_abs = df["Ewe/V"].abs()
        v_max_this_run = v_abs.max()
        v_max_list.append(v_max_this_run)

    ceiling_voltage = max(v_max_list)

    for df, density in cp_results:
        v_abs = df["Ewe/V"].abs()
        v_max = v_abs.max()
        if (
            v_max >= 0.99 * ceiling_voltage
        ):  # i.e. diverged and fully reached ceiling voltage
            idx_list = df[v_abs >= (v_max * 0.99)].index
            if not idx_list.empty:
                idx = idx_list[0]
                t_sand = df.loc[idx, "norm_time_h"]
                sands.append(
                    {
                        "Current (mA/cm^2)": round(abs(density), 3),
                        "Sand's Time (h)": t_sand,
                    }
                )
        t_end_s = df["norm_time_h"].iloc[-1] * 3600
        df_final = df[(df["norm_time_h"] * 3600) >= (t_end_s - 120)]

        if not df_final.empty:
            the_v_vals = df_final["Ewe/V"].abs().values
            ratio = the_v_vals[-1] / the_v_vals[0]
            if ratio >= 0.998 and ratio <= 1.001:
                v_avg = df_final["Ewe/V"].mean()
                pols.append(
                    {
                        "Current (mA/cm^2)": round(density, 3),
                        "Steady State Voltage (V)": v_avg,
                    }
                )
    return pd.DataFrame(sands), pd.DataFrame(pols)


def diffusion_exp_model(
    t: np.ndarray, a: float, b: float, k0: float
) -> np.ndarray:
    """Compute the exponential relaxation model at time t.

    Args:
        t: The time values, in seconds.
        a: The amplitude of the decay.
        b: The decay rate constant.
        k0: The steady-state offset voltage.

    Returns:
        The modeled voltage at each time value.
    """
    return k0 + a * np.exp(-b * t)


def analyze_diffusion_coefficient(
    files: list[IO[bytes]],
    thickness_cm: float,
    cutoff_time_s: float,
    alpha: float = 0.05,
) -> tuple[pd.DataFrame, pd.DataFrame, io.BytesIO, io.BytesIO]:
    """Fit OCV relaxation data and calculate the diffusion coefficient.

    For each file, fit the model V(t) = a exp(-b t) + k0. Advance the
    fit start time until it passes the minimum time for the chosen
    alpha. Calculate D from the decay rate and the sample thickness.
    Plot the fit and the log relaxation magnitude for each file.

    Args:
        files: A list of MPR file objects that contain OCV relaxation
            data.
        thickness_cm: The sample thickness, in cm.
        cutoff_time_s: The latest time to include in the fit, in
            seconds.
        alpha: The target value of D t / L² at the fit start time.

    Returns:
        A tuple with the results dataframe, the fit curve dataframe,
        the OCV fit plot buffer, and the log relaxation plot buffer.

    Raises:
        ValueError: The thickness, cutoff time, or alpha is not
            positive. A file has too little data, or the fit fails.
    """
    if thickness_cm <= 0:
        raise ValueError("Thickness must be greater than 0 cm.")
    if cutoff_time_s <= 0:
        raise ValueError("Cutoff time must be greater than 0 seconds.")
    if alpha <= 0:
        raise ValueError("Alpha must be greater than 0.")

    results = []
    fit_exports = []
    fig_original, ax_original = plt.subplots(figsize=(9, 5))
    fig_log, ax_log = plt.subplots(figsize=(9, 5))

    for file_obj in files:
        file_obj.seek(0)
        mpr = BioLogic.MPRfile(file_obj)
        df_raw = pd.DataFrame(mpr.data)

        time_col = find_cf_mpr_column(df_raw, ["time/s", "time"], "time")
        voltage_col = find_cf_mpr_column(
            df_raw, ["Ewe/V", "Ewe", "voltage", "potential"], "voltage"
        )

        df = pd.DataFrame(
            {
                "time_s": pd.to_numeric(df_raw[time_col], errors="coerce"),
                "potential_mV": pd.to_numeric(df_raw[voltage_col], errors="coerce")
                * 1000,
            }
        ).dropna()

        if df.empty:
            raise ValueError(f"{file_obj.name} has no numeric OCV relaxation data.")

        df["time_s"] = df["time_s"] - df["time_s"].iloc[0]
        total_time_h = df["time_s"].max() / 3600
        df = df[df["time_s"] <= cutoff_time_s].reset_index(drop=True)
        if len(df) < 6:
            raise ValueError(
                f"{file_obj.name} has fewer than 6 points before the cutoff time."
            )

        t = df["time_s"].to_numpy(dtype=float)
        ewe = df["potential_mV"].to_numpy(dtype=float)
        dt = np.median(np.diff(t)) if len(t) > 1 else 5.0
        if not np.isfinite(dt) or dt <= 0:
            dt = 5.0

        a_guess = ewe[0] - ewe[-1]
        if abs(a_guess) < 1e-12:
            a_guess = 1.0
        initial = [a_guess, 5e-4, ewe[-1]]

        start_idx = 0
        coeff = None
        diffusion = np.nan
        alpha_final = np.nan
        t_min_s = np.nan

        for _ in range(25):
            t_fit = t[start_idx:] - t[start_idx]
            ewe_fit = ewe[start_idx:]
            if len(t_fit) < 5:
                raise ValueError(
                    f"{file_obj.name} does not have enough data after the alpha cutoff."
                )

            coeff, _ = curve_fit(
                diffusion_exp_model,
                t_fit,
                ewe_fit,
                p0=initial,
                maxfev=20000,
            )
            b = coeff[1]
            if b <= 0:
                raise ValueError(
                    f"{file_obj.name} fit produced a non-positive decay constant."
                )

            diffusion = thickness_cm**2 * b / np.pi**2
            t_min_s = alpha * thickness_cm**2 / diffusion
            alpha_final = diffusion * t[start_idx] / thickness_cm**2

            if t[start_idx] > t_min_s:
                break

            next_start_time = t_min_s + 5 * dt
            next_idx = int(np.searchsorted(t, next_start_time, side="left"))
            if next_idx <= start_idx or next_idx >= len(t) - 5:
                break
            start_idx = next_idx
            initial = coeff

        fit_x = np.linspace(0, t[-1] - t[start_idx], 1000)
        fit_y = diffusion_exp_model(fit_x, *coeff)
        fit_time_abs = fit_x + t[start_idx]

        ax_original.plot(t, ewe, ".", markersize=3, label=f"{file_obj.name} data")
        ax_original.plot(fit_time_abs, fit_y, "-", linewidth=2, label=f"{file_obj.name} fit")
        voltage_relax_mV = np.abs(ewe - coeff[2])
        fit_relax_mV = np.abs(fit_y - coeff[2])
        positive_mask = voltage_relax_mV > 0
        fit_positive_mask = fit_relax_mV > 0
        if np.any(positive_mask):
            ax_log.plot(
                t[positive_mask],
                np.log(voltage_relax_mV[positive_mask]),
                ".",
                markersize=3,
                label=f"{file_obj.name} data",
            )
        if np.any(fit_positive_mask):
            ax_log.plot(
                fit_time_abs[fit_positive_mask],
                np.log(fit_relax_mV[fit_positive_mask]),
                "-",
                linewidth=2,
                label=f"{file_obj.name} fit",
            )

        results.append(
            {
                "File Name": file_obj.name,
                "D_salt (cm^2/s)": f"{diffusion:.4e}",
                "alpha = D_salt t / L^2": alpha_final,
                "Total Time (h)": total_time_h,
                "Fit Start Time (s)": t[start_idx],
                "Minimum Time (s)": t_min_s,
                "Cutoff Time (h)": cutoff_time_s / 3600,
                "Thickness (um)": thickness_cm / 1e-4,
                "a (mV)": coeff[0],
                "b (1/s)": coeff[1],
                "k0 (mV)": coeff[2],
            }
        )

        fit_exports.append(
            pd.DataFrame(
                {
                    "File Name": file_obj.name,
                    "Fit Time (s)": fit_time_abs,
                    "Fit Potential (mV)": fit_y,
                }
            )
        )

    ax_original.set_title("OCV Relaxation Fit: U(t) = k0 + a exp(-bt)")
    ax_original.set_xlabel("Time (s)")
    ax_original.set_ylabel("Potential (mV)")
    ax_original.grid(True, alpha=0.3)
    ax_original.legend(loc="best", fontsize="small")

    ax_log.set_title("Log Relaxation Magnitude Fit")
    ax_log.set_xlabel("Time (s)")
    ax_log.set_ylabel("log(|U(t) - k0| / mV)")
    ax_log.grid(True, alpha=0.3)
    ax_log.legend(loc="best", fontsize="small")

    original_buf = io.BytesIO()
    fig_original.savefig(original_buf, format="png", dpi=300, bbox_inches="tight")
    original_buf.seek(0)

    log_buf = io.BytesIO()
    fig_log.savefig(log_buf, format="png", dpi=300, bbox_inches="tight")
    log_buf.seek(0)

    results_df = pd.DataFrame(results)
    fit_df = pd.concat(fit_exports, ignore_index=True) if fit_exports else pd.DataFrame()
    plt.close(fig_original)
    plt.close(fig_log)
    return results_df, fit_df, original_buf, log_buf


def _cf_file_type(name: str) -> Optional[str]:
    """Classify a Current Fraction file as OCV or CA from its name.

    Check for "OCV" first, then "CA", as a substring of the file
    name.

    Args:
        name: The file name to classify.

    Returns:
        "OCV" if the name contains "OCV". "CA" if the name contains
        "CA" and not "OCV". None if neither pattern matches.
    """
    name_upper = name.upper()
    if "OCV" in name_upper:
        return "OCV"
    if "CA" in name_upper:
        return "CA"
    return None


def _cf_short_label(name: str) -> str:
    """Get a short label for a Current Fraction file, for titles.

    Use the leading run of digits in the file name if it has one (the
    usual numbering convention, for example "03" from "03_OCV.mpr").
    Otherwise, use the file name without its extension.

    Args:
        name: The file name to label.

    Returns:
        The short label.
    """
    stem = name.rsplit(".", 1)[0] if "." in name else name
    digits = ""
    for ch in stem:
        if ch.isdigit():
            digits += ch
        else:
            break
    return digits if digits else stem


def build_cf_file_pairs(files: list[IO[bytes]]) -> list[dict[str, Any]]:
    """Group Current Fraction files into a positive and negative trial.

    Classify each file as OCV or CA from its name, in upload order.
    Discard the first OCV file found; it is a leading rest step, not
    part of a trial. Treat the next OCV as a trial's OCV file, and
    collect every CA file that immediately follows it as that trial's
    CA chain, so a chain can hold one CA file or several. Discard the
    OCV that starts the next leading rest step, then repeat to find
    the second trial's OCV and CA chain. Stop once two trials are
    found, since Current Fraction expects exactly one positive and one
    negative trial.

    Args:
        files: A list of CA and OCV MPR file objects, in upload order.

    Returns:
        A list of up to two trial dictionaries, one for each complete
        OCV + CA chain found.
    """
    typed_files = [(f, _cf_file_type(f.name)) for f in files]
    typed_files = [(f, t) for f, t in typed_files if t is not None]

    labels = [("R_pos", "Positive"), ("R_neg", "Negative")]
    pairs = []
    ocv_count = 0
    i = 0
    n = len(typed_files)

    while i < n and len(pairs) < 2:
        f, t = typed_files[i]
        if t != "OCV":
            i += 1
            continue
        ocv_count += 1
        i += 1
        if ocv_count % 2 == 1:
            # Odd-numbered OCV: a leading rest step. Discard it.
            continue
        # Even-numbered OCV: the trial's OCV file. Collect its CA chain.
        ocv_file = f
        ca_files = []
        while i < n and typed_files[i][1] == "CA":
            ca_files.append(typed_files[i][0])
            i += 1
        if not ca_files:
            continue
        resistance_key, run_label = labels[len(pairs)]
        title = f"{_cf_short_label(ocv_file.name)} OCV + " + " + ".join(
            f"{_cf_short_label(c.name)} CA" for c in ca_files
        )
        pairs.append(
            {
                "ocv_file": ocv_file,
                "ca_files": ca_files,
                "experiment": run_label,
                "resistance_key": resistance_key,
                "description": title,
            }
        )
    return pairs


def read_cf_mpr_file(file_obj: IO[bytes]) -> pd.DataFrame:
    """Read an MPR file into a dataframe.

    Args:
        file_obj: An MPR file object.

    Returns:
        A dataframe with the raw MPR data.
    """
    file_obj.seek(0)
    mpr = BioLogic.MPRfile(file_obj)
    return pd.DataFrame(mpr.data)


def find_cf_mpr_column(
    df: pd.DataFrame, candidates: list[str], required_label: str
) -> str:
    """Find a column name in a dataframe from a list of candidates.

    Match column names by exact text first. Then match column names
    that contain a candidate as a substring.

    Args:
        df: The dataframe to search.
        candidates: A list of candidate column names.
        required_label: A label for the error message if no match
            exists.

    Returns:
        The matching column name.

    Raises:
        ValueError: No column matches any candidate.
    """
    lower_to_col = {str(col).lower().strip(): col for col in df.columns}
    for candidate in candidates:
        if candidate.lower() in lower_to_col:
            return lower_to_col[candidate.lower()]

    for col in df.columns:
        col_lower = str(col).lower().strip()
        if any(candidate.lower() in col_lower for candidate in candidates):
            return col

    raise ValueError(f"Missing {required_label} column")


def _read_cf_ca_chain(ca_files: list[IO[bytes]]) -> pd.DataFrame:
    """Read and concatenate a chain of CA files into one timeline.

    Read each CA file's time, current, and voltage data. Zero-base
    each file's time to its own first point, then offset it to
    continue from where the previous file in the chain left off, so
    the chain reads as one continuous run.

    Args:
        ca_files: The CA MPR file objects in the chain, in order.

    Returns:
        A dataframe with continuous "time", "current", "voltage", and
        "ca_file" columns, one row per data point across the chain.
    """
    segments = []
    time_offset = 0.0
    for ca_file in ca_files:
        ca_data = read_cf_mpr_file(ca_file)
        ca_time_col = find_cf_mpr_column(ca_data, ["time/s", "time"], "CA time")
        ca_voltage_col = find_cf_mpr_column(
            ca_data, ["Ewe/V", "Ewe", "voltage", "potential"], "CA voltage"
        )
        ca_current_col = find_cf_mpr_column(
            ca_data, ["I/mA", "<I>/mA", "current"], "CA current"
        )
        seg = pd.DataFrame(
            {
                "time": pd.to_numeric(ca_data[ca_time_col], errors="coerce"),
                "current": pd.to_numeric(ca_data[ca_current_col], errors="coerce"),
                "voltage": pd.to_numeric(ca_data[ca_voltage_col], errors="coerce")
                * 1000,
            }
        ).dropna()
        if seg.empty:
            continue
        seg["time"] = seg["time"] - seg["time"].iloc[0] + time_offset
        time_offset = seg["time"].iloc[-1]
        seg["ca_file"] = ca_file.name
        segments.append(seg)
    return (
        pd.concat(segments, ignore_index=True) if segments else pd.DataFrame()
    )


def analyze_current_fraction_mpr(
    files: list[IO[bytes]],
    resistances: dict[str, list[float]],
    average_points: int = 5000,
) -> tuple[pd.DataFrame, pd.DataFrame, io.BytesIO, float]:
    """Calculate the current fraction rho+ for each trial.

    For each trial, read the OCV data and the trial's chained CA
    files. Calculate the initial current from the first CA file, the
    steady-state current from the tail of the CA chain, and the
    migration current. Calculate rho+ from these currents and the
    fitted resistances. Plot the CA chain with current markers for
    each trial, with a dotted line at each join between CA files.

    Args:
        files: A list of CA and OCV MPR file objects.
        resistances: A dictionary that maps each resistance key to a
            list of R_bulk and R_i values.
        average_points: The number of points from the end of each
            trial's CA chain to average.

    Returns:
        A tuple with the summary dataframe, the per-trial results
        dataframe, the combined plot buffer, and the average rho+
        value.

    Raises:
        ValueError: No valid trials exist, or a trial has no numeric
            data.
    """
    file_pairs = build_cf_file_pairs(files)
    if not file_pairs:
        raise ValueError(
            "No valid OCV + CA trials found. Upload a leading rest OCV, "
            "a trial OCV, and one or more CA files for each of the two "
            "trials."
        )

    fig, axes = plt.subplots(len(file_pairs), 1, figsize=(12, 6 * len(file_pairs)))
    if len(file_pairs) == 1:
        axes = [axes]
    fig.suptitle("CA Curves with Current Markers", fontsize=16)

    results = []
    rho_values = []

    for idx, pair in enumerate(file_pairs):
        ocv_data = read_cf_mpr_file(pair["ocv_file"])
        ocv_voltage_col = find_cf_mpr_column(
            ocv_data, ["Ewe/V", "Ewe", "voltage", "potential"], "OCV voltage"
        )
        ocv_voltage = pd.to_numeric(ocv_data[ocv_voltage_col], errors="coerce") * 1000
        ocv_voltage = ocv_voltage.dropna()

        ca_clean = _read_cf_ca_chain(pair["ca_files"])

        if ca_clean.empty or ocv_voltage.empty:
            raise ValueError(
                f"{pair['experiment']} trial ({pair['description']}) has no "
                "numeric CA/OCV data."
            )

        tail_n = min(int(average_points), len(ca_clean), len(ocv_voltage))
        if tail_n < 1:
            raise ValueError("Average points must be at least 1.")

        I_o = ca_clean["current"].iloc[1] if len(ca_clean) > 1 else ca_clean["current"].iloc[0]
        I_ss = ca_clean["current"].iloc[-tail_n:].mean()
        delV = ca_clean["voltage"].iloc[-tail_n:].mean()
        OCV = ocv_voltage.iloc[-tail_n:].mean()

        Rbulk_o, R_i_o, Rbulk_ss, R_i_ss = resistances[pair["resistance_key"]]
        delV_prime = delV - OCV
        I_omega = delV_prime / (Rbulk_o + R_i_o)
        rho_add = (I_ss / I_omega) * (
            (delV_prime - I_omega * R_i_o) / (delV_prime - I_ss * R_i_ss)
        )
        rho_values.append(rho_add)

        ax = axes[idx]
        ax.scatter(ca_clean["time"], ca_clean["current"], s=1, alpha=0.6, c="blue", label="CA curve")
        join_mask = ca_clean["ca_file"] != ca_clean["ca_file"].shift(1)
        join_times = ca_clean.loc[join_mask, "time"].iloc[1:]
        for j, join_time in enumerate(join_times):
            ax.axvline(
                x=join_time,
                color="gray",
                linestyle=":",
                alpha=0.6,
                label="CA file join" if j == 0 else None,
            )
        ax.axhline(y=I_o, color="red", linestyle="--", alpha=0.8, linewidth=2, label=f"I,o = {I_o:.3f} mA")
        ax.axhline(y=I_ss, color="green", linestyle="--", alpha=0.8, linewidth=2, label=f"I,ss = {I_ss:.3f} mA")
        ax.axhline(y=I_omega, color="orange", linestyle="--", alpha=0.8, linewidth=2, label=f"I,omega = {I_omega:.3f} mA")
        ax.axvspan(
            ca_clean["time"].iloc[-tail_n],
            ca_clean["time"].iloc[-1],
            alpha=0.2,
            color="green",
            label=f"SS region (last {tail_n} points)",
        )
        ax.set_xlabel("Time (seconds)")
        ax.set_ylabel("Current (mA)")
        ax.set_title(f"{pair['experiment']}: {pair['description']}")
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)

        results.append(
            {
                "experiment": pair["experiment"],
                "description": pair["description"],
                "I_o": I_o,
                "I_ss": I_ss,
                "I_omega": I_omega,
                "delV": delV,
                "OCV": OCV,
                "delV_prime": delV_prime,
                "rho_add": rho_add,
                "resistance_type": pair["resistance_key"],
                "ocv_file": pair["ocv_file"].name,
                "ca_files": ", ".join(c.name for c in pair["ca_files"]),
            }
        )

    fig.tight_layout()
    plot_buf = io.BytesIO()
    fig.savefig(plot_buf, format="png", dpi=300, bbox_inches="tight")
    plot_buf.seek(0)
    plt.close(fig)

    results_df = pd.DataFrame(results)
    avg_rho = np.mean(rho_values) if rho_values else np.nan
    summary_row = {
        "experiment": "AVERAGE",
        "description": "Average of all experiments",
        "I_o": np.nan,
        "I_ss": np.nan,
        "I_omega": np.nan,
        "delV": np.nan,
        "OCV": np.nan,
        "delV_prime": np.nan,
        "rho_add": avg_rho,
        "resistance_type": "",
        "ocv_file": "",
        "ca_files": "",
    }
    summary_df = pd.concat([results_df, pd.DataFrame([summary_row])], ignore_index=True)
    summary_df = summary_df.rename(
        columns={
            "experiment": "Experiment",
            "description": "Description",
            "I_o": "I,o (mA)",
            "I_ss": "I,ss (mA)",
            "I_omega": "I,omega (mA)",
            "delV": "delV (mV)",
            "OCV": "OCV (mV)",
            "delV_prime": "delV' (mV)",
            "rho_add": "rho+",
            "resistance_type": "Resistance Type",
            "ocv_file": "OCV File",
            "ca_files": "CA Files",
        }
    )

    return summary_df, results_df, plot_buf, avg_rho


def series100(
    y: Union[float, np.ndarray], current: Union[float, np.ndarray], i_L: float
) -> Union[float, np.ndarray]:
    """Evaluate the Sand's time series expansion.

    Sum 100 terms of the series for each combination of y and current.

    Args:
        y: One or more values of L² / (D t).
        current: One or more current density values.
        i_L: The limiting current density.

    Returns:
        The series value at each combination of y and current. Return
        a scalar if both y and current are scalars.
    """
    y_arr = np.atleast_1d(y)
    current_arr = np.atleast_1d(current)

    y_col = y_arr[:, np.newaxis]
    current_col = current_arr[:, np.newaxis]
    
    x = current_col / i_L
    
    n = np.arange(1, 101)
    beta_n = (2 * n - 1) * np.pi
    
    matrix_terms = 8 * x / beta_n**2 * (1 - np.exp(-beta_n**2 / y_col))
    result = np.sum(matrix_terms, axis=1)
    
    if np.isscalar(y) and np.isscalar(current):
        return result[0]
        
    return result


def solve_sands_fit(
    sands_df: pd.DataFrame,
    L: float,
    D: float,
    last_stable_i: float,
    first_div_i: float,
) -> tuple[float, np.ndarray, list[float]]:
    """Fit the limiting current from Sand's time data.

    Fit i_L to the Sand's time series model. Compute the theoretical
    curve near the fitted limiting current.

    Args:
        sands_df: A dataframe with Sand's time and current density
            columns.
        L: The electrolyte thickness, in cm.
        D: The diffusion coefficient, in cm²/s.
        last_stable_i: The highest current density that did not
            diverge.
        first_div_i: The lowest current density that diverged.

    Returns:
        A tuple with the fitted limiting current, the theoretical x
        values, and the theoretical y values.
    """
    t_sand_s = sands_df["Sand's Time (h)"].values * 3600
    current_vals = sands_df["Current (mA/cm^2)"].values
    y_data = L**2 / (D * t_sand_s)

    def sse(k, y, curr):
        return np.sum(np.sqrt((series100(y, curr, *k) - 1) ** 2))
        
    i_guess = [(last_stable_i + first_div_i) / 2]
    res = fmin(sse, i_guess, args=(y_data, current_vals), disp=False)
    i_optimized = res[0]

    def series_root(x):
        return lambda y_root: series100(y_root, x, 1.0) - 1

    x_right = max(current_vals) / i_optimized if len(current_vals) > 0 else 2.0
    x_range = np.linspace(1.0, max(1.1, x_right), 100)

    y_theory = []
    for x in x_range:
        y_val = fsolve(series_root(x), 0.5)[0]
        y_theory.append(y_val * D * 3600)

    return i_optimized, x_range * i_optimized * L, y_theory


def plot_sands_analysis(
    sands_df: pd.DataFrame,
    cell_label: str,
    L: float,
    D: float,
    last_stable_i: float,
    first_div_i: float,
) -> tuple[io.BytesIO, float]:
    """Plot the Sand's time analysis and fit the limiting current.

    Args:
        sands_df: A dataframe with Sand's time and current density
            columns.
        cell_label: The label of the cell under test.
        L: The electrolyte thickness, in cm.
        D: The diffusion coefficient, in cm²/s.
        last_stable_i: The highest current density that did not
            diverge.
        first_div_i: The lowest current density that diverged.

    Returns:
        A PNG image buffer of the plot, and the fitted limiting
        current.
    """
    i_opt, x_theory, y_theory = solve_sands_fit(
        sands_df, L, D, last_stable_i, first_div_i
    )

    fig, ax1 = plt.subplots(figsize=(8, 5))
    plotsandsx = sands_df["Current (mA/cm^2)"] * L
    plotsandsy = L**2 / sands_df["Sand's Time (h)"]

    ax1.scatter(plotsandsx, plotsandsy, color="black", label="Data Points")
    ax1.plot(
        x_theory,
        y_theory,
        color="tab:blue",
        label=f"Series Fit\n$i_L L = {i_opt*L:.5f}$ mA/cm",
    )

    ax1.axvline(
        x=last_stable_i * L,
        color="tab:red",
        linestyle="--",
        alpha=0.6,
        label="Last Stable iL",
    )
    ax1.axvline(
        x=first_div_i * L,
        color="tab:green",
        linestyle="--",
        alpha=0.6,
        label="First Diverged iL",
    )
    ax1.axvline(x=i_opt * L, color="tab:blue", linestyle=":", alpha=0.8)

    ax1.set_title(f"Sand's Time Analysis: {cell_label}")
    ax1.set_xlabel(r"$iL$ (mA/cm)")
    ax1.set_ylabel(r"$L^2/t_{sand}$ ($cm^2/h$)")
    ax1.set_ylim(bottom=0)

    def xaxistrans(x):
        return x / (i_opt * L)

    def xaxistransinv(xtrans):
        return xtrans * (i_opt * L)
    secax = ax1.secondary_xaxis("top", functions=(xaxistrans, xaxistransinv))
    secax.set_xlabel(r"$i/i_{lim}$")

    ax1.legend(loc="upper left", bbox_to_anchor=(1.05, 1))

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=300, bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)
    return buf, i_opt
