""" This module contain all the import related function for Qudi files

It is order from the low level reading of raw file to the high level Dataframe constructor

"""
from pathlib import Path
import numpy as np
import pandas as pd


def parse_data_file(filename, filters=[], do_not_load_data=False):
    """ Read a Qudi ".dat" data file and return the parameters, columns and data parsed

    @param string filename: the file to read
    @param list(function) filters: list of functions to filter
    @param (bool) do_not_load_data: Force the function to return only the parameters and the columns

    @return tuple dict(parameters), list(columns), numpy_2d_array(data)

    This function :
    1. First read the parameters of the file line by line to construct a dictionary of the parameters.
    2. Check if all the filters return True when given the built dictionary
    3. Build an list of the data columns keys
    4. Load the data via numpy.loadtxt() (or use pandas.read_csv() if first option fails)

    Function return None if filtered out

    Data is always returned as a 2d numpy array.
    """
    # 1.
    try:
        file = open(filename, "r")
    except FileNotFoundError:
        raise FileNotFoundError('The file specified does not exist.')
    line = file.readline()
    last_line = ''  # last line will be the data keys
    parameters = {}
    while line[0] == '#':  # read line by line as long as the line start by a #
        line = line[1:]  # remove the '#' character
        pair = line.split(':')
        if len(pair) == 2:  # if line is a key value pair
            key, value = pair
            if key not in ['Parameters', 'Data']:  # Do not confuse these two lines with a parameter
                try:
                    value = float(value)
                except ValueError:  # If value can not be parsed as a float, use a string
                    value = str.strip(value)
                parameters[key] = value
        last_line = line
        line = file.readline()
    # 2.
    for filter in filters:  # If the filter applied on the parameters return False, do not load
        if not filter(parameters):
            return None
    # 3.
    columns = last_line.split('\t')
    columns = [column.strip() for column in columns]
    if '' in columns:  # Can occur because of \t at the end of the line
        columns.remove('')

    if do_not_load_data:
        return parameters, columns, None
    # 4.
    try:
        data = np.loadtxt(filename)
    except ValueError:  # If file can not be parsed, probably because there is a string in the data.
        # Let's use pandas read_csv instead, we will get array of objects instead of numbers
        try:
            data = pd.read_csv(filename, comment='#', sep='\t', header=None).values
        except ValueError:
            print('Can not read file {}, something is wrong with it. File ignored.'.format(filename))
            return
    if data.ndim == 1:
        data = data[np.newaxis, :]
    elif data.ndim == 2:
        data = data.transpose()
    else:
        raise ValueError('The number of dimension of this file is neither 1 or 2.')
    return parameters, columns, data


def get_serie_from_file(filename, filters=[]):
    """ Get a pandas Series corresponding to a single file

    @param (str) filename: the file to read
    @param list(function) filters: list of functions to filter out files before full loading (see parse_data_file)

    @return pandas.Series: Panda series representing the data file

    Each parameter will lead to a key in the series index with its corresponding value
    Each data column will lead to a key in the series index with the 1d numpy array as value

    A '_raw_data' column is created containing the full 2d array extracted from numpy.loadtxt method.
    A '_path' column is created containing a reference to the pathlib.Path object
    A '_timestamp' column is created containing timestamp based on the filename

    Return None if filtered out
    """
    parsed = parse_data_file(filename, filters=filters)
    if parsed is None:
        return None
    dictionary, columns, data = parsed
    if len(columns) == len(data):  # if the file is a list of 1d array
        for i, column in enumerate(columns):
            dictionary.update({column: data[i]})
    dictionary.update({'_raw_data': data})
    dictionary.update({'_path': Path(filename)})
    dictionary.update({'_timestamp': pd.to_datetime(Path(filename).stem[0:16], format='%Y%m%d-%H%M-%S')})
    return pd.Series(dictionary)


def get_dataframe_from_files(files, filters=[]):
    """ Get a pandas Dataframe from a list of files

    @param list(str) files: files path
    @param list(function) filters: list of functions to filter out files before full loading (see parse_data_file)

    @return pandas.DataFrame: Panda DataFrame containing all the data, one row per file
    """
    if isinstance(files, str):  # In case only one file has be given directly as a string (instead of a list)
        files = [files]
    series = []
    for file in files:
        serie = get_serie_from_file(file, filters=filters)
        if serie is not None:
            series.append(serie)
    return pd.DataFrame(series)


def get_dataframe_from_folders(folders, filters=[], recursively=True, pattern='*.dat'):
    """ Get a pandas Dataframe from one or multiple folders

    @param list(str) folders: folders path
    @param list(function) filters: list of functions to filter out files before full loading (see parse_data_file)
    @param (bool) recursively: Whether all the sub-folders should be parsed as well
    @param (str) pattern: The pattern fed to glob to filter files by name

    @return (pandas.DataFrame): Pandas DataFrame containing all the data, one row per file

    pattern can be used to filter out folders like : 'Counter/*.dat' will only match .dat file inside a Counter folder.
    See Python glob for more information
    """
    if isinstance(folders, str):  # In case only one file has be given directly as a string (instead of a list)
        folders = [folders]
    total_files = []
    for folder in folders:
        method = Path(folder).rglob if recursively else Path(folder).glob
        files = list(method(pattern))
        total_files.extend(files)
    return get_dataframe_from_files(total_files, filters=filters)


# Last function is apart from the rest. It gives a Dataframe from a single file, another paradigm.
# This paradigm is closer to what Pandas is made for, but is less useful on a day to day basis.
def get_dataframe_from_text_file(file):
    """ Read a Qudi data file and return the file as a one Dataframe, 1 row per file row

    @param file: The file to read

    @return (pandas.DataFrame): The file as DataFrame
    """
    dictionary, columns, _ = parse_data_file(file, do_not_load_data=True)
    dataframe = pd.read_csv(file, comment='#', sep='\t', header=None)
    dataframe.columns = columns
    for key in dictionary:
        dataframe[key] = dictionary[key]
    return dataframe
