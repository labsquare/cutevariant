# Changelog
All notable changes to this project will be documented in this file.

0.4.4 (2022-06-30)
aaaaaaaaaaaaaaaaaa

- Nothing changed yet.


0.4.2 (2022-06-21)
aaaaaaaaaaaaaaaaaa

- Nothing changed yet.


0.4.1 (2022-06-20)
aaaaaaaaaaaaaaaaaa

- Nothing changed yet.


0.4.0 (2022-06-20)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.8] - 2021-07-04
### Added 
- Bug fixed
- 
## [0.3.7] - 2021-07-04
### Added 
- Bug fixed
- 
## [0.3.6] - 2021-07-04
### Added 
- Bug fixed

## [0.3.5] - 2021-07-04
### Added
#### VQL 
- Add new operator HAS to filter a string in a string list separated by "&" . For instance "intron&exon"
- Make possible to create a condition within all samples.  For instance " SELECT pos FROM variants WHERE sample[*].gt = 1 "

#### Variant view 
- Add Tags option 
- Refactor Formatter plugin. 

#### Filter Editor & Fields Editor 
- You can now drag and drop a condition from the Fields editor 
- Preset are now saved into the config.yaml

#### Groupby plugin
- New groupby plugin making possible to group variants

#### Settings
- Replace QSettings by a yaml file stored in /home/.config/cutevariant/cutevariant.yaml on Linux 




## [0.3.3] - 2021-06-02
### Added
- Add Harmonizome plugin [ test ] 
- Improve actions for differents plugins ) 
- Refactor internal plugin system 
- Fix bugs 
- 
## [0.3.2] - 2021-02-03
- Refactor backend with new VQL to SQL flow 
- Update Filters And Fields editor with new style and features 
- Add new History plugin 
- Add VCF and CSV export features 
- Remove Groupby action from variant view
- Fixed bugs 
- Hot fix : Samples if VQL filter expression generated wrong query


## [0.2.9] - 2021-01-03
### Added
#### Variant View
- Variant count and variant data are loaded separately in different thread 
- Use a cache system to avoid loading variants 2 times during pagination 
- Option to load links from a browser or from an XHR request . See (settings )
- Double click on variant to open default link ( see settings ) 
- Add Shortcut to mark variant as favorite ( space ) and move into the view ( left, right ... ) 
- Add a button to interrupt long query 

#### VQL editor 
- New completer showing fields information 

#### Filter editor 
- Update UI with branching and new buttons
- Filter can now be stored into a Json file 

#### Variant Info 
- New UI to edit current variant 

## [0.2.6] - 2020-12-17
### Added
  - Now sqlite contains NULL for empty string and float Nan values
  - VQL support IS NULL and IS NOT NULL operation
  - Fields can be ignored from Wizard before importation
  - Variant view support double click with default link action
  - Variant view has a debug button to show sql query and Explain Plan


## [0.2.5] - 2020-12-09
### Added
- fix bug with sample fields
- add history plugin
- add Trio analysis plugin
- You must now click on "Apply filter" from the filter plugin
- Add "IS NULL" in VQL
