####################################################
########## Basic MFL implementation ########
####################################################

"""
V 1.0 03/2019 
AAG @ UniBristol
some functions derived from CG @Microsoft
"""

import sys, os, copy, warnings, time
import qinfer as qi
import numpy as np
from copy import deepcopy

from functools import partial
from abc import ABCMeta, abstractmethod, abstractproperty
from future.utils import with_metaclass
import scipy.linalg as la

####################################################
########## Magnetometry related definitions ########
####################################################

gamma = 28.0247
PI = np.pi


def radfreq_to_B(radfreq):
    # radfreq: in rad*MHz
    # B: in uT
    radfreq = np.array([radfreq])
    if len(radfreq) is 1:
        return (radfreq / (2 * PI) / gamma * 1000)[0]
    else:
        B = list(lambda fq: fq / (2 * PI) / gamma * 1000, fq in radfreq)
        return B


def B_to_radfreq(B):
    # radfreq: in rad*MHz
    # B: in uT
    B = np.array([B])
    if len(B) is 1:
        return (B * 2 * PI * gamma / 1000)[0]
    else:
        radfreq = list(lambda eachB: eachB * 2 * PI * gamma / 1000, eachB in B)
        return radfreq


####################################################
########## Qinfer routine dependencies ########
####################################################

def particle_meanfn(weights, locations, fn=None):
    r"""
    Returns the mean of a function :math:`f` over model
    parameters.

    :param numpy.ndarray weights: Weights of each particle.
    :param numpy.ndarray locations: Locations of each
        particle.
    :param callable fn: Function of model parameters to
        take the mean of. If `None`, the identity function
        is assumed.
    """
    fn_vals = fn(locations) if fn is not None else locations
    return np.sum(weights * fn_vals.transpose([1, 0]),
                  axis=1)


def particle_covariance_mtx(weights, locations):
    """
    Returns an estimate of the covariance of a distribution
    represented by a given set of SMC particle.

    :param weights: An array containing the weights of each
        particle.
    :param location: An array containing the locations of
        each particle.
    :rtype: :class:`numpy.ndarray`, shape
        ``(n_modelparams, n_modelparams)``.
    :returns: An array containing the estimated covariance matrix.
    """
    # TODO: add shapes to docstring.

    # Find the mean model vector, shape (n_modelparams, ).
    mu = particle_meanfn(weights, locations)

    # Transpose the particle locations to have shape
    # (n_modelparams, n_particles).
    xs = locations.transpose([1, 0])
    # Give a shorter name to the particle weights, shape (n_particles, ).
    ws = weights

    cov = (
        # This sum is a reduction over the particle index, chosen to be
        # axis=2. Thus, the sum represents an expectation value over the
        # outer product $x . x^T$.
        #
        # All three factors have the particle index as the rightmost
        # index, axis=2. Using the Einstein summation convention (ESC),
        # we can reduce over the particle index easily while leaving
        # the model parameter index to vary between the two factors
        # of xs.DataPrecModel
        #
        # This corresponds to evaluating A_{m,n} = w_{i} x_{m,i} x_{n,i}
        # using the ESC, where A_{m,n} is the temporary array created.
            np.einsum('i,mi,ni', ws, xs, xs)
            # We finish by subracting from the above expectation value
            # the outer product $mu . mu^T$.
            - np.dot(mu[..., np.newaxis], mu[np.newaxis, ...])
    )

    # The SMC approximation is not guaranteed to produce a
    # positive-semidefinite covariance matrix. If a negative eigenvalue
    # is produced, we should warn the caller of this.
    assert np.all(np.isfinite(cov))
    if not np.all(la.eig(cov)[0] >= 0):
        warnings.warn('Numerical error in covariance estimation causing positive semidefinite violation.',
                      ApproximationWarning)

    return cov


def safe_shape(arr, idx=0, default=1):
    shape = np.shape(arr)
    return shape[idx] if idx < len(shape) else default


####################################################
########## Standard Data Analysis ##################
####################################################

from scipy.optimize import curve_fit
import scipy.integrate as integrate
from scipy.stats import norm


def Lorentzian(x, x0, gamma, norm_factor):
    """
    Defines a Lorentzian function with parameters x0, gamma, norm_factor
    """
    return gamma / (2 * PI * ((x - x0) ** 2 + (gamma / 2) ** 2)) / norm_factor


def Gaussian(x, mean=0., sigma=1.):
    """
    Defines a Gaussian function with parameters mean, sigma
    """
    return norm.pdf(x, loc=mean, scale=sigma)


####################################################
########## Additional Data Analysis ##################
####################################################


def DampedOscill(t, Omega, invT2):
    y = 1 - np.exp(-t * invT2) * np.cos(Omega * t / 2) ** 2 - 0.5 * (1 - np.exp(-t * invT2))
    return (y)


####################################################
########## Model  definitions     ##################
####################################################

####################################################
########## Ramsey models
####################################################

class ExpDecoKnownPrecessionModel():
    r"""
    Model that simulates a sinusoidal Precession in magnetic field,
    imposing a (known) decoherence as a user-defined parameter

    :param float min_freq: Impose a minimum frequency (often 0 to avoid degeneracies in the problem)
    :param float invT2: If a dephasing time T_2* for the system is known, user can input its inverse here
    """

    ## INITIALIZER ##

    def __init__(self, min_freq=0, invT2=0., eta_assym=1):
        super(ExpDecoKnownPrecessionModel, self).__init__()

        self._min_freq = min_freq
        self._invT2 = invT2
        if eta_assym is None:
            eta_assym = 1
        self._eta_assym = eta_assym

        # Initialize a default scale matrix.
        self._Q = np.ones((self.n_modelparams,))

    ## GENERIC METHODS ##

    def clear_cache(self):
        """
        Tells the model to clear any internal caches used in computing
        likelihoods and drawing samples. Calling this method should not cause
        any different results, but should only affect performance.
        """
        # By default, no cache to clear.
        pass

    def distance(self, a, b):
        r"""
        Gives the distance between two model parameter vectors :math:`\vec{a}` and
        :math:`\vec{b}`. By default, this is the vector 1-norm of the difference
        :math:`\mathbf{Q} (\vec{a} - \vec{b})` rescaled by
        :attr:`~Model.Q`.

        :param np.ndarray a: Array of model parameter vectors having shape
            ``(n_models, n_modelparams)``.
        :param np.ndarray b: Array of model parameters to compare to, having
            the same shape as ``a``.
        :return: An array ``d`` of distances ``d[i]`` between ``a[i, :]`` and
            ``b[i, :]``.
        """

        return np.apply_along_axis(
            lambda vec: np.linalg.norm(vec, 1),
            1,
            self._Q * (a - b)
        )

    def update_timestep(self, modelparams, expparams):
        r"""
        Returns a set of model parameter vectors that is the update of an
        input set of model parameter vectors, such that the new models are
        conditioned on a particular experiment having been performed.
        By default, this is the trivial function
        :math:`\vec{x}(t_{k+1}) = \vec{x}(t_k)`.

        :param np.ndarray modelparams: Set of model parameter vectors to be
            updated.
        :param np.ndarray expparams: An experiment parameter array describing
            the experiment that was just performed.

        :return np.ndarray: Array of shape
            ``(n_models, n_modelparams, n_experiments)`` describing the update
            of each model according to each experiment.
        """
        return np.tile(modelparams, (expparams.shape[0], 1, 1)).transpose((1, 2, 0))

    @staticmethod
    def pr0_to_likelihood_array(outcomes, pr0):
        """
        Assuming a two-outcome measurement with probabilities given by the
        array ``pr0``, returns an array of the form expected to be returned by
        ``likelihood`` method.

        :param numpy.ndarray outcomes: Array of integers indexing outcomes.
        :param numpy.ndarray pr0: Array of shape ``(n_models, n_experiments)``
            describing the probability of obtaining outcome ``0`` from each
            set of model parameters and experiment parameters.
        """
        pr0 = pr0[np.newaxis, ...]
        pr1 = 1 - pr0

        if len(np.shape(outcomes)) == 0:
            outcomes = np.array(outcomes)[None]

        return np.concatenate([
            pr0 if outcomes[idx] == 0 else pr1
            for idx in range(safe_shape(outcomes))
        ])

        ## PROPERTIES ##

    @property
    def n_modelparams(self):
        """
        the number of parameters the algorithm will learn, here just the frequency
        """
        return 1

    # these 3 properties are just for ease of call of the various required parameters, feel free to ignore in non-python implementations
    @property
    def modelparam_names(self):
        return ['w_']

    @property
    def modelparam_dtype(self):
        return [('w_', 'float')]

    @property
    def expparams_dtype(self):
        return [('t', 'float'), ('w_', 'float')]

    @property
    def is_n_outcomes_constant(self):
        """
        Returns ``True`` if and only if the number of outcomes for each
        experiment is independent of the experiment being performed.

        This property is assumed by inference engines to be constant for
        the lifetime of a Model instance.
        """
        return True

    # METHODS ##

    def are_models_valid(self, modelparams):
        """
        checks that no particles have been extracted with physically wrong parameters, e.g. frequencies < 0
        """
        return np.all(modelparams > self._min_freq, axis=1)

    def n_outcomes(self, expparams):
        """
        n_outcomes enforces a binary outcome from each experiment
        """
        return 2

    def simulate_experiment(self, modelparams, expparams, repeat=1, res_no_noise=None, full_result=False):
        """
        Provides a simulated binary outcome for an experiment, given the model (self), and its parameters

        :param np.ndarray modelparams: Set of model parameter vectors to be
                updated.
        :param np.ndarray expparams: An experiment parameter array describing
            the experiment that was just performed.
        :param flaot repeat: how many times the experiment is repeated before an update is called, can be useful for majority voting schemes

        :return int: single integer representing the experimental outcome
        """

        if self.is_n_outcomes_constant:
            # In this case, all expparams have the same domain [0,1]
            all_outcomes = np.array([0, 1])
            try:
                probabilities = self.likelihood(all_outcomes, modelparams, expparams, noisy=True,
                                                res_no_noise=res_no_noise)
                noisy = True
            except TypeError:
                noisy = False
                probabilities = self.likelihood(all_outcomes, modelparams, expparams)
            # probabilities = self.likelihood(all_outcomes, modelparams, expparams)
            cdf = np.cumsum(probabilities, axis=0)
            randnum = np.random.random((repeat, 1, modelparams.shape[0], expparams.shape[0]))
            outcome_idxs = all_outcomes[np.argmax(cdf > randnum, axis=1)]
            outcomes = all_outcomes[outcome_idxs]

            if full_result:
                if repeat > 1:
                    raise NotImplementedError
                else:
                    if type(res_no_noise) is list and noisy:
                        res_no_noise[0] = 1 - res_no_noise[0]
                    elif type(res_no_noise) is list and not noisy:
                        res_no_noise.append(1 - cdf[0, 0, 0])

                    assert (len(res_no_noise) == 0 or len(res_no_noise) == 1)
                    return 1 - cdf[0, 0, 0]  # defined mirrored
        else:
            # Loop over each experiment, sadly.
            # Assume all domains have the same dtype
            assert (self.are_expparam_dtypes_consistent(expparams))
            dtype = self.domain(expparams[0, np.newaxis])[0].dtype
            outcomes = np.empty((repeat, modelparams.shape[0], expparams.shape[0]), dtype=dtype)
            for idx_experiment, single_expparams in enumerate(expparams[:, np.newaxis]):
                all_outcomes = self.domain(single_expparams).values
                probabilities = self.likelihood(all_outcomes, modelparams, single_expparams)
                cdf = np.cumsum(probabilities, axis=0)[..., 0]
                randnum = np.random.random((repeat, 1, modelparams.shape[0]))
                outcomes[:, :, idx_experiment] = all_outcomes[np.argmax(cdf > randnum, axis=1)]

        return outcomes[0, 0, 0] if repeat == 1 and expparams.shape[0] == 1 and modelparams.shape[0] == 1 else outcomes

    def likelihood(self, outcomes, modelparams, expparams):
        """
        :param np.ndarray outcomes: set of possible experimental outcomes (here [0,1])
        :param np.ndarray modelparams: Set of model parameter vectors to be
                updated.
        :param np.ndarray expparams: An experiment parameter array describing
            the experiment that was just performed.

        :param numpy.ndarray: likelihoods of obtaining outcome ``0`` from each
            set of model parameters and experiment parameters.

        """

        # this is just for array dimension matching
        if len(modelparams.shape) == 1:
            modelparams = modelparams[..., np.newaxis]

        t = expparams['t']
        dw = modelparams[:, 0]

        # ESSENTIAL STEP > the likelihoods (i.e. cosines with a damping exp term) are evaluated for all particles
        pr0 = np.zeros((modelparams.shape[0], expparams.shape[0]))
        l = np.exp(-t * self._invT2) * (np.cos(t * dw / 2) ** 2) + 0.5 * (1 - np.exp(-t * self._invT2))

        # prepare output dimensions st. plot_zs() works
        try:
            pr0[:, :] = l.transpose()
        except ValueError:
            try:
                pr0[:, :] = l[..., np.newaxis]
            except ValueError:
                pr0[:, :] = l[np.newaxis, ...]

        pr1 = self._eta_assym * (1 - pr0)

        return self.pr0_to_likelihood_array(outcomes, 1 - pr1)


