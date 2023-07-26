import numpy as np
from collections import OrderedDict


from logic.pulsed.sampling_functions import SamplingBase
from logic.pulsed.sampling_function_defs.basic_sampling_functions import Sin, DoubleSinSum, TripleSinSum, QuadSinSum




class EnvelopeParabolaMixin(SamplingBase):
    """
    Mixin to sine like sampling functions that adds an envelope is a parabola of Nth order.
    To use, create a subclass inheritng the bare sine sampling function and this mixin.
    """
    params = OrderedDict()

    params['order_P'] = {'unit': '', 'init': 1, 'min': 0, 'max': 1000, 'type': int}

    def __init__(self, *args, **kwargs):

        self.order_P = self.params['order_P']['init']if 'order_P' not in kwargs else kwargs.pop('order_P')

        super().__init__(*args, **kwargs)

    def get_samples(self, time_array):
        bare_samples = super().get_samples(time_array)
        t_rel = np.arange(time_array.size) / time_array.size  # time in units from 0..1

        samples_arr = bare_samples * \
                      (1. - (2. * (t_rel - 0.5)) ** (2 * self.order_P))
        return samples_arr


class SinEnvelopeParabola(EnvelopeParabolaMixin, Sin):
    pass

class DoubleSinSumEnvelopeParabola(EnvelopeParabolaMixin, DoubleSinSum):
    pass

class TripleSinSumEnvelopeParabola(EnvelopeParabolaMixin, TripleSinSum):
    pass

class QuadSinSumEnvelopeParabola(EnvelopeParabolaMixin, QuadSinSum):
    pass


class EnvelopeSinnMixin(SamplingBase):
    """
    Mixin to sine like sampling functions that adds an envelope is a sin**n.
    To use, create a subclass inheritng the bare sine sampling function and this mixin.
    """
    params = OrderedDict()

    params['order_n'] = {'unit': '', 'init': 1, 'min': 0, 'max': 1000, 'type': float}

    def __init__(self, *args, **kwargs):

        self.order_n = self.params['order_n']['init']if 'order_n' not in kwargs else kwargs.pop('order_n')

        super().__init__(*args, **kwargs)

    def get_samples(self, time_array):
        bare_samples = super().get_samples(time_array)
        self.log.debug(f'type time_array:{type(time_array)}')
        t_rel = np.arange(time_array.size) / time_array.size  # time in units from 0..1
        self.log.debug(f'time_relaive:{t_rel}')
        samples_arr = bare_samples * \
                      np.sin(np.pi*t_rel) **self.order_n

        self.log.debug(f'sample_array:{samples_arr}')
        return samples_arr

class SinEnvelopeSinn(EnvelopeSinnMixin, Sin):
    pass

class DoubleSinSumEnvelopeSinn(EnvelopeSinnMixin, DoubleSinSum):
    pass

class TripleSinSumEnvelopeSinn(EnvelopeSinnMixin, TripleSinSum):
    pass

class QuadSinSumEnvelopeSinn(EnvelopeSinnMixin, QuadSinSum):
    pass

class EnvelopeHermiteMixin(SamplingBase):
    """
    Mixin to sine like sampling functions that adds an envelope is a hermite function of second order.
    To use, create a subclass inheritng the bare sine sampling function and this mixin.
    """
    params = OrderedDict()

    params['T'] = {'unit': '', 'init': 1, 'min': 0, 'max': 1000, 'type': int}
    params['scale'] = {'unit': '', 'init': 1, 'min': 0, 'max': 1000, 'type': int}
    params['time_pos'] = {'unit': '', 'init': 1, 'min': 0, 'max': 1000, 'type': int}

    def __init__(self, *args, **kwargs):

        self.T = self.params['T']['init']if 'T' not in kwargs else kwargs.pop('T')
        self.scale = self.params['scale']['init'] if 'scale' not in kwargs else kwargs.pop('scale')
        self.time_pos = self.params['time_pos']['init'] if 'time_pos' not in kwargs else kwargs.pop('time_pos')

        super().__init__(*args, **kwargs)

    def get_samples(self, time_array):
        bare_samples = super().get_samples(time_array)
        #self.log.debug(f'type time_array:{type(time_array)}')
        #self.log.debug(f'type of bare_samples:{type(bare_samples)}') # Only small debug
        #self.log.debug(f'bare_samples:{bare_samples}')
        t_rel = np.arange(time_array.size) / time_array.size  # time in units from 0..1

        time_part = (t_rel-self.time_pos)/self.T
        self.log.debug(f'T: {self.T}')
        self.log.debug(f'time_pos: {self.time_pos}')
        self.log.debug(f'scale: {self.scale}')
        self.log.debug(f'time_relative: {t_rel}')
        self.log.debug(f'time_part:{time_part}')
        samples_arr = bare_samples * \
                      (1-self.scale*(time_part**2))*np.exp((-1)*(time_part**2))

        self.log.debug(f'samples_arr:{samples_arr}')
        return samples_arr

class SinHermiteEnvelope(EnvelopeHermiteMixin,Sin):
    pass