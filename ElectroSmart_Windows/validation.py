"""Check MPR files before analysis.

Read each uploaded MPR file once. Find files that are empty or that
galvani cannot read. Check that a file has the columns that an analysis
needs.
"""

from typing import IO, NamedTuple, Optional

from galvani import BioLogic

STATUS_OK = "ok"
STATUS_EMPTY = "empty"
STATUS_UNREADABLE = "unreadable"


class FileReport(NamedTuple):
    """The result of the first read of one MPR file.

    Attributes:
        name: The file name.
        status: One of STATUS_OK, STATUS_EMPTY, or STATUS_UNREADABLE.
        columns: The column names in the file. Empty if the file
            cannot be read.
        n_rows: The number of data rows in the file.
        detail: A short reason for the status. Empty if the status is
            STATUS_OK.
    """

    name: str
    status: str
    columns: tuple[str, ...]
    n_rows: int
    detail: str


class ColumnRequirement(NamedTuple):
    """One column that an analysis needs.

    Attributes:
        label: The name to show to the user.
        candidates: The accepted column names.
        fuzzy: If True, accept a column whose name contains a
            candidate. Use this only where the analysis code also
            matches names this way.
    """

    label: str
    candidates: tuple[str, ...]
    fuzzy: bool = False


class ColumnProblem(NamedTuple):
    """The columns that one file does not have.

    Attributes:
        file_name: The file name.
        missing: The labels of the missing columns.
        found: The column names that the file has.
    """

    file_name: str
    missing: tuple[str, ...]
    found: tuple[str, ...]


# The analysis code reads these columns by exact name.
PEIS_REQUIREMENTS = (
    ColumnRequirement("cycle number", ("cycle number",)),
    ColumnRequirement("Re(Z)/Ohm", ("Re(Z)/Ohm",)),
    ColumnRequirement("-Im(Z)/Ohm", ("-Im(Z)/Ohm",)),
)
LIMITING_CP_REQUIREMENTS = (
    ColumnRequirement("time/s", ("time/s",)),
    ColumnRequirement("Ewe/V", ("Ewe/V",)),
    ColumnRequirement("I/mA (or <I>/mA)", ("I/mA", "<I>/mA")),
)

def _one_line(text: str) -> str:
    """Replace all white space in a text with single spaces."""
    return " ".join(text.split())


def inspect_mpr_file(file_obj: IO[bytes]) -> FileReport:
    """Read an MPR file once and report whether the app can use it.

    Check the file size first. Then read the file with galvani. Report
    a file with no data rows as empty. Report a file that galvani
    cannot read as unreadable. Return the file pointer to the start.

    Args:
        file_obj: An MPR file object with a name attribute.

    Returns:
        A report with the status, the column names, and the row count.
    """
    name = file_obj.name

    file_obj.seek(0, 2)
    size = file_obj.tell()
    file_obj.seek(0)
    if size == 0:
        return FileReport(name, STATUS_EMPTY, (), 0, "The file has 0 bytes.")

    try:
        mpr = BioLogic.MPRfile(file_obj)
        data = mpr.data
        columns = tuple(data.dtype.names or ())
        n_rows = len(data)
    except Exception as exc:  # galvani raises many different error types
        detail = _one_line(f"{type(exc).__name__}: {exc}")
        return FileReport(name, STATUS_UNREADABLE, (), 0, detail)
    finally:
        file_obj.seek(0)

    if n_rows == 0 or not columns:
        return FileReport(
            name, STATUS_EMPTY, columns, 0, "The file has no data rows."
        )
    return FileReport(name, STATUS_OK, columns, n_rows, "")


def find_column(
    columns: tuple[str, ...], requirement: ColumnRequirement
) -> Optional[str]:
    """Find the column that meets a requirement.

    Look for an exact match first. If the requirement is fuzzy, then
    look for a column that contains a candidate name.

    Args:
        columns: The column names in the file.
        requirement: The column to find.

    Returns:
        The matching column name, or None if no column matches.
    """
    for candidate in requirement.candidates:
        if candidate in columns:
            return candidate

    if requirement.fuzzy:
        lower_to_col = {col.lower().strip(): col for col in columns}
        for candidate in requirement.candidates:
            if candidate.lower() in lower_to_col:
                return lower_to_col[candidate.lower()]
        for col_lower, col in lower_to_col.items():
            if any(c.lower() in col_lower for c in requirement.candidates):
                return col
    return None


def check_columns(
    reports: dict[str, FileReport],
    file_names: list[str],
    requirements: tuple[ColumnRequirement, ...],
) -> list[ColumnProblem]:
    """List the files that miss a required column.

    Skip files that are empty or unreadable. The upload check already
    reports those files.

    Args:
        reports: The file reports, keyed by file name.
        file_names: The names of the files to check.
        requirements: The columns that each file must have.

    Returns:
        One problem for each file that misses at least one column.
    """
    problems = []
    for name in file_names:
        report = reports.get(name)
        if report is None or report.status != STATUS_OK:
            continue
        missing = tuple(
            req.label
            for req in requirements
            if find_column(report.columns, req) is None
        )
        if missing:
            problems.append(ColumnProblem(name, missing, report.columns))
    return problems


def explain_file_problem(
    reports: dict[str, FileReport],
    file_name: str,
    requirements: tuple[ColumnRequirement, ...],
) -> Optional[str]:
    """Give the reason that a file cannot be used, if there is one.

    Args:
        reports: The file reports, keyed by file name.
        file_name: The name of the file to check.
        requirements: The columns that the file must have.

    Returns:
        A short reason, or None if the file can be used.
    """
    report = reports.get(file_name)
    if report is None:
        return "The file was not checked."
    if report.status == STATUS_EMPTY:
        return "The file is empty."
    if report.status == STATUS_UNREADABLE:
        return "galvani cannot read the file."
    problems = check_columns(reports, [file_name], requirements)
    if problems:
        return "Missing column(s): " + ", ".join(problems[0].missing) + "."
    return None
