# Cutevariant

**A standalone and free application to explore genetics variations from VCF file**

A preprint is [available in bioRxiv](https://www.biorxiv.org/content/10.1101/2021.02.10.430619v1)
Documentation available on [cutevariant.labsquare.org](cutevariant.labsquare.org/)

[![Test](https://github.com/labsquare/cutevariant/actions/workflows/test.workflows.yml/badge.svg)](https://github.com/labsquare/cutevariant/actions/workflows/test.workflows.yml) [![codecov](https://codecov.io/gh/labsquare/cutevariant/branch/devel/graph/badge.svg?token=p5CNtiNIfD)](https://codecov.io/gh/labsquare/cutevariant)

Cutevariant is a cross-plateform application dedicated to maniupulate and filter variation from annotated VCF file. 
When you create a project, data are imported into an sqlite database that cutevariant queries according your needs. 
Presently, SnpEff and VEP annotations are supported. 
Once your project is created, you can query variant using different gui controller or directly using the VQL language. This Domain Specific Language is specially designed for cutevariant and try to keep the same syntax than SQL for an easy use.

![](https://raw.githubusercontent.com/labsquare/cutevariant/master/screencast.gif)



| | | |
|:-------------------------:|:-------------------------:|:-------------------------:|
|<img width="1604" alt="screen shot 2017-08-07 at 12 18 15 pm" src="https://raw.githubusercontent.com/labsquare/cutevariant/master/screenshot1.png"> |<img width="1604" alt="screen shot 2017-08-07 at 12 18 15 pm" src="https://raw.githubusercontent.com/labsquare/cutevariant/master/screenshot2.png">|<img width="1604" alt="screen shot 2017-08-07 at 12 18 15 pm" src="https://raw.githubusercontent.com/labsquare/cutevariant/master/screenshot4.png">|


# Installation

## Windows 
Standalone binary are available for windows:  
- [Download cutevariant 32 bit](https://github.com/labsquare/cutevariant/releases/latest/download/cutevariant-standalone-x86.zip)
- [Download cutevariant 64 bit](https://github.com/labsquare/cutevariant/releases/latest/download/cutevariant-standalone-x64.zip)

## PyPi
Cutevariant is avaible from [Pypi](https://pypi.org/project/cutevariant/) : 

    pip install cutevariant # install
    python -m cutevariant   # run

## From source 
- Python 3.7 or newer is required  

```bash
# Clone repository
git clone https://github.com/labsquare/cutevariant.git
cd cutevariant
# Create a virtual environement
python3 -m virtualenv venv 
source venv/bin/activate
# Install cutevariant in local mode
python -m pip install -e 
# Run cutevariant as module 
python -m cutevariant # or `make run`
# Run test 
python -m pytest tests
```

## Usages 
You can follow this tutorial to familiarize yourself with cutevarant.       
https://github.com/labsquare/cutevariant/wiki/Usage-examples

The VQL langage specification is available here :      
https://github.com/labsquare/cutevariant/wiki/VQL-language

## Contributions / Bugs
Cutevariant is a new project and all contributors are welcome
### Issues
If you found a bug or have a feature request, you can report it from the [Github isse trackers](https://github.com/labsquare/cutevariant/issues).

### Create a plugin
Documentation to create a plugin is [available here](https://github.com/labsquare/cutevariant/wiki/Plugins)

### Chat 
You can join us [on discord](https://discord.gg/7sSH4VSPKK). We are speaking french right now, but we can switch to english. 

## Licenses
This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see https://www.gnu.org/licenses/gpl-3.0.txt.
