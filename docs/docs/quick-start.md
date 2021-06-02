## Load and read a VCF file  

1. Find a VCF file annotated with SnpEff.     
Cutevariant support [Variant Call Format (VCF) Version 4.2](https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=&ved=2ahUKEwjJ877s3_nwAhWpAWMBHYjGDp4QFjAAegQIAhAD&url=https%3A%2F%2Fsamtools.github.io%2Fhts-specs%2FVCFv4.2.pdf&usg=AOvVaw3UrlHdXnBVzm0df9OE90Rm).
It is strongly advised to annotate your VCF file in a second pass using annotation tool like [VEP](https://www.ensembl.org/info/docs/tools/vep/index.html) or [SnpEff](https://pcingola.github.io/SnpEff/). Annovar is yet not supported.     
An example file is [available here](https://drive.google.com/file/d/1xcLfioJ5hyNJ3bDlyJfuBbDmftDWUFLH/view?usp=sharing) for the quick start.

2. Import VCF into cutevariant
Cutevariant imports data from the VCF file into a local sqlite database. From cutevariant click on :material-database-plus: **New project** to start the import wizard.

![Import wizard](../images/cutevariant_import.gif)