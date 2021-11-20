Cutevariant support [Variant Call Format (VCF) Version 4.2](https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=&ved=2ahUKEwjJ877s3_nwAhWpAWMBHYjGDp4QFjAAegQIAhAD&url=https%3A%2F%2Fsamtools.github.io%2Fhts-specs%2FVCFv4.2.pdf&usg=AOvVaw3UrlHdXnBVzm0df9OE90Rm).
It is strongly advised to annotate your VCF file in a second pass using annotation tool like [VEP](https://www.ensembl.org/info/docs/tools/vep/index.html) or [SnpEff](https://pcingola.github.io/SnpEff/). Annovar is yet not supported.     

# Quick example
## Create a new project
 We will use the same protocol as SnpEff which is described [on this page](https://pcingola.github.io/SnpEff/examples/).       
As mentioned, the aim is to find a pathogenic mutation in a family of 17 individuals where 3 (in red) are affected by an homozygous inheritance disease.

![](https://pcingola.github.io/SnpEff/images/Cingolani_Figure2.png)  


## Download dataset

We provide here the VCF file annotated with SnpEff with the corresponding ped file.

- [Download SnpEff Annotated VCF file](https://drive.google.com/file/d/1xcLfioJ5hyNJ3bDlyJfuBbDmftDWUFLH/view?usp=sharing)
- [Download Ped file](https://drive.google.com/file/d/1lrVwpbDhHwM4fVYgvk73YeyIMFDGWyz-/view?usp=sharing)


## Create a new project 
After cutevariant is launched, click on :material-database-plus: new project on the upper toolbar and follow the instructions from the wizard. You will import the VCF file with the ped file describing affected and non affected samples.
Depending of the size of the file, it can take several minutes to be imported into sqlite database. But keep in mind, this step is performed only once. After the database creation, you can open the sqlite file directly with the :material-database-import: open project button. 

 
![Create new project](../../images/wizard.gif)

## Select fields to display
You should now see the following view displaying a table of all variants loaded from the VCF file. Different plugins are available around to control the view and filtering in different way. They are available from `view` menu. But you are encouraged to use the VQL which is much faster. For instance, write the following VQL query to select interesting fields: 

```sql
SELECT chr, pos, ref, alt, ann.gene, ann.impact FROM variants
```

![Create new project](../../images/fields.gif)

## Filter variant with VQL 
From the original SnpEff documentation, we have to find all variant with HIGH impact where three affected samples are homozygous mutated and the unaffected are not. 
Cutevariant generates special fields for each variant, telling the count of sample with a specific genotype. For instance, the field "control_count_hom" return the number of affected samples that are homozygous. 
In brief, the following query ask "Give me all variants with HIGH impact which are muted homozygous in 3 affected samples (case) and wild homozygous in 0 unaffected samples (control)".

```sql
SELECT favorite,comment,chr,ref,alt,ann.consequence,ann.impact,ann.gene FROM variants 
WHERE case_count_hom = 3.0 AND control_count_hom = 0.0 AND impact = 'HIGH'
```

![Create new project](../../images/filters.gif)

Congratulation, you succeeded to identify the variant in no time !