class MultimodePrecModel(qi.FiniteOutcomeModel):
    r"""
    ad hoc modification of the SimplePrecession model to include multimode capabilities in term of
    an explicitly degenerate 2-param likelihood
    """

    ## INITIALIZER ##

    def __init__(self, min_freq=0):
        super(MultimodePrecModel, self).__init__()
        self._min_freq = min_freq

    def simulate_experiment(self, modelparams, expparams, repeat=1, res_no_noise=None, full_result=False):
        """
        Provides a simulated binary outcome for an experiment, given the model (self), and its parameters

        :param np.ndarray modelparams: Set of model parameter vectors to be
                updated.
        :param np.ndarray expparams: An experiment parameter array describing
            the experiment that was just performed.
        :param flaot repeat: how many times the experiment is repeated before an update is called, can be useful for majority voting schemes

        :return int: single integer representing the experimental outcome
        """

        if self.is_n_outcomes_constant:
            # In this case, all expparams have the same domain [0,1]
            all_outcomes = np.array([0, 1])
            try:
                probabilities = self.likelihood(all_outcomes, modelparams, expparams, noisy=True,
                                                res_no_noise=res_no_noise)
                noisy = True
            except TypeError:
                noisy = False
                probabilities = self.likelihood(all_outcomes, modelparams, expparams)
            # probabilities = self.likelihood(all_outcomes, modelparams, expparams)
            cdf = np.cumsum(probabilities, axis=0)
            randnum = np.random.random((repeat, 1, modelparams.shape[0], expparams.shape[0]))
            outcome_idxs = all_outcomes[np.argmax(cdf > randnum, axis=1)]
            outcomes = all_outcomes[outcome_idxs]

            if full_result:
                if repeat > 1:
                    raise NotImplementedError
                else:
                    if type(res_no_noise) is list and noisy:
                        res_no_noise[0] = 1 - res_no_noise[0]
                    elif type(res_no_noise) is list and not noisy:
                        res_no_noise.append(1 - cdf[0, 0, 0])

                    if res_no_noise:
                        assert (len(res_no_noise) == 0 or len(res_no_noise) == 1)
                    return 1 - cdf[0, 0, 0]  # defined mirrored
        else:
            # Loop over each experiment, sadly.
            # Assume all domains have the same dtype
            assert (self.are_expparam_dtypes_consistent(expparams))
            dtype = self.domain(expparams[0, np.newaxis])[0].dtype
            outcomes = np.empty((repeat, modelparams.shape[0], expparams.shape[0]), dtype=dtype)
            for idx_experiment, single_expparams in enumerate(expparams[:, np.newaxis]):
                all_outcomes = self.domain(single_expparams).values
                probabilities = self.likelihood(all_outcomes, modelparams, single_expparams)
                cdf = np.cumsum(probabilities, axis=0)[..., 0]
                randnum = np.random.random((repeat, 1, modelparams.shape[0]))
                outcomes[:, :, idx_experiment] = all_outcomes[np.argmax(cdf > randnum, axis=1)]

        return outcomes[0, 0, 0] if repeat == 1 and expparams.shape[0] == 1 and modelparams.shape[0] == 1 else outcomes

    ## PROPERTIES ##

    @property
    def n_modelparams(self):
        return 2

    @property
    def modelparam_names(self):
        return [r'\omega1', r'\omega2']

    @property
    def expparams_dtype(self):
        return [('t', 'float'), ('w1', 'float'), ('w2', 'float')]

    @property
    def is_n_outcomes_constant(self):
        """
        Returns ``True`` if and only if the number of outcomes for each
        experiment is independent of the experiment being performed.

        This property is assumed by inference engines to be constant for
        the lifetime of a Model instance.
        """
        return True

    ## METHODS ##

    def are_models_valid(self, modelparams):
        return np.all(modelparams > self._min_freq, axis=1)

    def n_outcomes(self, expparams):
        """
        Returns an array of dtype ``uint`` describing the number of outcomes
        for each experiment specified by ``expparams``.

        :param numpy.ndarray expparams: Array of experimental parameters. This
            array must be of dtype agreeing with the ``expparams_dtype``
            property.
        """
        return 2

    def likelihood(self, outcomes, modelparams, expparams):
        # By calling the superclass implementation, we can consolidate
        # call counting there.
        super(MultimodePrecModel, self).likelihood(
            outcomes, modelparams, expparams
        )

        # print('outcomes = ' + repr(outcomes))

        # Possibly add a second axis to modelparams.
        if len(modelparams.shape) == 1:
            modelparams = modelparams[..., np.newaxis]

        #         print('modelparams = ' + repr(modelparams))
        # print('expparams = ' + repr(expparams))
        # print('m = ' + str(modelparams))
        # print('w_ = ' + str(expparams['w_']))

        t = expparams['t']
        # print('dw=' + repr(dw))

        # Allocating first serves to make sure that a shape mismatch later
        # will cause an error.
        pr0 = np.zeros((modelparams.shape[0], expparams.shape[0]))

        pr0[:, :] = 0.5 * (np.cos(t * modelparams[:, 0] / 2) ** 2 + np.cos(t * modelparams[:, 1] / 2) ** 2)[
            ..., np.newaxis]

        #         print("Pr0 = " + str(pr0) )

        # Now we concatenate over outcomes.
        # print("likelihoods: " + str(qi.FiniteOutcomeModel.pr0_to_likelihood_array(outcomes, pr0)))

        return qi.FiniteOutcomeModel.pr0_to_likelihood_array(outcomes, pr0)


class ExpDecoKnownMultimodePrecModel(MultimodePrecModel):

    def __init__(self, min_freq=0, inv_T2=0.):
        super().__init__()

        self._min_freq = min_freq
        self._invT2 = inv_T2

    def likelihood(self, outcomes, modelparams, expparams):
        """
        :param np.ndarray outcomes: set of possible experimental outcomes (here [0,1])
        :param np.ndarray modelparams: Set of model parameter vectors to be
                updated.
        :param np.ndarray expparams: An experiment parameter array describing
            the experiment that was just performed.

        :param numpy.ndarray: likelihoods of obtaining outcome ``0`` from each
            set of model parameters and experiment parameters.

        """

        # this is just for array dimension matching
        if len(modelparams.shape) == 1:
            modelparams = modelparams[..., np.newaxis]

        t = expparams['t']
        w1 = modelparams[:, 0]
        w2 = modelparams[:, 1]

        # ESSENTIAL STEP > the likelihoods (i.e. cosines with a damping exp term) are evaluated for all particles
        pr0 = np.zeros((modelparams.shape[0], expparams.shape[0]))
        l_no_decoh = 0.5 * (np.cos(t * w1 / 2) ** 2 + np.cos(t * w2 / 2) ** 2)
        l = np.exp(-t * self._invT2) * l_no_decoh + 0.5 * (1 - np.exp(-t * self._invT2))

        try:
            pr0[:, :] = l[..., np.newaxis]
        except ValueError:
            pr0[:, :] = l[np.newaxis, ...]

        return self.pr0_to_likelihood_array(outcomes, pr0)


####################################################
########## Hahn echo models
####################################################

