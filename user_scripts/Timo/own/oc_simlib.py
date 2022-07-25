import os
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

class TimeDependentSimulation():

    @staticmethod
    def get_pulse_filename(path, name="", name_ampl="amplitude.txt", name_phase="phase.txt"):
        return os.path.abspath(path + "/" + name + name_ampl), os.path.abspath(path + "/" + name + name_phase)

    @staticmethod
    def load_pulse(folder, name, extension='txt', func_volt_2_rabi=None, func_t_2_us=None):
        # expect experimental data in units ampl (V), time (s)
        # convert to Rabi drive in (MHz), (us)

        out_dict = {'name': name,
                    'folder': folder}

        if func_volt_2_rabi is None:
            func_volt_2_rabi = lambda x: x
        if func_t_2_us is None:
            func_t_2_us = lambda t:t

        if extension=='txt':
            f_ampl, f_ph = TimeDependentSimulation.get_pulse_filename(os.path.abspath(folder), name=name)

            data_ampl = np.loadtxt(f_ampl)[:,1]
            t_ampl = np.loadtxt(f_ampl)[:,0]
            data_ph = np.loadtxt(f_ph)[:,1]
            t_ph = np.loadtxt(f_ph)[:,0]

            out_dict.update({'file_ampl': f_ampl,
                             'file_phase': f_ph})
        elif extension =='npz':
            file = os.path.abspath(folder) + "/" + name + ".npz"
            data = np.load(file)
            t_ampl = data['time_grid1']
            data_ampl = data['pulse1']
            t_ph = data['time_grid2']
            data_ph = data['pulse2']

            out_dict.update({'file':file})

        else:
            raise ValueError

        if not np.all(t_ph == t_ampl):
            raise ValueError("Timegrids differ for quadratures")

        out_dict.update({
            'timegrid_ampl': t_ampl,
            'data_ampl': data_ampl,
            'timegrid_phase': t_ph,
            'data_phase': data_ph})

        # convert units
        out_dict['timegrid_unit'] = 'us'
        out_dict['data_unit'] = 'MHz'
        out_dict['data_ampl'] = func_volt_2_rabi(out_dict['data_ampl'])
        out_dict['data_phase'] = func_volt_2_rabi(out_dict['data_phase'])
        out_dict['timegrid_ampl'] = func_t_2_us(out_dict['timegrid_ampl'])
        out_dict['timegrid_phase'] = func_t_2_us(out_dict['timegrid_phase'])

        return out_dict

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
        B = B_gauss
        simp = sim_params
        oc_length = pulse['timegrid_ampl'][-1] + t_idle_extension*1e6

        t = np.linspace(0, oc_length, n_timebins)
        options=qutip.Options(atol=1e-15, rtol=1e-15, nsteps=1e8, store_final_state=True)

        freq_init_state = simp.rho_ms0

        # perform the measurement
        data_freq_detuning = np.zeros(len(freq_array))
        for idx,freq in enumerate(freq_array):
            oc_el = TimeDependentSimulation.oc_element(t, pulse['timegrid_ampl'], pulse['data_ampl'], pulse['data_phase'], freq, B, 1, simp)
            results_measurement = qutip.mesolve(oc_el, freq_init_state, t, [], [simp.P_nv], options=options, progress_bar=None)
            data_freq_detuning[idx] = results_measurement.expect[0][-1]

        return data_freq_detuning