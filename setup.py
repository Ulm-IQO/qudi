# -*- coding: utf-8 -*-

import os
import sys
from setuptools import setup
from setuptools.command.develop import develop
from setuptools.command.install import install

with open('README.md', 'r') as file:
    long_description = file.read()

with open(os.path.join('.', 'qudi', 'core', 'VERSION.txt'), 'r') as file:
    version = file.read().strip()

unix_dep = ['attrs==19.3.0',
            'backcall==0.1.0',
            'bleach==3.1.3',
            'decorator==4.4.2',
            'defusedxml==0.6.0',
            'entrypoints==0.3',
            'fysom==2.1.5',
            'gitdb==4.0.2',
            'GitPython==3.1.0',
            'importlib-metadata==1.5.0',
            'ipykernel==5.2.0',
            'ipython==7.13.0',
            'ipython-genutils==0.2.0',
            'ipywidgets==7.5.1',
            'jedi==0.16.0',
            'Jinja2==2.11.1',
            'jsonschema==3.2.0',
            'jupyter==1.0.0',
            'jupyter-client==6.1.0',
            'jupyter-console==6.1.0',
            'jupyter-core==4.6.3',
            'MarkupSafe==1.1.1',
            'matplotlib==3.2.1',
            'mistune==0.8.4',
            'nbconvert==5.6.1',
            'nbformat==5.0.4',
            'nidaqmx==0.5.7',
            'notebook==6.0.3',
            'numpy==1.18.2',
            'pandocfilters==1.4.2',
            'parso==0.6.2',
            'pexpect==4.8.0',
            'pickleshare==0.7.5',
            'pkg-resources==0.0.0',
            'plumbum==1.6.9',
            'prometheus-client==0.7.1',
            'prompt-toolkit==3.0.4',
            'ptyprocess==0.6.0',
            'Pygments==2.6.1',
            'pyqtgraph==0.11.0',
            'pyrsistent==0.15.7',
            'PySide2==5.14.1',
            'python-dateutil==2.8.1',
            'pyzmq==19.0.0',
            'qtconsole==4.7.1',
            'QtPy==1.9.0',
            'rpyc==4.1.4',
            'ruamel.yaml==0.16.10',
            'ruamel.yaml.clib==0.2.0',
            'scipy==1.5.1',
            'Send2Trash==1.5.0',
            'shiboken2==5.14.1',
            'six==1.14.0',
            'smmap==3.0.1',
            'terminado==0.8.3',
            'testpath==0.4.4',
            'tornado==6.0.4',
            'traitlets==4.3.3',
            'wcwidth==0.1.9',
            'webencodings==0.5.1',
            'widgetsnbextension==3.5.1',
            'zipp==3.1.0',
            ]

windows_dep = ['attrs==19.3.0',
               'backcall==0.1.0',
               'bleach==3.1.3',
               'certifi==2019.11.28',
               'colorama==0.4.3',
               'decorator==4.4.2',
               'defusedxml==0.6.0',
               'entrypoints==0.3',
               'fysom==2.1.5',
               'gitdb==4.0.2',
               'GitPython==3.1.0',
               'importlib-metadata==1.5.0',
               'ipykernel==5.2.0',
               'ipython==7.13.0',
               'ipython-genutils==0.2.0',
               'ipywidgets==7.5.1',
               'jedi==0.16.0',
               'Jinja2==2.11.1',
               'jsonschema==3.2.0',
               'jupyter==1.0.0',
               'jupyter-client==6.1.0',
               'jupyter-console==6.1.0',
               'jupyter-core==4.6.3',
               'MarkupSafe==1.1.1',
               'matplotlib==3.2.1',
               'mistune==0.8.4',
               'nbconvert==5.6.1',
               'nbformat==5.0.4',
               'nidaqmx==0.5.7',
               'notebook==6.0.3',
               'numpy==1.18.2',
               'pandocfilters==1.4.2',
               'parso==0.6.2',
               'pickleshare==0.7.5',
               'plumbum==1.6.8',
               'prometheus-client==0.7.1',
               'prompt-toolkit==3.0.4',
               'Pygments==2.6.1',
               'pyqtgraph==0.11.0',
               'pyrsistent==0.15.7',
               'PySide2==5.14.1',
               'python-dateutil==2.8.1',
               'pywin32==227',
               'pywinpty==0.5.7',
               'pyzmq==19.0.0',
               'qtconsole==4.7.1',
               'QtPy==1.9.0',
               'rpyc==4.1.4',
               'ruamel.yaml==0.16.10',
               'ruamel.yaml.clib==0.2.0',
               'scipy==1.5.1',
               'Send2Trash==1.5.0',
               'shiboken2==5.14.1',
               'six==1.14.0',
               'smmap==3.0.1',
               'terminado==0.8.3',
               'testpath==0.4.4',
               'tornado==6.0.4',
               'traitlets==4.3.3',
               'wcwidth==0.1.9',
               'webencodings==0.5.1',
               'widgetsnbextension==3.5.1',
               'wincertstore==0.2',
               'zipp==3.1.0'
               ]