class MultimodeHahnModel(qi.FiniteOutcomeModel):
    r"""
    ad hoc modification of the SimplePrecession model to include multimode capabilities in term of
    an explicitly degenerate 2-param likelihood
    """

    ## INITIALIZER ##

    def __init__(self, b_gauss, min_freq=0):
        super().__init__()
        self._min_freq = min_freq
        self._b_gauss = b_gauss
        self._gamma = 1.07084e3 * 2 * np.pi  # 13-C, Hz/G, [w] = Hz rad

    def simulate_experiment(self, modelparams, expparams, repeat=1, res_no_noise=None, full_result=False):
        """
        Provides a simulated binary outcome for an experiment, given the model (self), and its parameters

        :param np.ndarray modelparams: Set of model parameter vectors to be
                updated.
        :param np.ndarray expparams: An experiment parameter array describing
            the experiment that was just performed.
        :param flaot repeat: how many times the experiment is repeated before an update is called, can be useful for majority voting schemes

        :return int: single integer representing the experimental outcome
        """

        if self.is_n_outcomes_constant:
            # In this case, all expparams have the same domain [0,1]
            all_outcomes = np.array([0, 1])
            try:
                probabilities = self.likelihood(all_outcomes, modelparams, expparams, noisy=True,
                                                res_no_noise=res_no_noise)
                noisy = True
            except TypeError:
                noisy = False
                probabilities = self.likelihood(all_outcomes, modelparams, expparams)
            # probabilities = self.likelihood(all_outcomes, modelparams, expparams)
            cdf = np.cumsum(probabilities, axis=0)
            randnum = np.random.random((repeat, 1, modelparams.shape[0], expparams.shape[0]))
            outcome_idxs = all_outcomes[np.argmax(cdf > randnum, axis=1)]
            outcomes = all_outcomes[outcome_idxs]

            if full_result:
                if repeat > 1:
                    raise NotImplementedError
                else:
                    if type(res_no_noise) is list and noisy:
                        res_no_noise[0] = 1 - res_no_noise[0]
                    elif type(res_no_noise) is list and not noisy:
                        res_no_noise.append(1 - cdf[0, 0, 0])

                    if res_no_noise:
                        assert (len(res_no_noise) == 0 or len(res_no_noise) == 1)
                    return 1 - cdf[0, 0, 0]  # defined mirrored
        else:
            # Loop over each experiment, sadly.
            # Assume all domains have the same dtype
            assert (self.are_expparam_dtypes_consistent(expparams))
            dtype = self.domain(expparams[0, np.newaxis])[0].dtype
            outcomes = np.empty((repeat, modelparams.shape[0], expparams.shape[0]), dtype=dtype)
            for idx_experiment, single_expparams in enumerate(expparams[:, np.newaxis]):
                all_outcomes = self.domain(single_expparams).values
                probabilities = self.likelihood(all_outcomes, modelparams, single_expparams)
                cdf = np.cumsum(probabilities, axis=0)[..., 0]
                randnum = np.random.random((repeat, 1, modelparams.shape[0]))
                outcomes[:, :, idx_experiment] = all_outcomes[np.argmax(cdf > randnum, axis=1)]

        return outcomes[0, 0, 0] if repeat == 1 and expparams.shape[0] == 1 and modelparams.shape[0] == 1 else outcomes

    ## PROPERTIES ##

    @property
    def n_modelparams(self):
        return 2

    @property
    def modelparam_names(self):
        return [r'\omega1', r'\omega2']

    @property
    def expparams_dtype(self):
        return [('t', 'float'), ('w1', 'float'), ('w2', 'float')]

    @property
    def is_n_outcomes_constant(self):
        """
        Returns ``True`` if and only if the number of outcomes for each
        experiment is independent of the experiment being performed.

        This property is assumed by inference engines to be constant for
        the lifetime of a Model instance.
        """
        return True

    ## METHODS ##

    def are_models_valid(self, modelparams):
        return np.all(modelparams > self._min_freq, axis=1)

    def n_outcomes(self, expparams):
        """
        Returns an array of dtype ``uint`` describing the number of outcomes
        for each experiment specified by ``expparams``.

        :param numpy.ndarray expparams: Array of experimental parameters. This
            array must be of dtype agreeing with the ``expparams_dtype``
            property.
        """
        return 2

    def likelihood(self, outcomes, modelparams, expparams):
        # approximation: see labbook 20191114
        # uses parameters: |A|, phi_01

        # By calling the superclass implementation, we can consolidate
        # call counting there.
        super().likelihood(
            outcomes, modelparams, expparams
        )

        # Possibly add a second axis to modelparams.
        if len(modelparams.shape) == 1:
            modelparams = modelparams[..., np.newaxis]

        t = expparams['t']  # us
        # modelparams[:,0]: A_hfs [MHz rad]
        # modelparams[:,1]: phi_h01 [rad]

        h_0 = self._b_gauss
        h_1 = self._b_gauss - modelparams[:, 0] * 1e6 / self._gamma
        theta_0 = self._gamma * h_0 * t * 1e-6
        theta_1 = self._gamma * h_1 * t * 1e-6
        # gamma in Hz rad / G (w units)

        # Allocating first serves to make sure that a shape mismatch later
        # will cause an error.
        pr0 = np.zeros((modelparams.shape[0], expparams.shape[0]))

        l = 0.5 + 0.5 * (1 - 2 * np.sin(modelparams[:, 1]) ** 2 * np.sin(theta_0 / 2) ** 2 * np.sin(theta_1 / 2) ** 2)

        try:
            pr0[:, :] = l[..., np.newaxis]
        except ValueError:
            pr0[:, :] = l[np.newaxis, ...]

        return qi.FiniteOutcomeModel.pr0_to_likelihood_array(outcomes, pr0)


class AparrKnownHahnModel():
    r"""
    Model that simulates a double sinusoidal coupling to a nuclear spin in low magnetic field
    imposing a (known) decoherence as a user-defined parameter

    :param float min_freq: Impose a minimum frequency (often 0 to avoid degeneracies in the problem)
    :param float invT2: If a dephasing time T_2* for the system is known, user can input its inverse here
    """

    ## INITIALIZER ##

    def __init__(self, b_gauss, a_par, min_freq=0, c_scale_2=1):
        super().__init__()

        self._min_freq = min_freq  # MHz rad
        self._b_gauss = b_gauss
        self._gamma = 1.07084e3 * 2 * np.pi  # 13-C, Hz/G, [w] = Hz rad
        self._a_par = a_par  # parallel A_hfs, Hz rad
        self._c_sc2 = c_scale_2  # amplitude of HE, overwrites sin(phi_01) amplitude

        # Initialize a default scale matrix.
        self._Q = np.ones((self.n_modelparams,))

    ## GENERIC METHODS ##

    def clear_cache(self):
        """
        Tells the model to clear any internal caches used in computing
        likelihoods and drawing samples. Calling this method should not cause
        any different results, but should only affect performance.
        """
        # By default, no cache to clear.
        pass

    def distance(self, a, b):
        r"""
        Gives the distance between two model parameter vectors :math:`\vec{a}` and
        :math:`\vec{b}`. By default, this is the vector 1-norm of the difference
        :math:`\mathbf{Q} (\vec{a} - \vec{b})` rescaled by
        :attr:`~Model.Q`.

        :param np.ndarray a: Array of model parameter vectors having shape
            ``(n_models, n_modelparams)``.
        :param np.ndarray b: Array of model parameters to compare to, having
            the same shape as ``a``.
        :return: An array ``d`` of distances ``d[i]`` between ``a[i, :]`` and
            ``b[i, :]``.
        """

        return np.apply_along_axis(
            lambda vec: np.linalg.norm(vec, 1),
            1,
            self._Q * (a - b)
        )

    def update_timestep(self, modelparams, expparams):
        r"""
        Returns a set of model parameter vectors that is the update of an
        input set of model parameter vectors, such that the new models are
        conditioned on a particular experiment having been performed.
        By default, this is the trivial function
        :math:`\vec{x}(t_{k+1}) = \vec{x}(t_k)`.

        :param np.ndarray modelparams: Set of model parameter vectors to be
            updated.
        :param np.ndarray expparams: An experiment parameter array describing
            the experiment that was just performed.

        :return np.ndarray: Array of shape
            ``(n_models, n_modelparams, n_experiments)`` describing the update
            of each model according to each experiment.
        """
        return np.tile(modelparams, (expparams.shape[0], 1, 1)).transpose((1, 2, 0))

    @staticmethod
    def pr0_to_likelihood_array(outcomes, pr0):
        """
        Assuming a two-outcome measurement with probabilities given by the
        array ``pr0``, returns an array of the form expected to be returned by
        ``likelihood`` method.

        :param numpy.ndarray outcomes: Array of integers indexing outcomes.
        :param numpy.ndarray pr0: Array of shape ``(n_models, n_experiments)``
            describing the probability of obtaining outcome ``0`` from each
            set of model parameters and experiment parameters.
        """
        pr0 = pr0[np.newaxis, ...]
        pr1 = 1 - pr0

        if len(np.shape(outcomes)) == 0:
            outcomes = np.array(outcomes)[None]

        return np.concatenate([
            pr0 if outcomes[idx] == 0 else pr1
            for idx in range(safe_shape(outcomes))
        ])

        ## PROPERTIES ##

    @property
    def n_modelparams(self):
        """
        the number of parameters the algorithm will learn, here just the frequency
        """
        return 1

    # these 3 properties are just for ease of call of the various required parameters, feel free to ignore in non-python implementations
    @property
    def modelparam_names(self):
        return ['w_']

    @property
    def modelparam_dtype(self):
        return [('w_', 'float')]

    @property
    def expparams_dtype(self):
        return [('t', 'float'), ('w_', 'float')]

    @property
    def is_n_outcomes_constant(self):
        """
        Returns ``True`` if and only if the number of outcomes for each
        experiment is independent of the experiment being performed.

        This property is assumed by inference engines to be constant for
        the lifetime of a Model instance.
        """
        return True

    # METHODS ##

    def are_models_valid(self, modelparams):
        """
        checks that no particles have been extracted with physically wrong parameters, e.g. frequencies < 0
        """
        return np.all(modelparams > self._min_freq, axis=1)

    def n_outcomes(self, expparams):
        """
        n_outcomes enforces a binary outcome from each experiment
        """
        return 2

    def simulate_experiment(self, modelparams, expparams, repeat=1, res_no_noise=None, full_result=False):
        """
        Provides a simulated binary outcome for an experiment, given the model (self), and its parameters

        :param np.ndarray modelparams: Set of model parameter vectors to be
                updated.
        :param np.ndarray expparams: An experiment parameter array describing
            the experiment that was just performed.
        :param flaot repeat: how many times the experiment is repeated before an update is called, can be useful for majority voting schemes

        :return int: single integer representing the experimental outcome
        """

        if self.is_n_outcomes_constant:
            # In this case, all expparams have the same domain [0,1]
            all_outcomes = np.array([0, 1])
            try:
                probabilities = self.likelihood(all_outcomes, modelparams, expparams, noisy=True,
                                                res_no_noise=res_no_noise)
                noisy = True
            except TypeError:
                noisy = False
                probabilities = self.likelihood(all_outcomes, modelparams, expparams)
            # probabilities = self.likelihood(all_outcomes, modelparams, expparams)
            cdf = np.cumsum(probabilities, axis=0)
            randnum = np.random.random((repeat, 1, modelparams.shape[0], expparams.shape[0]))
            outcome_idxs = all_outcomes[np.argmax(cdf > randnum, axis=1)]
            outcomes = all_outcomes[outcome_idxs]

            if full_result:
                if repeat > 1:
                    raise NotImplementedError
                else:
                    if type(res_no_noise) is list and noisy:
                        res_no_noise[0] = 1 - res_no_noise[0]
                    elif type(res_no_noise) is list and not noisy:
                        res_no_noise.append(1 - cdf[0, 0, 0])

                    assert (len(res_no_noise) == 0 or len(res_no_noise) == 1)
                    return 1 - cdf[0, 0, 0]  # defined mirrored
        else:
            # Loop over each experiment, sadly.
            # Assume all domains have the same dtype
            assert (self.are_expparam_dtypes_consistent(expparams))
            dtype = self.domain(expparams[0, np.newaxis])[0].dtype
            outcomes = np.empty((repeat, modelparams.shape[0], expparams.shape[0]), dtype=dtype)
            for idx_experiment, single_expparams in enumerate(expparams[:, np.newaxis]):
                all_outcomes = self.domain(single_expparams).values
                probabilities = self.likelihood(all_outcomes, modelparams, single_expparams)
                cdf = np.cumsum(probabilities, axis=0)[..., 0]
                randnum = np.random.random((repeat, 1, modelparams.shape[0]))
                outcomes[:, :, idx_experiment] = all_outcomes[np.argmax(cdf > randnum, axis=1)]

        return outcomes[0, 0, 0] if repeat == 1 and expparams.shape[0] == 1 and modelparams.shape[0] == 1 else outcomes

    def likelihood(self, outcomes, modelparams, expparams):
        """
        :param np.ndarray outcomes: set of possible experimental outcomes (here [0,1])
        :param np.ndarray modelparams: Set of model parameter vectors to be
                updated.
        :param np.ndarray expparams: An experiment parameter array describing
            the experiment that was just performed.

        :param numpy.ndarray: likelihoods of obtaining outcome ``0`` from each
            set of model parameters and experiment parameters.

        """

        # this is just for array dimension matching
        if len(modelparams.shape) == 1:
            modelparams = modelparams[..., np.newaxis]

        # get units rights (all SI)
        t = expparams['t']  # us
        A_abs = modelparams[:, 0]  # MHz rad, due to model scaling

        tau = t * 1e-6  # s
        A = A_abs * 1e6  # Hz rad
        alpha = np.arccos(self._a_par / A)
        A_par = A_abs * np.cos(alpha) * 1e6  # Hz rad
        A_perp = A_abs * np.sin(alpha) * 1e6  # Hz rad

        # gamma in Hz rad / G (w units)

        A_as_B = A / self._gamma  # Hz rad -> Gauss
        B = self._b_gauss  # Gauss

        h_0 = self._b_gauss
        h_1 = np.sqrt((B - A_par / self._gamma) ** 2 + (A_perp / self._gamma) ** 2)
        theta_0 = self._gamma * h_0 * tau
        theta_1 = self._gamma * h_1 * tau

        phi_h01 = np.arcsin(A_as_B * np.sin(alpha) / (np.sqrt(B ** 2 - 2 * A_as_B * B * np.cos(alpha) + A_as_B ** 2)))

        # Allocating first serves to make sure that a shape mismatch later
        # will cause an error.
        pr0 = np.zeros((modelparams.shape[0], expparams.shape[0]))

        if self._c_sc2 is 1:
            l = 0.5 + 0.5 * (1 - 2 * np.sin(phi_h01) ** 2 * np.sin(theta_0 / 2) ** 2 * np.sin(theta_1 / 2) ** 2)
        else:
            # c_scale_contrast_2 = 0.3
            l = 0.5 + 0.5 * (1 - 2 * self._c_sc2 * np.sin(theta_0 / 2) ** 2 * np.sin(
                theta_1 / 2) ** 2)

        try:
            pr0[:, :] = 1 - l.transpose()
        except ValueError:
            try:
                pr0[:, :] = 1 - l[..., np.newaxis]
            except ValueError:
                pr0[:, :] = 1 - l[np.newaxis, ...]

        return self.pr0_to_likelihood_array(outcomes, pr0)


class BKnownHahnModel():
    r"""
    Model that simulates a double sinusoidal coupling to a nuclear spin in low magnetic field
    imposing a (known) decoherence as a user-defined parameter

    :param float min_freq: Impose a minimum frequency (often 0 to avoid degeneracies in the problem)
    :param float invT2: If a dephasing time T_2* for the system is known, user can input its inverse here
    """

    ## INITIALIZER ##

    def __init__(self, b_gauss, min_freq=0, c_scale_2=1):
        super().__init__()

        self._min_freq = min_freq  # MHz rad
        self._b_gauss = b_gauss
        self._gamma = 1.07084e3 * 2 * np.pi  # 13-C, Hz/G, [w] = Hz rad

        self._c_sc2 = c_scale_2  # amplitude of HE, overwrites sin(phi_01) amplitude

        # Initialize a default scale matrix.
        self._Q = np.ones((self.n_modelparams,))

    ## GENERIC METHODS ##

    def clear_cache(self):
        """
        Tells the model to clear any internal caches used in computing
        likelihoods and drawing samples. Calling this method should not cause
        any different results, but should only affect performance.
        """
        # By default, no cache to clear.
        pass

    def distance(self, a, b):
        r"""
        Gives the distance between two model parameter vectors :math:`\vec{a}` and
        :math:`\vec{b}`. By default, this is the vector 1-norm of the difference
        :math:`\mathbf{Q} (\vec{a} - \vec{b})` rescaled by
        :attr:`~Model.Q`.

        :param np.ndarray a: Array of model parameter vectors having shape
            ``(n_models, n_modelparams)``.
        :param np.ndarray b: Array of model parameters to compare to, having
            the same shape as ``a``.
        :return: An array ``d`` of distances ``d[i]`` between ``a[i, :]`` and
            ``b[i, :]``.
        """

        return np.apply_along_axis(
            lambda vec: np.linalg.norm(vec, 1),
            1,
            self._Q * (a - b)
        )

    def update_timestep(self, modelparams, expparams):
        r"""
        Returns a set of model parameter vectors that is the update of an
        input set of model parameter vectors, such that the new models are
        conditioned on a particular experiment having been performed.
        By default, this is the trivial function
        :math:`\vec{x}(t_{k+1}) = \vec{x}(t_k)`.

        :param np.ndarray modelparams: Set of model parameter vectors to be
            updated.
        :param np.ndarray expparams: An experiment parameter array describing
            the experiment that was just performed.

        :return np.ndarray: Array of shape
            ``(n_models, n_modelparams, n_experiments)`` describing the update
            of each model according to each experiment.
        """
        return np.tile(modelparams, (expparams.shape[0], 1, 1)).transpose((1, 2, 0))

    @staticmethod
    def pr0_to_likelihood_array(outcomes, pr0):
        """
        Assuming a two-outcome measurement with probabilities given by the
        array ``pr0``, returns an array of the form expected to be returned by
        ``likelihood`` method.

        :param numpy.ndarray outcomes: Array of integers indexing outcomes.
        :param numpy.ndarray pr0: Array of shape ``(n_models, n_experiments)``
            describing the probability of obtaining outcome ``0`` from each
            set of model parameters and experiment parameters.
        """
        pr0 = pr0[np.newaxis, ...]
        pr1 = 1 - pr0

        if len(np.shape(outcomes)) == 0:
            outcomes = np.array(outcomes)[None]

        return np.concatenate([
            pr0 if outcomes[idx] == 0 else pr1
            for idx in range(safe_shape(outcomes))
        ])

        ## PROPERTIES ##

    @property
    def n_modelparams(self):
        """
        the number of parameters the algorithm will learn, here just the frequency
        """
        return 1

    # these 3 properties are just for ease of call of the various required parameters, feel free to ignore in non-python implementations
    @property
    def modelparam_names(self):
        return ['w_']

    @property
    def modelparam_dtype(self):
        return [('w_', 'float')]

    @property
    def expparams_dtype(self):
        return [('t', 'float'), ('w_', 'float')]

    @property
    def is_n_outcomes_constant(self):
        """
        Returns ``True`` if and only if the number of outcomes for each
        experiment is independent of the experiment being performed.

        This property is assumed by inference engines to be constant for
        the lifetime of a Model instance.
        """
        return True

    # METHODS ##

    def are_models_valid(self, modelparams):
        """
        checks that no particles have been extracted with physically wrong parameters, e.g. frequencies < 0
        """
        return np.all(modelparams > self._min_freq, axis=1)

    def n_outcomes(self, expparams):
        """
        n_outcomes enforces a binary outcome from each experiment
        """
        return 2

    def simulate_experiment(self, modelparams, expparams, repeat=1, res_no_noise=None, full_result=False):
        """
        Provides a simulated binary outcome for an experiment, given the model (self), and its parameters

        :param np.ndarray modelparams: Set of model parameter vectors to be
                updated.
        :param np.ndarray expparams: An experiment parameter array describing
            the experiment that was just performed.
        :param flaot repeat: how many times the experiment is repeated before an update is called, can be useful for majority voting schemes

        :return int: single integer representing the experimental outcome
        """

        if self.is_n_outcomes_constant:
            # In this case, all expparams have the same domain [0,1]
            all_outcomes = np.array([0, 1])
            try:
                probabilities = self.likelihood(all_outcomes, modelparams, expparams, noisy=True,
                                                res_no_noise=res_no_noise)
                noisy = True
            except TypeError:
                noisy = False
                probabilities = self.likelihood(all_outcomes, modelparams, expparams)
            # probabilities = self.likelihood(all_outcomes, modelparams, expparams)
            cdf = np.cumsum(probabilities, axis=0)
            randnum = np.random.random((repeat, 1, modelparams.shape[0], expparams.shape[0]))
            outcome_idxs = all_outcomes[np.argmax(cdf > randnum, axis=1)]
            outcomes = all_outcomes[outcome_idxs]

            if full_result:
                if repeat > 1:
                    raise NotImplementedError
                else:
                    if type(res_no_noise) is list and noisy:
                        res_no_noise[0] = 1 - res_no_noise[0]
                    elif type(res_no_noise) is list and not noisy:
                        res_no_noise.append(1 - cdf[0, 0, 0])

                    assert (len(res_no_noise) == 0 or len(res_no_noise) == 1)
                    return 1 - cdf[0, 0, 0]  # defined mirrored
        else:
            # Loop over each experiment, sadly.
            # Assume all domains have the same dtype
            assert (self.are_expparam_dtypes_consistent(expparams))
            dtype = self.domain(expparams[0, np.newaxis])[0].dtype
            outcomes = np.empty((repeat, modelparams.shape[0], expparams.shape[0]), dtype=dtype)
            for idx_experiment, single_expparams in enumerate(expparams[:, np.newaxis]):
                all_outcomes = self.domain(single_expparams).values
                probabilities = self.likelihood(all_outcomes, modelparams, single_expparams)
                cdf = np.cumsum(probabilities, axis=0)[..., 0]
                randnum = np.random.random((repeat, 1, modelparams.shape[0]))
                outcomes[:, :, idx_experiment] = all_outcomes[np.argmax(cdf > randnum, axis=1)]

        return outcomes[0, 0, 0] if repeat == 1 and expparams.shape[0] == 1 and modelparams.shape[0] == 1 else outcomes

    def likelihood(self, outcomes, modelparams, expparams):
        """
        :param np.ndarray outcomes: set of possible experimental outcomes (here [0,1])
        :param np.ndarray modelparams: Set of model parameter vectors to be
                updated.
        :param np.ndarray expparams: An experiment parameter array describing
            the experiment that was just performed.

        :param numpy.ndarray: likelihoods of obtaining outcome ``0`` from each
            set of model parameters and experiment parameters.

        """

        # this is just for array dimension matching
        if len(modelparams.shape) == 1:
            modelparams = modelparams[..., np.newaxis]

        # get units rights (all SI)
        t = expparams['t']  # us
        f_theta_1 = modelparams[:, 0] * 1e6  # MHz rad -> Hz rad, due to model scaling

        tau = t * 1e-6  # s

        # gamma in Hz rad / G (w units)

        h_0 = self._b_gauss

        theta_0 = self._gamma * h_0 * tau
        theta_1 = f_theta_1 * tau

        # Allocating first serves to make sure that a shape mismatch later
        # will cause an error.
        pr0 = np.zeros((modelparams.shape[0], expparams.shape[0]))

        l = 0.5 + 0.5 * (1 - 2 * self._c_sc2 * np.sin(theta_0 / 2) ** 2 * np.sin(theta_1 / 2.) ** 2)

        try:
            pr0[:, :] = 1 - l.transpose()
        except ValueError:
            try:
                pr0[:, :] = 1 - l[..., np.newaxis]
            except ValueError:
                pr0[:, :] = 1 - l[np.newaxis, ...]

        return self.pr0_to_likelihood_array(outcomes, pr0)


####################################################
##########  Heuristic  definitions       ##########
####################################################

