# -*- coding: utf-8 -*-

"""
This file contains the QuDi WFMX header file creator for pulsing devices.

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

Copyright (C) 2015 Simon Schmitt simon.schmitt@uni-ulm.de
"""

import os
from lxml import etree as ET


class WFMX_header():
    """ This class creates the header for all .WFMX files """

    

    def __init__(self, sampling_rate=35000000, total_amplitude=0.35, offset=0,
                 number_of_samples=2701652, temp_dir= ''):
        """ The needed parameters are specified in the init

        @param int sampling_rate:
        @param float total_amplitude:
        @param int offset:
        @param int number_of_samples:
        @param str temp_dir:
        """

        # a directory to store the temporarily created file:
        self.temp_dir = temp_dir

        self.name_of_file = 'header.xml'
        self.name_of_waveform = 'Waveform_1'
        self.sampling_rate = sampling_rate
        self.total_amplitude = total_amplitude
        self.offset = offset
        self.number_of_samples = number_of_samples
        self.time = '2014-10-28T12:59:52.9004865-07:00'
        self.basic_waveform = 'Basic Waveform'
        self.software_version = '4.0.0075'

    def create_xml_file(self):
        """ This function creates the html file using etree. """

        root = ET.Element('DataFile', offset='xxxxxxxxx', version="0.1")
        DataSetsCollection = ET.SubElement(root, 'DataSetsCollection', xmlns="http://www.tektronix.com")
        DataSets = ET.SubElement(DataSetsCollection, 'DataSets', version="1", xmlns="http://www.tektronix.com")
        DataDescription = ET.SubElement(DataSets, 'DataDescription')
        NumberSamples = ET.SubElement(DataDescription, 'NumberSamples')
        NumberSamples.text = str(self.number_of_samples)
        SamplesType = ET.SubElement(DataDescription, 'SamplesType')
        SamplesType.text = 'AWGWaveformSample'
        MarkersIncluded = ET.SubElement(DataDescription, 'MarkersIncluded')
        MarkersIncluded.text = 'true'
        NumberFormat = ET.SubElement(DataDescription, 'NumberFormat')
        NumberFormat.text = 'Single'
        Endian = ET.SubElement(DataDescription, 'Endian')
        Endian.text = 'Little'
        Timestamp = ET.SubElement(DataDescription, 'Timestamp')
        Timestamp.text = self.time
        ProductSpecific = ET.SubElement(DataSets, 'ProductSpecific', name="")
        ReccSamplingRate = ET.SubElement(ProductSpecific,'ReccSamplingRate', units="Hz")
        ReccSamplingRate.text = str(self.sampling_rate)
        ReccAmplitude = ET.SubElement(ProductSpecific,'ReccAmplitude', units="Volts")
        ReccAmplitude.text = str(self.total_amplitude)
        ReccOffset = ET.SubElement(ProductSpecific,'ReccOffset', units="Volts")
        ReccOffset.text = str(self.offset)
        SerialNumber = ET.SubElement(ProductSpecific,'SerialNumber')
        SoftwareVersion = ET.SubElement(ProductSpecific,'SoftwareVersion')
        SoftwareVersion.text = self.software_version
        UserNotes = ET.SubElement(ProductSpecific,'UserNotes')
        OriginalBitDepth = ET.SubElement(ProductSpecific,'OriginalBitDepth')
        OriginalBitDepth.text = 'EightBit'
        Thumbnail = ET.SubElement(ProductSpecific,'Thumbnail')
        CreatorProperties = ET.SubElement(ProductSpecific,'CreatorProperties',name=self.basic_waveform)
        Setup = ET.SubElement(root, 'Setup')

        filepath = os.path.join(self.temp_dir, self.name_of_file)

        ##### This command creates the first version of the file

        tree = ET.ElementTree(root)
        tree.write(filepath, pretty_print=True, xml_declaration=True)

        # Calculates the length of the header:
        # 40 is subtracted since the first line of the above created file has a length of 39 and is
        # not included later and the last endline (\n) is also not neccessary.
        # The for loop is needed to give a nine digit length: xxxxxxxxx

        length_of_header = ''
        size = str(os.path.getsize(filepath)-40)

        for ii in range(9-len(size)):
            length_of_header += '0'
        length_of_header += size

        # The header length is written into the file
        # The first line is not included since it is redundant
        # Also the last endline (\n) is excluded

        text = open(filepath, "U").read()
        text = text.replace("xxxxxxxxx", length_of_header)
        text = bytes(text, 'UTF-8')
        #text = text.replace("\n", "\r\n")
        f=open(filepath, "wb")
        f.write(text[39:-1])
        f.close

# testing=WFMX_header()
# testing.create_xml_file()