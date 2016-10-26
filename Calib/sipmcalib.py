#
# sipmcal is a module with a main data class CalData and a list of functions
# to do the calibration of the SiPMs in IC
#

import math
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar, least_squares
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

NBOARDS = 28
NSENSOR_PER_BOARD = 64
SENSORID_UNIT = 1000
NSENSORS = NBOARDS*NSENSOR_PER_BOARD

# --- Utilities


def index_of_sensorid(sensorID):
    """ Converts SiPM sensorID into index ID in a list rage(28*64))
    """
    if (sensorID < SENSORID_UNIT): return sensorID # temp fix
    iboard = sensorID / SENSORID_UNIT
    isensor = sensorID % SENSORID_UNIT
    index = (iboard-1) * NSENSOR_PER_BOARD + isensor
    return index


def sensorid_of_index(index):
    """ Converts SiPM index ID into
    """
    iboard = int(index/NSENSOR_PER_BOARD)
    isensor = index % NSENSOR_PER_BOARD
    senid = SENSORID_UNIT*(iboard+1) + isensor
    return senid


def np_index_of_xrange(xs, xrange):
    """ Returns the indexs of the list where the list of ordered values, xs,
    in inside the range given by the 2-item ntuple xrange=(x0,x1),
    where x0 is the lower limit and x1 is the upper one.
    """
    x0, x1 = xrange
    i0, i1 = np.where(xs >= x0)[0][0], np.where(xs >= x1)[0][0]
    return i0, i1


def np_percentile(pars, percentile=0.01):
    """ from a list of parameters, returns the values of the range (percentile,
    1-percentile)
    """
    lpars = list(pars)
    lpars.sort()
    nn = 1.*len(lpars)
    ni = int(percentile*nn)
    nf = int((1.-percentile)*nn)
    return lpars[ni], lpars[nf]


def plt_subplots(n, figsize=None):
    """ nice division of plt into subplots, returns nx, ny for n
    """
    if (n > 20):
        print('WARNING: large number of SiPMs to plot!')
    nx = int(math.sqrt(n))
    ny = nx
    while (nx*ny < n):
        nx += 1
    if (not figsize):
        figsize = (4*ny, 3*nx)
    return nx, ny, figsize


# --- Data class


class CalData:
    """ Holds the SiPM calibration data.
    Data is stored into NSENSORS array.
    xbins: is an np.array with the center of the bins of the histograms
    of all SiPMs.
    values: is a np.array 2D one per NSESORS, indexed by SiPM index, with the
    contents of the SiPMs histograms
    """

    def __init__(self, ifilename=None, nsensors=NSENSORS):
        """ reads the SiPMs calibration histograms (dark current or led)
        from a txt file. The first row of the txt file is the xbins of the
        histograms (the adcs counts).
        The 1-n rows are the values of the contents of the histograms for each
        SiPMD. The first element of each row (from 1-n) is the sensorID
        of the SiPM. indexes are the list of all sequencial index with data.
        """
        self.nsensors = nsensors
        if (ifilename):
            cal_load_txtfile(self, ifilename)
        return

    def values_in_range(self, index, xrange):
        """ returns xbins and values of the SiPM with index in the rage [x0, x1]
        """
        i0, i1 = np_index_of_xrange(self.xbins, xrange)
        return self.xbins[i0:i1], self.values[index, i0:i1]


def cal_load_txtfile(cal, fname):
        """ load the calibration data from a file
        The file contains as first row the xbins (discarting the first item)
        The following rows are the contents of each SiPM.
        The first item in the row is sensorID.
        """
        data = np.loadtxt(fname)
        cal.xbins = data[0, 1:]
        cal.nbins = len(cal.xbins)
        senids = map(int, data[1:, 0])
        cal.indexes = []
        cal.values = np.array([[0]*cal.nbins, ]*cal.nsensors)
        for i, senid in enumerate(senids):
            index = index_of_sensorid(senid)
            cal.indexes.append(index)
            # print('sensor ID {} index {} i {}'.format(senid,index,i))
            cal.values[index] = data[i+1, 1:]
        print('loaded calibration data from file {}'.format(fname))
        print('number of SiPMs with data {}'.format(len(cal.indexes)))
        return


def cal_set_values(xbins, values, indexes):
    """ create a CalData class for the indexes, with the xbins and values
    """
    cal = CalData()
    cal.xbins = np.array(xbins)
    cal.nbins = len(cal.xbins)
    cal.indexes = np.array(indexes)
    cal.values = np.array([[0]*cal.nbins, ]*cal.nsensors)
    for i, index in enumerate(indexes):
        cal.values[index] = values[i]
    return cal


# ---- Simple estimation of the main calibration parameters


def cal_est_noise(cal, indexes=None):
    """ Simple estimate the noise of the list of SiPMs indexes.
    Compute the rms of the negative part of the charge distribution.
    """
    xs = cal.xbins
    if (not indexes):
        indexes = cal.indexes

    def noise_(index):
        i0 = np.where(xs > 0.)[0][0]
        xxs, yys = cal.xbins[:i0], cal.values[index, :i0]
        return math.sqrt(np.sum(xxs*xxs*yys)/np.sum(yys))
    nois = np.array(map(noise_, indexes))
    return nois


def cal_est_pes(cal, indexes=None):
    """ Simple estimation of the mean poisson (in pes) of the set of SiPMs
    indexes.
    It compute the p(0) compute the size of the 0-peak from the negative part.
    """
    xs = cal.xbins
    if (not indexes):
        indexes = cal.indexes

    def mu_(index):
        # ibin1 = np.where(xs<0)[-1][0]
        ibin0 = np.where(xs >= 0.)[0][0]
        if (ibin0 < 0):
            return -1
        ys = cal.values[index]
        n = 2*np.sum(ys[:ibin0])
        if (abs(xs[ibin0]) < 1e-6):
            n += ys[ibin0]
        else:
            n += 2*ys[ibin0]
        p0 = (1.*n)/(1.*np.sum(ys))
        # print(' i0 {} n {} ntot {} p0 {} '.format(ibin0,sum(ys),n,p0))
        if (p0 > 1.):
            return -0.1
        return -1*math.log(p0)

    mus = np.array(map(mu_, indexes))
    return mus


def cal_est_pes_ave(cal, indexes=None):
    """ Estimates the poisson mean in pes from the mean of the adcs
    of the SiPMs
    """
    xs = cal.xbins
    if (not indexes):
        indexes = cal.indexes

    def mu_(index):
        ys = cal.values[index]
        mu = np.sum(xs*ys)/np.sum(ys)
        return mu
    mus = np.array(map(mu_, indexes))
    return mus


def cal_est_gain(cal, indexes=None, bounds=(12., 30.)):
    """ Estimate the gain looking for a period in the histogram.
    """
    xs = cal.xbins
    if (not indexes):
        indexes = cal.indexes

    def fun_period(ys):
        """ returns a function which minimum is the adcs/count
        of a histogram with xs-array with adcs counts and ys-contnets
        """
        def fun(pe):
            # set the bins to the corresponding int period
            x0s = np.array(map(int, xs/pe+0.5))*pe
            # first bin non zero
            bin0 = np.where(x0s > 0)[0][0]
            # remove the zero and negative periods, keep only the positive ones
            x0s, x1s, y1s = x0s[bin0:], xs[bin0:], ys[bin0:]
            # compute the chi2
            chi2 = math.sqrt(np.sum((x0s-x1s)*(x0s-x1s)*y1s)/np.sum(y1s))
            return chi2
        return fun

    def fit_(index):
        if (index % 500 == 0):
            print('fitting...')
        fun = fun_period(cal.values[index])
        result = minimize_scalar(fun, bounds=bounds, method='Bounded')
        if (result.success):
            return result.x
        return 0.

    gains = np.array(map(fit_, indexes))
    return gains


def cal_est_led_signal(caldark, called, indexes=None):
    """  Estimate the signal (led-dark) of the SiPMs
    """
    xs = called.xbins
    if (not indexes):
        indexes = called.indexes

    def signal_(index):
        ibin0 = np.where(xs > 0.)[0][0]
        yled, ydark = called.values[index], caldark.values[index]
        frat = 1.*np.sum(yled[:ibin0])/(1.*np.sum(ydark[:ibin0]))
        # print(' f rat ',frat)
        # print(' yled ',len(yled))
        # print(' ydark ',len(ydark))
        ydark2 = frat*ydark
        # print(' ydark2 ',len(ydark2))
        xsig = (yled-ydark2)
        # print(' sig ',len(xsig))
        return xsig

    sigs = np.array(map(signal_, indexes))
    return sigs


def cal_est_led_pes(caldark, called, indexes=None):
    """  Estimate the

    """
    def mu_(sig, yled):
        fvis = (1.*sum(sig))/(1.*sum(yled))
        if (fvis >= 1.):
            return -1.
        muhat = -1.*(math.log(1.-fvis))
        return muhat
    if (not indexes):
        indexes = called.indexes
    sigs = cal_est_led_signal(caldark, called, indexes=indexes)
    mus = map(lambda i, index: mu_(sigs[i], called.values[index]),
              range(len(sigs)), indexes)
    return np.array(mus)


# --- Polos - plotting functions


def polo_cal(cal, indexes, xrange=None, figsize=None, ylog=True):
    """ plot the charge distribution of the SiPMs indexes in xrange=(x0,x1).
    returns the figure.
    """
    n = len(indexes)
    nx, ny, figsize = plt_subplots(n, figsize=figsize)
    fig, axes = plt.subplots(nx, ny, figsize=figsize)
    xs = cal.xbins
    if (not xrange):
        xrange = (np.min(xs), np.max(xs))
    for i, index in enumerate(indexes):
        plt.subplot(nx, ny, i+1)
        xs, ys = cal.values_in_range(index, xrange)
        plt.plot(xs, ys)
        if (ylog):
            plt.yscale('log')
    fig.tight_layout()
    plt.show()
    return fig


def polo_cals(cals, indexes, xrange=None, figsize=None, ylog=True):
    """ plots the charge distribution of the SiPMs indixes in the xrange=(x0,x1)
    for the list of calibration data (cals)
    """
    n = len(indexes)
    nx, ny, figsize = plt_subplots(n)
    fig, axes = plt.subplots(nx, ny, figsize=figsize)
    xs = cals[0].xbins
    if (not xrange):
        xrange = (np.min(xs), np.max(xs))
    for i, index in enumerate(indexes):
        plt.subplot(nx, ny, i+1)
        for cal in cals:
            xs, ys = cal.values_in_range(index, xrange)
            plt.plot(xs, ys)
        if(ylog):
            plt.yscale('log')
    fig.tight_layout()
    plt.show()
    return fig


def polo_pars(indexes, pars, pos, bins=100, label=''):
    """ plot the variable pars distribution, its value vs index
    and the x,y plot.
    Pos is a list with the (x,y) positions of the SiPMs.
    """
    fig = plt.figure(figsize=(4*3, 3*3))
    gs = gridspec.GridSpec(4, 5)
    ax1 = plt.subplot(gs[0:2, 0:2])
    ax1.hist(pars, bins)
    ax1.set_xlabel(label)
    ax1.set_ylabel('# events')
    ax2 = plt.subplot(gs[2:, 0:2])
    ax2.scatter(indexes, pars)
    ax2.set_xlabel('index')
    ax2.set_ylabel(label)
    ax3 = plt.subplot(gs[:, 2:])
    cxs = map(lambda x: x[0], pos)
    cys = map(lambda x: x[1], pos)
    cc = ax3.scatter(cxs, cys, c=pars)
    ax3.set_title(label)
    ax3.set_xlabel('x (mm)')
    ax3.set_ylabel('y (mm)')
    fig.colorbar(cc)
    fig.tight_layout()
    plt.show()
    return fig


