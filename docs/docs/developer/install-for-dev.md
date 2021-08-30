This documentation assumes that you are working under a Linux environment with python 3.7 or newer. But the process is almost the same for windows and mac os.

# Installation from source 

> :material-information-outline: Please note that in order to avoid any conflict between python modules, it is strongly advised that you install cutevariant in its own python virtual environment. However, due to the very few dependencies of cutevariant (only PySide2 and numpy for now), this package will have very low impact on your python environment.

Python 3.7 or newer is required

```bash
# Clone repository
git clone https://github.com/labsquare/cutevariant.git
cd cutevariant
# Create a virtual environement
python3 -m virtualenv venv 
source venv/bin/activate
# Install cutevariant in local mode
python -m pip install -e .
# Run cutevariant as module 
python -m cutevariant # or `make run`
# Run test 
python -m pytest tests
```