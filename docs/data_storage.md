# Data storage with qudi {#data_storage}

Qudi provides data storage objects that can be imported from `qudi.util.datastorage` for saving and 
loading (measurement) data. There is an object for each supported data storage format, which 
currently includes:

- `TextDataStorage` for text files 
- `CsvDataStorage` for csv files (specialized text file)
- `NpyDataStorage` for numpy binary files (.npy)

There may be more supported storage formats in the future (e.g. database storage like SQL or HDF5) 
so you might want to check `qudi.util.datastorage` for any objects not listed in this 
documentation.  
All these objects are derived from the abstract base class `qudi.util.datastorage.DataStorageBase` 
which is defining a generalized API for all storage classes.  
If you want to implement a new storage format class, it must inherit this base class.

The most important API methods that each specialized sub-class must implement are:

```Python
def save_data(self, data, *, metadata=None, notes=None, nametag=None, timestamp=None, **kwargs):
    # Save data to appropriate format
    pass

def load_data(self, *args, **kwargs):
    # Load data and metadata and return it
    pass
```

The exact method signatures with additional keyword-only arguments can differ between storage 
classes and can be looked up individually.

Before you can start saving or loading data arrays with the methods mentioned above, you need to 
instantiate and configure the storage object appropriately.
Each specialized storage object can provide an entirely different set of parameters to initialize.
You can look up configuration options for a specific storage object in the `__init__` method doc 
string of the respective class.  
All configuration parameters present in the `__init__` of the storage class should also be 
accessible through as instance attributes or properties (setters and getters) to read and alter 
them dynamically after the instance has been created.

So the first step before loading and saving data arrays is always to create an instance of the 
desired storage object. 

Here is an example for storing text files that is using a commonly used subset of the available 
`__init__` parameters to initialize the storage object:

```Python
from qudi.util.datastorage import TextDataStorage, ImageFormat

# Instantiate text storage object and configure it
data_storage = TextDataStorage(root_dir='C:\\Data\\MyMeasurementCategory',
                               number_format='%.18e',
                               comments='# ', 
                               delimiter='\t',
                               file_extension='.dat',
                               image_format=ImageFormat.PNG)
```

Let's go through the parameters one-by-one:
- `root_dir`:
  The root or working directory for the storage class to work in. Files will be saved into this dir.
- `number_format`:
  Numpy style format string used to convert the values to text. Can also provide iterable of strings
  for each column.
- `comments`:
  String used at the start of lines in the text file to identify them as comment lines.
- `delimiter`:
  Delimiter string used to separate columns.
- `file_extension`:
  The default file extension to use for new data files. Used if not explicit file name is provided
- `image_format`:
  The image format used to save matplotlib figures to file using storage method `save_thumbnail`.

## Storage location
Generally you have to set the `root_dir` parameter for (file-based) storage objects before saving 
or loading any data.

For your convenience each qudi module (GUI, logic or hardware) has an attribute 
`module_default_data_dir` containing a standardized generic data directory. This directory respects 
the global config options `default_data_dir` and `daily_data_dirs` and adds a module-specific 
sub-directory. If applicable, you should always use this attribute to set `root_dir` in storage 
objects.  
By default this path resolves to: 
`<user home>/qudi/Data/<YYYY>/<MM>/<YYYYMMDD>/<configured module name>`

In case you really want to customize the storage location on a per-module basis, you should 
overwrite `module_default_data_dir` in the module class definition in order to make the custom path 
accessible from outside the module.
By default all file based data is stored in daily sub-directories of the qudi data directory 
(default is `<user_home>/qudi/Data/` but it can be changed via global config parameter 
`default_data_dir`).


## Saving data
The method `save_data` is used to store data in the desired format once the storage object has been 
initialized.  
In the text file example from above this could look like:

