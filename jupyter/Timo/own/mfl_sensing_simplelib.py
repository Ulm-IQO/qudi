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
        return (radfreq / (2*PI) / gamma * 1000)[0]
    else:
        B = list(lambda fq: fq / (2*PI) / gamma * 1000, fq in radfreq)
        return B

def B_to_radfreq(B):
    # radfreq: in rad*MHz
    # B: in uT
    B = np.array([B])
    if len(B) is 1:
        return (B * 2*PI * gamma / 1000)[0]
    else:
        radfreq = list(lambda eachB: eachB * 2*PI * gamma / 1000, eachB in B)
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
        
        
        
def particle_covariance_mtx(weights,locations):
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
        # of xs.
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
        warnings.warn('Numerical error in covariance estimation causing positive semidefinite violation.', ApproximationWarning)

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
    return gamma / ( 2*PI* ( (x-x0)**2 + (gamma/2)**2 )  ) / norm_factor 

def Gaussian(x, mean = 0., sigma = 1.):
    """
    Defines a Gaussian function with parameters mean, sigma 
    """
    return norm.pdf(x, loc = mean, scale = sigma)
    


####################################################
########## Additional Data Analysis ##################
####################################################    

   
    
def DampedOscill(t, Omega, invT2):
    y = 1- np.exp(-t*invT2) * np.cos(Omega * t / 2) ** 2 - 0.5*(1-np.exp(-t*invT2))
    return(y)

    
    
  
  
####################################################
########## Model  definitions     ##################
#################################################### 

        
        
       
 
class ExpDecoKnownPrecessionModel():
    r"""
    Model that simulates a sinusoidal Precession in magnetic field, 
    imposing a (known) decoherence as a user-defined parameter
    
    :param float min_freq: Impose a minimum frequency (often 0 to avoid degeneracies in the problem)
    :param float invT2: If a dephasing time T_2* for the system is known, user can input its inverse here
    """
    
    ## INITIALIZER ##

    def __init__(self, min_freq=0, invT2 = 0.):
        super(ExpDecoKnownPrecessionModel, self).__init__()

        self._min_freq = min_freq
        self._invT2 = invT2
        
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
        return np.tile(modelparams, (expparams.shape[0],1,1)).transpose((1,2,0))   


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
        
    
        
    def simulate_experiment(self, modelparams, expparams, repeat=1):
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
            all_outcomes = np.array([0,1])
            probabilities = self.likelihood(all_outcomes, modelparams, expparams)
            cdf = np.cumsum(probabilities, axis=0)
            randnum = np.random.random((repeat, 1, modelparams.shape[0], expparams.shape[0]))
            outcome_idxs = all_outcomes[np.argmax(cdf > randnum, axis=1)]
            outcomes = all_outcomes[outcome_idxs]
        else:
            # Loop over each experiment, sadly.
            # Assume all domains have the same dtype
            assert(self.are_expparam_dtypes_consistent(expparams))
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
        dw = modelparams[:,0]
        
        # ESSENTIAL STEP > the likelihoods (i.e. cosines with a damping exp term) are evaluated for all particles
        pr0 = np.zeros((modelparams.shape[0], expparams.shape[0]))
        pr0[:, :] = (np.array([np.exp(-t*self._invT2) * (np.cos(t * dw / 2) ** 2) + 0.5*(1-np.exp(-t*self._invT2))])).T
        
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
        eps[self._t]  = self._t_func(1 / self._updater.model.distance(x, xp)) #self._t_func(1 / self._updater.model.distance(x, xp))
        
        # the way the code is written, other fields are instead passed without modification
        for field, value in self._other_fields.items():
            eps[field] = value
        
        return eps
        
        

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
        return 1 / (np.sum(self.particle_weights**2))

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
            warnings.warn("Negative weights occured in particle approximation. Smallest weight observed == {}. Clipping weights.".format(np.min(weights)), ApproximationWarning)
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
                warnings.warn("All particle weights are zero. This will very likely fail quite badly.", ApproximationWarning)
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
        self.particle_weights[:] = weights[0,0,:]
        
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
        self.a = a # Implicitly calls the property setter below to set _h.
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
            self._h = np.sqrt(1 - new_a**2)

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
            mus[...] = a * l[js,:] + (1 - a) * mean
            
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