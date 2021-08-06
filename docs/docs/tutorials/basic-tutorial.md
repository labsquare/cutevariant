We will use the same protocol as SnpEff which is described [on this page](https://pcingola.github.io/SnpEff/examples/).       
As mentioned, the aim is to find a pathogenic mutation in a family of 17 individuals where 3 (in red) are affected by an homozygous inheritance disease.

![](https://pcingola.github.io/SnpEff/images/Cingolani_Figure2.png)  

## Download dataset

- [Download Raw VCF file](https://drive.google.com/file/d/1GtuYPS5b5rNyr39hvtv6Dcbp3wOm9OE2/view?usp=sharing)
- [Download SnpEff Annotated VCF file](https://drive.google.com/file/d/1xcLfioJ5hyNJ3bDlyJfuBbDmftDWUFLH/view?usp=sharing)
- [Download Ped file](https://drive.google.com/file/d/1lrVwpbDhHwM4fVYgvk73YeyIMFDGWyz-/view?usp=sharing)

You can download raw VCF file and annoate yourself using [SnpEff](https://pcingola.github.io/SnpEff/examples/) or [VEP](http://www.ensembl.org/info/docs/tools/vep/index.html).       
But to make the example  easier, we provide the SnpEff annotated file VCF available [here](https://drive.google.com/file/d/1xcLfioJ5hyNJ3bDlyJfuBbDmftDWUFLH/view). 

## Create a new project 
After cutevariant is launched, click on :material-database-plus: new project on the upper toolbar and follow the instructions from the wizard. 
Depending of the size of the file, it can take several minutes to be imported into sqlite database. But keep in mind, this step is performed only once per project. Once created, you can open the sqlite file directly with the :material-database-import: open project button. 
 
![Create new project](https://user-images.githubusercontent.com/1911063/98835839-383e1900-2441-11eb-893f-bd30c5524830.gif)

## Select fields to display
You should now see the following view displaying a table of all variants loaded from the VCF file. Different plugins are available around to control the view and filtering in different way.       
For instance, we selected here from the _columns selector_ plugin, 7 differents fields (chr,pos,ref,alt,consequence,impact,gene).
You can choose as many fields as you wish. But displaying too much fields will be probably unreadable. Instead you can read fields value from of the current selected variant inside the _InfoVariant_ plugin. 

![image](https://user-images.githubusercontent.com/1911063/98836859-7ee04300-2442-11eb-9f51-0b76a0fbdf64.png)

## Filter variant with VQL 
From the original SnpEff documentation, we have to find all variant with HIGH impact where three cases are homozygous mutated and the controls are not. 
Cutevariant generates special fields for each variant, telling the count of sample with a specific genotype. For instance, the field "control_count_hom" return the number of case samples that are homozygous. Using those fields, you can then filters variants which are homozygous in the 3 samples from case group but not in the control group using the following VQL query.

```sql
SELECT favorite,comment,chr,ref,alt,consequence,impact,gene FROM variants 
WHERE case_count_hom = 3.0 AND control_count_hom = 0.0 AND impact = 'HIGH'
```

We then find the variant in CFTR mentioned in the example of snpEff. You can then right-click on this variant to get more information about it.

![image](https://user-images.githubusercontent.com/1911063/98838794-06c74c80-2445-11eb-9373-d0413fada83e.png)