def polo_cal_fit(cal, indexes, pss, fun, xrange=None, norma=True, title=''):
    """ plots the fit results for the SiPMs with indexes
    """
    n = len(indexes)
    nx, ny, figsize = plt_subplots(n)
    fig, axes = plt.subplots(nx, ny, figsize=figsize)
    plt.suptitle(title)
    xs = cal.xbins
    if (not xrange):
        xrange = (np.min(xs), np.max(xs))
    for i, index in enumerate(indexes):
        ax = plt.subplot(nx, ny, i+1)
        xs, ys = cal.values_in_range(index, xrange)
        plt.plot(xs, ys)
        ax.set_title(str(index))
        ps = pss[i]
        fys = fun(ps, xs)
        scale = np.sum(ys)/np.sum(fys)
        # print(' scale {}'.format(scale))
        plt.plot(xs, scale*fys)
    fig.tight_layout()
    plt.show()
    return fig

# --- Fits to estimate the calibration paramters


def ffun_ngauss(ps, xs):
    """ function to fit a n-periodic gaussian peaks distribution
    ps[0] - origin (usually 0.)
    ps[1] - period (usually gain)
    ps[2] - noise
    ps[3] - noise 1st peak
    ps[4:] - number of events in each peak
    """
    ngauss = int(len(ps)-4)
    x0, pe, s0, s1, ns = ps[0], ps[1], ps[2], ps[3], ps[4:]
    # print(ngauss,x0,pe,ns,ss)
    efacto = 1./math.sqrt(2.*math.pi)

    def funi_(i):
        s2 = s0*s0 + i*s1*s1
        yfact = efacto/math.sqrt(s2)
        y = yfact*ns[i]*np.exp(-(xs-x0-pe*i)*(xs-x0-pe*i)/(2*s2))
        return y

    ys = map(funi_, range(ngauss))
    y = reduce(lambda x, y: x+y, ys)
    return y


def ffun_poissongauss(ps, xs, ngauss=7):
    """ function to fo a poisson distribution with gaussian peaks
    ps[0] - scale
    ps[1] - origin (usually 0.)
    ps[2] - period
    ps[3] - poisson mean (dark current)
    ps[4] - noise (peak 0)
    ps[5] - sigma of the first gaussian
    m is the number of peak to fit
    """
    ifacto = np.array(map(math.factorial, range(ngauss)))
    efacto = 1./math.sqrt(2.*math.pi)
    nn, x0, pe, mu, s0, s1 = ps

    def ifun_(i):
        s2 = s0*s0 + i*s1*s1
        xref = x0+i*pe
        fact = (efacto/math.sqrt(s2))
        yg = fact*np.exp(-(xs-xref)*(xs-xref)/(2.*s2))
        yp = (math.exp(i*math.log(mu))/ifacto[i])
        return yg*yp

    iys = map(ifun_, range(ngauss))
    ys = reduce(lambda x, y: x+y, iys)
    ys = nn*math.exp(-mu)*ys
    return ys


def cal_fit_(ps0, xs, ys, fun, bounds=None):
    """ Wrapper to least_squares.
    Returns result with the addition of the chi2.
    ps0: the initial guess parameters,
    xs, ys: np arrays with the x, y data,
    fun: is a function of the ps.
    """
    def func(ps):
        return (ys-fun(ps, xs))/(1.+np.sqrt(ys))

    result = least_squares(func, ps0, bounds=bounds)
    chi2 = -1.
    if (result.success):
        res = func(result.x)
        chi2 = np.sum(res*res)/(1.*(len(ys)-len(ps0)))
    result.chi2 = chi2
    return result


def cal_fit_poissongauss(cal, indexes=None, ngauss=5):
    """ for the indexes of the cal (CalData) to n-gaussian,
    returns the lists of chi2 and the fitted-parameters
    """
    xrange = (-20., 120.)
    if (not indexes):
        indexes = cal.indexes
    fun = ffun_poissongauss
    chi2, pss = [], []
    for index in indexes:
        xs, ys = cal.values_in_range(index, xrange)
        if (index % 200 == 0):
            print('fitting data...')
        # for SiPMs
        # ps0 = np.array([10000., 0., 16., 1., 2., 2.])
        # bounds = ((0., -10., 12., 0.0, 0.5, 0.5),
        #          (35000., 10., 30., 6., 10., 10.))
        ps0 = np.array([35000., 0., 22., 1., 7., 7.])
        bounds = ((0., -10., 10., 0.0, 2., 2.),
                 (200000., 10., 40., 2., 15., 15.))
        # print(' bounds {}'.format(bounds))
        result = cal_fit_(ps0, xs, ys, fun, bounds=bounds)
        if (not result.success):
            print(' fit {} success {}'.format(index, result.success))
        chi2.append(result.chi2)
        pss.append(result.x)
    return chi2, pss


def cal_fit_ngauss(cal, indexes=None, ngauss=5):
    """ fot the indexes of the cal (CalData) to n-gaussian,
    returns the lists of chi2 and the fitted-parameters
    """
    xrange = (-20., 120.)
    fun = ffun_ngauss
    chi2, pss = [], []
    for i, index in enumerate(indexes):
        xs, ys = cal.values_in_range(index, xrange)
        if (index % 400 == 0):
            print('fitting data...')
        ps0 = np.array([0., 15., 2., 2.] + [10000.]*ngauss)
        bounds = ([-6., 12., 1., 1.] + [0.]*ngauss,
                  [6., 40., 5., 5.] + [35000.]*ngauss)
        # print(' bounds {}'.format(bounds))
        result = cal_fit_(ps0, xs, ys, fun, bounds=bounds)
        if (not result.success):
            print(' fit {} success {}'.format(index, result.success))
        # success.append(result.success)
        chi2.append(result.chi2)
        pss.append(result.x)
        # print(' fit success {}'.format(result.success))
        # print(' guess values {}'.format(ps0))
        # print(' fit results {}'.format(pshat))
    return chi2, pss


def cal_fit_ngauss_panda(indexes, chi2, pss):
    """ create a panda table with the resuls of the n-gauss fit
    """
    nss = []
    for i in range(4, len(pss[0])):
        ni = np.array(map(lambda ps: ps[i], pss))
        nss.append(ni)
    ntot = np.array(reduce(lambda x, y: x+y, nss))
    n0 = nss[0]
    p0 = n0/ntot
    pes = -1*np.log(p0)
    dpan = {'indexes': indexes,
            'chi2': chi2,
            'ntot': ntot,
            'pedestal': map(lambda ps: ps[0], pss),
            'gain': map(lambda ps: ps[1], pss),
            'pes': pes,
            'noise': map(lambda ps: ps[2], pss),
            'noise-pe': map(lambda ps: ps[3], pss)}
    pan = pd.DataFrame(dpan)
    return pan


def cal_fit_poissongauss_panda(indexes, chi2, pss):
    """ create a panda table with the result of the poisson + n-gaussian fit
    """
    dpan = {'indexes': indexes,
            'chi2': chi2,
            'ntot': map(lambda ps: ps[0], pss),
            'pedestal': map(lambda ps: ps[1], pss),
            'gain': map(lambda ps: ps[2], pss),
            'pes': map(lambda ps: ps[3], pss),
            'noise': map(lambda ps: ps[4], pss),
            'noise-pe': map(lambda ps: ps[5], pss)}
    pan = pd.DataFrame(dpan)
    return pan
