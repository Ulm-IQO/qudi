# -*- coding: utf-8 -*-
"""
This file contains the QuDi task runner module.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (C) 2016 Jochen Scheuer jochen.scheuer@uni-ulm.de
"""

import numpy as np

from scipy.ndimage import filters

############################################################################
#                                                                          #
#                             General methods                              #
#                                                                          #
############################################################################

def _substitute_parameter(self, parameters=None, update_parameters=None):
    """ This method substitutes all parameters handed in the
    update_parameters object in an initial set of parameters.

    @param object parameters: lmfit.parameter.Parameters object, initial
                              parameters
    @param object update_parameters: lmfit.parameter.Parameters object, new
                                     parameters

    @return object parameters: lmfit.parameter.Parameters object, new object
                               with substituted parameters
    """

    for para in update_parameters:
        #first check if completely new parameter, which is added in the else
        if para in parameters:
            #store value because when max,min is set the value is overwritten
            store_value = parameters[para].value

            # the Parameter object changes the value, min and max when the
            # value is called therefore the parameters have to be saved from
            # the reseted Parameter object therefore the Parameters have to be
            # saved also here

            para_temp = update_parameters
            if para_temp[para].value is not None:
                value_new = True
                value_value = para_temp[para].value
            else:
                value_new = False

            para_temp = update_parameters
            if para_temp[para].min is not None:
                min_new = True
                min_value = para_temp[para].min
            else:
                min_new = False

            para_temp = update_parameters
            if para_temp[para].max is not None:
                max_new = True
                max_value = para_temp[para].max
            else:
                max_new = False

            # vary is set by default to True
            parameters[para].vary = update_parameters[para].vary

            # if the min, max and expression and value are new overwrite
            # them here

            if min_new:
                parameters[para].min = update_parameters[para].min

            if max_new:
                parameters[para].max = update_parameters[para].max

            if update_parameters[para].expr is not None:
                parameters[para].expr = update_parameters[para].expr

            if value_new:
                parameters[para].value = value_value

            # if the min or max are changed they overwrite the value
            # therefore here the values have to be reseted to the initial
            # value also when no new value was set in the beginning

            if min_new:
                if parameters[para].value is not None:
                    # in case the value is 0, devision by 0 has to be avoided
                    if parameters[para].value < 1e-12:
                        if abs((min_value+1.)/(parameters[para].value+1.)-1.) < 1e-12:
                            parameters[para].value = store_value
                    else:
                        if abs(min_value/parameters[para].value-1.)<1e-12:
                            parameters[para].value = store_value
            if max_new:
                # in case the value is 0, devision by 0 has to be avoided
                if parameters[para].value is not None:
                    if parameters[para].value < 1e-12:
                        if abs((max_value+1.)/(parameters[para].value+1.)-1.) < 1e-12:
                            parameters[para].value=store_value
                    else:
                        if abs(max_value/parameters[para].value-1.) < 1e-12:
                            parameters[para].value=store_value

            # check if the suggested value or the value in parameters is
            # smaller/bigger than min/max values and set then the value to
            # min or max

            if min_new:
                if parameters[para].value is not None:
                    if parameters[para].value<min_value:
                        parameters[para].value=min_value

            if max_new:
                if parameters[para].value is not None:
                    if parameters[para].value>max_value:
                        parameters[para].value=max_value
        else:
            #if parameter is new add here
            parameters.add(para)

    return parameters


def create_fit_string(self, result, model, units=dict(), decimal_digits_value_given=None,
                      decimal_digits_err_given=None):
    """ This method can produces a well readable string from the results of a fitted model.
    If units is not given or one unit missing there will be no unit in string.
    If decimal_digits_value_given is not provided it will be set to precision of error and digits
    of error will be set to 1.

    @param lmfit object result: the fitting result
    @param lmfit object model: the corresponding model
    @param dict units: units for parameters of model if not given all units are set to "arb. u."
    @param int decimal_digits_err_given: (optional) number of decimals displayed in output for error
    @param int decimal_digits_value_given: (optional) number of decimals displayed in output for value

    @return str fit_result: readable string
    """
    # TODO: Add multiplicator
    # TODO: Add decimal dict
    # TODO: Add sensible output such that e only multiple of 3 and err and value have same exponent

    fit_result = ''
    for variable in model.param_names:
        # check order of number
        exponent_error = int("{:e}".format(result.params[variable].stderr)[-3:])
        exponent_value = int("{:e}".format(result.params[variable].value)[-3:])
        if decimal_digits_value_given is None:
            decimal_digits_value = int(exponent_value-exponent_error)+1
        if decimal_digits_err_given is None:
            decimal_digits_err = 1
        try:
            fit_result += ("{0} [{1}] : {2} ± {3}\n".format(str(variable),
                                                            units[variable],
                                                            "{0:.{1}e}".format(
                                                                result.params[variable].value,
                                                                decimal_digits_value),
                                                            "{0:.{1}e}".format(
                                                                result.params[variable].stderr,
                                                                decimal_digits_err)))
        except:
            # self.logMsg('No unit given for parameter {}, setting unit '
            #             'to empty string'.format(variable),
            #             msgType='warning')
            fit_result += ("{0} [{1}] : {2} ± {3}\n".format(str(variable),
                                                            "arb. u.",
                                                            "{0:.{1}e}".format(
                                                                result.params[variable].value,
                                                                decimal_digits_value),
                                                            "{0:.{1}e}".format(
                                                                result.params[variable].stderr,
                                                                decimal_digits_err)))
    return fit_result


