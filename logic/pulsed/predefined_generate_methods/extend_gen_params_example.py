

from logic.pulsed.pulse_objects import PulseBlock, PulseBlockEnsemble
from logic.pulsed.pulse_objects import PredefinedGeneratorBase


class ExampleGenerator(PredefinedGeneratorBase):
    """

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._init_custom_generation_params()

    def _init_custom_generation_params(self):
        self.optimal_control_assets_path = 'C:\Software\qudi_data\optimal_control_assets'
        self.laser_2_length = 2.5e-6

    # extend generation parameters. These will be shown also in Gui.
    @property
    def optimal_control_assets_path(self):
        try:
            gen_params = self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters
            return gen_params['optimal_control_assets_path']
        except KeyError:
            return None

    @optimal_control_assets_path.setter
    def optimal_control_assets_path(self, path):
        gen_params = self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters
        gen_params.update({'optimal_control_assets_path': path})
        self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters = gen_params

    @property
    def laser_2_length(self):
        try:
            gen_params = self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters
            return gen_params['laser_2_length']
        except KeyError:
            return None

    @laser_2_length.setter
    def laser_2_length(self, laser_length):
        gen_params = self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters
        gen_params.update({'laser_2_length': laser_length})
        self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters = gen_params

    @property
    def pulse_envelope(self):
        try:
            gen_params = self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters
            return gen_params['pulse_envelope']
        except KeyError:
            return None

    @pulse_envelope.setter
    def pulse_envelope(self, envelope):
        gen_params = self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters
        gen_params.update({'pulse_envelope': envelope})
        self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters = gen_params

    # evil setters for common generation settings, use with care.
    # Typically, restore after changing in generation method.
    @PredefinedGeneratorBase.rabi_period.setter
    def rabi_period(self, t_rabi):

        gen_params = self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters
        gen_params.update({'rabi_period': t_rabi})
        self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters = gen_params

    @PredefinedGeneratorBase.microwave_amplitude.setter
    def microwave_amplitude(self, ampl):
        gen_params = self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters
        gen_params.update({'microwave_amplitude': ampl})
        self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters = gen_params

    @PredefinedGeneratorBase.microwave_frequency.setter
    def microwave_frequency(self, freq):
        gen_params = self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters
        gen_params.update({'microwave_frequency': freq})
        self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters = gen_params

    def generate_TEST(self, name='test'):
        self.log.debug(f"Optimal control path is: {self.optimal_control_assets_path}")

        created_blocks, created_ensembles, created_sequences = list(), list(), list()

        id_element = self._get_idle_element(0e-9, 0)

        # Create block ensemble
        pulse_block = PulseBlock(name=name)
        pulse_block.append(id_element)
        created_blocks.append(pulse_block)

        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((pulse_block.name, 0))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        block_ensemble.measurement_information['alternating'] = False
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = list()
        block_ensemble.measurement_information['units'] = ('Hz', '')
        block_ensemble.measurement_information['labels'] = ('Frequency', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = 0
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences