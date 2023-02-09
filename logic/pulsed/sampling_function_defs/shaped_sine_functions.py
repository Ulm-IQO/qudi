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

        self.order_P = self.params['order_n']['init']if 'order_n' not in kwargs else kwargs.pop('order_n')

        super().__init__(*args, **kwargs)

    def get_samples(self, time_array):
        bare_samples = super().get_samples(time_array)
        t_rel = np.arange(time_array.size) / time_array.size  # time in units from 0..1

        samples_arr = bare_samples * \
                      np.sin(np.pi*t_rel) **self.order_n
        return samples_arr

class SinEnvelopeSinn(EnvelopeSinnMixin, Sin):
    pass

class DoubleSinSumEnvelopeSinn(EnvelopeSinnMixin, DoubleSinSum):
    pass

class TripleSinSumEnvelopeSinn(EnvelopeSinnMixin, TripleSinSum):
    pass

class QuadSinSumEnvelopeSinn(EnvelopeSinnMixin, QuadSinSum):
    pass

