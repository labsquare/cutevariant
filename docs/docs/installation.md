# Download and install

## Windows binaries

Windows binaries are available from [github](https://github.com/labsquare/cutevariant/releases).    
They are generated for each release thanks to [github action](https://github.com/labsquare/cutevariant/actions).
It has been tested on Windows 7 and Windows 10. 

[:material-download: Download cutevariant - 32 bits](https://github.com/labsquare/cutevariant/releases/latest/download/cutevariant-standalone-x86.zip)    
[:material-download: Download cutevariant - 64 bits](https://github.com/labsquare/cutevariant/releases/latest/download/cutevariant-standalone-x64.zip)


## Install from Pypi

For Linux, MacOS and windows, cutevariant is available from [pypi](https://pypi.org/project/cutevariant/).     
You need [:material-language-python: Python 3.8 or newer](https://www.python.org/). Older version of Python are not supported. 

```bash
python -m pip install cutevariant
```

!!! bug "Known bug"
    If you run Linux and get the following error:

    ``` bash
    Could not load the Qt platform plugin "xcb"
    ```

    You can fix it with the following command:
    
    ``` bash
    sudo apt-get install libxcb-xinerama0
    ```


## Install from source code

If you are a developer, or need the latest bug fixes and newest features, you can head over to our github repository and clone the devel branch to get the most recent (development) version.

```bash

# Create a virtual env and activate
python -m virtualenv venv
source venv/bin/activate
# Clone the repository and switch to devel
git clone https://github.com/labsquare/cutevariant.git
git checkout devel
# Install cutevariant dependencies  
python -m pip install -e . 
# Run cutevariant 
python -m cutevariant 

```

