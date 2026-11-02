# Zirong-ECM

The only EIS fitting circuit is **(Rb ∥ Qb) + (Ri ∥ Qi) + Qt**.

The eight fitted parameters are **Rb, Qb, nb, Ri, Qi, ni, Qt, nt**. Each parallel branch uses R / [1 + R Q (jω)^n]; the series tail uses 1 / [Qt (jω)^nt]. There is no fitted series resistor or Warburg element.

| Symbol | Meaning | Unit |
|---|---|---|
| Rb | Resistance of the branch assigned to bulk electrolyte | Ω |
| Qb | CPE coefficient of the bulk branch | Ω⁻¹ sⁿᵇ |
| nb | Exponent describing the bulk CPE’s departure from ideal capacitive behaviour | Dimensionless |
| Ri | Resistance of the branch assigned to the interface | Ω |
| Qi | CPE coefficient of the interface branch | Ω⁻¹ sⁿⁱ |
| ni | Exponent describing the interface CPE’s departure from ideal capacitive behaviour | Dimensionless |
| Qt | CPE coefficient used to describe the low-frequency tail | Ω⁻¹ sⁿᵗ |
| nt | Exponent controlling the tail’s frequency dependence and angle | Dimensionless |
| ∥ | Elements connected in parallel | — |
| + | Elements connected in series | — |

## Run

- macOS: open `ElectroSmart_macOS/ElectroSmart_v4_macOS.command`.
- Windows: open `ElectroSmart_Windows/ElectroSmart.bat` (Python 3.11+ required).
- The app runs at http://127.0.0.1:8502. Set ELECTROSMART_PORT to use another port.
- On this Mac, the launcher can reuse the existing environment in the sibling ElectroSmart-try-ECM-fitting folder. It does not change its packages. On another machine, the launcher creates its own environment and installs requirements on first launch.

Upload MPR files and use the existing single-file, preconditioning, limiting-current, or current-fraction workflow. Every EIS workflow uses this circuit automatically. Other analysis tools (current transients, OCV relaxation, etc.) retain their own models because they do not fit impedance spectra.

## Fitting and output

All finite, nonzero impedance points at positive frequency are retained. No tail removal, point-discard controls, capacitance cutoff, or alternative EIS fitting methods are available. The renderer shows a measured spectrum, fitted curve, and a clear list of the eight parameters plus fit error. CSV exports also retain solver diagnostics, starting values, and local uncertainty information.

The optimizer uses modulus-weighted complex residuals, positive scales in log space, and 36 deterministic starts per cycle (seed 20261101). It never warm-starts from another cycle. One start targets an unresolved bulk branch; the others sample peak frequencies from the measured minimum to 100 times the measured maximum. Bounds: R 1e-6–1e10 Ω, Q 1e-18–1 Ω^-1 s^n, nb/ni 0.3–1, nt 0.05–1. TRF, three-point Jacobian, max_nfev 2500, ftol/xtol/gtol 1e-9. Only converged finite solutions are considered.

The higher-frequency branch is labelled Rb/Qb/nb by convention. R_bulk = Rb and R_i = Ri for downstream calculations; Qt is not included in their sum. These labels alone do not identify the physical processes. An unmeasured bulk peak leaves Qb poorly constrained; nt near 0.05 makes Qt nearly resistive and can change which feature the first branch describes. These diagnostics are retained in exports without adding plot annotations.

## Branch and provenance

This is a separate local repository made from the user's modified ElectroSmart download. `main` contains the pre-change snapshot; `feature/qt-only-fitting` contains this edition. No remote is configured or published. The original downloaded app remains separate.

macOS and Windows Python sources are identical. The folder contains the app and its supporting files; no test datasets or test suite are included. Numerical checks and the macOS app were verified on PEO and PPM data before packaging.

## Credits

ElectroSmart retains its original MIT license and contributors. Equivalent-circuit equations and modulus weighting follow the impedance.py conventions; the optimizer is implemented directly with NumPy/SciPy. The Qt model is a CPE-tail variant.
