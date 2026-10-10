# ElectroSmart

An interface/app for data analysis work in the Balsara Lab.

Author: Hansen Yang, Zirong He    
Last updated: October 9, 2026  
Version: 4.5 (v4.5)  
Purpose: This document contains instructions to run the Python programs for data analysis. The methods of data analysis include preconditioning EIS fits, Sand's time analysis, current fraction analysis, and diffusion coefficient fitting.  
Properties: This app is run locally on your computer, or on the Streamlit website. It is displayed in your default browser.

## Changes in v4.5

The two main changes are the metadata file and the checks for empty and unreadable files. Together, they record how the app made each result, and which input files it did not use.

1. Added a metadata file for each analysis.
   - The metadata `.txt` file records: the ElectroSmart version, the analysis name, the time of the analysis, the cell type, the cell label, the files that the analysis used, all uploaded `.mpr` files, the input parameters, the EIS fit settings, the `I,ss` method, and all warnings and errors that the app shows at the time of download.
   - Each ZIP file includes the metadata file. Each analysis also has a purple `Download Metadata (TXT)` button.
   - See `Metadata File` in the Analysis Notes.

2. Added checks for empty and unreadable `.mpr` files.
   - The app shows a warning for each file that is empty, and for each file that `galvani` cannot read. The warning is nonblocking (the app allows data analysis even if there are bad files).
   - EIS Fit, Preconditioning, and Limiting Current do not use these files. In Limiting Current, a bad file does not change how the app pairs the other files.
   - See `Empty and Unreadable Files` in the Analysis Notes.

3. Changed how Limiting Current finds the runs that do not diverge.
   - The Polarization CSV lists only the runs that do not diverge.
   - The app now counts the peaks in the slope of the voltage curve. A run that has two slope peaks diverges.

## Changes From v4 to v4.4

1. Changed how Current Fraction finds its files.
   - The app no longer looks for the numbers `03/04` and `09/10` in file names.
   - The app now reads the file names for `OCV` or `CA`. It uses the upload order to find the two trials.
   - Each trial can have one CA file or several CA files. The app joins several CA files into one continuous run.
   - The CA plot shows a dotted line at each join between CA files.
   - The results table column `CA File` is now `CA Files`. It lists every CA file in the trial.

## Changes From v3 to v4

1. Added Current Fraction analysis.
   - Uses `.mpr` CA/OCV files instead of `.txt` files.
   - Keeps the existing `03/04` and `09/10` file numbering convention.
   - Uses positive and negative PEIS/EIS `.mpr` files to fit `R_bulk` and `R_i`.
   - Uses the first fitted EIS cycle as the initial resistance and the last fitted EIS cycle as the steady-state resistance.
   - Exports summary CSV, Excel, plot PNG, EIS fit table, and ZIP bundle.

2. Added Diffusion Coefficient fitting.
   - Fits OCV relaxation data with `V(t) = A exp(-k t) + C`.
   - Calculates `D = k L^2 / pi^2`.
   - User inputs thickness in `um`, cutoff time in `h`, and alpha.
   - Default alpha is `0.05`.
   - Default cutoff time is `4 h`.
   - Reports total polarization/relaxation time in hours.
   - Reports `D (cm^2/s)` in scientific notation.
   - Plots OCV fit and `log(|V(t) - V_inf| / mV)` vs time for sanity check, reliable D comes from the linear regime.

3. Added cross-platform launchers.
   - Windows users can run `ElectroSmart.bat`.
   - macOS users can run `ElectroSmart_v4_macOS.command` in the macOS package.

4. Added `openpyxl` to `requirements.txt` for Excel export.

## Changes From v2 to v3

1. Modified `ElectroSmart.bat` so that:
   - Relevant libraries are installed automatically.
   - The app is run through the installed Python on the computer.
   - A Desktop shortcut to ElectroSmart is set up when the `.bat` file is first run.
2. Eliminated unnecessary library imports in `app.py` and `plotting.py`.
3. Enabled the recommended choices of fitting and type of fit, semi-ellipse fit and two ellipse, as the default selection.

## Description of Files

1. `app.py`  
   The program that displays the interface for data analysis. Responsible for the UI of the app.

2. `plotting.py`  
   The mathematical workhorse of the application. Performs the electrochemical analysis.

3. `validation.py`  
   Checks each uploaded `.mpr` file. Finds files that are empty, files that `galvani` cannot read, and files that do not have the necessary data columns.

4. `ElectroSmart.bat`  
   Windows launcher. It installs dependencies, creates a Desktop shortcut, opens the browser, and runs the Streamlit app.

5. `requirements.txt`  
   Required Python libraries needed to run ElectroSmart.

6. `Logo.ico`  
   Display icon for the Windows shortcut.

