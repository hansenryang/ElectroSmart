"""Two R-CPE branches plus semi-infinite Warburg; no series resistor.

The higher-frequency branch is assigned to bulk by model assumption.
Parameters: Rb, Qb, nb, Ri, Qi, ni, A_W. Positive scales are optimized
in log space. Fixed deterministic starts are used independently per cycle.
"""
import numpy as np
from scipy.optimize import least_squares


def impedance(p, f):
    w = 2 * np.pi * np.asarray(f, dtype=float)
    rb, qb, nb, ri, qi, ni, aw = p
    return (rb / (1 + rb * qb * (1j*w)**nb)
            + ri / (1 + ri * qi * (1j*w)**ni)
            + aw * (1-1j) / np.sqrt(w))


def fit_spectrum(f, z):
    f, z = np.asarray(f, dtype=float), np.asarray(z, dtype=complex)
    if (len(f) < 6 or not np.all(np.isfinite(f)) or np.any(f <= 0)
            or not np.all(np.isfinite(z)) or np.any(abs(z) == 0)):
        raise RuntimeError('Fit requires at least six finite, positive-frequency, nonzero impedance points.')
    order = np.argsort(-f, kind='stable')
    f, z = f[order], z[order]
    log_indices = np.array([0, 1, 3, 4, 6])
    lower = np.array([1e-6, 1e-18, .3, 1e-6, 1e-18, .3, 1e-12])
    upper = np.array([1e10, 1., 1., 1e10, 1., 1., 1e10])

    def encode(p):
        t = np.array(p, dtype=float).copy()
        t[log_indices] = np.log(t[log_indices])
        return t

    def decode(t):
        p = t.copy()
        p[log_indices] = np.exp(p[log_indices])
        return p

    def residual(t):
        d = (impedance(decode(t), f) - z) / abs(z)
        return np.r_[d.real, d.imag]

    def canonical(p):
        p = np.array(p).copy()
        log_fb = -np.log(p[0]*p[1])/p[2]
        log_fi = -np.log(p[3]*p[4])/p[5]
        perm = [3, 4, 5, 0, 1, 2, 6] if log_fi > log_fb else list(range(7))
        return p[perm], perm

    rb0 = max(float(z.real[0]), 1.)
    ri0 = max(float(z.real.max()) - rb0, rb0)
    fi0 = float(f[np.argmax(-z.imag)])
    aw0 = max(float(-z.imag[-1])*np.sqrt(2*np.pi*f[-1]), 1.)
    attempts = []
    for rb_scale in [.5, 1.]:
        for fb in [max(fi0*10, f.max()/10), f.max()*10, f.max()*1000]:
            for nb in [.65, .9, 1.]:
                rb, ni = rb0*rb_scale, .8
                start = [rb, 1/(rb*(2*np.pi*fb)**nb), nb,
                         ri0, 1/(ri0*(2*np.pi*fi0)**ni), ni, aw0]
                start = np.clip(start, lower, upper)
                result = least_squares(residual, encode(start),
                    bounds=(encode(lower), encode(upper)), method='trf',
                    jac='3-point', x_scale='jac', max_nfev=2500,
                    ftol=1e-9, xtol=1e-9, gtol=1e-9)
                if result.success and np.isfinite(result.cost):
                    attempts.append((result, start))
    if not attempts:
        raise RuntimeError('No bulk/interface ECM fit converged.')
    best, start = min(attempts, key=lambda a: a[0].cost)
    raw = decode(best.x)
    params, perm = canonical(raw)
    initial = np.asarray(start)[perm]
    # Local linearized errors, conditional on this circuit and weighting.
    _, s, vt = np.linalg.svd(best.jac, full_matrices=False)
    rank = int(np.sum(s > np.finfo(float).eps * max(best.jac.shape) * s[0]))
    se = np.full(7, np.nan)
    if rank == 7 and 2*len(f) > 7:
        cov = (vt.T / s**2) @ vt * (2*best.cost/(2*len(f)-7))
        scale = np.ones(7)
        scale[log_indices] = raw[log_indices]
        se = np.sqrt(np.maximum(np.diag(cov), 0))*scale
        se = se[perm]
    fb = float(np.exp(-np.log(params[0]*params[1])/params[2])/(2*np.pi))
    fi = float(np.exp(-np.log(params[3]*params[4])/params[5])/(2*np.pi))
    notes = ['bulk = higher-frequency branch (model assumption)']
    if not f.min() <= fb <= f.max():
        notes.append('bulk peak outside measured range; Qb and nb not resolved by a measured peak')
        se[1:3] = np.nan
    if rank < 7:
        notes.append('rank-deficient fit; standard errors unavailable')
    near = [canonical(decode(r.x))[0] for r, _ in attempts
            if r.cost <= best.cost*1.01 + 1e-12]
    near = np.asarray(near)
    rb_range = [float(near[:, 0].min()), float(near[:, 0].max())]
    if rb_range[1] - rb_range[0] > .1*params[0]:
        notes.append('Rb varies by >10% among starts within 1% of best cost')
    if np.any(np.isclose(best.x, encode(lower), atol=1e-5, rtol=0)
              | np.isclose(best.x, encode(upper), atol=1e-5, rtol=0)):
        notes.append('parameter at a bound; local errors may be unreliable')
    # Shared plot renderer uses [series offset, arc1, arc2, Warburg].
    # The zero is fixed, never optimized or exported as a fitted parameter.
    padded = [0.] + params.tolist()
    return dict(params=padded, conf=[0.] + se.tolist(),
                initial=[0.] + initial.tolist(), fit_params=padded,
                success=True, predict=lambda freq: impedance(params, freq),
                notes=notes, diagnostics={
                    'Bulk peak frequency (Hz)': fb,
                    'Interface peak frequency (Hz)': fi,
                    'Converged starts': len(attempts),
                    'Near-best Rb min (Ohm)': rb_range[0],
                    'Near-best Rb max (Ohm)': rb_range[1],
                    'Jacobian rank': rank})
