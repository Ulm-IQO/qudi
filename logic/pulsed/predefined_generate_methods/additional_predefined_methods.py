import numpy as np
from logic.pulsed.pulse_objects import PulseBlock, PulseBlockEnsemble, PulseSequence
from logic.pulsed.pulse_objects import PredefinedGeneratorBase
from logic.pulsed.sampling_functions import SamplingFunctions
from core.util.helpers import csv_2_list


class MyPredefinedGeneratorBase(PredefinedGeneratorBase):
    """ Description goes here """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def generate_T1_AOM(self, name='T1AOM', tau_start=1.0e-6, tau_step=1.0e-6, num_of_points=50):

        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step

        trigger_element = self._get_sync_element()

        laser_element = self._get_laser_element(length=self.laser_length,
                                                increment=0)

        tau_element = self._get_idle_element(length=tau_start,
                                             increment=tau_step)

        waiting_element = self._get_idle_element(length=self.wait_time,
                                                 increment=0)

        sync_block = PulseBlock(name='{0}_sync'.format(name))
        sync_block.append(trigger_element)
        created_blocks.append(sync_block)

        t1_block = PulseBlock(name=name)
        t1_block.append(laser_element)
        t1_block.append(tau_element)
        created_blocks.append(t1_block)

        wait_block = PulseBlock(name='wait')
        wait_block.append(waiting_element)
        created_blocks.append(wait_block)

        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((sync_block.name, 0))

        block_ensemble.append((t1_block.name, num_of_points-1))
        block_ensemble.append((wait_block.name, 0))

        number_of_lasers = num_of_points
        block_ensemble.measurement_information['alternating'] = False
        block_ensemble.measurement_information['laser_ignore_list'] = [0]
        block_ensemble.measurement_information['controlled_variable'] = tau_array[:-1]
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('Tau', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_T1_AOM_green(self, name='t1AOMgreen', tau_start=1.0e-6, tau_step=1.0e-6, num_of_points=50, green_initialization=False, length_green=1.0e-6, green_channel='d_ch3'):
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step

        trigger_element = self._get_sync_element()

        laser_element = self._get_laser_element(length=self.laser_length,
                                                increment=0)

        tau_element = self._get_idle_element(length=tau_start,
                                             increment=tau_step)

        waiting_element = self._get_idle_element(length=self.wait_time,
                                                 increment=0)

        sync_block = PulseBlock(name='{0}_sync'.format(name))
        sync_block.append(trigger_element)
        created_blocks.append(sync_block)

        if green_initialization:
            green_element = self._get_trigger_element(length=length_green, channels=green_channel, increment=0)
            green_wait_element = self._get_idle_element(length=500e-9, increment=0)
            green_block = PulseBlock(name='green_init')
            green_block.append(green_element)
            green_block.append(green_wait_element)
            created_blocks.append(green_block)

        t1_block = PulseBlock(name=name)
        t1_block.append(laser_element)
        t1_block.append(tau_element)
        created_blocks.append(t1_block)

        wait_block = PulseBlock(name='wait_{0}'.format(self.wait_time * 10e6))
        wait_block.append(waiting_element)
        created_blocks.append(wait_block)

        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((sync_block.name, 0))

        if green_initialization:
            block_ensemble.append((green_block.name, 0))
        block_ensemble.append((t1_block.name, num_of_points - 1))
        block_ensemble.append((wait_block.name, 0))

        number_of_lasers = num_of_points + 1 if green_initialization else num_of_points
        block_ensemble.measurement_information['alternating'] = False
        block_ensemble.measurement_information['laser_ignore_list'] = [0, 1] if green_initialization else [0]
        block_ensemble.measurement_information['controlled_variable'] = tau_array[:-1]
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('Tau', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_lifetime_with_awg(self, name='lifetimeWithAwg', recording_window=100e-9):  # , record_from_start=True):
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # create the elements
        # trigger_fc = self._get_trigger_element(length=self.laser_length,
        #                                        channels='d_ch2',
        #                                        increment=0)

        fastcounter_trigger_and_or_laser_element = self._get_trigger_element(length=self.laser_length,
                                                                             channels=['d_ch1', 'd_ch2'],
                                                                             increment=0)

        recording_window_element = self._get_idle_element(length=recording_window, increment=0)

        lifetime_block = PulseBlock(name=name)

        lifetime_block.append(fastcounter_trigger_and_or_laser_element)
        lifetime_block.append(recording_window_element)

        created_blocks.append(lifetime_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((lifetime_block.name, 0))

        # add metadata to invoke settings later on
        number_of_lasers = 1
        block_ensemble.measurement_information['alternating'] = False
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = [1, 2]
        block_ensemble.measurement_information['units'] = ('a.u.', '')
        block_ensemble.measurement_information['labels'] = ('', '')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_t1_like(self, name='T1liketest', tau_start=1.0e-6, tau_step=1.0e-6, num_of_points=50):
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # create the elements
        # trigger_fc = self._get_trigger_element(length=self.laser_length,
        #                                        channels='d_ch2',
        #                                        increment=0)

        fastcounter_trigger_and_or_laser_element = self._get_trigger_element(length=self.laser_length,
                                                                             channels=['d_ch1', 'd_ch2'],
                                                                             increment=0)

        laser_element = self._get_trigger_element(length=self.laser_length, channels='d_ch1', increment=0)

        tau_array = tau_start + np.arange(num_of_points) * tau_step

        delay_element = self._get_delay_element()

        t1_like_block = PulseBlock(name=name)

        t1_like_block.append(fastcounter_trigger_and_or_laser_element)
        for tau in tau_array:
            tau_element = self._get_idle_element(length=tau, increment=0.0)
            t1_like_block.append(tau_element)
            t1_like_block.append(laser_element)

        t1_like_block.append(delay_element)

        created_blocks.append(t1_like_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((t1_like_block.name, 0))

        number_of_lasers = num_of_points
        block_ensemble.measurement_information['alternating'] = False
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('Tau', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_drift_test_method(self, name='DriftTest', pause_between=20e-9, number_of_lasers=2):
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # create the elements
        # trigger_fc = self._get_trigger_element(length=self.laser_length,
        #                                        channels='d_ch2',
        #                                        increment=0)

        fastcounter_trigger_and_or_laser_element = self._get_trigger_element(length=self.laser_length,
                                                                             channels=['d_ch1', 'd_ch2'],
                                                                             increment=0)

        laser_element = self._get_trigger_element(length=self.laser_length, channels='d_ch1', increment=0)

        pause_element = self._get_idle_element(length=pause_between, increment=0.0)

        delay_element = self._get_delay_element()

        dc_drift_test_block = PulseBlock(name=name)

        dc_drift_test_block.append(fastcounter_trigger_and_or_laser_element)

        for num in np.arange(number_of_lasers-1):
            dc_drift_test_block.append(pause_element)
            dc_drift_test_block.append(laser_element)

        dc_drift_test_block.append(delay_element)

        created_blocks.append(dc_drift_test_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((dc_drift_test_block.name, 0))

        number_of_lasers = number_of_lasers
        block_ensemble.measurement_information['alternating'] = False
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = range(number_of_lasers)
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('Tau', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_t1_like_laser_analog(self, name='T1liketestLaserAnalog', tau_start=1.0e-6, tau_step=1.0e-6, num_of_points=50):
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # create the elements
        # trigger_fc = self._get_trigger_element(length=self.laser_length,
        #                                        channels='d_ch2',
        #                                        increment=0)

        fastcounter_trigger_and_or_laser_element = self._get_trigger_element(length=self.laser_length,
                                                                             channels=['a_ch1', 'd_ch2'],
                                                                             increment=0)

        laser_element = self._get_trigger_element(length=self.laser_length, channels='a_ch1', increment=0)

        tau_array = tau_start + np.arange(num_of_points) * tau_step

        delay_element = self._get_delay_element()

        t1_like_block = PulseBlock(name=name)

        t1_like_block.append(fastcounter_trigger_and_or_laser_element)
        for tau in tau_array:
            tau_element = self._get_idle_element(length=tau, increment=0.0)
            t1_like_block.append(tau_element)
            t1_like_block.append(laser_element)

        t1_like_block.append(delay_element)

        created_blocks.append(t1_like_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((t1_like_block.name, 0))

        number_of_lasers = num_of_points
        block_ensemble.measurement_information['alternating'] = False
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('Tau', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences
