"""
Table Functions
GML, October 2016

ChangeLog
14/10: import table io functions from wfmFunctions
19/10 copied functions that read tables from sensorFunctions. Keep the old
functions in sensorFunctions for now, give functions here more coherente names
(e.g, read_geom_table rather than read_data_geom). Function read_FEE_table
now returns also calibration constants for RWF and BLR (MC version)
"""

from __future__ import print_function
import numpy as np
import tables as tb
import pandas as pd
import wfmFunctions as wfm
import HLObjects as hlo


def filters(name):
    """
    Returns the filter corresponding to a given key.
    """
    if name == "NOCOMPR":
        return tb.Filters(complevel=0)  # no compression
    if name == "ZLIB1":
        return tb.Filters(complevel=1, complib="zlib")
    if name == "ZLIB4":
        return tb.Filters(complevel=4, complib="zlib")
    if name == "ZLIB5":
        return tb.Filters(complevel=5, complib="zlib")
    if name == "ZLIB9":
        return tb.Filters(complevel=9, complib="zlib")
    if name == "BLOSC5":
        return tb.Filters(complevel=5, complib="blosc")
    if name == "BLZ4HC5":
        return tb.Filters(complevel=5, complib="blosc:lz4hc")
    raise ValueError("Compression option {} not found.".format(name))


def read_geom_table(geom_t):
    """
    Reads the geom table en returns a PD Series
    """
    ga = geom_t.read()
    G = pd.Series([ga[0][0][0], ga[0][0][1], ga[0][1][0], ga[0][1][1],
                   ga[0][2][0], ga[0][2][1], ga[0][3]],
                  index=["xdet_min", "xdet_max", "ydet_min", "ydet_max",
                         "zdet_min", "zdet_max", "R"])
    return G


def read_FEE_table(fee_t):
    """
    Reads the FEE table en returns a PD Series for the simulation parameters
    and a PD series for the values of the capacitors used in the simulation
    """

    fa = fee_t.read()

    F = pd.Series([fa[0][0], fa[0][1], fa[0][2], fa[0][3], fa[0][4],
                   fa[0][5], fa[0][6], fa[0][7], fa[0][8], fa[0][9],
                   fa[0][10], fa[0][11], fa[0][12],fa[0][13],fa[0][14],
                   fa[0][15],fa[0][16],fa[0][17]],
                  index=["OFFSET", "CEILING", "PMT_GAIN", "FEE_GAIN", "R1",
                         "C1","C2","Zin","DAQ_GAIN","NBITS","LSB",
                         "NOISE_I","NOISE_DAQ","t_sample","f_sample","f_mc",
                         "f_LPF1","f_LPF2"])
    FEE = {}
    FEE["fee_param"] = F
    #FEE["coeff_c"] = pd.Series([fa[0][18]], index=["coeff_c"])
    #FEE["coeff_blr"] = pd.Series([fa[0][19]], index=["coeff_blr"])
    #FEE["adc_to_pes"] = pd.Series([fa[0][20]], index=["adc_to_pes"])
    #FEE["pmt_noise_rms"] = pd.Series([fa[0][21]], index=["pmt_noise_rms"])
    FEE["coeff_c"] = np.array(fa[0][18], dtype=np.double)
    FEE["coeff_blr"] = np.array(fa[0][19], dtype=np.double)
    FEE["adc_to_pes"] = np.array(fa[0][20], dtype=np.double)
    FEE["pmt_noise_rms"] = np.array(fa[0][21], dtype=np.double)

    return FEE


def get_column_(pmta, ic):
    """
    Access column ic of table pmta and returns column as an array
    """
    col = []
    for i in range(pmta.shape[0]):
        col.append(pmta[i][ic])
    return np.array(col)


def read_sensors_table(sensor_table):
    """
    Reads the sensors table and returns a data frame
    """
    pmta = sensor_table.read()
    PMT = {}
    PMT["channel"] = get_column_(pmta, 0)
    PMT["sensorID"] = get_column_(pmta, 1)
    PMT["x"], PMT["y"], dummy = get_column_(pmta, 2).T
    PMT["coeff"] = get_column_(pmta, 3)
    PMT["adc_to_pes"] = get_column_(pmta, 4)
    PMT["noise_rms"] = get_column_(pmta, 5)
    return pd.DataFrame(PMT)


