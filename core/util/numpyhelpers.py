# -*- coding: utf-8 -*-

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
