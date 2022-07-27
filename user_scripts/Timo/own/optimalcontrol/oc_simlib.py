import os
import copy as cp
import numpy as np
from scipy import interpolate

import qutip

# Version: 0.0.2
# Date:    2022-07-22
# Author:  P. J. Vetter / converted to lib: Timo Joas
# Email=  philipp.vetter@uni-ulm.de;

# Simulation to investigate the robustness of the optimal control pulse.
# Please note that all variables/ parameters must be in MHz!!!


class SimParameters():

    # zero-field splitting of NV in [MHz/G]
    D = 2870

    # gyromagnetic ratio of NV [MHz/G]
    gamma_nv = 2.8

    # gyromangetic ratio of 14N [MHz/G]
    gamma_14n = 3.077e-4

    # nuclear quadrupole moment [MHz] (https://journals.aps.org/prb/pdf/10.1103/PhysRevB.79.075203)
    Q = -5.01

    # NV-14N hyperfine couplings [MHz] (https://journals.aps.org/prb/pdf/10.1103/PhysRevB.79.075203)
    A_perpendicular = -2.7
    A_parallel = -2.14


    # NV- spin matrices
    S_x = qutip.jmat(0.5)[0]
    S_y = qutip.jmat(0.5)[1]
    S_z = - qutip.basis(2,1) * qutip.basis(2,1).dag()

    # N14 spin matrices
    I_x = qutip.jmat(1)[0]
    I_y = qutip.jmat(1)[1]
    I_z = qutip.jmat(1)[2]

    # Adjust the matrices to the given Hilbert space
    S_x = qutip.tensor(S_x,qutip.qeye(3))
    S_y = qutip.tensor(S_y,qutip.qeye(3))
    S_z = qutip.tensor(S_z,qutip.qeye(3))
    I_x = qutip.tensor(qutip.qeye(2),I_x)
    I_y = qutip.tensor(qutip.qeye(2),I_y)
    I_z = qutip.tensor(qutip.qeye(2),I_z)

    # Projectors (needed for the readout)
    P_nv = qutip.tensor(qutip.basis(2,0) * qutip.basis(2,0).dag(),qutip.qeye(3))

    # NV- ms0 starting state
    rho_ms0_nv = qutip.basis(2,0) * qutip.basis(2,0).dag()

    # NV- ms-1 starting state
    rho_msm1_nv = qutip.basis(2,1) * qutip.basis(2,1).dag()

    # NV- x starting state
    rho_x_nv = 1/2 * (qutip.basis(2,0) + qutip.basis(2,1)) * (qutip.basis(2,0) + qutip.basis(2,1)).dag()

    # NV- x starting state
    rho_y_nv = 1/2 * (qutip.basis(2,0) + 1.0j * qutip.basis(2,1)) * (qutip.basis(2,0) + 1.0j * qutip.basis(2,1)).dag()

    # 13C starting state
    rho_14n = qutip.maximally_mixed_dm(3)

    # Systems starting state
    rho_ms0 = qutip.tensor(rho_ms0_nv, rho_14n)
    rho_msm1 = qutip.tensor(rho_msm1_nv, rho_14n)
    rho_x = qutip.tensor(rho_x_nv, rho_14n)
    rho_y = qutip.tensor(rho_y_nv, rho_14n)


class ArbPulse():

    __allowed_si_units = ['s', 'V', 'Hz']
    __unit_prefix_dict = {
        'y': 1e-24,
        'z': 1e-21,
        'a': 1e-18,
        'f': 1e-15,
        'p': 1e-12,
        'n': 1e-9,
        'µ': 1e-6,
        'u': 1e-6,
        'm': 1e-3,
        '': 1,
        'k': 1e3,
        'M': 1e6,
        'G': 1e9,
        'T': 1e12,
        'P': 1e15,
        'E': 1e18,
        'Z': 1e21,
        'Y': 1e24
    }

    def __init__(self):
        self.name = None
        self._folder = None
        self._file = None
        self._file_ampl = None
        self._file_phase = None
        self.timegrid_unit = 'us'
        self.data_unit = 'MHz'

        self._data_ampl = None
        self._data_phase = None
        self._timegrid_ampl = None
        self._timegrid_phase = None

        self.length_pix = np.nan

        self._func_p_v_2_omega_mhz = None

    @property
    def file(self):
        if self._file and not self._file_ampl and not self._file_phase:
            return [self._file]
        elif not self._file and self._file_ampl:
            return [self._file_ampl, self._file_phase]
        elif not self._file and not self._file_ampl:
            return []
        else:
            raise RuntimeError("Should either have a single file or at least an ampl file.")

    def get_timegrid(self, unit=None):
        if unit is None:
            unit = self.timegrid_unit
        t_a, t_ph = self.convert_unit_time(unit)
        assert np.array_equal(t_a, t_ph)
        return t_a
    # @property, acts like decorator
    timegrid = property(get_timegrid)

    def get_data_ampl(self, unit=None):
        if unit is None:
            unit = self.data_unit
        return self.convert_unit_data(unit)[0]
    # @property, acts like decorator
    data_ampl = property(get_data_ampl)

    def get_data_phase(self, unit='Hz'):
        return self.convert_unit_data(unit)[1]
    data_phase = property(get_data_phase)

    def as_dict(self):
        out_dict = {'name': self.name,
                    'folder': self._folder,
                    'file': self.file}

        out_dict['timegrid_unit'] = self.timegrid_unit
        out_dict['data_unit'] = self.data_unit
        out_dict['data_ampl'] = self._data_ampl
        out_dict['data_phase'] = self._data_phase
        out_dict['timegrid_ampl'] = self._timegrid_ampl
        out_dict['timegrid_phase'] = self._timegrid_phase

        return out_dict

    def _split_unit_prefix(self, unit_str):

        full_str = cp.copy(unit_str)
        # Attentions: requires that entries of __allowed_si_units don't overlap with __unit_prefix_dict
        for si in self.__allowed_si_units:
            unit_str = unit_str.replace(si, '')

        prefix = unit_str
        unit_str = full_str.replace(unit_str, '')

        return prefix, unit_str

    def _get_unit_type_data(self, unit=None):
        if unit is None:
            unit = self.data_unit
        if 'Hz' in unit:
            return 'rabi_freq'
        elif 'V' in unit:
            return 'voltage'
        else:
            raise ValueError

    def _check_unit_sanity(self, unit):
        sane = True
        try:
            prefix, unit = self._split_unit_prefix(unit)
            if not(prefix in self.__unit_prefix_dict.keys() and unit in self.__allowed_si_units):
                sane = False
        except:
            sane = False
        return sane

    def convert_p_2_rabi(self, unit='Hz'):
        type_old = self._get_unit_type_data()
        type_new = self._get_unit_type_data(unit)
        prefix_old, unit_si_old = self._split_unit_prefix(self.data_unit)

        if type_old == 'voltage' and type_new == 'rabi_freq':
            if not self._func_p_v_2_omega_mhz:
                raise ValueError("No available scaling function for voltage->rabi conversion.")
                # to Rabi freq units
            data_ampl = self._func_p_v_2_omega_mhz(self._data_ampl)
            data_phase = self._func_p_v_2_omega_mhz(self._data_phase)

            scale_old = self.__unit_prefix_dict[prefix_old]
            inter_scale = 1e6*scale_old
            # guaranteed to be exactly once in dict
            inter_prefix = [k for k,v in self.__unit_prefix_dict.items() if v == inter_scale][0]
            data_unit = f'{inter_prefix}Hz'

            return data_ampl, data_phase, data_unit
        else:
            raise ValueError

    def convert_unit_data(self, unit='Hz'):
        prefix_old, unit_si_old = self._split_unit_prefix(self.data_unit)
        prefix_new, unit_si_new = self._split_unit_prefix(unit)
        type_old = self._get_unit_type_data()
        type_new = self._get_unit_type_data(unit)
        conv_factor = self.__unit_prefix_dict[prefix_old]/self.__unit_prefix_dict[prefix_new]

        if type_old == 'voltage' and type_new == 'rabi_freq':
            self._data_ampl, self._data_phase, self.data_unit = self.convert_p_2_rabi(unit=unit)
            return self.convert_unit_data(unit=unit)

        if type_old != type_new or unit_si_old != unit_si_new:
            raise ValueError(f"Can't automatically convert units {unit_si_old}->{unit_si_new} "
                             f"of type ({type_old}) to ({type_new})")

        return conv_factor*self._data_ampl, conv_factor*self._data_phase

    def convert_unit_time(self, unit='s'):
        prefix_old, unit_si_old = self._split_unit_prefix(self.timegrid_unit)
        prefix_new, unit_si_new = self._split_unit_prefix(unit)

        if unit_si_old != unit_si_new:
            raise ValueError(f"Can't automatically convert units {unit_si_old}->{unit_si_new}")
        conv_factor = self.__unit_prefix_dict[prefix_old]/self.__unit_prefix_dict[prefix_new]

        return conv_factor*self._timegrid_ampl, conv_factor*self._timegrid_phase

    def set_unit_data(self, unit='Hz'):
        self._data_ampl, self._data_phase = self.convert_unit_data(unit)
        self.data_unit = unit

    def set_unit_time(self, unit='s'):
        self._timegrid_ampl, self._timegrid_phase = self.convert_unit_time(unit)
        self.timegrid_unit = unit

    @staticmethod
    def get_pulse_filename(path, name="", name_ampl="amplitude.txt", name_phase="phase.txt"):
        return os.path.abspath(path + "/" + name + name_ampl), os.path.abspath(path + "/" + name + name_phase)

    @staticmethod
    def load_pulse(folder, name, extension='txt', unit_t='s', unit_data='V', func_p_v_2_omega_mhz=None):
        pulse = ArbPulse()
        pulse.load(folder, name, extension, unit_t, unit_data, func_p_v_2_omega_mhz)

        return pulse

    def load(self, folder, name, extension='txt', unit_t='s', unit_data='V', func_p_v_2_omega_mhz=None):
        self.name = name
        self._folder = folder
        self._func_p_v_2_omega_mhz = func_p_v_2_omega_mhz

        if extension=='txt':
            f_ampl, f_ph = ArbPulse.get_pulse_filename(os.path.abspath(folder), name=name)

            data_ampl = np.loadtxt(f_ampl)[:,1]
            t_ampl = np.loadtxt(f_ampl)[:,0]
            try:
                data_ph = np.loadtxt(f_ph)[:,1]
                t_ph = np.loadtxt(f_ph)[:,0]
            except OSError:
                t_ph = t_ampl
                data_ph = np.zeros((len(data_ampl)))

            self._file_ampl  = f_ampl
            self._file_phase = f_ph

        elif extension == 'npz':
            file = os.path.abspath(folder) + "/" + name + ".npz"
            data = np.load(file)
            t_ampl = data['time_grid1']
            data_ampl = data['pulse1']
            t_ph = data['time_grid2']
            data_ph = data['pulse2']

            self._file = file
        else:
            raise ValueError

        if not np.all(t_ph == t_ampl):
            raise ValueError("Timegrids differ for quadratures")

        self._timegrid_ampl = t_ampl
        self._timegrid_phase = t_ph
        self._data_ampl = data_ampl
        self._data_phase = data_ph

        if self._check_unit_sanity(unit_t) and self._check_unit_sanity(unit_data):
            # convert units
            self.timegrid_unit = unit_t
            self.data_unit = unit_data
        else:
            raise ValueError(f"Don't understand units (t/data): {unit_t}, {unit_data}")

