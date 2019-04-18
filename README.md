# objectbox-python

An unofficial binding of ObjectBox for Python 3.

## Requirements

Linux, only tested on Ubuntu 16.04 x86_64. Make sure that Python 3 and `libobjectbox.so` are installed and that you have [flatc](https://github.com/google/flatbuffers) readily available.

1. `pip3 install flatbuffers`
2. `./objectbox-pygen.py /path/to/flatc entities.fbs`
3. `./demo.py 123 hello`

If everything works correctly, an output like the following should appear:

    before: 0
    after: 1