class PrePostDevelopCommands(develop):
    """ Pre- and Post-installation script for development mode.
    """
    def run(self):
        # PUT YOUR PRE-INSTALL SCRIPT HERE or CALL A FUNCTION
        develop.run(self)
        # PUT YOUR POST-INSTALL SCRIPT HERE or CALL A FUNCTION
        try:
            from qudi.core.qudikernel import install_kernel
            install_kernel()
        except:
            pass


class PrePostInstallCommands(install):
    """ Pre- and Post-installation for installation mode.
    """
    def run(self):
        # PUT YOUR PRE-INSTALL SCRIPT HERE or CALL A FUNCTION
        install.run(self)
        # PUT YOUR POST-INSTALL SCRIPT HERE or CALL A FUNCTION
        try:
            from qudi.core.qudikernel import install_kernel
            install_kernel()
        except:
            pass


setup(name='qudi',
      version=version,
      packages=['qudi',
                'qudi.core',
                'qudi.core.gui',
                'qudi.core.gui.main_gui',
                'qudi.core.gui.qtwidgets',
                'qudi.core.logger',
                'qudi.core.jupyterkernel',
                'qudi.core.jupyterkernel.mpl',
                'qudi.core.util',
                'qudi.tools',
                'qudi.tools.config_editor'
                ],
      package_data={'': ['LICENSE.txt', 'COPYRIGHT.txt'],
                    'qudi.core': ['VERSION.txt', 
                                  'default.cfg',
                                  'artwork/logo/*',
                                  'artwork/icons/oxygen/*',
                                  'artwork/icons/oxygen/**/*.png',
                                  'artwork/icons/qudiTheme/*',
                                  'artwork/icons/qudiTheme/**/*.png',
                                  'artwork/logo/*.png',
                                  'artwork/logo/*.ico',
                                  'artwork/logo/*.txt',
                                  'artwork/styles/application/*.qss',
                                  'artwork/styles/application/*.txt',
                                  'artwork/styles/application/**/*.png',
                                  'artwork/styles/application/**/*.txt',
                                  'artwork/styles/console/*.qss',
                                  'artwork/styles/console/*.txt',
                                  'artwork/styles/log/*.qss',
                                  'artwork/styles/log/*.txt'
                                  ]
                    },
      description='A modular laboratory experiment management suite',
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
      cmdclass={'develop': PrePostDevelopCommands, 'install': PrePostInstallCommands},
      entry_points={
          'console_scripts': ['qudi=qudi.runnable:main',
                              'qudi-uninstall-kernel=qudi.core.qudikernel:uninstall_kernel',
                              'qudi-install-kernel=qudi.core.qudikernel:install_kernel'
                              ]
      },
      zip_safe=False
      )