class PredefinedArbPulses():

    @staticmethod
    def get_iq(phi):
        if phi==0 or phi==2*np.pi:
            return 1,0
        elif phi==np.pi/2:
            return 0,1
        elif phi==np.pi:
            return -1,0
        elif phi==3*np.pi/2:
            return 0,-1
        else:
            raise ValueError

    @staticmethod
    def get_t_pix(omega, pix=1):
        return 0.5*pix/omega

    @staticmethod
    def generate_levitt(omega, phase=0, n_t=1000):
        """
        Generate a levitt pulse as a optimal control pulse file.
        Assumes that quadratues I*sin(f_mw*t) + Q*cos(f_mw*t) are used in sampling.
        """
        omega_mhz = omega * 1e-6

        get_t_pix = PredefinedArbPulses.get_t_pix
        get_iq = PredefinedArbPulses.get_iq

        tpi_us = get_t_pix(omega_mhz, pix=1)

        # rabi in MHz, times in us
        timegrid_us = np.linspace(0, 2 * tpi_us, n_t)  # total pulse area 2pi
        data_ampl = np.zeros((len(timegrid_us)))  # I quadrature
        data_phase = np.zeros((len(timegrid_us)))  # Q

        phases = np.asarray([np.pi / 2, 0, np.pi / 2]) + phase
        tpulse_by_pi = [0.5, 1, 0.5]

        # phases = [np.pi/2]
        # tpulse_by_pi = [0.5]

        t_curr_us = 0
        for i_comppulse, phi in enumerate(phases):
            pix = tpulse_by_pi[i_comppulse]
            t_end_us = t_curr_us + get_t_pix(omega_mhz, pix=pix)
            idx_start = np.argmin(np.abs(timegrid_us - t_curr_us))
            idx_end = np.argmin(np.abs(timegrid_us - t_end_us))

            val_iq = np.asarray(get_iq(phi)) * omega_mhz
            data_ampl[idx_start:idx_end + 1] = val_iq[0]
            data_phase[idx_start:idx_end + 1] = val_iq[1]

            if t_curr_us == timegrid_us[-1]:
                break
            t_curr_us = t_end_us

        idx_end = np.argmin(np.abs(timegrid_us - t_end_us))

        assert idx_end == n_t - 1

        pulse = ArbPulse()
        pulse.name = f'levitt_phi={phase / np.pi:.1f}pi'
        pulse.timegrid_unit = 'µs'
        pulse.data_unit = 'MHz'

        pulse._data_ampl = data_ampl
        pulse._data_phase = data_phase
        pulse._timegrid_ampl = timegrid_us
        pulse._timegrid_phase = timegrid_us

        return pulse

    @staticmethod
    def generate_rect_pi(omega, phase=0, n_t=1000):
        """
        Generate a levitt pulse as a optimal control pulse file.
        Assumes that quadratues I*sin(f_mw*t) + Q*cos(f_mw*t) are used in sampling.
        """

        omega_mhz = omega * 1e-6

        get_t_pix = PredefinedArbPulses.get_t_pix
        get_iq = PredefinedArbPulses.get_iq

        tpi_us = get_t_pix(omega_mhz, pix=1)

        # rabi in MHz, times in us
        timegrid_us = np.linspace(0, tpi_us, n_t)
        data_ampl = np.zeros((len(timegrid_us)))  # I quadrature
        data_phase = np.zeros((len(timegrid_us)))  # Q

        phases = np.asarray([0]) + phase
        tpulse_by_pi = [1]

        # phases = [np.pi/2]
        # tpulse_by_pi = [0.5]

        t_curr_us = 0
        for i_comppulse, phi in enumerate(phases):
            pix = tpulse_by_pi[i_comppulse]
            t_end_us = t_curr_us + get_t_pix(omega_mhz, pix=pix)
            idx_start = np.argmin(np.abs(timegrid_us - t_curr_us))
            idx_end = np.argmin(np.abs(timegrid_us - t_end_us))

            val_iq = np.asarray(get_iq(phi)) * omega_mhz
            data_ampl[idx_start:idx_end + 1] = val_iq[0]
            data_phase[idx_start:idx_end + 1] = val_iq[1]

            if t_curr_us == timegrid_us[-1]:
                break
            t_curr_us = t_end_us

        idx_end = np.argmin(np.abs(timegrid_us - t_end_us))

        assert idx_end == n_t - 1

        pulse = ArbPulse()
        pulse.name = 'rect_phi={phase/np.pi:.1f}pi'

        pulse.timegrid_unit = 'µs'
        pulse.data_unit = 'MHz'

        pulse._data_ampl = data_ampl
        pulse._data_phase = data_phase
        pulse._timegrid_ampl = timegrid_us
        pulse._timegrid_phase = timegrid_us

        return pulse


