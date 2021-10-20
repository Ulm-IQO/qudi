import numpy as np
import random
from logic.pulsed.pulse_objects import PulseBlock, PulseBlockEnsemble
from logic.pulsed.pulse_objects import PredefinedGeneratorBase



class SensingPredefinedGeneratorS3(PredefinedGeneratorBase):
    """

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)




    def generate_cpmg_tau(self, name='CPMG', rabi_period=100e-9, tau_start=1.0e-9, tau_step =1.0e-9, num_of_points=50,
                          microwave_amplitude=1.0, microwave_frequency=2.8e9, cpmg_order = 8, alternating = True):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        tau_start = self._adjust_to_samplingrate(tau_start, 2)
        tau_step = self._adjust_to_samplingrate(tau_step, 2)
        rabi_period = self._adjust_to_samplingrate(rabi_period, 4)
        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step

        # get readout element
        readout_element = self._get_readout_element()

        # get pihalf element
        pihalf_element = self._get_mw_element(length=rabi_period / 4,
                                                      increment=0.0,
                                                      amp=microwave_amplitude,
                                                      freq=microwave_frequency,
                                                      phase=0.0)
        if alternating:
            pi3half_element = self._get_mw_element(length=rabi_period / 4,
                                                   increment=0.0,
                                                   amp=microwave_amplitude,
                                                   freq=microwave_frequency,
                                                   phase=180.0)
        # get pi elements
        piy_element = self._get_mw_element(length=rabi_period / 2,
                                           increment=0.0,
                                           amp=microwave_amplitude,
                                           freq=microwave_frequency,
                                           phase=90.0)
        # get tauhalf element
        tauhalf_element = self._get_idle_element(length=tau_start/2.0 - rabi_period/4, increment = tau_step / 2)
        # get tau element
        tau_element = self._get_idle_element(length=tau_start - rabi_period/2,increment = tau_step)

        block = PulseBlock(name=name)
        # actual CPMG-N sequence
        block.append(pihalf_element)
        block.append(tauhalf_element)

        for n in range(cpmg_order):
            block.append(piy_element)
            if n != cpmg_order-1:
                block.append(tau_element)
        block.append(tauhalf_element)
        block.append(pihalf_element)
        block.extend(readout_element)

        if alternating:
            block.append(pihalf_element)
            block.append(tauhalf_element)
            for n in range(cpmg_order):
                block.append(piy_element)
                if n !=cpmg_order - 1:
                    block.append(tau_element)
            block.append(tauhalf_element)
            block.append(pi3half_element)
            block.extend(readout_element)

        created_blocks.append(block)
        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((block.name, num_of_points- 1))

        # Create and append sync trigger block if needed
        created_blocks, block_ensemble = self._add_trigger(created_blocks, block_ensemble)
        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks,
                                                        alternating=alternating,
                                                        controlled_variable=tau_array)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_kdd_tau(self, name='KDD', rabi_period=100e-9, tau_start=1.0e-9, tau_step=1.0e-9, num_of_points=50,
                          microwave_amplitude=0.25, microwave_frequency=2.8e9, kdd_order=8, alternating=True):
        """
        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        rabi_period = self._adjust_to_samplingrate(rabi_period, 4)
        start_tau = self._adjust_to_samplingrate(tau_start, 2)
        tau_incr = self._adjust_to_samplingrate(tau_step, 2)
        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step

        # get readout element
        readout_element = self._get_readout_element()

        # get pihalf element
        pihalf_element = self._get_mw_element(length=rabi_period / 4,
                                              increment=0.0,
                                              amp=microwave_amplitude,
                                              freq=microwave_frequency,
                                              phase=0.0)
        if alternating:
            pi3half_element = self._get_mw_element(length=rabi_period / 4,
                                                   increment=0.0,
                                                   amp=microwave_amplitude,
                                                   freq=microwave_frequency,
                                                   phase=180.0)

        # get tauhalf element
        tauhalf_element = self._get_idle_element(length=start_tau / 2.0 - rabi_period / 4, increment=tau_incr / 2)
        # get tau element
        tau_element = self._get_idle_element(length=start_tau - rabi_period / 2, increment=tau_incr)

        # get pi elements
        pix_element = self._get_mw_element(length=rabi_period / 2,
                                           increment=0.0,
                                           amp=microwave_amplitude,
                                           freq=microwave_frequency,
                                           phase=0.0)
        pi30_element = self._get_mw_element(length=rabi_period / 2,
                                           increment=0.0,
                                           amp=microwave_amplitude,
                                           freq=microwave_frequency,
                                           phase=30.0)
        pi60_element = self._get_mw_element(length=rabi_period / 2,
                                           increment=0.0,
                                           amp=microwave_amplitude,
                                           freq=microwave_frequency,
                                           phase=60.0)
        piy_element = self._get_mw_element(length=rabi_period / 2,
                                           increment=0.0,
                                           amp=microwave_amplitude,
                                           freq=microwave_frequency,
                                           phase=90.0)
        pi120_element = self._get_mw_element(length=rabi_period / 2,
                                           increment=0.0,
                                           amp=microwave_amplitude,
                                           freq=microwave_frequency,
                                           phase=120.0)
        pi180_element = self._get_mw_element(length=rabi_period / 2,
                                           increment=0.0,
                                           amp=microwave_amplitude,
                                           freq=microwave_frequency,
                                           phase=180.0)

        block = PulseBlock(name=name)
        # actual KDD-N sequence
        block.append(pihalf_element)
        block.append(tauhalf_element)
        for nn in range(kdd_order):
            if nn==0:
                block.append(pi60_element)
            else:
                block.append(pi30_element)
            block.append(tau_element)
            block.append(pix_element)
            block.append(tau_element)
            block.append(piy_element)
            block.append(tau_element)
            block.append(pix_element)
            block.append(tau_element)
            block.append(pi30_element)
            block.append(tau_element)
            block.append(pi120_element)
            block.append(tau_element)
            block.append(piy_element)
            block.append(tau_element)
            block.append(pi180_element)
            block.append(tau_element)
            block.append(piy_element)
            block.append(tau_element)
            block.append(pi120_element)
            if nn != kdd_order-1:
                block.append(tau_element)
        block.append(tauhalf_element)
        block.append(pihalf_element)
        block.extend(readout_element)

        if alternating:
            block.append(pihalf_element)
            block.append(tauhalf_element)
            for nn in range(kdd_order):
                block.append(pi30_element)
                block.append(tau_element)
                block.append(pix_element)
                block.append(tau_element)
                block.append(piy_element)
                block.append(tau_element)
                block.append(pix_element)
                block.append(tau_element)
                block.append(pi30_element)
                block.append(tau_element)
                block.append(pi120_element)
                block.append(tau_element)
                block.append(piy_element)
                block.append(tau_element)
                block.append(pi180_element)
                block.append(tau_element)
                block.append(piy_element)
                block.append(tau_element)
                block.append(pi120_element)
                if nn != kdd_order - 1:
                    block.append(tau_element)
            block.append(tauhalf_element)
            block.append(pi3half_element)
            block.extend(readout_element)

        created_blocks.append(block)
        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((block.name, num_of_points - 1))

        # Create and append sync trigger block if needed
        created_blocks, block_ensemble = self._add_trigger(created_blocks, block_ensemble)
        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks,
                                                        alternating=alternating,
                                                        controlled_variable=tau_array)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences


    def generate_cpmg_nsweep(self, name='CPMG-Nsweep', rabi_period=100e-9, tau=1.0e-6, n_start = 1, n_step = 1,
                             num_of_points=50, microwave_amplitude=1.0, microwave_frequency=2.8e9, alternating = True):
        """

        """
        # Sanity checks
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get pulse number array for measurement ticks
        n_array = n_start + np.arange(num_of_points) * n_step
        n_array.astype(int)
        # change parameters in a way that they fit to the current sampling rate
        rabi_period = self._adjust_to_samplingrate(rabi_period, 4)
        tau = self._adjust_to_samplingrate(tau, 2)

        # get readout element
        readout_element = self._get_readout_element()

        # get pihalf element
        pihalf_element = self._get_mw_element(length=rabi_period / 4,
                                              increment=0.0,
                                              amp=microwave_amplitude,
                                              freq=microwave_frequency,
                                              phase=0.0)
        if alternating:
            pi3half_element = self._get_mw_element(length=rabi_period / 4,
                                                   increment=0.0,
                                                   amp=microwave_amplitude,
                                                   freq=microwave_frequency,
                                                   phase=180.0)

        # get tauhalf element
        tauhalf_element = self._get_idle_element(length=tau / 2.0 - rabi_period / 4, increment=0)


        # get pi elements
        piy_element = self._get_mw_element(length=rabi_period / 2,
                                           increment=0.0,
                                           amp=microwave_amplitude,
                                           freq=microwave_frequency,
                                           phase=90.0)


        # create CPMG-N block element list
        block = PulseBlock(name=name)
        for ii in range(num_of_points):
            block.append(pihalf_element)
            for nn in range(n_array[ii]):
                block.append(tauhalf_element)
                block.append(piy_element)
                block.append(tauhalf_element)
            block.append(pihalf_element)
            block.extend(readout_element)
            if alternating:
                block.append(pihalf_element)
                block.append(tauhalf_element)
                for nn in range(n_array[ii]):
                    block.append(tauhalf_element)
                    block.append(piy_element)
                    block.append(tauhalf_element)
                block.append(pi3half_element)
                block.extend(readout_element)

        created_blocks.append(block)
        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((block.name, 0))

        # Create and append sync trigger block if needed
        created_blocks, block_ensemble = self._add_trigger(created_blocks, block_ensemble)
        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks,
                                                        alternating=alternating,
                                                        controlled_variable=n_array * tau)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences



    def generate_xy8_nsweep(self, name='XY8-Nsweep', rabi_period=100e-9, tau=1.0e-6, xy8_start = 1, xy8_step = 1,
                             num_of_points=50, microwave_amplitude=0.25, microwave_frequency=2.8e9, alternating = True):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get pulse number array for measurement ticks
        xy8_array = xy8_start + np.arange(num_of_points) * xy8_step
        xy8_array.astype(int)
        # change parameters in a way that they fit to the current sampling rate
        rabi_period = self._adjust_to_samplingrate(rabi_period, 4)
        tau = self._adjust_to_samplingrate(tau, 2)
        real_tau = max(0, tau - self.rabi_period / 2)

        # get readout element
        readout_element = self._get_readout_element()

        # get pihalf element
        pihalf_element = self._get_mw_element(length=rabi_period / 4,
                                              increment=0.0,
                                              amp=microwave_amplitude,
                                              freq=microwave_frequency,
                                              phase=0.0)

        # Use a 180 deg phase shiftet pulse as 3pihalf pulse if microwave channel is analog
        if self.microwave_channel.startswith('a'):
            pi3half_element = self._get_mw_element(length=self.rabi_period / 4,
                                                   increment=0,
                                                   amp=self.microwave_amplitude,
                                                   freq=self.microwave_frequency,
                                                   phase=180)
        else:
            pi3half_element = self._get_mw_element(length=3 * self.rabi_period / 4,
                                                   increment=0,
                                                   amp=self.microwave_amplitude,
                                                   freq=self.microwave_frequency,
                                                   phase=0)
        # get pi elements
        pix_element = self._get_mw_element(length=rabi_period / 2,
                                           increment=0.0,
                                           amp=microwave_amplitude,
                                           freq=microwave_frequency,
                                           phase=0.0)

        piy_element = self._get_mw_element(length=rabi_period / 2,
                                           increment=0.0,
                                           amp=microwave_amplitude,
                                           freq=microwave_frequency,
                                           phase=90.0)

        # get tau elements
        tau_element = self._get_idle_element(length=real_tau, increment=0)
        tauhalf_element = self._get_idle_element(length=real_tau / 2, increment=0)
        #self.log.warning(locals())



        # create XY8-N block element list
        xy8_block = PulseBlock(name=name)
        for ii in range(num_of_points):
            xy8_block.append(pihalf_element)
            xy8_block.append(tauhalf_element)
            xy8_order = xy8_array[ii]
            for n in range(xy8_order):
                xy8_block.append(pix_element)
                xy8_block.append(tau_element)
                xy8_block.append(piy_element)
                xy8_block.append(tau_element)
                xy8_block.append(pix_element)
                xy8_block.append(tau_element)
                xy8_block.append(piy_element)
                xy8_block.append(tau_element)
                xy8_block.append(piy_element)
                xy8_block.append(tau_element)
                xy8_block.append(pix_element)
                xy8_block.append(tau_element)
                xy8_block.append(piy_element)
                xy8_block.append(tau_element)
                xy8_block.append(pix_element)
                if n != xy8_order - 1:
                    xy8_block.append(tau_element)
            xy8_block.append(tauhalf_element)
            xy8_block.append(pihalf_element)
            xy8_block.extend(readout_element)
            if alternating:
                xy8_block.append(pihalf_element)
                xy8_block.append(tauhalf_element)
                for n in range(xy8_order):
                    xy8_block.append(pix_element)
                    xy8_block.append(tau_element)
                    xy8_block.append(piy_element)
                    xy8_block.append(tau_element)
                    xy8_block.append(pix_element)
                    xy8_block.append(tau_element)
                    xy8_block.append(piy_element)
                    xy8_block.append(tau_element)
                    xy8_block.append(piy_element)
                    xy8_block.append(tau_element)
                    xy8_block.append(pix_element)
                    xy8_block.append(tau_element)
                    xy8_block.append(piy_element)
                    xy8_block.append(tau_element)
                    xy8_block.append(pix_element)
                    if n != xy8_order - 1:
                        xy8_block.append(tau_element)
                xy8_block.append(tauhalf_element)
                xy8_block.append(pi3half_element)
                xy8_block.extend(readout_element)

        created_blocks.append(xy8_block)
        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((xy8_block.name, 0))

        # Create and append sync trigger block if needed
        created_blocks, block_ensemble = self._add_trigger(created_blocks, block_ensemble)
        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks,
                                                        alternating=alternating,
                                                        controlled_variable= 8 * xy8_array * tau)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)

        return created_blocks, created_ensembles, created_sequences




    def generate_xy8_random_phase(self, name='CPMG', rabi_period=100e-9, tau_start=1.0e-9, tau_step =1.0e-9, num_of_points=50,
                          microwave_amplitude=1.0, microwave_frequency=2.8e9, xy8_order = 8, randomize=True, alternating = True):

        """
        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # change parameters in a way that they fit to the current sampling rate
        rabi_period = self._adjust_to_samplingrate(rabi_period, 4)
        start_tau = self._adjust_to_samplingrate(tau_start, 2)
        tau_incr = self._adjust_to_samplingrate(tau_step, 2)

        # get tau array for measurement ticks
        tau_array = start_tau + np.arange(num_of_points) * tau_step

        # get readout element
        readout_element = self._get_readout_element()

        # get pihalf element
        pihalf_element = self._get_mw_element(length=rabi_period / 4,
                                              increment=0.0,
                                              amp=microwave_amplitude,
                                              freq=microwave_frequency,
                                              phase=0.0)
        if alternating:
            pi3half_element = self._get_mw_element(length=rabi_period / 4,
                                                   increment=0.0,
                                                   amp=microwave_amplitude,
                                                   freq=microwave_frequency,
                                                   phase=180.0)

        # get tauhalf element
        tauhalf_element = self._get_idle_element(length=start_tau / 2.0 - rabi_period / 4, increment = tau_incr/2)
        # get tau element
        tau_element = self._get_idle_element(length=start_tau - rabi_period / 2, increment = tau_incr)



        # create XY8-N block element list
        block = PulseBlock(name=name)
        # actual XY8-N sequence
        block.append(pihalf_element)
        for nn in range(xy8_order):
            # get pi elements
            if randomize:
                random_phase = random.uniform(0, 360)
            else:
                random_phase = 0
            # get pi elements
            pix_element = self._get_mw_element(length=rabi_period / 2,
                                               increment=0.0,
                                               amp=microwave_amplitude,
                                               freq=microwave_frequency,
                                               phase=random_phase)
            # get pi elements
            piy_element = self._get_mw_element(length=rabi_period / 2,
                                               increment=0.0,
                                               amp=microwave_amplitude,
                                               freq=microwave_frequency,
                                               phase=90.0+random_phase)
            block.append(tauhalf_element)
            block.append(pix_element)
            block.append(tau_element)
            block.append(piy_element)
            block.append(tau_element)
            block.append(pix_element)
            block.append(tau_element)
            block.append(piy_element)
            block.append(tau_element)
            block.append(piy_element)
            block.append(tau_element)
            block.append(pix_element)
            block.append(tau_element)
            block.append(piy_element)
            block.append(tau_element)
            block.append(pix_element)
            block.append(tauhalf_element)
        block.extend(readout_element)

        if alternating:
            block.append(pihalf_element)
            block.append(tauhalf_element)
            for nn in range(xy8_order):
                if randomize:
                    random_phase = random.uniform(0, 360)
                else:
                    random_phase = 0
                # get pi elements
                pix_element = self._get_mw_element(length=rabi_period / 2,
                                                   increment=0.0,
                                                   amp=microwave_amplitude,
                                                   freq=microwave_frequency,
                                                   phase=random_phase)
                # get pi elements
                piy_element = self._get_mw_element(length=rabi_period / 2,
                                                   increment=0.0,
                                                   amp=microwave_amplitude,
                                                   freq=microwave_frequency,
                                                   phase=90.0 + random_phase)
                block.append(tauhalf_element)
                block.append(pix_element)
                block.append(tau_element)
                block.append(piy_element)
                block.append(tau_element)
                block.append(pix_element)
                block.append(tau_element)
                block.append(piy_element)
                block.append(tau_element)
                block.append(piy_element)
                block.append(tau_element)
                block.append(pix_element)
                block.append(tau_element)
                block.append(piy_element)
                block.append(tau_element)
                block.append(pix_element)
                block.append(tauhalf_element)
            block.append(pi3half_element)
            block.extend(readout_element)

        created_blocks.append(block)
        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((block.name, 0))

        # Create and append sync trigger block if needed
        created_blocks, block_ensemble = self._add_trigger(created_blocks, block_ensemble)
        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks,
                                                        alternating=alternating,
                                                        controlled_variable=tau_array)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences









