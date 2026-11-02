"""Run: python -m unittest discover -s tests -v."""
from pathlib import Path
import sys
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'ElectroSmart_macOS'))
from qt_circuit import impedance, fit_spectrum
from plotting import impedance_fit, ecm_fit, fit_ecm_spectrum


class QtCircuitTests(unittest.TestCase):
    def test_recovery_and_order_invariance(self):
        f = np.geomspace(1e7, 1e-3, 100)
        p = np.array([600, 1e-8, .9, 2500, 5e-6, .8, .001, .6])
        w = 2*np.pi*f
        # Generate through parallel admittances, independently of impedance().
        z = (1/(1/p[0]+p[1]*(1j*w)**p[2])
             + 1/(1/p[3]+p[4]*(1j*w)**p[5]) + 1/(p[6]*(1j*w)**p[7]))
        result = fit_spectrum(f, z)
        np.testing.assert_allclose(result['params'], p, rtol=.01)
        self.assertLess(np.max(abs((result['predict'](f)-z)/z)), 1e-5)
        reverse = fit_spectrum(f[::-1], z[::-1])
        np.testing.assert_allclose(reverse['params'], result['params'], rtol=1e-8)

    def test_warburg_is_half_exponent_special_case(self):
        f = np.geomspace(.1, 1e6, 50)
        p = [500, 1e-9, .9, 2000, 1e-6, .8, 1/(np.sqrt(2)*120), .5]
        w = 2*np.pi*f
        expected = (500/(1+500*1e-9*(1j*w)**.9)
                    + 2000/(1+2000*1e-6*(1j*w)**.8)
                    + 120*(1-1j)/np.sqrt(w))
        np.testing.assert_allclose(impedance(p, f), expected, rtol=1e-12)

    def test_invalid_spectra_fail_clearly(self):
        with self.assertRaises(RuntimeError):
            fit_spectrum([1, 2], [1j, 2j])
        with self.assertRaises(RuntimeError):
            fit_spectrum(np.arange(8), np.ones(8))
        with self.assertRaises(RuntimeError):
            fit_spectrum(np.arange(1, 9), np.zeros(8))

    def test_other_eis_methods_are_rejected(self):
        with self.assertRaises(ValueError):
            fit_ecm_spectrum([], [], 'R1 + R2|Q2 + W')
        with self.assertRaises(ValueError):
            impedance_fit({'technique': 'Semi-ellipse fit'}, '', '', None, '')
        with self.assertRaises(ValueError):
            ecm_fit('', '', None, '', remove_tail=True)

    def test_platform_sources_match(self):
        for name in ['app.py', 'plotting.py', 'qt_circuit.py', 'validation.py']:
            self.assertEqual((ROOT/'ElectroSmart_macOS'/name).read_bytes(),
                             (ROOT/'ElectroSmart_Windows'/name).read_bytes())


if __name__ == '__main__':
    unittest.main()
