# Qt-only branch validation

- Five automated tests passed: independently generated synthetic-parameter recovery; frequency-order repeatability; exact nt=0.5 correspondence to semi-infinite Warburg; malformed input rejection; alternative EIS method/cutoff rejection; and identical Python sources on macOS/Windows (some grouped in one test).
- Synthetic parameters recovered within 1%, with maximum relative curve error below 1e-5. Frequency reversal preserved fitted values to relative tolerance 1e-8.
- Real-data integration passed for the supplied PPM Cell B C08 spectrum (42/42 points) and all ten PEO Cell 50 preconditioning spectra (43/43 points each). No tail points removed. All fits converged. Qt and nt were exported; no A_W parameter was exported. Summary resistances equal the corresponding fitted Rb/Ri.
- PPM relative RMS: 2.523532%. PEO cycle 10: 1.810759%. These reproduce the earlier Qt comparison results to displayed precision.
- Streamlit app startup passed. A real PPM file was supplied through the upload boundary in AppTest; Generate EIS Plots completed, the eight fitted values appeared without standard-error annotations, and metadata recorded the Qt circuit and solver settings. No EIS technique, circuit, ellipse, or tail-removal selector appeared.
- Plot output was visually checked. Launch script syntax and Git whitespace checks passed.
- Windows Python sources match macOS. The Windows launcher itself has not been executed on this Mac.

Run portable numerical checks using the configured Python environment:

    python -m unittest discover -s tests -v

The raw user MPR files are not included in the repository.
