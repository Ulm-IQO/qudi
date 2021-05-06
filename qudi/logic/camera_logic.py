# -*- coding: utf-8 -*-

"""
A module for controlling a camera.

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import datetime
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from PySide2 import QtCore
from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption
from qudi.util.mutex import RecursiveMutex
from qudi.core.module import LogicBase


class CameraLogic(LogicBase):
    """
    Control a camera.
    """

    # declare connectors
    _camera = Connector(name='camera', interface='CameraInterface')
    # declare config options
    _minimum_exposure_time = ConfigOption(name='minimum_exposure_time',
                                          default=0.05,
                                          missing='warn')

    # signals
    sigFrameChanged = QtCore.Signal(object)
    sigAcquisitionFinished = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self.__timer = None
        self._thread_lock = RecursiveMutex()
        self._exposure = -1
        self._gain = -1
        self._last_frame = None

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        camera = self._camera()
        self._exposure = camera.get_exposure()
        self._gain = camera.get_gain()

        self.__timer = QtCore.QTimer()
        self.__timer.setSingleShot(True)
        self.__timer.timeout.connect(self.__acquire_video_frame)

    def on_deactivate(self):
        """ Perform required deactivation. """
        self.__timer.stop()
        self.__timer.timeout.disconnect()
        self.__timer = None

    @property
    def last_frame(self):
        return self._last_frame

    def set_exposure(self, time):
        """ Set exposure time of camera """
        with self._thread_lock:
            if self.module_state() == 'idle':
                camera = self._camera()
                camera.set_exposure(time)
                self._exposure = camera.get_exposure()
            else:
                self.log.error('Unable to set exposure time. Acquisition still in progress.')

    def get_exposure(self):
        """ Get exposure of hardware """
        with self._thread_lock:
            self._exposure = self._camera().get_exposure()
            return self._exposure

    def set_gain(self, gain):
        with self._thread_lock:
            if self.module_state() == 'idle':
                camera = self._camera()
                camera.set_gain(gain)
                self._gain = camera.get_gain()
            else:
                self.log.error('Unable to set gain. Acquisition still in progress.')

    def get_gain(self):
        with self._thread_lock:
            self._gain = self._camera().get_gain()
            return self._gain

    def capture_frame(self):
        """
        """
        with self._thread_lock:
            if self.module_state() == 'idle':
                self.module_state.lock()
                camera = self._camera()
                camera.start_single_acquisition()
                self._last_frame = camera.get_acquired_data()
                self.module_state.unlock()
                self.sigFrameChanged.emit(self._last_frame)
                self.sigAcquisitionFinished.emit()
            else:
                self.log.error('Unable to capture single frame. Acquisition still in progress.')

    def toggle_video(self, start):
        if start:
            self._start_video()
        else:
            self._stop_video()

    def _start_video(self):
        """ Start the data recording loop.
        """
        with self._thread_lock:
            if self.module_state() == 'idle':
                self.module_state.lock()
                exposure = max(self._exposure, self._minimum_exposure_time)
                camera = self._camera()
                if camera.support_live_acquisition():
                    camera.start_live_acquisition()
                else:
                    camera.start_single_acquisition()
                self.__timer.start(1000 * exposure)
            else:
                self.log.error('Unable to start video acquisition. Acquisition still in progress.')

    def _stop_video(self):
        """ Stop the data recording loop.
        """
        with self._thread_lock:
            if self.module_state() == 'locked':
                self.__timer.stop()
                self._camera().stop_acquisition()
                self.module_state.unlock()
                self.sigAcquisitionFinished.emit()

    def __acquire_video_frame(self):
        """ Execute step in the data recording loop: save one of each control and process values
        """
        with self._thread_lock:
            camera = self._camera()
            self._last_frame = camera.get_acquired_data()
            self.sigFrameChanged.emit(self._last_frame)
            if self.module_state() == 'locked':
                exposure = max(self._exposure, self._minimum_exposure_time)
                self.__timer.start(1000 * exposure)
                if not camera.support_live_acquisition():
                    camera.start_single_acquisition()  # the hardware has to check it's not busy

    def save_xy_data(self, colorscale_range=None, percentile_range=None):
        """ Save the current confocal xy data to file.

        Two files are created.  The first is the imagedata, which has a text-matrix of count values
        corresponding to the pixel matrix of the image.  Only count-values are saved here.

        The second file saves the full raw data with x, y, z, and counts at every pixel.

        A figure is also saved.

        @param: list colorscale_range (optional) The range [min, max] of the display colour scale (for the figure)

        @param: list percentile_range (optional) The percentile range [min, max] of the color scale
        """
        with self._thread_lock:
            pass
        # filepath = self._save_logic.get_path_for_module('Camera')
        # timestamp = datetime.datetime.now()
        # # Prepare the metadata parameters (common to both saved files):
        # parameters = dict()
        #
        # parameters['Gain'] = self._gain
        # parameters['Exposure time (s)'] = self._exposure
        # # Prepare a figure to be saved
        #
        # axes = ['X', 'Y']
        # xy_pixels = self._hardware.get_size()
        # image_extent = [0,
        #                 xy_pixels[0],
        #                 0,
        #                 xy_pixels[1]]
        #
        # fig = self.draw_figure(data=self._last_image,
        #                        image_extent=image_extent,
        #                        scan_axis=axes,
        #                        cbar_range=colorscale_range,
        #                        percentile_range=percentile_range)
        #
        #
        # # data for the text-array "image":
        # image_data = dict()
        # image_data['XY image data.'] = self._last_image
        # filelabel = 'xy_image'
        # self._save_logic.save_data(image_data,
        #                            filepath=filepath,
        #                            timestamp=timestamp,
        #                            parameters=parameters,
        #                            filelabel=filelabel,
        #                            fmt='%.6e',
        #                            delimiter='\t',
        #                            plotfig=fig)
        #
        # # prepare the full raw data in a dict:
        # # data = dict()
        # # data['x position (m)'] = self.xy_image[:, :, 0].flatten()
        # # data['y position (m)'] = self.xy_image[:, :, 1].flatten()
        # # data['z position (m)'] = self.xy_image[:, :, 2].flatten()
        # #
        # #
        # # # Save the raw data to file
        # # filelabel = 'xy_image_data'
        # # self._save_logic.save_data(data,
        # #                            filepath=filepath,
        # #                            timestamp=timestamp,
        # #                            parameters=parameters,
        # #                            filelabel=filelabel,
        # #                            fmt='%.6e',cc
        # #                            delimiter='\t')
        #
        # self.log.debug('Image saved.')
        # return

    # def draw_figure(self, data, image_extent, scan_axis=None, cbar_range=None, percentile_range=None,  crosshair_pos=None):
    #     """ Create a 2-D color map figure of the scan image.
    #
    #     @param: array data: The NxM array of count values from a scan with NxM pixels.
    #
    #     @param: list image_extent: The scan range in the form [hor_min, hor_max, ver_min, ver_max]
    #
    #     @param: list axes: Names of the horizontal and vertical axes in the image
    #
    #     @param: list cbar_range: (optional) [color_scale_min, color_scale_max].  If not supplied then a default of
    #                              data_min to data_max will be used.
    #
    #     @param: list percentile_range: (optional) Percentile range of the chosen cbar_range.
    #
    #     @param: list crosshair_pos: (optional) crosshair position as [hor, vert] in the chosen image axes.
    #
    #     @return: fig fig: a matplotlib figure object to be saved to file.
    #     """
    #     if scan_axis is None:
    #         scan_axis = ['X', 'Y']
    #
    #     # If no colorbar range was given, take full range of data
    #     if cbar_range is None:
    #         cbar_range = [np.min(data), np.max(data)]
    #
    #     # Scale color values using SI prefix
    #     prefix = ['', 'k', 'M', 'G']
    #     prefix_count = 0
    #     image_data = data
    #     draw_cb_range = np.array(cbar_range)
    #     image_dimension = image_extent.copy()
    #
    #     while draw_cb_range[1] > 1000:
    #         image_data = image_data/1000
    #         draw_cb_range = draw_cb_range/1000
    #         prefix_count = prefix_count + 1
    #
    #     c_prefix = prefix[prefix_count]
    #
    #
    #     # Scale axes values using SI prefix
    #     axes_prefix = ['', 'm', r'$\mathrm{\mu}$', 'n']
    #     x_prefix_count = 0
    #     y_prefix_count = 0
    #
    #     while np.abs(image_dimension[1]-image_dimension[0]) < 1:
    #         image_dimension[0] = image_dimension[0] * 1000.
    #         image_dimension[1] = image_dimension[1] * 1000.
    #         x_prefix_count = x_prefix_count + 1
    #
    #     while np.abs(image_dimension[3] - image_dimension[2]) < 1:
    #         image_dimension[2] = image_dimension[2] * 1000.
    #         image_dimension[3] = image_dimension[3] * 1000.
    #         y_prefix_count = y_prefix_count + 1
    #
    #     x_prefix = axes_prefix[x_prefix_count]
    #     y_prefix = axes_prefix[y_prefix_count]
    #
    #     # Create figure
    #     fig, ax = plt.subplots()
    #
    #     # Create image plot
    #     cfimage = ax.imshow(image_data,
    #                         cmap=plt.get_cmap('inferno'), # reference the right place in qd
    #                         origin="lower",
    #                         vmin=draw_cb_range[0],
    #                         vmax=draw_cb_range[1],
    #                         interpolation='none',
    #                         extent=image_dimension
    #                         )
    #
    #     ax.set_aspect(1)
    #     ax.set_xlabel(scan_axis[0] + ' position (' + x_prefix + 'm)')
    #     ax.set_ylabel(scan_axis[1] + ' position (' + y_prefix + 'm)')
    #     ax.spines['bottom'].set_position(('outward', 10))
    #     ax.spines['left'].set_position(('outward', 10))
    #     ax.spines['top'].set_visible(False)
    #     ax.spines['right'].set_visible(False)
    #     ax.get_xaxis().tick_bottom()
    #     ax.get_yaxis().tick_left()
    #
    #     # draw the crosshair position if defined
    #     if crosshair_pos is not None:
    #         trans_xmark = mpl.transforms.blended_transform_factory(
    #             ax.transData,
    #             ax.transAxes)
    #
    #         trans_ymark = mpl.transforms.blended_transform_factory(
    #             ax.transAxes,
    #             ax.transData)
    #
    #         ax.annotate('', xy=(crosshair_pos[0]*np.power(1000,x_prefix_count), 0),
    #                     xytext=(crosshair_pos[0]*np.power(1000,x_prefix_count), -0.01), xycoords=trans_xmark,
    #                     arrowprops=dict(facecolor='#17becf', shrink=0.05),
    #                     )
    #
    #         ax.annotate('', xy=(0, crosshair_pos[1]*np.power(1000,y_prefix_count)),
    #                     xytext=(-0.01, crosshair_pos[1]*np.power(1000,y_prefix_count)), xycoords=trans_ymark,
    #                     arrowprops=dict(facecolor='#17becf', shrink=0.05),
    #                     )
    #
    #     # Draw the colorbar
    #     cbar = plt.colorbar(cfimage, shrink=0.8)#, fraction=0.046, pad=0.08, shrink=0.75)
    #     cbar.set_label('Fluorescence (' + c_prefix + 'c/s)')
    #
    #     # remove ticks from colorbar for cleaner image
    #     cbar.ax.tick_params(which=u'both', length=0)
    #
    #     # If we have percentile information, draw that to the figure
    #     if percentile_range is not None:
    #         cbar.ax.annotate(str(percentile_range[0]),
    #                          xy=(-0.3, 0.0),
    #                          xycoords='axes fraction',
    #                          horizontalalignment='right',
    #                          verticalalignment='center',
    #                          rotation=90
    #                          )
    #         cbar.ax.annotate(str(percentile_range[1]),
    #                          xy=(-0.3, 1.0),
    #                          xycoords='axes fraction',
    #                          horizontalalignment='right',
    #                          verticalalignment='center',
    #                          rotation=90
    #                          )
    #         cbar.ax.annotate('(percentile)',
    #                          xy=(-0.3, 0.5),
    #                          xycoords='axes fraction',
    #                          horizontalalignment='right',
    #                          verticalalignment='center',
    #                          rotation=90
    #                          )
    #     return fig
