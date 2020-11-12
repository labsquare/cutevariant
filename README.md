# Cutevariant

**A standalone and free application to explore genetics variations from VCF file**


![CI](https://github.com/labsquare/cutevariant/workflows/CI/badge.svg)



Cutevariant is a cross-plateform application dedicated to maniupulate and filter variation from annotated VCF file. 
When you create a project, data are imported into an sqlite database that cutevariant queries according your needs. 
Presently, SnpEff and VEP annotations are supported. 
Once your project is created, you can query variant using different gui controller or directly using the VQL language. This Domain Specific Language is specially designed for cutevariant and try to keep the same syntax than SQL for an easy use.

![](https://raw.githubusercontent.com/labsquare/cutevariant/devel/screencast.gif)



| | | |
|:-------------------------:|:-------------------------:|:-------------------------:|
|<img width="1604" alt="screen shot 2017-08-07 at 12 18 15 pm" src="https://raw.githubusercontent.com/labsquare/cutevariant/devel/screenshot1.png"> |<img width="1604" alt="screen shot 2017-08-07 at 12 18 15 pm" src="https://raw.githubusercontent.com/labsquare/cutevariant/devel/screenshot2.png">|<img width="1604" alt="screen shot 2017-08-07 at 12 18 15 pm" src="https://raw.githubusercontent.com/labsquare/cutevariant/devel/screenshot4.png">|


# Installation

## Windows 
[Windows standalone binary](https://github.com/labsquare/cutevariant/releases/download/0.2.1/cutevariant-win32-latest.zip)

## PyPi
Cutevariant is avaible from [Pypi](https://pypi.org/project/cutevariant/) : 

    pip install cutevariant # install
    cutevariant             # run

## From source 
- Python 3.7 or newer is required  

```
git clone https://github.com/labsquare/cutevariant.git
make install_deps 
make run 
```

## Contributions / Bugs
cutevariant is a new project and all contributors are welcome.
### Issues
If you found a bug or have a feature request, you can report it from the [Github isse trackers](https://github.com/labsquare/cutevariant/issues).

### Create a plugin
Documentation to create a plugin is [available here](https://github.com/labsquare/cutevariant/wiki/Plugins)

### Chat 
You can join us [on discord](https://discord.gg/7sSH4VSPKK). We are speaking french right now, but we can switch to english. 


