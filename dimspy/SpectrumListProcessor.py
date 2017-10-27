import numpy as np
import warnings
import multiprocess
import scipy.stats as sc_stats
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.preprocessing import Imputer
from joblib import Parallel, delayed

class SpectrumListProcessor(object):

    def __init__(self, spectrum_list):
        '''

        :param spectrum_list:
        '''
        self.spectrum_list = spectrum_list
        self._outlier_detected = False
        self._binned = False
        self._centered = False
        self._value_imputated = False

    def remove(self, spectrum):
        '''

        :param spectrum:
        :return:
        '''
        self.spectrum_list.remove(spectrum)

    def outlier_detection(self, mad_threshold=3, inplace=True, plot_path=None, results_path=None):
        '''

        :param mad_threshold:
        :param inplace:
        :param plot_path:
        :param results_path:
        :return:
        '''
        tics = [np.nansum(s.intensities) for s in self.spectrum_list.to_list()]
        mean_tic = np.nanmean(tics)
        mean_abs_dev = np.nanmean([abs(x - mean_tic) for x in tics])
        ad_f_m = [abs((x - mean_tic) / mean_abs_dev) for x in tics]
        outlier_spectrum = [s for i, s in enumerate(self.spectrum_list.to_list()) if ad_f_m[i] > mad_threshold]

        if inplace == True:
            [self.remove(x) for x in outlier_spectrum]
            warnings.warn("Outlier detection removed: " + ",".join([x.id for x in outlier_spectrum]))
            self._outlier_detected = True
        else:
            return outlier_spectrum


    def binning(self, bin_size=1, statistic="mean", inplace=True, n_jobs=1):
        '''

        :param bin_size:
        :param statistic:
        :param inplace:
        :param n_jobs:
        :return:
        '''
        def _bin(spectrum):
            bins = np.arange(round(min(spectrum.masses)), round(max(spectrum.masses)), step=bin_size)

            b_intensities, b_masses, b_number = sc_stats.binned_statistic(spectrum.masses,
                                                                          spectrum.intensities,
                                                                          bins=bins,
                                                                          statistic=statistic)

            return [b_masses[:-1], b_intensities, spectrum.id]



        pool = multiprocess.Pool(n_jobs)
        binned_spectra = pool.map_async(_bin, [spectrum for spectrum in self.spectrum_list.to_list()]).get()
        pool.close()
        pool.join()

        if inplace == True:
            for result in binned_spectra:
                binned_masses, binned_intensities, id = result

                for spectrum in self.spectrum_list.to_list():
                    if spectrum.id == id:
                        spectrum.masses = binned_masses
                        spectrum.intensities = binned_intensities
                        break
            self._binned = True

        else:
            warnings.warn("Non inplace binning yet to be implemented")



    def center(self, inplace=True, n_jobs=1):
        '''

        :param inplace:
        :param n_jobs:
        :return:
        '''
        def _center(data):
            spectrum, binned_masses = data
            centered_intensities = []
            spectrum_intensities = spectrum.intensities.tolist()
            spectrum_masses = spectrum.masses.tolist()
            for b_mass in binned_masses:
                if b_mass in spectrum_masses:
                    centered_intensities.append(spectrum_intensities[spectrum_masses.index(b_mass)])
                else:
                    centered_intensities.append(np.nan)
            centered_intensities = np.array(centered_intensities)
            return centered_intensities, spectrum.id

        if self._binned == False:
            warnings.warn("You need to bin the data before you can center it!")
        else:
            binned_masses = np.array(sum([x.masses.tolist() for x in self.spectrum_list.to_list()], []))

            pool = multiprocess.Pool(n_jobs)
            centered_spectrum = pool.map_async(_center, [[spectrum, binned_masses] for spectrum in self.spectrum_list.to_list()]).get()
            pool.close()
            pool.join()

            for result in centered_spectrum:
                centered_intensities, id = result
                if inplace == True:
                    for spectrum in self.spectrum_list.to_list():
                        if spectrum.id == id:
                            spectrum.masses = binned_masses
                            spectrum.intensities = centered_intensities
                            break
                    self._centered = True
                else:
                    warnings.warn("Inplace centering not implemented!")


    def value_imputation(self, method="knn", threshold=0.5, inplace=True):
        '''

        :param method:
        :param threshold:
        :param inplace:
        :return:
        '''
        def _remove_bins_by_threshold():
            sample_threshold = len(self.spectrum_list.to_list()) * threshold
            df = self.spectrum_list.flatten_to_dataframe()
            df.dropna(axis=1, thresh=sample_threshold, inplace=True)
            return df

        def _value_imputation(df):
            if method.upper() == "KNN":
                imp = Imputer(axis=0)
                imputated = imp.fit_transform(df)
                df = pd.DataFrame(imputated, columns=df.columns, index=df.index)
            elif method.upper == "BASIC":
                df.fillna(value=(np.nanargmin(df.values) / 2), inplace=True)

            return df

        df = _remove_bins_by_threshold()
        df = _value_imputation(df)

        if inplace == True:
            self.pandas_to_spectrum(df)
            self._value_imputated = True
        else:
            return df

    def pandas_to_spectrum(self, df):
        '''

        :param df:
        :return:
        '''
        masses = df.columns
        for id, values in df.iterrows():
            intensities = values.values
            spectrum = [x for x in self.spectrum_list.to_list() if x.id == id][0]
            spectrum.masses = masses
            spectrum.intensities = intensities


    def to_spectrumlist(self):
        '''

        :return:
        '''
        from SpectrumList import SpectrumList
        return SpectrumList(self.spectrum_list.to_list())