7. `Logo.png`  
   ElectroSmart logo image.

8. `.gitignore`  
   Prevents virtual environments, Python cache files, and local Streamlit folders from being committed to GitHub.

## Libraries and Packages Needed

These are also listed in `requirements.txt`.

1. streamlit (version 1.50 or later)
2. pandas
3. matplotlib
4. numpy
5. scipy
6. galvani
7. openpyxl

## Operating Instructions for Windows

### First Time Use

1. Double-click `ElectroSmart.bat`.
2. Required packages should be installed or updated in the computer's Python environment.
3. The app should load in your default browser at `http://localhost:8501`.
4. Do not close the terminal window generated by the `.bat` file. Closing it stops the local Streamlit server.
5. If a Desktop shortcut is not automatically created, follow the backup desktop shortcut instructions below.

### Non-First Time Use

1. Double-click the Desktop shortcut named `ElectroSmart`, or double-click `ElectroSmart.bat`.
2. If that does not work, follow the first-time use instructions again.

### Backup Manual Run

If the launcher does not work:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.port 8501
```

### Backup Desktop Shortcut Instructions

1. Right-click `ElectroSmart.bat` and select Properties.
2. Click Show more options, then select Create shortcut.
3. Drag the shortcut to the Desktop.
4. Right-click the Desktop shortcut, select Properties, then select Change Icon.
5. Browse to `Logo.ico` in the same folder.
6. Click OK on all windows.

## Analysis Notes

### Metadata File

Each analysis makes a metadata `.txt` file. Keep this file with your results. It tells you how the app made them.

The file contains these parts:

1. Header: the ElectroSmart version, the analysis name, the time of the analysis, the cell type, and the cell label.
2. `Files Used in This Analysis`: the files that the analysis used.
3. `Input Parameters`: the values that you entered for this analysis.
4. `EIS Fitting`: the technique, the points to discard (left and right), and the fit choice. This part shows only if the analysis fits EIS data.
5. `All Uploaded .mpr Files`: the name of each uploaded file, including the files that the analysis did not use.
6. `Warnings Shown at Download`: each warning and error that the app shows when you download the file. If there are none, this part shows `None`.

The file records only the inputs that the analysis needs. For Limiting Current, Potentiometric Data, the file shows the diffusion coefficient only if the app made a Sand's time fit.

You can get the metadata file in two ways:

- Each ZIP file includes it.
- Each analysis has a purple `Download Metadata (TXT)` button. In Preconditioning, the button is next to `Generate EIS Plots`. In the other analyses, the button is with the download buttons for the individual files.

The button shows after you run the analysis.

Notes on the times:

- The app records the settings and the time of the analysis when you run the analysis. If you change a setting after that, run the analysis again.
- The app records the warnings and the list of uploaded files when you download the file.
- The time of the analysis is in the time zone of your browser. The file also shows the UTC offset, for example `2026-10-09 21:37:48 UTC-07:00 (America/Los_Angeles)`. If the app cannot find the time zone, it shows the time in UTC.

### Empty and Unreadable Files

The app reads each `.mpr` file one time, at upload. It puts each file in one of three groups:

- Good: the app can read the file, and the file has data.
- Empty: the file has 0 bytes, or it has no data rows.
- Unreadable: `galvani` cannot read the file. This occurs with a corrupt file, and with some files from older EC-Lab software.

The app shows a warning that lists the empty files and the unreadable files. The warning is nonblocking (the app allows data analysis even if there are bad files). If the app can use none of the uploaded files, it shows an error.

Each analysis uses these checks as follows:

- EIS Fit (Single File) and Preconditioning: The app does not show a bad file in the PEIS file list. The file that you select must have the columns `cycle number`, `Re(Z)/Ohm`, and `-Im(Z)/Ohm`.
- Limiting Current: See the rules below.
- Current Fraction and Diffusion Coefficient: These analyses do not use the checks yet. A bad file can make the analysis fail with an error message. Remove the bad file and upload the files again.

Rules for Limiting Current:

1. The app pairs the CP, OCV, and PEIS files by name and upload order. It includes the bad files in this step. Thus, a bad file does not change the other runs.
2. If the CP file of a run is bad, the app does not use the run.
3. If the PEIS file of a run is bad, the app uses the run for the potentiometric analysis only.
4. The app does not check the OCV file, because the analysis does not use it.
5. A CP file must have the columns `time/s`, `Ewe/V`, and `I/mA` (or `<I>/mA`).
6. The app shows a warning that lists each run it cannot fully use, and the reason.

The metadata file records all of these warnings.

### Preconditioning

Upload `.mpr` PEIS files and identify one positive PEIS and one negative PEIS file. The semi-ellipse fit can be run on all cycles.

### Limiting Current

Upload all `.mpr` files for a limiting current experiment. The app expects CP, OCV, and PEIS files grouped by filename prefix and upload/discovery order.

### Current Fraction

Upload all `.mpr` files of the run. Include the OCV, CA, and PEIS/EIS files. The app uses the PEIS/EIS files only to fit `R_bulk` and `R_i`.

The app finds the two trials from the file names and the upload order. Each OCV file name must contain `OCV`. Each CA file name must contain `CA`. The file numbers do not matter.

The app uses this order:

1. The first `OCV` file is a leading rest step. The app discards it.
2. The next `OCV` file is the positive trial OCV.
3. Every `CA` file directly after it forms the positive CA chain.
4. The next `OCV` file is a leading rest step. The app discards it.
5. The next `OCV` file is the negative trial OCV.
6. Every `CA` file directly after it forms the negative CA chain.

The app stops after it finds two trials. The first trial is positive. The second trial is negative.

Example (file names are shortened):

```text
01_OCV                 leading rest step (discarded)
02_CA                  ignored (comes after a discarded OCV)
03_OCV                 positive trial OCV
04_CA, 05_CA           positive CA chain (joined into one run)
07_OCV                 leading rest step (discarded)
08_OCV                 negative trial OCV
09_CA                  negative CA chain
```

The app joins the CA files of a chain into one continuous timeline. It calculates the currents from this joined run:

- `I,o` is the highest current in the first 10 points of the chain.
- `I,ss` is set by the `I,ss method` option (see below).

Select the positive PEIS file and the negative PEIS file in the app. The app fits `R_bulk` and `R_i` for each file. It uses the first fitted EIS cycle as the initial resistance. It uses the last fitted EIS cycle as the steady-state resistance. The positive PEIS file must match the first trial. The negative PEIS file must match the second trial.

`I,ss` method:

- `Tail average` averages the last N points of the CA chain. Set N with `Points from the end to average`. The same N is used to average the OCV and the final voltage.
- `Transient fit (Na-Sn alloy)` fits the CA chain with a transient model. Use it for Na-Sn alloy current-fraction data only.

Make sure no other file name contains `CA` or `OCV`. The app finds these names by text match. A name such as `CALIBRATION` is read as a CA file.

### Diffusion Coefficient

Upload OCV relaxation `.mpr` files. Enter:

- Thickness in `um`
- Cutoff time in `h`
- Alpha, default `0.05`

The app fits:

```text
V(t) = A exp(-k t) + C
```

and calculates:

```text
D = k L^2 / pi^2
```

The log plot uses:

```text
log(|V(t) - V_inf| / mV)
```

where `V_inf` is the fitted offset `C`.

## Test Data

There are four sets of test data under the original `test dataset` directory.

They are:

- Cell 8: LiIn Symmetric 500 um PEO r = 0.08 | D = 6.9e-8 cm^2/s | L = 0.0537 cm
- Cell 19: LiIn Symmetric 500 um PEO r = 0.08 | D = 6.9e-8 cm^2/s | L = 0.0493 cm
- Cell 51: LiIn Symmetric 1000 um PEO r = 0.08 | D = 6.9e-8 cm^2/s | L = 0.1074 cm
- Cell 52: LiIn Symmetric 1000 um PEO r = 0.08 | D = 6.9e-8 cm^2/s | L = 0.1328 cm

They contain raw `.mpr` files of preconditioning and limiting current runs.

## Points of Concern / FAQs

1. Please upload all files of a run in `.mpr` format.
2. Older `.mpr` files from older EC-Lab software may not work with the `galvani` library. The app shows a warning for each file that it cannot read. Please re-download `.mpr` files from newer EC-Lab software if needed.
3. Do not close the terminal window opened by the launcher. The terminal must remain open while the app is in use.
4. The terminal logs function calls and errors. If the terminal is accidentally closed, close the Streamlit browser tab and re-open the launcher.
5. If the app shows a warning for an empty file, the experiment possibly did not record data for that step. Check the file in EC-Lab. See `Empty and Unreadable Files` in the Analysis Notes.
6. Keep the metadata `.txt` file with your results. It records the files, the settings, and the warnings for each analysis.
7. If Current Fraction shows `No valid OCV + CA trials found`, check the file names and the upload order. Each trial needs a leading rest OCV file, a trial OCV file, and at least one CA file after the trial OCV file. Upload all the files at the same time.

## Contact Information

Should any questions or issues arise, please contact Hansen (hansenry [at] berkeley [dot] edu) or Zirong He (zironghe@berkeley.edu). Feedback, testimonials, and notes of appreciation are always welcome. If this software contributes to any publications outside the Balsara Lab, please acknowledge the Balsara Lab, University of California, Berkeley.
