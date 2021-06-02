## Load and read a VCF file  

### Find a VCF file annotated with SnpEff.     
Cutevariant support [Variant Call Format (VCF) Version 4.2](https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=&ved=2ahUKEwjJ877s3_nwAhWpAWMBHYjGDp4QFjAAegQIAhAD&url=https%3A%2F%2Fsamtools.github.io%2Fhts-specs%2FVCFv4.2.pdf&usg=AOvVaw3UrlHdXnBVzm0df9OE90Rm).
It is strongly advised to annotate your VCF file in a second pass using annotation tool like [VEP](https://www.ensembl.org/info/docs/tools/vep/index.html) or [SnpEff](https://pcingola.github.io/SnpEff/). Annovar is yet not supported.     
An example file is [available here](https://drive.google.com/file/d/1xcLfioJ5hyNJ3bDlyJfuBbDmftDWUFLH/view?usp=sharing) for the quick start.

### Import VCF into cutevariant
Cutevariant imports data from the VCF file into a local sqlite database. From cutevariant click on :material-database-plus: **New project** to start the import wizard.

![Import wizard](../images/cutevariant_import.gif)

1. In the first page, set a project name with a destination path. This is your sqlite database file. 
2. In the second page, select your VCF file. SnpEff or VEP annotation will be autodetected. However, you can force the usage of a specific annotation by selecting the parser in the combo box.
3. The Third page is optional and can be skipped. It asks you to edit samples pedigree found in the VCF file. You can edit it manually or by loading a PED file. Using a pedfile makes available extra fields to filters variants.
4. The Fourth page shows you all available fields from the VCF file. Select the ones you want to import. *chr*, *pos*, *ref*, *alt* are mandatories field and cannot be ignored.
5. The final page starts the database creation. It may take a while depending the size of the VCF file. For a typical Exome with 30 000 annotated variants and one sample, it takes around 5 minutes on a personal computer. 

### Select and filters variants 

The fastest way to query a set of variants is to use a VQL statement from the VQL editor. 
This langage looks like SQL and allows to filters variants using logical and arithmetics operators.     
For instance, the following query select variants with a quality greather than 30 and with a HIGH predicted impact. 

```sql
SELECT chr,pos,ann.gene, ann.impact FROM variants WHERE ann.impact = "HIGH" AND qual > 30
```