def _search_end_of_dip(self, direction, data, peak_arg, start_arg, end_arg, sigma_threshold, minimal_threshold, make_prints):
    """
    data has to be offset leveled such that offset is substracted
    """
    absolute_min  = data[peak_arg]

    if direction == 'left':
        mult = -1
        sigma_arg=start_arg
    elif direction == 'right':
        mult = +1
        sigma_arg=end_arg
    else:
        print('No valid direction in search end of peak')
    ii=0

    #if the minimum is at the end set this as boarder
    if (peak_arg != start_arg and direction=='left' or
        peak_arg != end_arg   and direction=='right'):
        while True:
            # if no minimum can be found decrease threshold
            if ((peak_arg-ii<start_arg and direction == 'left') or
                (peak_arg+ii>end_arg   and direction=='right')):
                sigma_threshold*=0.9
                ii=0
                if make_prints:
                    print('h1 sigma_threshold',sigma_threshold)

            #if the dip is always over threshold the end is as
            # set before
            if abs(sigma_threshold/absolute_min)<abs(minimal_threshold):
                if make_prints:
                    print('h2')
                break

             #check if value was changed and search is finished
            if ((sigma_arg == start_arg and direction == 'left') or
                (sigma_arg == end_arg   and direction=='right')):
                # check if if value is lower as threshold this is the
                # searched value
                if make_prints:
                    print('h3')
                if abs(data[peak_arg+(mult*ii)])<abs(sigma_threshold):
                    # value lower than threshold found - left end found
                    sigma_arg=peak_arg+(mult*ii)
                    if make_prints:
                        print('h4')
                    break
            ii+=1

    # in this case the value is the last index and should be search set
    # as right argument
    else:
        if make_prints:
            print('neu h10')
        sigma_arg=peak_arg

    return sigma_threshold,sigma_arg


