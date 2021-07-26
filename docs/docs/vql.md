VQL is a Domain Specific Language designed to perform several actions on a cutevariant project. The main purpose is to filter variants using a syntax similar to SQL. VQL language can be run from the [VQL editor](plugins/vql-editor.md).

In most cases, you will use the following **SELECT** statements with **[fields](#fields)**, **[source](#source)** and **[filters](#filters)** to select variants as you like:

```
SELECT {fields} FROM {source} WHERE {filters} 
```

## Fields

Fields are arguments for the `SELECT` command, and correspond to the name of the columns you want to select in the variant view.
These columns belong to 3 categories. **variants**, **transcripts** or **samples**.

### Variants 
Annotation about a variant can be selected from their name. They are available from the *Fields plugin* in the **variants** tab. 

- Display chromosome and positions:

```sql 
SELECT chr, pos FROM variants
```

- Display chromosome, position, reference and alternative base where quality is greater than 30:

```sql
SELECT chr, pos, ref,alt FROM variants WHERE qual > 30
```

### Transcripts
One variant may have multiple transcripts with their own annotations. In VQL, they must be prefixed by ```ann.```
They are available from the *[Fields editor Plugin](plugins/fields.md)* in the **annotations** tab. 

!!!note 
When selected an annotation field, variant in the list view output are duplicated. One for each variants. 

- Display impact, which is an annotation field, from variants tables 
```sql 
SELECT chr, pos, ann.impact, ann.gene FROM variants
```

- Select variant where gene is CFTR 
```sql
SELECT chr, pos, ref, alt FROM variants WHERE ann.gene = "CFTR"
```
### Samples

With each variant comes the list of samples it was found in, along with their properties, if any (this corresponds to the INFO field in a VCF).

Cutevariant can show you, for each sample, the attached fields, such as genotype (gt), sequencing depth (dp), or allele frequency (af, vaf) just to name a few.

The **gt field** can have the following values: 

- -1 : Unknown genotype
- 0: homozygous ref (0/0)
- 1: heterozygous (1/0 or 1|0 or 0|1)
- 2: homozygous alt

In VQL, these fields are selected using the sample name (quoted) between square brackets. They are available from the [fields editor plugin](plugins/fields.md) in the **sample** tab. 

- Display genotype field from "boby" sample 

```sql
SELECT samples['boby'].gt FROM variants
/* If you omit the field, by default it will select the genotype */
SELECT samples['boby'] FROM variants
```

- Display depth and VAF from "boby" samples:

```sql
SELECT samples['boby'].dp , samples['boby'].af FROM variants
```

- Get variants where boby is hererozygous:
```sql
SELECT chr,pos,ref,alt FROM variants WHERE samples["boby"].gt = 1
```

- Get variants where all samples are heterozygous:
```sql
SELECT chr,pos,ref,alt FROM variants WHERE samples[*].gt = 1
```


### Special fields
When importing a VCF file, cutevariant computes fields that are not usually present in VCF files. These fields describe genotype properties. Example:

- **count_hom**: counts how many homozygous mutant within samples   
- **count_ref**: counts how many homozygous wild within samples   
- **count_het**: counts how many heterozygous mutant within samples   
- **count_var**: counts how many variation (homozygous or heterozygous)  within samples   

For instance, with a variant dataset of two samples (boby and raymond), the following lines are equivalent. Meaning, selecting all variants with 1 sample homozygous and 1 sample heterozygous.

```sql 
SELECT chr, pos FROM variants WHERE (samples["boby"].gt = 1 AND samples["raymond"].gt = 2) OR (samples["boby"].gt = 2 AND samples["raymond"].gt = 1)
SELECT chr, pos FROM variants WHERE count_hom = 1 AND count_het=1
```

If your dataset was imported with a pedigree, cutevariant also counts case and control status of samples, along with their genotype

- **case_count_hom**   : counts how many homozygous mutant within affected samples   
- **case_count_ref**   : counts how many homozygous wild within affected samples   
- **case_count_het**   : counts how many heterozygous mutant within affected samples  
- **control_count_hom**: counts how many homozygous mutant within unaffected samples   
- **control_count_ref**: counts how many homozygous wild within unaffected samples   
- **control_count_het**: counts how many heterozygous mutant within unaffected samples   

For instance, with 4 affected samples and 6 unaffected samples, select variants which are homozygous mutant in affected samples and heterozygous in unaffected samples:

```sql
SELECT chr,pos FROM variants WHERE case_count_hom = 4 AND control_count_het = 6
```


## Source

Sources are selections that contain variants. By default, all variants belong to the **variants** selection. During your analysis, you may want to create new sub-selections from the [source editor plugin](plugins/selections.md). Then you can select variants from this new source.

```sql 
/* Create a new source with only "C" as reference */
CREATE subsetA FROM variants WHERE ref = "C"
SELECT chr, pos, ref, alt FROM subsetA
```

## Filters
The `WHERE` clause is used to filter variants according to condition rules.
You can edit the filter manually using the [filter plugin](plugins/filters.md). 

### Arithmetic operators
Traditional arithmetic operator are supported:

```sql
WHERE field = "value" /* field equals string value */
WHERE field = True    /* For boolean, you can use True/False or 0/1 */
WHERE field = 233244  /* field equals integer value */
WHERE field != 32234  /* field is different from (supports any type of value)*/
WHERE field > 333334  /* field is greater than (float or integer) */
WHERE field >= 34333  /* field is greater than or equals (float or integer)*/
WHERE field < 301111  /* field is lower than equals (float or integer)*/
WHERE field <= 30444  /* field is lower than or equals (float or integer)*/
```

Empty fields are selected as follow:

```sql
WHERE field = NULL   /* Field is empty*/
WHERE field != NULL   /* Field is not empty*/
```


`IN` operator is used to test if a set contains the given field:
```sql
WHERE field IN ("CFTR", "boby")
WHERE field IN WORDSET["mylist"]
```
See [wordsets plugin](plugins/wordset.md) for the second one.

[Regular expression](https://en.wikipedia.org/wiki/Regular_expression) is supported using the ```~``` operator:

```sql
WHERE gene ~ "HLA-.+"
```
### Logical operators
Condition rules can be combined using **AND** and **OR** operator. In the [filter plugin](plugins/filters.md), It will generate a nested tree of condition.

- Select variants where position belongs to a range:
```sql 
SELECT chr,pos FROM variants WHERE pos > 10 AND pos < 1000 
```

- Select variants with MODERATE OR HIGH impact in the CFTR gene
```sql 
SELECT chr,pos FROM variants WHERE ann.gene ='CFTR' AND (ann.impact = "LOW" OR ann.impact="HIGH")
```

## Other keywords
### Create a selection 

*CREATE* clause is used to create a [selection](plugins/selections.md) of variants.
For instance the following code creates a new selection named *myselection*

```sql
CREATE myselection FROM variants WHERE ann.gene = 'CFTR' 
/* You can now select variants from CFTR gene without any filters */
SELECT chr,pos FROM myselection
```

You can also create a selection using set operations performed on 2 different selections.
Currently, union, intersection and difference operators are supported 

```sql
/*Intersection between A and B */
CREATE myselection = A & B 
/*Union between A and B */
CREATE myselection = A | B 
/*Difference between A and B */
CREATE myselection = A - B 
```

You can also make an intersection with a bed file : 

```sql
CREATE myselection FROM variants INTERSECT "/home/boby/panel.bed"  
```

### Importing a wordset

VQL supports importation of different features. Currently, it supports only word WORDSETS. 
For example, using a simple text file containing a list of words: 

```sql 
IMPORT WORDSETS "gene.txt" AS mygenes
SELECT chr, pos FROM variants WHERE gene IN WORDSET["mygenes"]

```

### Drop selection or wordset
This clause removes a selection or a wordset based on their names.

```sql
/* Remove selection named myselection */
DROP SELECTIONS myselection

/* Remove wordset named mygenes */
DROP WORDSETS mygenes
```