class stdPGH(qi.Heuristic):
    """
    Function to extract the experimental time invoked from the equipment
	:param object updater: the prior distribution represented as an SMC updater
	:param string inv_field: the dtype-identified item of the expparams array indicating the frequency
	:param string t_field: the dtype-identified item of the expparams array indicating the free evolution time

	param np.ndarray: an array with the next experimental time chosen, along with the value of the frequency currently estimated

    """

    def __init__(self, updater, inv_field='x_', t_field='t',
                 inv_func=qi.expdesign.identity,
                 t_func=qi.expdesign.identity,
                 maxiters=10,
                 other_fields=None
                 ):
        super(stdPGH, self).__init__(updater)
        self._x_ = inv_field
        self._t = t_field
        self._inv_func = inv_func
        self._t_func = t_func
        self._maxiters = maxiters
        self._other_fields = other_fields if other_fields is not None else {}

    def __call__(self):
        idx_iter = 0
        while idx_iter < self._maxiters:

            # ESSENTIAL STEP sampling of two particles from the updated distribution
            x, xp = self._updater.sample(n=2)[:, np.newaxis, :]
            if self._updater.model.distance(x, xp) > 0:
                break
            else:
                idx_iter += 1

        # control to prevent sampling from a distribution with variance numerically 0
        if self._updater.model.distance(x, xp) == 0:
            raise RuntimeError("PGH did not find distinct particles in {} iterations.".format(self._maxiters))

        eps = np.empty((1,), dtype=self._updater.model.expparams_dtype)
        eps[self._x_] = self._inv_func(x)
        # ESSENTIAL STEP once successful extraction of two particles, their distance is inverted
        # this is the time returned for the following experiment
        # (_updater.model.distance  can be replaced by an np.abs for one parameter estimation)
        eps[self._t] = self._t_func(
            1 / self._updater.model.distance(x, xp))  # self._t_func(1 / self._updater.model.distance(x, xp))

        # the way the code is written, other fields are instead passed without modification
        for field, value in self._other_fields.items():
            eps[field] = value

        return eps


class T2RandPenalty_PGH(stdPGH):
    def __init__(self, updater, tau_thresh_rescale, inv_field='x_', t_field='t',
                 inv_func=qi.expdesign.identity,
                 t_func=qi.expdesign.identity,
                 maxiters=10,
                 other_fields=None, scale_f=2.0):
        """
        Apply a penalty on taus calculated from stdPGH and rescale them to lower values.
        :param tau_thresh_rescale: values above will be rescaled
        :param scale_f: controls the cut off tau. tau_cut = tau_thresh_rescale + scale_f * tau_thresh_rescale
                        = 2 -> tau_max = 3*tau_thresh_rescale
        """

        super().__init__(updater, inv_field, t_field, inv_func, t_func, maxiters, other_fields)
        self.tau_thresh_rescale = tau_thresh_rescale
        self.scale_f = scale_f

    def __call__(self):
        eps = super().__call__()
        tau = float(eps['t'][0])  # us

        if self.should_correct(tau):
            eps['t'] = self.apply_penalty_randomized(tau * 1e-6) * 1e6

        return eps

    def should_correct(self, taus_s):
        return True

    def should_correct_randomized(self, tau_s):

        if tau_s > self.tau_thresh_rescale:
            rand = np.random.rand()  # [0, 1)
            if rand > - np.exp(- tau_s / self.tau_thresh_rescale) + 1:  # -exp(-x)+1 < 1
                return True

        return False

    def apply_penalty(self, tau_s):

        if tau_s <= self.tau_thresh_rescale:
            return tau_s

        # rescale tau-t2* to 0... T2* (*scale_f)
        tau_corrected_s = self.tau_thresh_rescale + (1 - np.exp(
            - (tau_s / self.tau_thresh_rescale - 1))) * self.scale_f * self.tau_thresh_rescale  # 0 < -exp(-(x-1))+1 < 1

        return tau_corrected_s

    def apply_penalty_randomized(self, tau_s):
        # randomly multiply scale with [0, 1)
        # avoid that all very big taus get mapped to a single value

        save_scale_f = self.scale_f
        rand = np.random.rand()
        self.scale_f *= rand
        tau_corrected_s = self.apply_penalty(tau_s)
        self.scale_f = save_scale_f

        return tau_corrected_s


def identity(arg): return arg


class MultiPGH(qi.Heuristic):

    def __init__(self, updater, oplist=None, norm='Frobenius', inv_field='x_', t_field='t',
                 inv_func=identity,
                 t_func=identity,
                 maxiters=10,
                 other_fields=None
                 ):
        super().__init__(updater)
        self._updater = updater
        self._oplist = oplist
        self._norm = norm
        self._x_ = inv_field
        self._t = t_field
        self._inv_func = inv_func
        self._t_func = t_func
        self._maxiters = maxiters
        self._other_fields = other_fields if other_fields is not None else {}

    def __call__(self):
        idx_iter = 0
        while idx_iter < self._maxiters:

            x, xp = self._updater.sample(n=2)[:, np.newaxis, :]
            if self._updater.model.distance(x, xp) > 0:
                break
            else:
                idx_iter += 1

        if self._updater.model.distance(x, xp) == 0:
            raise RuntimeError("PGH did not find distinct particles in {} iterations. Pos1 {}, Pos2 {}".format(
                self._maxiters, x, xp))

        # print('Selected particles: #1 ' + repr(x) + ' #2 ' + repr(xp))

        eps = np.empty((1,), dtype=self._updater.model.expparams_dtype)
        #         print("eps dtypes >", self._updater.model.expparams_dtype)

        idx_iter = 0  # modified in order to cycle through particle parameters with different names
        #         print("self._x_ >", self._x_)

        for field_i in self._x_:
            #             print("field i", field_i)
            eps[field_i] = self._inv_func(x)[0][idx_iter]
            idx_iter += 1
        if self._oplist is None:  # Standard QInfer geom distance
            eps[self._t] = self._t_func(1 / self._updater.model.distance(x, xp))
        else:
            deltaH = getH(x, self._oplist) - getH(xp, self._oplist)
            if self._norm == 'Frobenius':
                eps[self._t] = 1 / np.linalg.norm(deltaH)  # Frobenius norm
            elif self._norm == 'MinSingVal':
                eps[self._t] = 1 / minsingvalnorm(deltaH)  # Min SingVal norm
            elif self._norm == 'SingVal':
                eps[self._t] = 1 / singvalnorm(deltaH)  # Max SingVal
            else:
                eps[self._t] = 1 / np.linalg.norm(deltaH)
                raise RuntimeError("Unknown Norm: using Frobenius norm instead")
        for field, value in self._other_fields.items():
            eps[field] = value

        return eps

    def norm_mean_projection(self, x, xp):
        return 0


class T2RandPenalty_MultiPGH(MultiPGH):
    def __init__(self, updater, tau_thresh_rescale, inv_field='x_', t_field='t',
                 inv_func=qi.expdesign.identity,
                 t_func=qi.expdesign.identity,
                 oplist=None,
                 maxiters=10,
                 other_fields=None, scale_f=2.0):
        """
        Apply a penalty on taus calculated from stdPGH and rescale them to lower values.
        :param tau_thresh_rescale: values above will be rescaled
        :param scale_f: controls the cut off tau. tau_cut = tau_thresh_rescale + scale_f * tau_thresh_rescale
                        = 2 -> tau_max = 3*tau_thresh_rescale
        """

        super().__init__(updater, oplist=oplist, inv_field=inv_field, t_field=t_field, inv_func=inv_func, t_func=t_func,
                         maxiters=maxiters, other_fields=other_fields)
        self.tau_thresh_rescale = tau_thresh_rescale
        self.scale_f = scale_f

    def __call__(self):
        eps = super().__call__()
        tau = float(eps['t'][0])  # us

        if self.should_correct(tau):
            eps['t'] = self.apply_penalty_randomized(tau * 1e-6) * 1e6

        return eps

    def should_correct(self, taus_s):
        return True

    def should_correct_randomized(self, tau_s):

        if tau_s > self.tau_thresh_rescale:
            rand = np.random.rand()  # [0, 1)
            if rand > - np.exp(- tau_s / self.tau_thresh_rescale) + 1:  # -exp(-x)+1 < 1
                return True

        return False

    def apply_penalty(self, tau_s):

        if tau_s <= self.tau_thresh_rescale:
            return tau_s

        # rescale tau-t2* to 0... T2* (*scale_f)
        tau_corrected_s = self.tau_thresh_rescale + (1 - np.exp(
            - (tau_s / self.tau_thresh_rescale - 1))) * self.scale_f * self.tau_thresh_rescale  # 0 < -exp(-(x-1))+1 < 1

        return tau_corrected_s

    def apply_penalty_randomized(self, tau_s):
        # randomly multiply scale with [0, 1)
        # avoid that all very big taus get mapped to a single value

        save_scale_f = self.scale_f
        rand = np.random.rand()
        self.scale_f *= rand
        tau_corrected_s = self.apply_penalty(tau_s)
        self.scale_f = save_scale_f

        return tau_corrected_s


class MultiHahnPGH(MultiPGH):

    def __init__(self, updater, B_gauss, oplist=None, norm='Frobenius', inv_field='x_', t_field='t',
                 inv_func=identity,
                 t_func=identity,
                 maxiters=10,
                 other_fields=None
                 ):
        super().__init__(updater)
        self._updater = updater
        self._oplist = oplist
        self._norm = norm
        self._x_ = inv_field
        self._t = t_field
        self._inv_func = inv_func
        self._t_func = t_func
        self._maxiters = maxiters
        self._other_fields = other_fields if other_fields is not None else {}
        self._b_gauss = B_gauss

    def __call__(self):
        eps = super().__call__()
        eps[self._t] = 10 * eps[self._t]

        # return eps
        return self.avoid_flat_likelihood(eps)

    def avoid_flat_likelihood(self, eps):
        # tau_period_us = 1 / self._b_gauss   # us, rough (empirically)
        tau_period_us = 1 / (1070.84 * self._b_gauss) * 1e6  # lamor precesion of 13-C
        tau = eps[self._t]
        n_periods = tau / tau_period_us

        is_flat_l = True
        while is_flat_l:
            if abs((tau % tau_period_us) - tau_period_us / 2) > tau_period_us / 4:
                tau += tau_period_us / 10
            else:
                is_flat_l = False

        eps[self._t] = tau

        return eps


class T2_Thresh_MultiHahnPGH(MultiHahnPGH):

    def __init__(self, updater, B_gauss, tau_thresh_us, oplist=None, norm='Frobenius', inv_field='x_', t_field='t',
                 inv_func=identity,
                 t_func=identity,
                 maxiters=10,
                 other_fields=None
                 ):
        super().__init__(updater, B_gauss)
        self._updater = updater
        self._oplist = oplist
        self._norm = norm
        self._x_ = inv_field
        self._t = t_field
        self._inv_func = inv_func
        self._t_func = t_func
        self._maxiters = maxiters
        self._other_fields = other_fields if other_fields is not None else {}
        self._b_gauss = B_gauss
        self._tau_thesh_us = tau_thresh_us

    def __call__(self):
        eps = super().__call__()
        # eps[self._t] = 100

        if eps[self._t] > self._tau_thesh_us:
            eps[self._t] = self._tau_thesh_us / 2

        # return eps
        return self.avoid_flat_likelihood(eps)


