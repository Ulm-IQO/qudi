# -*- coding: utf-8 -*-
from logic.GenericLogic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.Mutex import Mutex
from collections import OrderedDict
import os
import sys
import inspect
import time

class FunctionImplementationError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)


class SaveLogic(GenericLogic):
    """
    UNSTABLE: Alexander Stark
    A general class which saves all kind of data in a general sense.
    """
    
    def __init__(self, manager, name, config, **kwargs):
        
        state_actions = {'onactivate': self.activation}
        GenericLogic.__init__(self, manager, name, config, state_actions, **kwargs)
        self._modclass = 'savelogic'
        self._modtype = 'logic'

        ## declare connectors
        
        self.connector['out']['savelogic'] = OrderedDict()
        self.connector['out']['savelogic']['class'] = 'SaveLogic'
        
        #locking for thread safety
        self.lock = Mutex()

        self.logMsg('The following configuration was found.', 
                    msgType='status')
                  
        # Some default variables concerning the operating system:
        self.os_system = None                  
        self.default_unix_data_dir = '/$HOME/Data'
        self.default_win_data_dir = 'C:/Data/'                        
                  
        # Chech which operation system is used and include a case if the 
        # directory was not found in the config:
        if 'linux' in sys.platform or sys.platform == 'darwin':
            self.os_system = 'unix'
            if 'unix_data_directory' in config.keys():
                self.data_dir = config['unix_data_directory']
            else:
                self.data_dir = self.default_unix_data_dir
            
        elif 'win32' in sys.platform or 'AMD64' in sys.platform :
            self.os_system = 'win'
            if 'win_data_directory' in config.keys():
                self.data_dir = config['win_data_directory'] 
            else:
                self.data_dir = self.default_win_data_dir                      
        else:
            self.logMsg('Identify the operating system.', 
                    msgType='error')
                            
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')
                        
                             
    def activation(self,e=None):
        pass

    
    
    def save_data(self, data, filepath, parameters=None, filename=None, 
                  as_text=False, as_xml=True, precision=None, delimiter=None):
            """ General save routine for data.

              @param dict data: Any dictonary with a keyword of the data
                                and a corresponding list, where the data are situated.
                                E.g. like:
                                    data = {'Frequency (MHz)':[1,2,4,5,6]}
                                    data = {'Frequency':[1,2,4,5,6],'Counts':[234,894,743,423,235]}
                                    data = {'Frequency (MHz),Counts':[ [1,234],[2,894],...[30,504] ]}

              @param string filepath: The path to the directory, where the data
                                      will be saved.
                                      If filepath is corrupt, the saving routine 
                                      will retrieve the basic filepath for the 
                                      data from the inherited base module 
                                      'get_data_dir' and saves the data in the
                                      directory .../UNSPECIFIED_<module_name>/
              @param dict parameters: optional, a dictionary with all parameters 
                                      you want to pass to the saving routine.
              @parem string filename: optional, if you really want to fix an own
                                      filename, otherwise an unique filename 
                                      will be generated from the class which is
                                      calling the save method with a timestamp.  
                                      The filename will be looking like:

                                        <filename>_JJJJ-MM-DD_HHh-MMm.dat

 

              @param int precision: optional, specifies the number of degits 
                                       after the comma for the saving precision.
                                       All number, which follows afterwards are 
                                       cut off. For 'precision=3' a number like
                                       '323.423842' is saved as '323.423'.
                                       Default is precision = 3.

              @param string delimiter: optional, insert here the di  



            This method should be called from the modules and it will call all 
            the needed methods for the saving routine.


            Saves data as text files or as xml files. 

               


              data is saved in a file with <filename>_JJJJ-MM-DD_HHh-MMm
            
            1D data
            =======
            1D data should be passed in a dictionary where the data trace should be
            assigned to one identifier like
            
                {'<identifier>':[list of values]}
                {'Numbers of counts':[1.4, 4.2, 5, 2.0, 5.9 , ... , 9.5, 6.4]}
            
            You can also pass as much 1D arrays as you want:
                {'Frequency (MHz)':list1, 'signal':list2, 'correlations': list3, ...}
               
            YOU ARE RESPONSIBLE FOR THE IDENTIFIER! DO NOT FORGET THE UNITS FOR THE
            SAVED TIME TRACE/MATRIX.
            
            2D data
            =======
            
            
            """

            frm = inspect.stack()[1]    # try to trace back the functioncall to
                                        # the class which was calling it.
            mod = inspect.getmodule(frm[0]) # this will get the object, which 
                                            # called the save_data function.
            module_name =  mod.__name__.split('.')[-1]  # that will extract the 
                                                        # name of the class.


            if not os.path.exists(filepath):
                filepath = self.get_daily_directory('UNSPECIFIED_'+str(module_name))



            if len(data)==1:

                pure_data = data[list(data)[0]]   # get the pure data from the 
                                                # dictionary
                if len(np.shape(pure_data)) ==1:

                    self._save_1d_trace_as_text(trace_data=pure_data, 
                                                trace_name=list(data)[0],
                                                )

                self._save_1d_trace_as_text(data)

            else:
                pass



            

    def _save_1d_trace_as_text(self, trace_data, trace_name):
        print('Not implemented yet.')
        raise FunctionImplementationError('SaveLogic>_save_1d_trace_as_text')
        return -1
        

    def _save_N_1d_traces_as_text(self,):
        print('Not implemented yet.')
        raise FunctionImplementationError('SaveLogic>_save_N_1d_traces_as_text')
        return -1

    def _save_2d_points_as_text(self,):
        print('Not implemented yet.')
        raise FunctionImplementationError('SaveLogic>_save_2d_points_as_text')
        return -1

    def _save_matrix_as_text():
        """
        x_[column][row]
        """
        print('Not implemented yet.')
        raise FunctionImplementationError('SaveLogic>_save_matrix_as_text')
        return -1


    def _save_general_2d_data_as_text():
        print('Not implemented yet.')
        raise FunctionImplementationError('SaveLogic>_save_general_2d_data_as_text')
        return -1

    def _save_1d_traces_as_xml():
        

        if as_xml:        
        
            root = ET.Element(module_name)  # which class wanted to access the save
                                            # function
            
            para = ET.SubElement(root, 'Parameters')
            
            if parameters != None:
                for element in parameters:
                    ET.SubElement(para, element).text = parameters[element]
            
            data_xml = ET.SubElement(root, 'data')
            
            for entry in data:
                
                dimension_data_array = len(np.shape(data[entry]))   
                
                # filter out the events which has only a single trace:  
                if dimension_data_array == 1:
                    
                    value = ET.SubElement(data_xml, entry)
                                     
                    for list_element in data[entry]:

                        ET.SubElement(value, 'value').text = str(list_element)
                    
                elif dimension_data_array == 2:
                    
                    dim_list_entry = len(np.shape(data[entry][0])) 
                    length_list_entry = np.shape(data[entry][0])[0]
                    if (dim_list_entry == 1) and (np.shape(data[entry][0])[0] == 2):
                    
                        # get from the keyword, which should be within the string
                        # separated by the delimiter ',' the description for the
                        # values:
                        try:
                            axis1 = entry.split(',')[0] 
                            axis2 = entry.split(',')[1] 
                        except:
                            print('Enter a commaseparated description for the given values!!!')
                            print('like:  dict_data[\'Frequency (MHz), Signal (arb. u.)\'] = 2d_list ')
                            print('But your data will be saved.')
                            
                            axis1 = str(entry)  
                            axis2 = 'value2'
                            
                        for list_element in data[entry]:
                                                                         
                            element = ET.SubElement(data_xml, 'value' ).text = str(list_element)
