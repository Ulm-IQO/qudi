# -*- coding: utf-8 -*-
"""
Created on Fri Aug 07 14:47:10 2015

@author: Simon Schmitt

"""


import os
from lxml import etree as ET

##### This class creates the header for all .WFMX files


class WFMX_header():
    
    ###### The needed parameters are specified in the init
    ###### TO DO: Correct timestamp
    
    def __init__(self,sampling_rate=35000000, total_amplitude=0.35, offset=0, number_of_samples=2701652):
    
        self.name_of_file = 'header.xml'
        self.name_of_waveform = 'Waveform_1'
        self.sampling_rate = sampling_rate
        self.total_amplitude = total_amplitude
        self.offset = offset
        self.number_of_samples = number_of_samples
        self.time = '2014-10-28T12:59:52.9004865-07:00'
        self.basic_waveform = 'Basic Waveform'
        self.software_version = '4.0.0075'
    
    
    ##### This function creates the html file using etree
    
    
    def create_xml_file(self):
        
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
        

        ##### This command creates the first version of the file
        
        tree = ET.ElementTree(root)
        tree.write(self.name_of_file, pretty_print=True, xml_declaration=True)
    
  
    
    ##### Calculates the length of the header
    ##### 40 is subtracted since the first line of the above created file has a length 
    ##### of 39 and is not included later and the last endline (\n) is also not neccessary 
    ##### The for loop is needed to give a nine digit length: xxxxxxxxx
    
        length_of_header = ''
        size = str(os.path.getsize(self.name_of_file)-40)
        
        for ii in range(9-len(size)):
            length_of_header += '0'
        length_of_header += size    
    
    
        print (length_of_header)
    
    
    ##### The header length is written into the file
    ##### The first line is not included since it is redundant
    ##### Also the last endline (\n) is excluded 
    
        text = open(self.name_of_file, "U").read()
        text = text.replace("xxxxxxxxx", length_of_header)
        text = bytes(text, 'UTF-8')
        #text = text.replace("\n", "\r\n")
        f=open(self.name_of_file, "wb")
        f.write(text[39:-1])
        f.close
        
testing=WFMX_header()
testing.create_xml_file()