# -*- coding: utf-8 -*-
"""
This module contains a QWidgets.QDialog subclass representing an "about qudi" dialog.

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

from qtpy import QtCore, QtWidgets


class AboutQudiDialog(QtWidgets.QDialog):
    """
    QWidgets.QDialog subclass representing an "about qudi" dialog
    """
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

        self.setWindowFlags(QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowCloseButtonHint)

        buttonbox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)
        buttonbox.setOrientation(QtCore.Qt.Horizontal)
        self.ok_button = buttonbox.button(buttonbox.Ok)
        self.ok_button.clicked.connect(self.accept)

        self.header_label = QtWidgets.QLabel('qudi')
        self.header_label.setObjectName('headerLabel')
        font = self.header_label.font()
        font.setBold(True)
        font.setPointSize(20)
        self.header_label.setFont(font)
        self.version_label = QtWidgets.QLabel('Version number goes here...')
        self.version_label.setObjectName('versionLabel')
        self.version_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse
                                                   | QtCore.Qt.TextBrowserInteraction)
        self.version_label.setOpenExternalLinks(True)

        self.about_label = QtWidgets.QLabel('<html><head/><body><p>Qudi is a suite of tools for '
                                            'operating multi-instrument and multi-computer '
                                            'laboratory experiments. Originally built around a '
                                            'confocal fluorescence microscope experiments, it has '
                                            'grown to be a generally applicaple framework for '
                                            'controlling experiments.</p></body></html>')
        self.about_label.setWordWrap(True)
        self.about_label.setObjectName('aboutLabel')
        self.about_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse
                                                 | QtCore.Qt.TextBrowserInteraction)
        self.about_label.setOpenExternalLinks(True)

        self.credits_label = QtWidgets.QLabel('<html><head/><body><p><span style=" text-decoration:'
                                              ' underline;">Qudi is developed by the Institute for '
                                              'Quantum Optics at Ulm University. </span></p><p>Kay '
                                              'D. Jahnke</p><p>Jan M. Binder</p><p>Alexander Stark'
                                              '</p><p>Lachlan J, Rogers</p><p>Nikolas Tomek</p><p>'
                                              'Florian S. Frank</p><p>Mathias Metsch</p><p>'
                                              'Christoph Müller</p><p>Simon Schmitt</p><p>Thomas '
                                              'Unden</p><p>Jochen Scheuer</p><p>Ou Wang</p><p><span'
                                              ' style=" text-decoration: underline;">External '
                                              'Contributors:</span></p><p>Tobias Gehring, DTU '
                                              'Copenhagen</p><p>...</p></body></html>')
        self.credits_label.setWordWrap(True)
        self.credits_label.setObjectName('creditsLabel')
        self.credits_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse
                                                   | QtCore.Qt.TextBrowserInteraction)
        self.credits_label.setOpenExternalLinks(True)

        self.license_label = QtWidgets.QLabel('<html>\n<head/>\n<body>\n<p><span style=" '
                                              'font-family:"monospace";">\nQudi is free software: '
                                              'you can redistribute it and/or modify it under the '
                                              'terms <br/>\nof the GNU General Public License as '
                                              'published by the Free Software Foundation,<br/>\n'
                                              'either version 3 of the License, or (at your option)'
                                              ' any later version.\n</span></p>\n<p><span style=" '
                                              'font-family:"monospace";">\nQudi is distributed in '
                                              'the hope that it will be useful, but WITHOUT ANY '
                                              'WARRANTY;<br/>\nwithout even the implied warranty of'
                                              ' MERCHANTABILITY or FITNESS FOR A PARTICULAR '
                                              'PURPOSE.<br/>\nSee the GNU General Public License '
                                              'for more details.<br/>\n</span>\n</p><p><span '
                                              'style=" font-family:"monospace";">\nYou should have'
                                              ' received a copy of the GNU General Public License '
                                              'along with Qudi.<br/>\nIf not, see\n</span>\n<a '
                                              'href="http://www.gnu.org/licenses/"><span style=" '
                                              'text-decoration: underline; color:#00ffff;">'
                                              'http://www.gnu.org/licenses/</span></a>.<br/>\n</p>'
                                              '\n<p><span style=" text-decoration: underline;">\n'
                                              'Qudi is derived in parts from ACQ4, so here is its '
                                              'license:</span></p>\n<p><span style=" font-family:'
                                              '"monospace";">\nPermission is hereby granted, free '
                                              'of charge, to any person obtaining a copy <br/>\nof '
                                              'this software and associated documentation files '
                                              '(the &quot;Software&quot;), to deal <br/>\nin the '
                                              'Software without restriction, including without '
                                              'limitation the rights <br/>\nto use, copy, modify, '
                                              'merge, publish, distribute, sublicense, and/or sell'
                                              ' <br/>\ncopies of the Software, and to permit '
                                              'persons to whom the Software is <br/>\nfurnished to '
                                              'do so, subject to the following conditions: <br/>\n'
                                              '<br/>\nThe above copyright notice and this '
                                              'permission notice shall be included in all <br/>\n'
                                              'copies or substantial portions of the Software. '
                                              '<br/>\n<br/>\nTHE SOFTWARE IS PROVIDED &quot;AS '
                                              'IS&quot;, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR '
                                              '<br/>\nIMPLIED, INCLUDING BUT NOT LIMITED TO THE '
                                              'WARRANTIES OF MERCHANTABILITY, <br/>\nFITNESS FOR A'
                                              ' PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT'
                                              ' SHALL THE <br/>\nAUTHORS OR COPYRIGHT HOLDERS BE '
                                              'LIABLE FOR ANY CLAIM, DAMAGES OR OTHER <br/>\n'
                                              'LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR'
                                              ' OTHERWISE, ARISING FROM, <br/>\nOUT OF OR IN '
                                              'CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER '
                                              'DEALINGS IN THE <br/>\nSOFTWARE.<br/>\n</span></p>\n'
                                              '<p><span style=" font-family:"monospace"; '
                                              'text-decoration: underline;">\nParts of Qudi are '
                                              'derived from IPython, which is licensed as follows:'
                                              '\n</span></p>\n<p><span style=" font-family:'
                                              '"monospace";">\n<br/>\nThis project is licensed '
                                              'under the terms of the Modified BSD License <br/>\n'
                                              '(also known as New or Revised or 3-Clause BSD), as '
                                              'follows: <br/>\n<br/>\nCopyright (c) 2015, IPython '
                                              'Development Team <br/>\n<br/>\nAll rights reserved. '
                                              '<br/>\n<br/>\nRedistribution and use in source and '
                                              'binary forms, with or without <br/>\nmodification, '
                                              'are permitted provided that the following conditions'
                                              ' are met: <br/>\n<br/>\nRedistributions of source '
                                              'code must retain the above copyright notice, this '
                                              '<br/>\nlist of conditions and the following '
                                              'disclaimer. <br/>\n<br/>\nRedistributions in binary '
                                              'form must reproduce the above copyright notice, this'
                                              ' <br/>\nlist of conditions and the following '
                                              'disclaimer in the documentation and/or <br/>\nother '
                                              'materials provided with the distribution. <br/>\n'
                                              '<br/>\nNeither the name of the IPython Development '
                                              'Team nor the names of its <br/>\ncontributors may be'
                                              ' used to endorse or promote products derived from '
                                              'this <br/>\nsoftware without specific prior written '
                                              'permission. <br/>\n<br/>\nTHIS SOFTWARE IS PROVIDED '
                                              'BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS &quot;AS '
                                              'IS&quot; AND <br/>\nANY EXPRESS OR IMPLIED '
                                              'WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE '
                                              'IMPLIED <br/>\nWARRANTIES OF MERCHANTABILITY AND '
                                              'FITNESS FOR A PARTICULAR PURPOSE ARE <br/>\n'
                                              'DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR'
                                              ' CONTRIBUTORS BE LIABLE <br/>\nFOR ANY DIRECT, '
                                              'INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR '
                                              'CONSEQUENTIAL <br/>\nDAMAGES (INCLUDING, BUT NOT '
                                              'LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR <br/>'
                                              '\nSERVICES; LOSS OF USE, DATA, OR PROFITS; OR '
                                              'BUSINESS INTERRUPTION) HOWEVER <br/>\nCAUSED AND ON '
                                              'ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT'
                                              ' LIABILITY, <br/>\nOR TORT (INCLUDING NEGLIGENCE OR '
                                              'OTHERWISE) ARISING IN ANY WAY OUT OF THE USE <br/>\n'
                                              'OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY'
                                              ' OF SUCH DAMAGE. <br/>\n<br/>\nAbout the IPython '
                                              'Development Team <br/>\n<br/>\nThe IPython '
                                              'Development Team is the set of all contributors to '
                                              'the IPython project. <br/>\nThis includes all of the'
                                              ' IPython subprojects. <br/><br/>The core team that '
                                              'coordinates development on GitHub can be found here:'
                                              ' <br/>\n</span>\n<a href='
                                              '"https://github.com/ipython/"><span style=" '
                                              'text-decoration: underline; color:#2980b9;">'
                                              'https://github.com/ipython/</span></a>\n<span '
                                              'style=" font-family:"monospace";">.<br/><br/></span>'
                                              '\n<span style=" font-family:"monospace"; '
                                              'text-decoration: underline;">\nParts of Qudi are '
                                              'derived from SciPy, which is licensed as follows:\n'
                                              '</span></p>\n<p><span style=" font-family:'
                                              '"monospace";">\nCopyright (c) 2001, 2002 Enthought, '
                                              'Inc. <br/>\nAll rights reserved. <br/>\n<br/>\n'
                                              'Copyright (c) 2003-2016 SciPy Developers. <br/>\nAll'
                                              ' rights reserved. <br/>\n<br/>\nRedistribution and '
                                              'use in source and binary forms, with or without '
                                              '<br/>\nmodification, are permitted provided that the'
                                              ' following conditions are met: <br/>\n<br/>\na. '
                                              'Redistributions of source code must retain the above'
                                              ' copyright notice, <br/>\nthis list of conditions '
                                              'and the following disclaimer. <br/>\nb. '
                                              'Redistributions in binary form must reproduce the '
                                              'above copyright <br/>\nnotice, this list of '
                                              'conditions and the following disclaimer in the <br/>'
                                              '\ndocumentation and/or other materials provided with'
                                              ' the distribution. <br/>\nc. Neither the name of '
                                              'Enthought nor the names of the SciPy Developers '
                                              '<br/>\nmay be used to endorse or promote products '
                                              'derived from this software <br/>\nwithout specific '
                                              'prior written permission. <br/>\n<br/>\n<br/>\nTHIS '
                                              'SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND '
                                              'CONTRIBUTORS &quot;AS IS&quot; <br/>\nAND ANY '
                                              'EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT '
                                              'LIMITED TO, THE <br/>\nIMPLIED WARRANTIES OF '
                                              'MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE'
                                              ' <br/>\nARE DISCLAIMED. IN NO EVENT SHALL THE '
                                              'COPYRIGHT HOLDERS OR CONTRIBUTORS <br/>\nBE LIABLE '
                                              'FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, '
                                              'EXEMPLARY, <br/>\nOR CONSEQUENTIAL DAMAGES '
                                              '(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF <br/>'
                                              '\nSUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, '
                                              'OR PROFITS; OR BUSINESS <br/>\nINTERRUPTION) HOWEVER'
                                              ' CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN '
                                              '<br/>\nCONTRACT, STRICT LIABILITY, OR TORT '
                                              '(INCLUDING NEGLIGENCE OR OTHERWISE) <br/>\nARISING '
                                              'IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF'
                                              ' ADVISED OF <br/>\nTHE POSSIBILITY OF SUCH DAMAGE.'
                                              '<br/>\n<br/>\n</span></p>\n</body>\n</html>')
        self.license_label.setWordWrap(True)
        self.license_label.setOpenExternalLinks(True)
        self.license_label.setObjectName('licenseLabel')
        self.license_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse
                                                   | QtCore.Qt.TextBrowserInteraction)
        self.license_label.setOpenExternalLinks(True)

        about_scroll_widget = QtWidgets.QScrollArea()
        about_scroll_widget.setWidgetResizable(True)
        about_scroll_widget.setWidget(self.about_label)
        about_scroll_widget.setObjectName('aboutScrollArea')
        credits_scroll_widget = QtWidgets.QScrollArea()
        credits_scroll_widget.setWidgetResizable(True)
        credits_scroll_widget.setWidget(self.credits_label)
        credits_scroll_widget.setObjectName('creditsScrollArea')
        license_scroll_widget = QtWidgets.QScrollArea()
        license_scroll_widget.setWidgetResizable(True)
        license_scroll_widget.setWidget(self.license_label)
        license_scroll_widget.setObjectName('licenseScrollArea')

        self.tab_widget = QtWidgets.QTabWidget()
        self.tab_widget.setObjectName('tabWidget')
        self.tab_widget.addTab(about_scroll_widget, 'About')
        self.tab_widget.addTab(credits_scroll_widget, 'Credits')
        self.tab_widget.addTab(license_scroll_widget, 'License')

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.header_label)
        layout.addWidget(self.version_label)
        layout.addWidget(self.tab_widget)
        layout.addWidget(buttonbox)

        self.setLayout(layout)
        self.about_label.setFocus()
        return
