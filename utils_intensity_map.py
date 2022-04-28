import numpy as np
import healpy as hp


def readout_intensity(the_data, intensity_map):
    n_beams = the_data['nbeams_total']
    r = the_data['target_radius'] / 1.0e4 # microns to cm
    total_TW = np.mean(intensity_map)*10**(-12)
    surface_area = 4.0 * np.pi * r**2

    #rms
    intensity_map_normalised, avg_power = imap_norm(intensity_map)
    imap_pn = np.sign(intensity_map_normalised)
    intensity_map_rms = 100.0 * np.sqrt(np.mean(intensity_map_normalised))
    intensity_map_rms_spatial = imap_pn * 100.0 * np.sqrt(intensity_map_normalised**2)

    print('')
    print('The total power deposited is ', total_TW * surface_area, 'TW')
    print('The power per beam deposited is ', total_TW * surface_area / n_beams, 'TW')
    print('This is a drive efficiency of ', total_TW * surface_area / (n_beams * 0.25) * 100.0, '%')
    print('RMS is ', intensity_map_rms, '%')
    print('Number of beams ', n_beams)
    print('')

    return intensity_map_rms_spatial



def power_spectrum(intensity_map, LMAX):
    intensity_map_normalized, avg_power = imap_norm(intensity_map)

    # Compute the corresponding normalized mode spectrum
    rmsalms = hp.sphtfunc.map2alm(intensity_map_normalized, lmax=LMAX)
    var = abs(rmsalms)**2
    the_modes = np.zeros(LMAX)
    power_spectrum = np.zeros(LMAX)
    for l in range(LMAX):
        for m in range(l):
            if (m>0):
                the_modes[l] = the_modes[l] + 2.*var[hp.sphtfunc.Alm.getidx(LMAX, l, m)]
            else:          
                the_modes[l] = the_modes[l] + var[hp.sphtfunc.Alm.getidx(LMAX, l, m)]
        power_spectrum[l] = (2.0 * l + 1.0) * the_modes[l] / (4.0 * np.pi)

    power_spectrum_unweighted = np.sqrt(the_modes)
    power_spectrum_weighted = np.sqrt(power_spectrum)
    print("The LLE quoted rms cumalitive over all modes is: ", np.sqrt(np.sum(the_modes))*100.0, "%")

    return power_spectrum_unweighted, power_spectrum_weighted



def create_ytrain(pointing_per_cone, pointing_nside, defocus_per_cone, num_defocus, power_per_cone, num_powers):

    Y_train = np.hstack((np.array(pointing_per_cone)/(pointing_nside-1), np.array(defocus_per_cone)/(num_defocus-1)))
    Y_train = np.hstack((Y_train, np.array(power_per_cone)/(num_powers-1)))
    Y_norms = [pointing_nside, num_defocus, num_powers]

    return Y_train, Y_norms



def create_xtrain(intensity_map, LMAX):

    intensity_map_normalized, avg_power = imap_norm(intensity_map)
    X_train = imap2xtrain(intensity_map_normalized, LMAX)

    return X_train



def imap2xtrain(intensity_map_normalized, LMAX):

    X_train_complex = hp.sphtfunc.map2alm(intensity_map_normalized, lmax=LMAX)
    X_train = np.hstack((X_train_complex.real, X_train_complex.imag))

    return X_train



def xtrain2imap(X_train, LMAX, imap_nside):

    num_coeff = int(((LMAX + 2) * (LMAX + 1))/2.0)
    np_complex = np.vectorize(complex)
    X_train = np.squeeze(X_train)
    X_train_complex = np_complex(X_train[:num_coeff], X_train[num_coeff:])
    intensity_map_normalized = hp.alm2map(X_train_complex, imap_nside)

    return intensity_map_normalized



def imap_norm(intensity_map):

    avg_power = np.mean(intensity_map)
    intensity_map_normalized = (intensity_map / avg_power - 1.0)

    return intensity_map_normalized, avg_power