def get_vectors(h5f):
    """
        Return the most relevant fields stored in a raw data file.
    """
    pmttwf = h5f.root.TWF.PMT
    sipmtwf = h5f.root.TWF.SiPM
    pmtrwf = h5f.root.RD.pmtrwf
    pmtblr = h5f.root.RD.pmtblr
    sipmrwf = h5f.root.RD.sipmrwf
    # geom_t = h5f.root.Detector.DetectorGeometry
    # fee_t = h5f.root.MC.FEE
    # pmt_t = h5f.root.Sensors.DataPMT
    # sipm_t = h5f.root.Sensors.DataSiPM
    # gdf = read_geom_table(geom_t)
    # pmtdf = read_sensors_table(pmt_t)
    # sipmdf = read_sensors_table(sipm_t)
    # dFEE = read_FEE_table(fee_t)
    return pmttwf, sipmtwf, pmtrwf, pmtblr, sipmrwf


def get_pmt_vectors(h5f):
    """
        Return the most relevant fields stored in a raw data file.
    """
    pmttwf = h5f.root.TWF.PMT
    pmtrwf = h5f.root.RD.pmtrwf
    pmtblr = h5f.root.RD.pmtblr
    # geom_t = h5f.root.Detector.DetectorGeometry
    # fee_t = h5f.root.MC.FEE
    # pmt_t = h5f.root.Sensors.DataPMT
    # sipm_t = h5f.root.Sensors.DataSiPM
    # gdf = read_geom_table(geom_t)
    # pmtdf = read_sensors_table(pmt_t)
    # sipmdf = read_sensors_table(sipm_t)
    # dFEE = read_FEE_table(fee_t)
    return pmttwf, pmtrwf, pmtblr


def get_cwf_vectors(h5f):
    """
        Return the most relevant fields stored in a raw data file.
    """
    pmtcwf = h5f.root.RD.pmtcwf
    mau = h5f.root.BLR.mau
    pulse_on = h5f.root.BLR.pulse_on
    wait_over = h5f.root.BLR.wait_over

    return pmtcwf, mau, pulse_on, wait_over


def store_wf(event, table, WF):
    """
    Store a wavform in a table
    """
    row = table.row
    for isens, wf in WF.iteritems():
        for t, e in zip(wf.time_mus, wf.ene_pes):
            row["event"] = event
            row["ID"] = isens
            row["time_mus"] = t
            row["ene_pes"] = e
            row.append()
    table.flush()


def read_wf(table, evt, isens):
    """
        Reads table and returns the waveform (time_mus and ene_pes)
        corresponding to sensor isens of event event_number.
    """
    return (table.read_where("(event=={}) & (ID=={})".format(evt, isens),
                             field="time_mus"),
            table.read_where("(event=={}) & (ID=={})".format(evt, isens),
                             field="ene_pes"))


def read_wf_table(table, event_number):
    """
    Reads back the TWF of the PMTs/SiPMs for event number:
    input: the table and the event number
    outputs: a PMT/SiPM panel

    """
    sensor_list = set(table.read_where("event == {}".format(event_number),
                      field="ID"))
    return pd.Panel({isens: wfm.wf2df(*read_wf(table, event_number, isens))
                     for isens in sensor_list})


def store_pmap(pmap, table, evt):
    """
    Stores a pmap in a table.
    """
    row = table.row
    for i, peak in enumerate(pmap.peaks):
        for time, ToT, e, qs in peak:
            row["event"] = evt
            row["peak"] = i
            row["signal"] = peak.signal
            row["time"] = time
            row["ToT"] = ToT
            row["cathode"] = e
            row["anode"] = qs
            row.append()
    table.flush()


def read_pmap(table, evt):
    """
    Reads back the pmap stored in table.
    """
    pmap = hlo.PMap()
    peaks = set(table.read_where("event=={}".format(evt), field="peak"))
    for peak in peaks:
        coords = table.get_where_list("(event == {}) & "
                                      "(peak == {})".format(evt, peak))
        signal = table[coords[0]]["signal"]
        times = table.read_coordinates(coords, "time")
        ToT = table.read_coordinates(coords, "ToT")
        cathode = table.read_coordinates(coords, "cathode")
        anode = table.read_coordinates(coords, "anode")
        pmap.peaks.append(hlo.Peak(times, cathode, anode, ToT, signal))
    return pmap
