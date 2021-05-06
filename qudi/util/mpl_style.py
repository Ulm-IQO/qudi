# -*- coding: utf-8 -*-

import cycler


# Matplotlib style definition for saving plots
__mpl_colors = ['#1f17f4', '#ffa40e', '#ff3487', '#008b00', '#17becf', '#850085']
__mpl_markers = ['o', 's', '^', 'v', 'D', 'd']
mpl_qd_style = {
    'axes.prop_cycle': cycler('color', __mpl_colors) + cycler('marker', __mpl_markers),
    'axes.edgecolor': '0.3',
    'xtick.color': '0.3',
    'ytick.color': '0.3',
    'axes.labelcolor': 'black',
    'font.size': '14',
    'lines.linewidth': '2',
    'figure.figsize': '12, 6',
    'lines.markeredgewidth': '0',
    'lines.markersize': '5',
    'axes.spines.right': True,
    'axes.spines.top': True,
    'xtick.minor.visible': True,
    'ytick.minor.visible': True,
    'savefig.dpi': '180'}