```Python
import numpy as np
from datetime import datetime

# Create example data
x = np.linspace(0, 1, 1000)  # 1 sec time interval
y = np.sin(2 * np.pi * 2 * x)  # 2 Hz sine wave
data = np.asarray([x, y]).transpose()  # Format data into a single 2D array with x being the first 
                                       # column and y being the second column
                                       
# Prepare a dict containing metadata to be saved in the file header
metadata = {'sample_number': 42,
            'batch'        : 'xyz-123'}

# Create an explicit timestamp.
timestamp = datetime(2021, 5, 6, 11, 11, 11)  # 06.05.2021 at 11h:11m:11s
# timestamp = datetime.now()  # Usually you would use this

# Create a nametag to include in the file name (optional)
nametag = 'amplitude_measurement'

# Create an iterable of data column header strings (optional)
column_headers = ('time (s)', 'amplitude (V)')

# Create an arbitrary string of informal "lab notes" that is included in the file header
notes = 'This measurement was performed under the influence of 10 mugs of coffee and no sleep.'

# Save data to file
file_path, timestamp, (rows, columns) = data_storage.save_data(data, 
                                                               metadata=metadata, 
                                                               notes=notes,
                                                               nametag=nametag,
                                                               timestamp=timestamp, 
                                                               column_headers=column_headers)
```

This will save the data to a file with a generic filename constructed from nametag and timestamp.
`<default_data_dir>/2021/05/20210506/20210506-1111-11_amplitude_measurement.dat` with the following 
content:

```
# [General]
# disclaimer='Saved Data on 06.05.2021 at 11h11m11s'
# dtype=float64
# comments='# '
# delimiter='\t'
# column_headers='time (s);;amplitude (V)'
# notes='This measurement was performed under the influence of 10 mugs of coffee and no sleep.'
# 
# [Metadata]
# sample_number=42
# batch='xyz-123'
# 
# ---- END HEADER ----
0.000000000000000000e+00	0.000000000000000000e+00
1.001001001001000992e-03	1.257861783874105778e-02
2.002002002002001985e-03	2.515524538937584723e-02
⋮ 				⋮
```

**NOTE**: metadata keys must be str type and not contain leading or trailing whitespaces as well as 
avoid the pattern `'[...]'`.  
**NOTE**: metadata values must be representable and reconstructable via `repr` and `eval`, i.e. 
`value == eval(repr(value))`.

Alternatively it is also possible to specify the filename directly instead of relying on the 
generic construction from nametag and timestamp:

```Python
# Save data to file
file_path, timestamp, (rows, columns) = data_storage.save_data(data, 
                                                               metadata=metadata,
                                                               timestamp=timestamp, 
                                                               column_headers=column_headers, 
                                                               filename='my_custom_filename.abc')
```

This would result in a file at `<default_data_dir>/2021/05/20210506/my_custom_filename.abc`.  
Please note that you need to provide the file extension as well in this case.


### Saving a thumbnail
In order to save a thumbnail alongside the data file, you can create a `matplotlib` figure and pass 
it to the data storage method `save_thumbnail`.  

`save_thumbnail` expects a full file path *without* file extension (this is automatically completed 
according to the configured `image_format` enum).  
Usually you want your thumbnail file name to be the same as your data file name. An easy way to 
achieve that is to remove the file extension from the first return value of `save_data` and pass it 
to `save_thumbnail`.

To continue our example with text files, this could look like:

```Python
import matplotlib.pyplot as plt

# Create figure and plot data
fig = plt.figure()
ax = fig.add_subplot()
ax.plot(x, y)
ax.set_xlabel('time (s)')
ax.set_ylabel('amplitude (V)')

# Save figure as thumbnail with the same file name as the corresponding data file
figure_path = data_storage.save_thumbnail(fig, file_path.rsplit('.')[0])
```

This example creates the file: 
`<default_data_dir>/2021/05/20210506/20210506-1111-11_amplitude_measurement.png`


## Loading data
All storage object provide means to load back data and corresponding metadata from disk.

**ToDo: COMPLETE THIS SECTION**

## Global metadata
It is possible to set global metadata that will be automatically included in all data storage 
objects (class attribute of `DataStorageBase`) until it is actively removed again.
So modules adding global metadata must handle robust and safe cleanup afterwards.