#                                
#                            ET.SubElement(element, str(axis1)).text = str(list_element[0])
#                            ET.SubElement(element, str(axis2)).text = str(list_element[1])
                        
                    elif (dim_list_entry == 1):
                        
                        for list_element in data[entry]:
                        
                            row = ET.SubElement(data_xml, 'row')
                            
                            for sub_element in list_element:
                                
                                ET.SubElement(row, 'value').text = str(sub_element)
                        
                        
                        
            #write to file:
            tree = ET.ElementTree(root)
            tree.write('output.xml', pretty_print=True, xml_declaration=True)



    def _save_2d_data_as_xml():
        pass





    def get_daily_directory(self):
        """
        Creates the daily directory.

          @return string: path to the daily directory.       
        
        If the daily directory does not exits in the specified <root_dir> path
        in the config file, then it is created according to the following scheme:
        
            <root_dir>\<year>\<month>\<day>
            
        and the filepath is returned. There should be always a filepath 
        returned.
        """
        
        # First check if the directory exists and if not then the default 
        # directory is taken.
        if not os.path.exists(self.data_dir):
                if self.data_dir != '':
                    print('The specified Data Directory in the config file '
                          'does not exist. Using default instead.')                         
                if self.os_system == 'unix':                    
                    self.data_dir = self.default_unix_data_dir
                elif self.os_system == 'win':
                    self.data_dir = self.default_win_data_dir
                else:
                    self.logMsg('Identify the operating system.', 
                                msgType='error')
                                
                # Check if the default directory does exist. If yes, there is 
                # no need to create it, since it will overwrite the existing
                # data there.
                if not os.path.exists(self.data_dir):
                    os.makedirs(self.data_dir)
                    self.logMsg('The specified Data Directory in the config '
                                'file does not exist. Using default for {0} '
                                'system instead. The directory\n{1} was '
                                'created'.format(self.os_system,self.data_dir), 
                                msgType='status', importance=5)
                                
        # That is now the current directory:
        current_dir = self.data_dir +time.strftime("\\%Y\\%m")

        
        folder_exists = False   # Flag to indicate that the folder does not exist.
        if os.path.exists(current_dir):
            
            # Get only the folders without the files there:
            folderlist = [d for d in os.listdir(current_dir) if os.path.isdir(os.path.join(current_dir, d))]
            # Search if there is a folder which starts with the current date:
            for entry in folderlist:
                if (time.strftime("%d") in (entry[:2])):
                    current_dir = current_dir +'\\'+ str(entry)
                    folder_exists = True
                    break
            
        if not folder_exists:
            current_dir = current_dir + time.strftime("\\%d")
            self.logMsg('Creating directory for today\'s data in \n'+current_dir, 
                                msgType='status', importance=5)
            os.makedirs(current_dir)
        
        return current_dir
                
    def get_path_for_module(self,module_name=None):
        """
        Method that creates a path for 'module_name' where data are stored.

          @param string module_name: Specify the folder, which should be 
                                     created in the daily directory. The
                                     module_name can be e.g. 'Confocal'.
          @retun string: absolute path to the module name
          
        This method should be called directly in the saving routine and NOT in
        the init method of the specified module! This prevents to create empty
        folders! 
        
        """
        if module_name == None:
            self.logMsg('No Module name specified! Please correct this! Data '
                        'are saved in the \'UNSPECIFIED_<module_name>\' folder.', 
                                msgType='status', importance=5)
                  
            frm = inspect.stack()[1]    # try to trace back the functioncall to
                                        # the class which was calling it.
            mod = inspect.getmodule(frm[0]) # this will get the object, which 
                                            # called the save_data function.
            module_name =  mod.__name__.split('.')[-1]  # that will extract the 
                                                        # name of the class.  
            module_name = 'UNSPECIFIED_'+module_name
            
        dir_path = self.get_daily_directory() +'\\'+ module_name
        
        if not os.path.exists(dir_path):        
            os.makedirs(dir_path)
        return dir_path




#    def pack(data):
#      # create the result element
#      result = xml.Element("Array")
#    
#      # report the dimensions
#      ref = data
#      while isinstance(ref, list):
#        xml.SubElement(result, "Dimsize").text = str(len(ref))
#        ref = ref[0]
#    
#      # flatten the data
#      while isinstance(data[0], list):
#        data = sum(data, [])
#    
#      # pack the data
#      for d in data:
#        result.append(pack_simple(d))
#    
#      # return the result
#      return result    


# from Manager:



        
#     def get_dll_dir(self):
#         """ Returns the absolut path to the directory of our dlls.
        
#           @return string: path to the dll directory       
#         """
#         dll_path = self.get_main_dir() + '\\hardware\\dll'
#         self.logMsg('Filepath request to dll was called.',importance=0)
        
#         return dll_path
#       