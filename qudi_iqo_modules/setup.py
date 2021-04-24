# -*- coding: utf-8 -*-

import os
import sys
from setuptools import setup, find_namespace_packages

_core_dist = os.path.abspath(os.path.join(os.getcwd(), '..', 'qudi_core'))

unix_dep = [f'qudi_core @ file://localhost/{_core_dist}#egg=qudi_core',
            'nidaqmx',
            'PyVisa',
            'scipy',
            ]

windows_dep = [f'qudi_core @ file://localhost/{_core_dist}#egg=qudi_core',
               'nidaqmx',
               'PyVisa',
               'scipy',
               ]

setup(name='qudi_iqo_modules',
      version='1.0.0',
      packages=find_namespace_packages(),
      package_data={'qudi.gui': ['*.ui', '*/*.ui']},
      description='IQO measurement modules',
      url='https://github.com/Ulm-IQO/qudi',
      keywords=['diamond',
                'quantum',
                'confocal',
                'experiment',
                'lab',
                'laboratory',
                'instrumentation',
                'instrument',
                'modular'
                ],
      license='GPLv3',
      install_requires=windows_dep if sys.platform == 'win32' else unix_dep,
      python_requires='~=3.7',
      zip_safe=False
      )