class TimeDependentSimulation():

    @staticmethod
    def oc_element(t, pulse_timegrid, data_ampl, data_ph, frequency, B_gauss, amplitude_scaling, sim_params):
        # t: time step
        # filename_1: filename for the S_x pulse
        # filename_2: filename for the S_y pulse
        # frequency: carrier frequency of the pulse
        # amplitude scaling: amplitude prefactor which is multiplicated on the pulse
        simp = sim_params

        # Zero-field splitting
        B = B_gauss
        H_zfs = simp.D * simp.S_z ** 2

        # Zeeman interaction
        H_zeeman_nv = simp.gamma_nv * B * simp.S_z
        H_zeeman_14n = simp.gamma_14n * B * simp.I_z

        # Hyperfine interaction
        H_hyperfine = simp.A_parallel * simp.S_z * simp.I_z

        # load and extract the date
        amp_1 = data_ampl
        amp_2 = data_ph

        # make sure the time_array starts at 0
        timegrid = pulse_timegrid
        timegrid = timegrid - timegrid[0]

        # interpolate the given data such that it matches the time grid
        amp_func_1 = interpolate.interp1d(timegrid, amp_1)
        amp_func_2 = interpolate.interp1d(timegrid, amp_2)

        # amplitude (=1) for the time-independent part
        # this needs to be interpolated as well because ... I don't know why ... just didn't work otherwise
        amp_func_tidp = interpolate.interp1d(timegrid, np.ones(len(timegrid)),kind='linear')

        # time dependent coefficients of the Hamiltonian
        H_oc_coeff_1 = amp_func_1(t)
        H_oc_coeff_2 = amp_func_2(t)
        H_oc_tidp_coeff = amp_func_tidp(t)

        # corresponding Hamiltonian
        H_oc_1 = 2 * np.pi * amplitude_scaling * simp.S_x
        H_oc_2 = 2 * np.pi * amplitude_scaling * simp.S_y

        # time independent parts of the Hamiltonian
        H_oc_tidp = H_zfs + H_zeeman_nv - frequency * simp.S_z ** 2 + H_zeeman_14n + H_hyperfine
        H_oc_tidp = 2 * np.pi * H_oc_tidp

        # save all Hamiltonians with corresponding coefficents
        H_list = []
        H_list.append([H_oc_tidp,H_oc_tidp_coeff])
        H_list.append([H_oc_1,H_oc_coeff_1])
        H_list.append([H_oc_2,H_oc_coeff_2])

        return H_list


    def run_sim_fsweep(self, freq_array, pulse, B_gauss, sim_params, n_timebins=500, t_idle_extension=-1e-9):

        # for compability reason, accept pulse as dict or ArbPulse object
        # if supplying a dict, you are responsible for correct units!
        if type(pulse) == ArbPulse:
            pulse.set_unit_time('µs')
            pulse.set_unit_data('MHz')
            pulse = pulse.as_dict()

        B = B_gauss
        simp = sim_params
        oc_length = pulse['timegrid_ampl'][-1] + t_idle_extension*1e6

        t = np.linspace(0, oc_length, n_timebins)
        options=qutip.Options(atol=1e-15, rtol=1e-15, nsteps=1e8, store_final_state=True)

        init_state = simp.rho_ms0

        # perform the measurement
        data_freq_detuning = np.zeros(len(freq_array))
        for idx,freq in enumerate(freq_array):
            oc_el = TimeDependentSimulation.oc_element(t, pulse['timegrid_ampl'], pulse['data_ampl'], pulse['data_phase'], freq, B, 1, simp)
            results_measurement = qutip.mesolve(oc_el, init_state, t, [], [simp.P_nv], options=options, progress_bar=None)
            data_freq_detuning[idx] = results_measurement.expect[0][-1]

        return data_freq_detuning

    def run_sim_ampsweep(self, amp_array, pulse, B_gauss, sim_params, n_timebins=500, t_idle_extension=-1e-9):

        # for compability reason, accept pulse as dict or ArbPulse object
        # if supplying a dict, you are responsible for correct units!
        if type(pulse) == ArbPulse:
            pulse.set_unit_time('µs')
            pulse.set_unit_data('MHz')
            pulse = pulse.as_dict()

        B = B_gauss
        simp = sim_params
        oc_length = pulse['timegrid_ampl'][-1] + t_idle_extension*1e6

        t = np.linspace(0, oc_length, n_timebins)
        options=qutip.Options(atol=1e-15, rtol=1e-15, nsteps=1e8, store_final_state=True)

        init_state = simp.rho_ms0
        freq = simp.D - simp.gamma_nv * B
        # perform the measurement
        data_amp_detuning = np.zeros(len(amp_array))
        for idx,amp in enumerate(amp_array):
            oc_el = TimeDependentSimulation.oc_element(t, pulse['timegrid_ampl'], pulse['data_ampl'], pulse['data_phase'], freq, B, 1+amp, simp)
            results_measurement = qutip.mesolve(oc_el, init_state, t, [], [simp.P_nv], options=options, progress_bar=None)
            data_amp_detuning[idx] = results_measurement.expect[0][-1]

        return data_amp_detuning