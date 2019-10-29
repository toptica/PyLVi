# Python-LabVIEW-Interface
With this library it is possible to exchange data between LabVIEW and Python via the ZeroMQ messaging protocoll (http://zeromq.org/).

## Requirements
### LabVIEW
* LabVIEW 2016, 32 bit
* In order to use ZeroMQ it is necessary to install the corresponding LabVIEW implementation. In order to do so download the code (http://labview-zmq.sourceforge.net/) and install it via the VI package manager (VIPM).
* Optional: Install the LabVIEW library with VIPM using the build specification `PyLVi.vipb`.

### Python
* Python >= 3.6
* zmq
* numpy

## Usage
`python_zmq_server.py` is a module that has to be imported by the python user application. Be sure that the code in the section if __name__ == '__main__': is included in the main user application or use the provided template.

See `./examples` for an example on how to use the library.