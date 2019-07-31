import unittest
from dimepy import Spectrum

class SpectrumTest(unittest.TestCase):

    def test_loading(self):
        spectrum = Spectrum("data/example.mzML", "test")
        spectrum.load_scans()

    def test_negative_polarity(self):
        # The entire spectrum is positive polarity, so this should return False
        spectrum = Spectrum("data/example.mzML", "test")
        spectrum.limit_polarity("negative")
        self.assertFalse(True in spectrum.to_use)

    def test_positive_polarity(self):
        # The entire spectrum is positive, so this should return False
        spectrum = Spectrum("data/example.mzML", "test")
        spectrum.limit_polarity("positive")
        self.assertFalse(False in spectrum.to_use)

    def test_binning(self):
        spectrum = Spectrum("data/example.mzML", "test")
        spectrum.limit_polarity("negative")
        spectrum._to_use[0] = True
        spectrum.load_scans()
        spectrum.bin(100)

        # Hand calculated, like the sadistic person I am.
        self.assertAlmostEqual(sum(spectrum.masses), 3742.8, 1)
        self.assertAlmostEqual(sum(spectrum.intensities), 492923.8, 1)


if __name__ == '__main__':
    unittest.main()