class T2RandPenalty_MultiHahnPGH(MultiHahnPGH):

    def __init__(self, updater, B_gauss, tau_thresh_rescale, oplist=None, norm='Frobenius', inv_field='x_', t_field='t',
                 inv_func=identity,
                 t_func=identity,
                 maxiters=10,
                 other_fields=None,
                 scale_f=2.0
                 ):
        super().__init__(updater, B_gauss)
        self._updater = updater
        self._oplist = oplist
        self._norm = norm
        self._x_ = inv_field
        self._t = t_field
        self._inv_func = inv_func
        self._t_func = t_func
        self._maxiters = maxiters
        self._other_fields = other_fields if other_fields is not None else {}
        self._b_gauss = B_gauss
        self.tau_thresh_rescale = tau_thresh_rescale
        self.scale_f = scale_f

    def __call__(self):
        eps = super().__call__()
        # eps[self._t] = 100

        tau = eps['t']

        if self.should_correct(tau):
            eps['t'] = self.apply_penalty_randomized(tau * 1e-6) * 1e6

        # return eps
        return self.avoid_flat_likelihood(eps)

    def should_correct(self, taus_s):
        return True

    def should_correct_randomized(self, tau_s):

        if tau_s > self.tau_thresh_rescale:
            rand = np.random.rand()  # [0, 1)
            if rand > - np.exp(- tau_s / self.tau_thresh_rescale) + 1:  # -exp(-x)+1 < 1
                return True

        return False

    def apply_penalty(self, tau_s):

        if tau_s <= self.tau_thresh_rescale:
            return tau_s

        # rescale tau-t2* to 0... T2* (*scale_f)
        tau_corrected_s = self.tau_thresh_rescale + (1 - np.exp(
            - (tau_s / self.tau_thresh_rescale - 1))) * self.scale_f * self.tau_thresh_rescale  # 0 < -exp(-(x-1))+1 < 1

        return tau_corrected_s

    def apply_penalty_randomized(self, tau_s):
        # randomly multiply scale with [0, 1)
        # avoid that all very big taus get mapped to a single value

        save_scale_f = self.scale_f
        rand = np.random.rand()
        self.scale_f *= rand
        tau_corrected_s = self.apply_penalty(tau_s)
        self.scale_f = save_scale_f

        return tau_corrected_s


####################################################
########## SMC updater  (from Qinfer)  ##############
####################################################


class basic_SMCUpdater(qi.Distribution):
    r"""
    Creates a new Sequential Monte carlo updater, using the algorithm of
    [GFWC12]_. Originated from Granade's QINFER package, but here we report a simplified version with essential features

    :param Model model: Model whose parameters are to be inferred.
    :param int n_particles: The number of particles to be used in the particle approximation.
    :param Distribution prior: A representation of the prior distribution.
    :param callable resampler: Specifies the resampling algorithm to be used. See :ref:`resamplers`
        for more details.
    :param float resample_thresh: Specifies the threshold for :math:`N_{\text{ess}}` to decide when to resample.
    """

    def __init__(self,
                 model, n_particles, prior,
                 resample_a=None, resampler=None, resample_thresh=0.5,
                 debug_resampling=False,
                 track_resampling_divergence=False,
                 zero_weight_policy='error', zero_weight_thresh=None
                 ):

        # Initialize zero-element arrays such that n_particles is always
        # a valid property.
        self.particle_locations = np.zeros((0, model.n_modelparams))
        self.particle_weights = np.zeros((0,))

        # Initialize metadata on resampling performance.
        self._resample_count = 0

        self.model = model
        self.prior = prior

        # check for how verbose the code should be
        self._debug_resampling = debug_resampling

        self.resample_thresh = resample_thresh

        self.resampler = basic_LiuWestResampler(a=resample_a)

        # Initialize properties to hold information about the history.
        self._just_resampled = False
        self._data_record = []
        self._normalization_record = []

        self._zero_weight_policy = zero_weight_policy
        self._zero_weight_thresh = (
            zero_weight_thresh
            if zero_weight_thresh is not None else
            10 * np.spacing(1)
        )

        ## PARTICLE INITIALIZATION ##
        self.reset(n_particles)

    ## PROPERTIES #############################################################

    @property
    def n_particles(self):
        """
        Returns the number of particles currently used in the sequential Monte
        Carlo approximation.

        :type: `int`
        """
        return self.particle_locations.shape[0]

    @property
    def just_resampled(self):
        """
        `True` if and only if there has been no data added since the last
        resampling, or if there has not yet been a resampling step.

        :type: `bool`
        """
        return self._just_resampled

    @property
    def n_ess(self):
        """
        Estimates the effective sample size (ESS) of the current distribution
        over model parameters.

        :type: `float`
        :return: The effective sample size, given by :math:`1/\sum_i w_i^2`.
        """
        return 1 / (np.sum(self.particle_weights ** 2))

    ## PRIVATE METHODS ########################################################

    def _maybe_resample(self):
        """
        Checks the resample threshold and conditionally resamples.
        """
        ess = self.n_ess
        if ess <= 10:
            warnings.warn(
                "Extremely small n_ess encountered ({}). "
                "Resampling is likely to fail. Consider adding particles, or "
                "resampling more often.".format(ess),
                ApproximationWarning
            )
        if ess < self.n_particles * self.resample_thresh:
            self.resample()
            pass

    ## INITIALIZATION METHODS #################################################

    def reset(self, n_particles=None, only_params=None, reset_weights=True):
        """
        Causes all particle locations and weights to be drawn fresh from the
        initial prior.

        :param int n_particles: Forces the size of the new particle set. If
            `None`, the size of the particle set is not changed.
        :param slice only_params: Resets only some of the parameters. Cannot
            be set if ``n_particles`` is also given.
        :param bool reset_weights: Resets the weights as well as the particles.
        """
        # Particles are stored using two arrays, particle_locations and
        # particle_weights, such that:
        #
        # particle_locations[idx_particle, idx_modelparam] is the idx_modelparam
        #     parameter of the particle idx_particle.
        # particle_weights[idx_particle] is the weight of the particle
        #     idx_particle.

        if n_particles is not None and only_params is not None:
            raise ValueError("Cannot set both n_particles and only_params.")

        if n_particles is None:
            n_particles = self.n_particles

        if reset_weights:
            self.particle_weights = np.ones((n_particles,)) / n_particles

        if only_params is None:
            sl = np.s_[:, :]
            # Might as well make a new array if we're resetting everything.
            self.particle_locations = np.zeros((n_particles, self.model.n_modelparams))
        else:
            sl = np.s_[:, only_params]

        self.particle_locations[sl] = self.prior.sample(n=n_particles)[sl]

        # Since this changes particle positions, we must recanonicalize.
        # self.particle_locations[sl] = self.model.canonicalize(self.particle_locations[sl])

    ## UPDATE METHODS #########################################################

    def hypothetical_update(self, outcomes, expparams, return_likelihood=False, return_normalization=False):
        """
        Produces the particle weights for the posterior of a hypothetical
        experiment.

        :param outcomes: Integer index of the outcome of the hypothetical
            experiment.
        :type outcomes: int or an ndarray of dtype int.
        :param numpy.ndarray expparams: Experiments to be used for the hypothetical
            updates.

        :type weights: ndarray, shape (n_outcomes, n_expparams, n_particles)
        :param weights: Weights assigned to each particle in the posterior
            distribution :math:`\Pr(\omega | d)`.
        """

        # It's "hypothetical", don't want to overwrite old weights yet!
        weights = self.particle_weights
        locs = self.particle_locations

        # Check if we have a single outcome or an array. If we only have one
        # outcome, wrap it in a one-index array.
        if not isinstance(outcomes, np.ndarray):
            outcomes = np.array([outcomes])

        # update the weights sans normalization
        # Rearrange so that likelihoods have shape (outcomes, experiments, models).
        # This makes the multiplication with weights (shape (models,)) make sense,
        # since NumPy broadcasting rules align on the right-most index.
        L = self.model.likelihood(outcomes, locs, expparams).transpose([0, 2, 1])
        hyp_weights = weights * L

        # Sum up the weights to find the renormalization scale.
        norm_scale = np.sum(hyp_weights, axis=2)[..., np.newaxis]

        # As a special case, check whether any entries of the norm_scale
        # are zero. If this happens, that implies that all of the weights are
        # zero--- that is, that the hypothicized outcome was impossible.
        # Conditioned on an impossible outcome, all of the weights should be
        # zero. To allow this to happen without causing a NaN to propagate,
        # we forcibly set the norm_scale to 1, so that the weights will
        # all remain zero.
        #
        # We don't actually want to propagate this out to the caller, however,
        # and so we save the "fixed" norm_scale to a new array.
        fixed_norm_scale = norm_scale.copy()
        fixed_norm_scale[np.abs(norm_scale) < np.spacing(1)] = 1

        # normalize
        norm_weights = hyp_weights / fixed_norm_scale
        # Note that newaxis is needed to align the two matrices.
        # This introduces a length-1 axis for the particle number,
        # so that the normalization is broadcast over all particles.
        if not return_likelihood:
            if not return_normalization:
                return norm_weights
            else:
                return norm_weights, norm_scale
        else:
            if not return_normalization:
                return norm_weights, L
            else:
                return norm_weights, L, norm_scale

    def update(self, outcome, expparams, check_for_resample=True):
        """
        Given an experiment and an outcome of that experiment, updates the
        posterior distribution to reflect knowledge of that experiment.

        After updating, resamples the posterior distribution if necessary.

        :param int outcome: Label for the outcome that was observed, as defined
            by the :class:`~qi.abstract_model.Model` instance under study.
        :param expparams: Parameters describing the experiment that was
            performed.
        :type expparams: :class:`~numpy.ndarray` of dtype given by the
            :attr:`~qi.abstract_model.Model.expparams_dtype` property
            of the underlying model
        :param bool check_for_resample: If :obj:`True`, after performing the
            update, the effective sample size condition will be checked and
            a resampling step may be performed.
        """

        # First, record the outcome.
        # TODO: record the experiment as well.
        self._data_record.append(outcome)
        self._just_resampled = False

        # Perform the update.
        weights, norm = self.hypothetical_update(outcome, expparams, return_normalization=True)

        # Check for negative weights before applying the update.
        if not np.all(weights >= 0):
            warnings.warn(
                "Negative weights occured in particle approximation. Smallest weight observed == {}. Clipping weights.".format(
                    np.min(weights)), ApproximationWarning)
            np.clip(weights, 0, 1, out=weights)

        # Next, check if we have caused the weights to go to zero, as can
        # happen if the likelihood is identically zero for all particles,
        # or if the previous clip step choked on a NaN.
        if np.sum(weights) <= self._zero_weight_thresh:
            if self._zero_weight_policy == 'ignore':
                pass
            elif self._zero_weight_policy == 'skip':
                return
            elif self._zero_weight_policy == 'warn':
                warnings.warn("All particle weights are zero. This will very likely fail quite badly.",
                              ApproximationWarning)
            elif self._zero_weight_policy == 'error':
                raise RuntimeError("All particle weights are zero.")
            elif self._zero_weight_policy == 'reset':
                warnings.warn("All particle weights are zero. Resetting from initial prior.", ApproximationWarning)
                self.reset()
            else:
                raise ValueError("Invalid zero-weight policy {} encountered.".format(self._zero_weight_policy))

        # Since hypothetical_update returns an array indexed by
        # [outcome, experiment, particle], we need to strip off those two
        # indices first.
        self.particle_weights[:] = weights[0, 0, :]

        # Record the normalization
        self._normalization_record.append(norm[0][0])

        # Update the particle locations according to the model's timestep.
        self.particle_locations = self.model.update_timestep(
            self.particle_locations, expparams
        )[:, :, 0]

        # Resample if needed.
        if check_for_resample:
            self._maybe_resample()

    ## RESAMPLING METHODS #####################################################

    def resample(self):
        """
        Forces the updater to perform a resampling step immediately.
        """

        if self.just_resampled:
            warnings.warn(
                "Resampling without additional data; this may not perform as "
                "desired.",
                ResamplerWarning
            )

        # Record that we have performed a resampling step.
        self._just_resampled = True
        self._resample_count += 1

        # Record the previous mean, cov if needed.
        if self._debug_resampling:
            old_mean = self.est_mean()
            old_cov = self.est_covariance_mtx()

        # Find the new particle locations according to the chosen resampling
        # algorithm.
        # We pass the model so that the resampler can check for validity of
        # newly placed particles.
        self.particle_weights, self.particle_locations = \
            self.resampler(self.model, self.particle_weights, self.particle_locations)

        # self.particle_locations[:, :] = self.model.canonicalize(self.particle_locations)

        # Instruct the model to clear its cache, demoting any errors to
        # warnings.
        try:
            self.model.clear_cache()
        except Exception as e:
            warnings.warn("Exception raised when clearing model cache: {}. Ignoring.".format(e))

    ## DISTRIBUTION CONTRACT ##################################################

    @property
    def n_rvs(self):
        """
        The number of random variables described by the posterior distribution.

        :type int:
        """
        return self._model.n_modelparams

    def sample(self, n=1):
        """
        Returns samples from the current posterior distribution.

        :param int n: The number of samples to draw.
        :return: The sampled model parameter vectors.
        :rtype: `~numpy.ndarray` of shape ``(n, updater.n_rvs)``.
        """
        cumsum_weights = np.cumsum(self.particle_weights)
        return self.particle_locations[np.minimum(cumsum_weights.searchsorted(
            np.random.random((n,)),
            side='right'
        ), len(cumsum_weights) - 1)]

    ## ESTIMATION METHODS #####################################################

    def est_mean(self):
        """
        Returns an estimate of the posterior mean model, given by the
        expectation value over the current SMC approximation of the posterior
        model distribution.

        :rtype: :class:`numpy.ndarray`, shape ``(n_modelparams,)``.
        :returns: An array containing the an estimate of the mean model vector.
        """
        return np.sum(
            # We need the particle index to be the rightmost index, so that
            # the two arrays align on the particle index as opposed to the
            # modelparam index.
            self.particle_weights * self.particle_locations.transpose([1, 0]),
            # The argument now has shape (n_modelparams, n_particles), so that
            # the sum should collapse the particle index, 1.
            axis=1
        )

    def est_covariance_mtx(self, corr=False):
        """
        Returns an estimate of the covariance of the current posterior model
        distribution, given by the covariance of the current SMC approximation.

        :param bool corr: If `True`, the covariance matrix is normalized
            by the outer product of the square root diagonal of the covariance matrix
            such that the correlation matrix is returned instead.

        :rtype: :class:`numpy.ndarray`, shape
            ``(n_modelparams, n_modelparams)``.
        :returns: An array containing the estimated covariance matrix.
        """

        cov = particle_covariance_mtx(
            self.particle_weights,
            self.particle_locations)

        if corr:
            dstd = np.sqrt(np.diag(cov))
            cov /= (np.outer(dstd, dstd))

        return cov


