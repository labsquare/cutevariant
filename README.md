# Cutevariant

**A standalone and free application to explore genetics variations from VCF file**

[![AppVeyor](https://ci.appveyor.com/api/projects/status/r526oy2rb04663dp?svg=true)](https://ci.appveyor.com/project/dridk/cutevariant-1ex8i)

Cutevariant is a cross-plateform application dedicated to maniupulate and filter variation from annotated VCF file. 
When you create a project, data are imported into an sqlite database that cutevariant queries according your needs. 
Presently, SnpEff and VEP annotations are supported. 
Once your project is created, you can query variant using different gui controller or directly using the VQL language. This Domain Specific Language is specially designed for cutevariant and try to keep the same syntax than SQL for an easy use.

![](https://raw.githubusercontent.com/labsquare/cutevariant/devel/screencast.gif)



| | | |
|:-------------------------:|:-------------------------:|:-------------------------:|
|<img width="1604" alt="screen shot 2017-08-07 at 12 18 15 pm" src="https://raw.githubusercontent.com/labsquare/cutevariant/devel/screenshot1.png"> |<img width="1604" alt="screen shot 2017-08-07 at 12 18 15 pm" src="https://raw.githubusercontent.com/labsquare/cutevariant/devel/screenshot2.png">|<img width="1604" alt="screen shot 2017-08-07 at 12 18 15 pm" src="https://raw.githubusercontent.com/labsquare/cutevariant/devel/screenshot4.png">|


# Installation
## PyPi
Cutevariant is avaible from Pypi : 

    pip install cutevariant # install
    cutevariant             # run

## From source 
- Python 3.7 or newer is required  

```
git clone https://github.com/labsquare/cutevariant.git
make install_deps 
make run 
```
