# -*- coding: utf-8 -*-

import os
import sys
from setuptools import setup, find_namespace_packages

with open('README.md', 'r') as file:
    long_description = file.read()

with open('VERSION.txt', 'r') as file:
    version = file.read().strip()

_core_dist = os.path.abspath(os.path.join('C:\\Software\\dist_test\\qudi\\', 'qudi_core'))

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
      version=version,
      packages=find_namespace_packages(),
      package_data={'qudi.gui': ['*.ui', '*/*.ui']},
      description='IQO measurement modules',
      long_description=long_description,
      long_description_content_type='text/markdown',
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