####################################################
########## Liu-West method (from Qinfer)   ##############
####################################################


class basic_LiuWestResampler(with_metaclass(ABCMeta, object)):
    r"""
    Creates a resampler instance that applies the algorithm of
    [LW01]_ to redistribute the particles.

    :param float a: Value of the parameter :math:`a` of the [LW01]_ algorithm
        to use in resampling.
    :param float h: Value of the parameter :math:`h` to use, or `None` to
        use that corresponding to :math:`a`.
    :param int maxiter: Maximum number of times to attempt to resample within
        the space of valid models before giving up.
    :param bool debug: Because the resampler can generate large amounts of
        debug information, nothing is output to the logger, even at DEBUG level,
        unless this flag is True.
    :param bool postselect: If `True`, ensures that models are valid by
        postselecting.
    :param float zero_cov_comp: Amount of covariance to be added to every
        parameter during resampling in the case that the estimated covariance
        has zero norm.
    :param callable kernel: Callable function ``kernel(*shape)`` that returns samples
        from a resampling distribution with mean 0 and variance 1.

    .. warning::

        The [LW01]_ algorithm preserves the first two moments of the
        distribution (in expectation over the random choices made by the
        resampler) if and only if :math:`a^2 + h^2 = 1`, as is set by the
        ``h=None`` keyword argument.
    """

    def __init__(self,
                 a=0.98, h=None, maxiter=1000, debug=False, postselect=True,
                 zero_cov_comp=1e-10,
                 kernel=np.random.randn
                 ):
        self.a = a  # Implicitly calls the property setter below to set _h.
        if h is not None:
            self._override_h = True
            self._h = h
        self._maxiter = maxiter
        self._debug = debug
        self._postselect = postselect
        self._zero_cov_comp = zero_cov_comp
        self._kernel = kernel

    _override_h = False

    ## PROPERTIES ##

    @property
    def a(self):
        return self._a

    @a.setter
    def a(self, new_a):
        self._a = new_a
        if not self._override_h:
            self._h = np.sqrt(1 - new_a ** 2)

    ## METHODS ##

    def __call__(self, model, particle_weights, particle_locations,
                 n_particles=None,
                 precomputed_mean=None, precomputed_cov=None
                 ):
        """
        Resample the particles according to algorithm given in
        [LW01]_.
        """

        # Give shorter names to weights and locations.
        w, l = particle_weights, particle_locations

        # Possibly recompute moments, if not provided.
        if precomputed_mean is None:
            mean = particle_meanfn(w, l, lambda x: x)
        else:
            mean = precomputed_mean
        if precomputed_cov is None:
            cov = particle_covariance_mtx(w, l)
        else:
            cov = precomputed_cov

        if n_particles is None:
            n_particles = l.shape[0]

        # parameters in the Liu and West algorithm
        a, h = self._a, self._h
        if la.norm(cov, 'fro') == 0:
            # The norm of the square root of S is literally zero, such that
            # the error estimated in the next step will not make sense.
            # We fix that by adding to the covariance a tiny bit of the
            # identity.
            warnings.warn(
                "Covariance has zero norm; adding in small covariance in "
                "resampler. Consider increasing n_particles to improve covariance "
                "estimates.",
                ResamplerWarning
            )
            cov = self._zero_cov_comp * np.eye(cov.shape[0])
        S, S_err = la.sqrtm(cov, disp=False)
        if not np.isfinite(S_err):
            raise ResamplerError(
                "Infinite error in computing the square root of the "
                "covariance matrix. Check that n_ess is not too small.")
        S = np.real(h * S)
        n_mp = l.shape[1]

        new_locs = np.empty((n_particles, n_mp))
        cumsum_weights = np.cumsum(w)

        idxs_to_resample = np.arange(n_particles, dtype=int)

        # Preallocate js and mus so that we don't have rapid allocation and
        # deallocation.
        js = np.empty(idxs_to_resample.shape, dtype=int)
        mus = np.empty(new_locs.shape, dtype=l.dtype)

        # Loop as long as there are any particles left to resample.
        n_iters = 0

        # Draw j with probability self.particle_weights[j].
        # We do this by drawing random variates uniformly on the interval
        # [0, 1], then see where they belong in the CDF.
        js[:] = cumsum_weights.searchsorted(
            np.random.random((idxs_to_resample.size,)),
            side='right'
        )

        while idxs_to_resample.size and n_iters < self._maxiter:
            # Keep track of how many iterations we used.
            n_iters += 1

            # Set mu_i to a x_j + (1 - a) mu.
            mus[...] = a * l[js, :] + (1 - a) * mean

            # Draw x_i from N(mu_i, S).
            new_locs[idxs_to_resample, :] = mus + np.dot(S, self._kernel(n_mp, mus.shape[0])).T

            # Now we remove from the list any valid models.
            # We write it out in a longer form than is strictly necessary so
            # that we can validate assertions as we go. This is helpful for
            # catching models that may not hold to the expected postconditions.
            resample_locs = new_locs[idxs_to_resample, :]
            if self._postselect:
                valid_mask = model.are_models_valid(resample_locs)
            else:
                valid_mask = np.ones((resample_locs.shape[0],), dtype=bool)

            assert valid_mask.ndim == 1, "are_models_valid returned tensor, expected vector."

            n_invalid = np.sum(np.logical_not(valid_mask))

            if self._debug and n_invalid > 0:
                logger.debug(
                    "LW resampler found {} invalid particles; repeating.".format(
                        n_invalid
                    )
                )

            assert (
                    (
                            len(valid_mask.shape) == 1
                            or len(valid_mask.shape) == 2 and valid_mask.shape[-1] == 1
                    ) and valid_mask.shape[0] == resample_locs.shape[0]
            ), (
                "are_models_valid returned wrong shape {} "
                "for input of shape {}."
            ).format(valid_mask.shape, resample_locs.shape)

            idxs_to_resample = idxs_to_resample[np.nonzero(np.logical_not(
                valid_mask
            ))[0]]

            # This may look a little weird, but it should delete the unused
            # elements of js, so that we don't need to reallocate.
            js = js[np.logical_not(valid_mask)]
            mus = mus[:idxs_to_resample.size, :]

        if idxs_to_resample.size:
            # We failed to force all models to be valid within maxiter attempts.
            # This means that we could be propagating out invalid models, and
            # so we should warn about that.
            warnings.warn((
                              "Liu-West resampling failed to find valid models for {} "
                              "particles within {} iterations."
                          ).format(idxs_to_resample.size, self._maxiter), ResamplerWarning)

        if self._debug:
            logger.debug("LW resampling completed in {} iterations.".format(n_iters))

        # Now we reset the weights to be uniform, letting the density of
        # particles represent the information that used to be stored in the
        # weights. This is done by SMCUpdater, and so we simply need to return
        # the new locations here.
        return np.ones((w.shape[0],)) / w.shape[0], new_locs


####################################################
# Extensions using qinfer, later added to simplelib
####################################################
class AsymmetricLossModel(qi.DerivedModel, qi.FiniteOutcomeModel):
    """
    Model representing the case in which a two-outcome model is subject
    to asymmetric loss, such that

        Pr(1 | modelparams; expparams) = η Pr(1 | modelparams; expparams, no loss),
        Pr(0 | modelparams; expparams)
            = Pr(0 | modelparams; expparams, no loss) + (1 - η) Pr(1 | modelparams; expparams, no loss)
            = 1 - Pr(1 | modelparams; expparams, no loss) + (1 - η) Pr(1 | modelparams; expparams, no loss)
            = 1 - η Pr(1 | modelparams; expparams, no loss)
            = 1 - Pr(1 | modelparams; expparams).

    This model considers η to be *known* and given at initialization time, rather than as a model parameter to be
    estimated.
    """

    def __init__(self, underlying_model, eta=1.0):
        super(AsymmetricLossModel, self).__init__(underlying_model)
        self._eta = float(eta)

        if not (underlying_model.is_n_outcomes_constant and underlying_model.n_outcomes(None) == 2):
            raise ValueError("Decorated model must be a two-outcome model.")

    def likelihood(self, outcomes, modelparams, expparams):
        # By calling the superclass implementation, we can consolidate
        # call counting there.
        super(AsymmetricLossModel, self).likelihood(outcomes, modelparams, expparams)

        pr1 = self._eta * self.underlying_model.likelihood(
            np.array([1], dtype='uint'),
            modelparams,
            expparams
        )[0, :, :]

        # Now we concatenate over outcomes.
        L = qi.FiniteOutcomeModel.pr0_to_likelihood_array(outcomes, 1 - pr1)
        assert not np.any(np.isnan(L))
        return L


