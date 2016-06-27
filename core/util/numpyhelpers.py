# -*- coding: utf-8 -*-
"""
Numpy array to string conversion functions

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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

from io import BytesIO
import numpy as np

def numpy_to_b(**kwargs):
    f = BytesIO()
    np.savez_compressed(f, **kwargs)
    # f.seek(0)
    #compressed_string = f.read()
    compressed_string = f.getvalue()
    f.close()
    return compressed_string

def numpy_from_b(compressed_b):
    f = BytesIO(bytes(compressed_b))
    np_file = np.load(f)
    redict = dict()
    for name in np_file.files:
        redict.update({name: np_file[name]})
    f.close()
    return redict

if __name__ == '__main__':
    arr = np.random.random_sample([2,3])
    print(arr)
    s = numpy_to_b(x=arr)
    print(s)
    arr2 = numpy_from_b(s)
    print(arr2['x'])
    print('Arrays are numerically close:', np.allclose(arr, arr2['x']))