def _search_double_dip(self, x_axis, data, threshold_fraction=0.3, minimal_threshold=0.01, sigma_threshold_fraction=0.3, make_prints=False):
    """ This method searches for a double dip. There are three values which can be set in order to adjust
    the search. A threshold which defines when  a minimum is a dip,
    this threshold is then lowered if no dip can be found until the
    minimal threshold which sets the absolute boarder and a
    sigma_threshold_fraction which defines when the

    @param array x_axis: x values
    @param array data: value of each data point corresponding to
                        x values
    @param float threshold_fraction: x values
    @param float minimal_threshold: x values
    @param float sigma_threshold_fraction: x values


    @return int error: error code (0:OK, -1:error)
    @return int sigma0_argleft: index of left side of 1st peak
    @return int dip0_arg: index of max of 1st peak
    @return int sigma0_argright: index of right side of 1st peak
    @return int sigma1_argleft: index of left side of 2nd peak
    @return int dip1_arg: index of max side of 2nd peak
    @return int sigma1_argright: index of right side of 2nd peak
    """

    if sigma_threshold_fraction is None:
        sigma_threshold_fraction=threshold_fraction

    error=0

    #first search for absolute minimum
    absolute_min=data.min()
    absolute_argmin=data.argmin()

    #adjust thresholds
    threshold=threshold_fraction*absolute_min
    sigma_threshold=sigma_threshold_fraction*absolute_min

    dip0_arg = absolute_argmin

    # ====== search for the left end of the dip ======

    sigma_threshold, sigma0_argleft = self._search_end_of_dip(
                             direction='left',
                             data=data,
                             peak_arg = absolute_argmin,
                             start_arg = 0,
                             end_arg = len(data)-1,
                             sigma_threshold = sigma_threshold,
                             minimal_threshold = minimal_threshold,
                             make_prints= make_prints)

    if make_prints:
        print('Left sigma of main peak: ',x_axis[sigma0_argleft])

    # ====== search for the right end of the dip ======
    # reset sigma_threshold

    sigma_threshold, sigma0_argright = self._search_end_of_dip(
                             direction='right',
                             data=data,
                             peak_arg = absolute_argmin,
                             start_arg = 0,
                             end_arg = len(data)-1,
                             sigma_threshold = sigma_threshold_fraction*absolute_min,
                             minimal_threshold = minimal_threshold,
                             make_prints= make_prints)

    if make_prints:
        print('Right sigma of main peak: ',x_axis[sigma0_argright])

    # ======== search for second lorentzian dip ========
    left_index=int(0)
    right_index=len(x_axis)-1

    mid_index_left=sigma0_argleft
    mid_index_right=sigma0_argright

    # if main first dip covers the whole left side search on the right
    # side only
    if mid_index_left==left_index:
        if make_prints:
            print('h11', left_index,mid_index_left,mid_index_right,right_index)
        #if one dip is within the second they have to be set to one
        if mid_index_right==right_index:
            dip1_arg=dip0_arg
        else:
            dip1_arg=data[mid_index_right:right_index].argmin()+mid_index_right

    #if main first dip covers the whole right side search on the left
    # side only
    elif mid_index_right==right_index:
        if make_prints:
            print('h12')
        #if one dip is within the second they have to be set to one
        if mid_index_left==left_index:
            dip1_arg=dip0_arg
        else:
            dip1_arg=data[left_index:mid_index_left].argmin()

    # search for peak left and right of the dip
    else:
        while True:
            #set search area excluding the first dip
            left_min=data[left_index:mid_index_left].min()
            left_argmin=data[left_index:mid_index_left].argmin()
            right_min=data[mid_index_right:right_index].min()
            right_argmin=data[mid_index_right:right_index].argmin()

            if abs(left_min) > abs(threshold) and \
               abs(left_min) > abs(right_min):
                if make_prints:
                    print('h13')
                # there is a minimum on the left side which is higher
                # than the minimum on the right side
                dip1_arg = left_argmin+left_index
                break
            elif abs(right_min)>abs(threshold):
                # there is a minimum on the right side which is higher
                # than on left side
                dip1_arg=right_argmin+mid_index_right
                if make_prints:
                    print('h14')
                break
            else:
                # no minimum at all over threshold so lowering threshold
                #  and resetting search area
                threshold*=0.9
                left_index=int(0)
                right_index=len(x_axis)-1
                mid_index_left=sigma0_argleft
                mid_index_right=sigma0_argright
                if make_prints:
                    print('h15')
                #if no second dip can be found set both to same value
                if abs(threshold/absolute_min)<abs(minimal_threshold):
                    if make_prints:
                        print('h16')
                    self.logMsg('threshold to minimum ratio was too '
                                'small to estimate two minima. So both '
                                'are set to the same value',
                                msgType='warning')
                    error=-1
                    dip1_arg=dip0_arg
                    break

    # if the dip is exactly at one of the boarders that means
    # the dips are most probably overlapping
    if dip1_arg == sigma0_argleft or dip1_arg == sigma0_argright:
        #print('Dips are overlapping')
        distance_left  = abs(dip0_arg - sigma0_argleft)
        distance_right = abs(dip0_arg - sigma0_argright)
        sigma1_argleft = sigma0_argleft
        sigma1_argright = sigma0_argright
        if distance_left > distance_right:
            dip1_arg = dip0_arg - abs(distance_left-distance_right)
        elif distance_left < distance_right:
            dip1_arg = dip0_arg + abs(distance_left-distance_right)
        else:
            dip1_arg = dip0_arg
        #print(distance_left,distance_right,dip1_arg)
    else:
        # if the peaks are not overlapping search for left and right
        # boarder of the dip

        # ====== search for the right end of the dip ======
        sigma_threshold, sigma1_argleft = self._search_end_of_dip(
                                 direction='left',
                                 data=data,
                                 peak_arg = dip1_arg,
                                 start_arg = 0,
                                 end_arg = len(data)-1,
                                 sigma_threshold = sigma_threshold_fraction*absolute_min,
                                 minimal_threshold = minimal_threshold,
                                 make_prints= make_prints)

        # ====== search for the right end of the dip ======
        sigma_threshold, sigma1_argright = self._search_end_of_dip(
                                 direction='right',
                                 data=data,
                                 peak_arg = dip1_arg,
                                 start_arg = 0,
                                 end_arg = len(data)-1,
                                 sigma_threshold = sigma_threshold_fraction*absolute_min,
                                 minimal_threshold = minimal_threshold,
                                 make_prints= make_prints)

    return error, sigma0_argleft, dip0_arg, sigma0_argright, sigma1_argleft, dip1_arg, sigma1_argright
    
    
############################################################################
#                                                                          #
#             Additional routines with Lorentzian-like filter              #
#                                                                          #
############################################################################

def find_offset_parameter(self, x_values=None, data=None):
    """ This method convolves the data with a Lorentzian and the finds the
    offset which is supposed to be the most likely valy via a histogram.
    Additional the smoothed data is returned

    @param array x_values: x values
    @param array data: value of each data point corresponding to
                        x values

    @return int error: error code (0:OK, -1:error)
    @return float array data_smooth: smoothed data
    @return float offset: estimated offset


    """
    # lorentzian filter
    mod, params = self.make_lorentzian_model()

    if len(x_values) < 20.:
        len_x = 5
    elif len(x_values) >= 100.:
        len_x = 10
    else:
        len_x = int(len(x_values)/10.)+1

    lorentz = mod.eval(x=np.linspace(0, len_x, len_x), amplitude=1, c=0.,
                       sigma=len_x/4., center=len_x/2.)
    data_smooth = filters.convolve1d(data, lorentz/lorentz.sum(),
                                     mode='constant', cval=data.max())

    # finding most frequent value which is supposed to be the offset
    hist = np.histogram(data_smooth, bins=10)
    offset = (hist[1][hist[0].argmax()]+hist[1][hist[0].argmax()+1])/2.

    return data_smooth, offset