class NoisyDataPrecModel():
    r"""

    """

    ## INITIALIZER ##

    def __init__(self, freq_min=0.0, freq_max=1.0, n_particles=1000, noise="Absent", eta=1.0):

        base_model = ExpDecoKnownPrecessionModel(min_freq=freq_min)

        if noise is "Absent":
            self.model = base_model
        elif noise is "Binomial":
            self.model = qi.BinomialModel(base_model)
        elif noise is "Unbalanced":
            self.model = qi.BinomialModel(AsymmetricLossModel(base_model, eta=eta))

        self.n_particles = n_particles

        self.freq_min = freq_min
        self.freq_max = freq_max

        self.fft_est = None
        self.bay_est = None

    def classfft_prec(self, data):

        [ft_freq, spectrum, est_omega, xlimit, err_omega, norm] = fft_prec(data)

        self.fft_est = est_omega

        return [ft_freq, spectrum, self.fft_est]

    def est_prec(self, data, n_shots=1, n_experiments=50, resample_a=None, resample_thresh=0.5, verbose=False,
                 TBC=False, use_heuristic="PGH", heuristic_ratio=1., heuristic_root=1):
        """
        Class for (decohered) Ramsey fringe learning

        data: set of [time, likelihood] data, or "None" if you want simulation
        n_experiments: number of experiments to be performed before interruption
        resample_a: provides an indicator of how much the Liu-West resampler is allowed to "move" the distribution in case of resampling
            >> higher "a" indicatively leads to slower learning, but smoother learning
        resample_thresh: provides an indicator of how frequently to call resampling.
            >> higher the "thresh" value, more frequently resampling events will occur, indicatively leading to faster but less smooth learning
        TBC: continues the learning from a previous prior instead of wiping it and restarting
        """

        if TBC:
            print("Continuing from...")
            print(self.prior)

        else:
            self.prior = qi.UniformDistribution([self.freq_min, self.freq_max])
            self.updater = qi.SMCUpdater(self.model, self.n_particles, self.prior, resample_a=resample_a,
                                         resample_thresh=resample_thresh)
            if use_heuristic is "PGH":
                self.heuristic = stdPGH(self.updater, inv_field='w_')
            elif use_heuristic is "rootPGH":
                self.heuristic = rootPGH(self.updater, root=1, inv_field='w_')
            else:
                self.heuristic = stepwise_heuristic(self.updater, n_shots=1, ts=data[0])

        if data is None:
            self.sim = True
            if verbose: print("Simulated run with")
            true_params = self.prior.sample()

        elif len(data) is 1:
            self.sim = True
            if verbose: print("Simulated run with")
            true_params = data

        else:
            self.sim = False
            if verbose: print("Experimental run with")
            if self.fft_est != None:
                true_params = np.array([[self.fft_est]])
            else:
                true_params = np.array([[self.classfft_prec(data)[2]]])

                if (true_params[0][0] >= self.prior._ranges[0][1] or true_params[0][0] <= self.prior._ranges[0][0]):
                    warnings.warn(
                        "Chosen prior appears incompatible with FFT analysis, consider modifying the range of the prior distribution")

            mydata = adjust_data_qi(data, n_shots=n_shots, omegabounds=[self.freq_min, self.freq_max])

        if verbose: print("(estimated) value: ", true_params)

        track_eval = []
        track_loss = np.empty(n_experiments)
        track_cov = np.empty(n_experiments)
        track_time = np.empty(n_experiments)
        track_pgh_time = np.empty(n_experiments)
        track_acctime = np.zeros(n_experiments)

        for idx_experiment in range(n_experiments):
            experiment = self.heuristic()
            experiment[0][0] = heuristic_ratio * experiment[0][0]
            track_pgh_time[idx_experiment] = deepcopy(experiment[0][0])

            if verbose: print("Proposed experiment ", experiment)

            if self.sim:
                datum = self.model.simulate_experiment(true_params, experiment)
            else:
                [datum, newtime] = retrieve_experiment(mydata, experiment)
                track_time[idx_experiment] = newtime
                experiment[0][0] = newtime
                if verbose: print("Found experiment ", experiment)

            track_acctime[idx_experiment] = track_acctime[max(0, idx_experiment - 1)] + experiment[0][0]

            if verbose: print("Datum", datum)

            self.updater.update(datum, experiment)

            track_eval.append(self.updater.est_mean()[0])
            if verbose: print("New eval ", track_eval[idx_experiment])
            new_loss = eval_loss(self.model, self.updater.est_mean(), true_params)
            track_loss[idx_experiment] = new_loss[0]
            if verbose: print("New loss: ", new_loss[0])

            track_cov[idx_experiment] = np.sqrt(self.updater.est_covariance_mtx())
            if verbose: print("New cov: ", track_cov[idx_experiment])

        if verbose: print('\nFinal estimate is: ' + str(self.updater.est_mean()[0]))
        if verbose: print('##########################\n')

        return [np.array(track_eval), track_loss, track_cov, track_acctime, track_pgh_time, track_time]


##################################################
# Ulm extensions (Timo)
##################################################


class NoisyGaussianExpDecoKnownPrecessionModel(ExpDecoKnownPrecessionModel):
    def __init__(self, min_freq=0.0, max_freq=1.0, invT2=0, c_eff=1, n_rep=1e6):
        super().__init__(min_freq, invT2)

        self.c_eff = c_eff  # readout efficiency parameter c
        self.n_rep = n_rep  # number of experimental repetitions

    def likelihood(self, outcomes, modelparams, expparams, noisy=False, res_no_noise=None):

        p = super().likelihood(outcomes, modelparams, expparams)
        if not noisy:
            return p

        if p.shape != (2, 1, 1):
            raise NotImplementedError("NoisyGaussian only implemented for 1d model. Shape: {}".format(p.shape))
        z = p[0, 0, 0]  # value of interet
        z, z_real = self.add_noise(z)
        if type(res_no_noise) is list:
            res_no_noise.append(z_real)

        # prepare shape for output
        pr0 = np.zeros((modelparams.shape[0], expparams.shape[0]))
        pr0[:, :] = z

        return self.pr0_to_likelihood_array(outcomes, pr0)

    def add_noise(self, z):
        import random
        noisy_z = z + np.random.normal(loc=0, scale=1. / np.sqrt(4 * self.c_eff ** 2 * self.n_rep))  # Degen 17 (eqn 37)

        return noisy_z, z

    def sample(self, z, n_samples=1e3):
        return np.random.normal(loc=z, scale=1. / np.sqrt(4 * self.c_eff ** 2 * self.n_rep), size=int(n_samples))


class NoisyPoissonianExpDecoKnownPrecessionModel(ExpDecoKnownPrecessionModel):
    def __init__(self, min_freq=0.0, max_freq=1.0, invT2=0, cts_0=0.04, cts_1=0.03, n_rep=1e6):
        """
        :param min_freq:
        :param max_freq:
        :param invT2:
        :param cts_0: counts per laser shot in |0>
        :param cts_1: counts per laser shot in |1>
        :param n_rep: (=n_sweeps) number of Ramsey reptitions per epoch
        """
        super().__init__(min_freq, invT2)

        self.cts_0 = cts_0
        self.cts_1 = cts_1
        self.n_rep = n_rep  # number of experimental repetitions

    def likelihood(self, outcomes, modelparams, expparams, noisy=False, res_no_noise=None):

        p = super().likelihood(outcomes, modelparams, expparams)
        if not noisy:
            return p

        if p.shape != (2, 1, 1):
            raise NotImplementedError("NoisyGaussian only implemented for 1d model. Shape: {}".format(p.shape))
        z = p[0, 0, 0]  # value of interet
        z, z_real = self.add_noise(z)
        if type(res_no_noise) is list:
            res_no_noise.append(z_real)

        # prepare shape for output
        pr0 = np.zeros((modelparams.shape[0], expparams.shape[0]))
        pr0[:, :] = z

        return self.pr0_to_likelihood_array(outcomes, pr0)

    def add_noise(self, z):
        # model z as single Poissonian distribution
        # assumes that quantum projection noise is much smaller than shot noise!
        # first noise in photons
        noisy_z_phot = self.sample(z, n_samples=1, as_photons=True)  # all repetitions
        noisy_z = self.photons_to_z(noisy_z_phot)

        return noisy_z, z

    def photons_to_z_lin_interp(self, z_phot):
        from scipy.interpolate import interp1d
        m = interp1d([self.n_rep * self.cts_0, self.n_rep * self.cts_1], [0, 1], fill_value='extrapolate')

        return m(z_phot)

    def photons_to_z_prob_fract(self, z_phot_int):
        from scipy.stats import poisson

        # method as in labbook 2019/9/26
        lamda_0 = self.n_rep * self.cts_0
        lamda_1 = self.n_rep * self.cts_1
        p_0 = np.asarray(poisson.pmf(z_phot_int, lamda_0))
        p_1 = np.asarray(poisson.pmf(z_phot_int, lamda_1))

        # numpy construction of output array
        z_arr = np.zeros(len(z_phot_int), dtype=float)
        z_0 = (p_0 > p_1).astype(int)  # array is one where p_0 > p_1
        z_arr += z_0 * 0.5 * p_1 / p_0
        z_1 = (p_0 <= p_1).astype(int)
        z_arr += z_1 * (1 - 0.5 * p_0 / p_1)

        return z_arr

    def photons_to_z_maxlike(self, z_phot_int, n_bin=50):
        from scipy.stats import poisson

        z_res = []
        for z_phot_int_i in z_phot_int:

            z_phot_check = np.asarray(z_phot_int_i, dtype=int)
            if not np.allclose(z_phot_check, z_phot_int_i):
                raise RuntimeError("Got non-integer photon number {}.".format(z_phot_int_i))

            p_max = 0
            z = 0
            for n_phot in np.linspace(self.n_rep * self.cts_1, self.n_rep * self.cts_0, n_bin):
                p_i = poisson.pmf(z_phot_int_i, n_phot)
                if p_i > p_max:
                    p_max = p_i
                    z = (n_phot / self.n_rep - self.cts_0) / (self.cts_1 - self.cts_0)

            z_res.append(z)

        return z_res

    def photons_to_z(self, z_phot, mode='linear'):

        z_phot_int = np.asarray(z_phot, dtype=int)
        if not np.allclose(z_phot, z_phot_int):
            raise RuntimeError(
                "Got non-integer photon number {}. Rel dif {}".format(z_phot, (z_phot - z_phot_int) / z_phot))

        if mode == 'linear':
            return self.photons_to_z_lin_interp(z_phot_int)
        elif mode == 'probfrac':
            return self.photons_to_z_prob_fract(z_phot_int)
        elif mode == 'maxlike':
            return self.photons_to_z_maxlike(z_phot_int)
        else:
            raise ValueError("Unknown conversion mode: {}".format(mode))

    def sample(self, z, n_samples=1e3, as_photons=False):
        z_phot = self.n_rep * (z * self.cts_1 + (1 - z) * self.cts_0)  # expectation value in photons
        z_phot = np.random.poisson(lam=z_phot, size=int(n_samples))

        if as_photons:
            z_ret = z_phot
        else:
            z_ret = self.photons_to_z(z_phot)

        return z_ret


# NOT WORKING, see Andrea's nv_sensing_lib
class NoisyExpDecoKnownPrecessionModel():

    def __init__(self, min_freq=0.0, max_freq=1.0, invT2=0, noise="Absent", eta=1.0):

        # super().__init__(min_freq, invT2)
        base_model = ExpDecoKnownPrecessionModel(min_freq=min_freq, invT2=invT2)

        if noise is "Absent":
            self.model = base_model
        elif noise is "Binomial":
            self.model = qi.BinomialModel(base_model)
        elif noise is "Unbalanced":
            self.model = qi.BinomialModel(AsymmetricLossModel(base_model, eta=eta))

    def get_model(self):
        return self.model


