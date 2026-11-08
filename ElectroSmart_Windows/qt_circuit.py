"""Fit (Rb || Qb) + (Ri || Qi) + Qt independently for each spectrum.

Higher-frequency branch = nominal bulk (an assignment, not physical proof).
Parameter order: Rb, Qb, nb, Ri, Qi, ni, Qt, nt. No series resistor.
"""
import numpy as np
from scipy.optimize import least_squares

CIRCUIT = "(Rb | Qb) + (Ri | Qi) + Qt"
PARAMETER_NAMES = ("Rb", "Qb", "nb", "Ri", "Qi", "ni", "Qt", "nt")
PARAMETER_UNITS = ("Ohm", "Ohm^-1 s^n", "-", "Ohm", "Ohm^-1 s^n", "-", "Ohm^-1 s^n", "-")
LOWER = np.array([1e-6, 1e-18, .3, 1e-6, 1e-18, .3, 1e-18, .05])
UPPER = np.array([1e10, 1., 1., 1e10, 1., 1., 1., 1.])
LOG_INDICES = np.array([0, 1, 3, 4, 6])
SEED = 20261101
N_STARTS = 36


def impedance(p, f):
    """Complex impedance in Ohm; Q is a CPE coefficient, not capacitance."""
    w = 2*np.pi*np.asarray(f, dtype=float)
    rb, qb, nb, ri, qi, ni, qt, nt = p
    return (rb/(1+rb*qb*(1j*w)**nb)
            + ri/(1+ri*qi*(1j*w)**ni) + 1/(qt*(1j*w)**nt))


def _encode(p):
    t = np.asarray(p, dtype=float).copy()
    t[LOG_INDICES] = np.log(t[LOG_INDICES])
    return t


def _decode(t):
    p = t.copy()
    p[LOG_INDICES] = np.exp(p[LOG_INDICES])
    return p


def _canonical(p):
    high = -np.log(p[0]*p[1])/p[2]
    low = -np.log(p[3]*p[4])/p[5]
    perm = [3, 4, 5, 0, 1, 2, 6, 7] if low > high else list(range(8))
    return p[perm], perm


def fit_spectrum(f, z):
    """Modulus-weighted complex least squares with deterministic starts."""
    f, z = np.asarray(f, dtype=float), np.asarray(z, dtype=complex)
    if (f.ndim != 1 or z.ndim != 1 or len(f) != len(z) or len(f) < 7
            or not np.all(np.isfinite(f)) or np.any(f <= 0)
            or not np.all(np.isfinite(z)) or np.any(abs(z) == 0)):
        raise RuntimeError('Fit requires at least seven finite positive-frequency, nonzero impedance points.')
    order = np.argsort(-f, kind='stable')
    f, z = f[order], z[order]
    rng = np.random.default_rng(SEED)
    r_scale = max(float(z.real.max()), float(np.median(abs(z))), 1.)
    tail_scale = max(float(-z.imag[-1]), 1.)
    starts = []
    for j in range(N_STARTS):
        p = []
        for _ in range(2):
            r = r_scale*rng.uniform(.15, .9)
            peak = 10**rng.uniform(np.log10(f.min()), np.log10(f.max())+2)
            n = rng.uniform(.4, 1.)
            p += [r, 1/(r*(2*np.pi*peak)**n), n]
        nt = [.2, .5, .8][j % 3]
        p += [1/(tail_scale*(2*np.pi*f[-1])**nt), nt]
        starts.append(np.clip(p, LOWER, UPPER))
    # Seed an unresolved bulk arc without fitting another circuit first.
    rb = max(float(z.real[0]), 1.)
    ri = max(float(z.real.max())-rb, rb)
    fi = float(f[np.argmax(-z.imag)])
    starts[0] = np.clip([rb, 1/(rb*(2*np.pi*f.max()*10)**.9), .9,
                        ri, 1/(ri*(2*np.pi*fi)**.8), .8,
                        1/(tail_scale*(2*np.pi*f.min())**.5), .5], LOWER, UPPER)

    def residual(t):
        delta = (impedance(_decode(t), f)-z)/abs(z)
        return np.r_[delta.real, delta.imag]

    attempts = []
    for start in starts:
        fit = least_squares(residual, _encode(start),
            bounds=(_encode(LOWER), _encode(UPPER)), method='trf',
            jac='3-point', x_scale='jac', max_nfev=2500,
            ftol=1e-9, xtol=1e-9, gtol=1e-9)
        if fit.success and np.isfinite(fit.cost):
            attempts.append((fit, start))
    if not attempts:
        raise RuntimeError('No Qt circuit fit converged.')
    best, start = min(attempts, key=lambda pair: pair[0].cost)
    raw = _decode(best.x)
    p, perm = _canonical(raw)
    _, s, vt = np.linalg.svd(best.jac, full_matrices=False)
    rank = int(np.sum(s > np.finfo(float).eps*max(best.jac.shape)*s[0]))
    se = np.full(8, np.nan)
    if rank == 8:
        cov = (vt.T/s**2) @ vt*(2*best.cost/(2*len(f)-8))
        scale = np.ones(8)
        scale[LOG_INDICES] = raw[LOG_INDICES]
        se = (np.sqrt(np.maximum(np.diag(cov), 0))*scale)[perm]
    fb = float(np.exp(-np.log(p[0]*p[1])/p[2])/(2*np.pi))
    fi = float(np.exp(-np.log(p[3]*p[4])/p[5])/(2*np.pi))
    notes = ['bulk = higher-frequency branch (model assumption)']
    for peak, indices, label in [(fb, [1, 2], 'bulk'), (fi, [4, 5], 'interface')]:
        if not f.min() <= peak <= f.max():
            notes.append(f'{label} peak outside measured range')
            se[indices] = np.nan
    bound = (np.isclose(_encode(p), _encode(LOWER), atol=1e-4, rtol=0)
             | np.isclose(_encode(p), _encode(UPPER), atol=1e-4, rtol=0))
    if bound.any():
        notes.append('parameter at bound: '+', '.join(np.array(PARAMETER_NAMES)[bound]))
        se[bound] = np.nan
    if p[-1] <= .0501:
        notes.append('Qt nearly resistive; branch labels do not establish physical bulk/interface identity')
    if rank < 8:
        notes.append('rank-deficient fit; local errors unavailable')
    near = np.array([_canonical(_decode(r.x))[0] for r, _ in attempts
                     if r.cost <= best.cost*1.01+1e-12])
    return dict(params=p.tolist(), fit_params=p.tolist(), conf=se.tolist(),
        initial=np.asarray(start)[perm].tolist(), success=True,
        predict=lambda freq: impedance(p, freq), notes=notes,
        diagnostics={'Bulk peak frequency (Hz)': fb, 'Interface peak frequency (Hz)': fi,
            'Converged starts': len(attempts), 'Attempted starts': N_STARTS,
            'Random seed': SEED, 'Jacobian rank': rank,
            'Near-best Rb min (Ohm)': float(near[:, 0].min()),
            'Near-best Rb max (Ohm)': float(near[:, 0].max())})