The global metadata is a dict and will be handled exactly the same as the `metadata` keyword-only 
parameter of the data storage `save_data` method. Except it does not need to be given each time 
data is saved and it applies globally to all data storage instances throughout the process.
You can combine global metadata and locally provided metadata. The latter will always take 
precedence over the global metadata if keys are present in both dicts.

### Adding global metadata
You can add global metadata key-value pairs by using the storage object 
class method `<storage_class>.add_global_metadata`. In our example from above this would look like:

```Python
# Create global metadata to ADD to the global metadata dict
global_meta = {'user': 'Batman'}

# Add metadata in a thread-safe way to ALL data storage objects 
data_storage.add_global_metadata(global_meta, overwrite=False)

# This would have the same effect
from qudi.util.datastorage import DataStorageBase
DataStorageBase.add_global_metadata(global_meta)
# ...or this
from qudi.util.datastorage import NpyDataStorage
NpyDataStorage.add_global_metadata(global_meta)

# You can also add a single key-value pair like this:
data_storage.add_global_metadata('frustration_level', 9000, overwrite=False)
```

Note the keyword-only `overwrite` parameter. If this flag is set to `False` (default) the method 
will raise a `KeyError` if any metadata keys to set are already present in the global metadata dict.
If it is set to `True` this method will silently overwrite any key-value pairs.  
It is highly recommended to use the default value (`False`) whenever possible in order to avoid hard
to track bugs when two threads (i.e. qudi logic modules) are using the same metadata keys.

### Removing global metadata
Always make sure the entity that added the global metadata also removes it, e.g. after it is not 
relevant anymore. For example the `on_deactivate` method of a qudi logic module would be a good 
place to remove any global metadata that has been added by the same module.  
You can remove metadata using the storage object class method 
`<storage_class>.remove_global_metadata`, e.g. like:

```Python
# to remove a single key-value pair
data_storage.remove_global_metadata('user')

# or if you want to remove multiple key-value pairs with one call
data_storage.remove_global_metadata(['user', 'frustration_level'])
```

## Logging Data
Another common use-case instead of dumping an entire data set at once is saving one chunk of data 
(or a single entry) at a time by appending to an already created file / database. This could for 
example be be useful for a data logger.

In order to do this, `TextDataStorage` and `CsvDataStorage` have additional API methods `new_file` 
and `append_file`.

`new_file` accepts the same keyword-only arguments as `save_data` and will create a new data file 
containing only the file header. The only difference is an additional keyword-only parameter `dtype`
for which you should provide a `numpy` dtype since it can not be derived from the data array in 
this case (`numpy.float` will be assumed by default).
 
The created file can then be appended by single or multiple rows of data using `append_file` 
(you can also append files created by `save_data`).

An example:
```Python
# Create data file with the same variables as in the save_data example above
file_path, timestamp = data_storage.new_file(metadata=metadata,
                                             notes=notes,
                                             nametag=nametag,
                                             timestamp=timestamp,
                                             column_headers=column_headers,
                                             dtype=np.dtype('float'))

# Append each row of the previously created data array one after the other
for data_row in data:
    data_storage.append_file(data_row, file_path)

# You can also append a chunk of multiple rows at once
data_storage.append_file(data[:10], file_path)
```

**NOTE:** appending to files like this is far less efficient than writing a single 
chunk of data at once. This comes from the implementation detail that each call to `append_file`
will have the overhead of opening and closing a file handle.  
If you are after high-frequency data logging, consider buffering data for a while and writing it 
out in chunks or implement a specialized data storage subclassing of `TextDataStorage` or 
`DataStorageBase`.

### Reading global metadata
You can get a _shallow_ copy of the global metadata dict via:
```Python
metadata = data_storage.get_global_metadata()
```
Since the returned dict is only a shallow copy of the actual global metadata dict one must avoid 
to mutate any of the values unless you are **very** sure what you are doing.


## Thread-Safety
Saving and loading data using the data storage objects is generally not thread-safe. 
In the intended use case of multiple threads reading and writing non-shared individual files, this 
should not pose a problem.  
Every thread should create its own instance of a data storage object and read/write different 
separate files.

The handling of the global parameters (read/add/remove) can be considered thread-safe.
