VQL is a Domain Specific Language designed to perform several actions on a cutevariant project. The main purpose is to filter variants in the same fashion as a SQL query. VQL language can be run from the VQL editor.

In the most of the case, you will use the following **SELECT** statements with **[fields](#fields)**, **[source](source)** and **[filters](filters)** to select variants as you like:

```
SELECT {fields} FROM {source} WHERE {filters} 
```

## Fields
Columns that you displayed belongs to 3 categories. **variants**, **transcripts** or **samples**.

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
One variant may have multiple transcript with their own annotation. In VQL, they must be prefixed by ```ann.```
They are available from the *Field Plugin* in the **annotations** tab. 

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
There are annotation associated with a variant and a sample. For instance, the genotype (gt) of a variant for a sample. 
The **gt field** can have the following values: 

- -1 : Unknown genotype
- 0: wild homozygous (0/0)
- 1: heterozygous (1/0 or 1|0 or 0|1)
- 2: mutant homozygous

In VQL, these fields are selected using the sample name between bracket. They are available from the *Field Plugin* in the **sample** tab. 

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

- Get variants where boby is hererozygous :
```sql 
SELECT chr,pos,ref,alt FROM variants WHERE samples["boby"].gt = 1
```

- Get variants where all samples are heterozygous :
```sql 
SELECT chr,pos,ref,alt FROM variants WHERE samples[*].gt = 1
```


### Special fields
When importing a VCF file, cutevariant computes fields that are not usually present in VCF files. These fields describe genotype properties. Example:

- **count_hom** : counts how many homozygous mutant within samples   
- **count_ref** : counts how many homozygous wild within samples   
- **count_het** : counts how many heterozygous mutant within samples   
- **count_var** : counts how many variation (homozygous or heterozygous)  within samples   

For instance, with a variant dataset of two samples (boby and raymond), the following lines are equivalent. Meaning, selecting all variants with 1 sample homozygous and 1 sample heterozygous.

```sql 
SELECT chr, pos FROM variants WHERE (samples["boby"].gt = 1 AND samples["raymond"].gt = 2) OR (samples["boby"].gt = 2 AND samples["raymond"].gt = 1)
SELECT chr, pos FROM variants WHERE count_hom = 1 AND count_het=1
```

If your dataset was imported with a pedigree, cutevariant counted case and control status of samples, along with their genotype

- **case_count_hom**    : count how many homozygous mutant within samples   
- **case_count_ref**    : count how many homozygous wild within samples   
- **case_count_het**    : count how many heterozygous mutant within samples  
- **control_count_hom** : count how many homozygous mutant within samples   
- **control_count_ref** : count how many homozygous wild within samples   
- **control_count_het** : count how many heterozygous mutant within samples   

For instance, with 4 affected samples and 6 unaffected samples, look for all variant which are heterozygous in affected samples and homozygous in unaffected samples:

```sql
SELECT chr,pos FROM variants WHERE case_count_ref = 4 AND control_count_hom = 6
```

## Source 
Source are selection which contains variants. By default, all variants belong to the **variants** selections. During your analysis, you may want to create a new sub selection from the **source editor plugin**. Then you can  select variants from this new source. 

```sql 
/* Create a new source with only "C" as reference */
CREATE subsetA FROM variants WHERE ref = "C"
SELECT chr, pos, ref, alt FROM subsetA

```

## Filters
*WHERE* clause is used to filter variants according to condition rules.
You can edit the filter manually from the **filter plugin**. 

### Arithmetic operators
Traditional arithmetic operator are supported:

```sql
WHERE field = "value" # field egal string value
WHERE field = True    # For boolean, you can use True/False or 0/1
WHERE field = 233244  # field egal integer value
WHERE field != 32234  # field different from 
WHERE field > 333334  # field greater than
WHERE field >= 34333  # field greater or egal than
WHERE field < 301111  # field lower or egal than
WHERE field <= 30444  # field lower egal than
```

Empty fields are selected as follow:

```sql
WHERE field is NULL   # Field is empty
WHERE field is NOT NULL   # Field is not empty
```

IN operator is supported to test a belonging:
```sql
WHERE field IN ("CFTR", "boby")
WHERE field IN WORDSET["mylist"]  # See WORDSETS
```

[Regular expression](https://en.wikipedia.org/wiki/Regular_expression) is supported using the ```~``` operator:

```sql
WHERE gene ~ "HLA-.+"
```
### Logic operators
Condition rule can be combined using **AND** and **OR** operator. In *Filter plugin*, It will generate a nested tree of condition.

- Select variants where position belongs to a range :
```sql 
SELECT chr,pos FROM variants WHERE pos > 10 AND pos < 1000 
```

- Select variants with MODERATE OR HIGH impact in the CFTR gene
```sql 
SELECT chr,pos FROM variants WHERE (ann.gene ='CFTR' AND (ann.impact = "LOW" OR ann.impact="HIGH"))
```

## Other keywords
### Create a selection 
*CREATE* clause is used to create a _selection_  of variants.
For instance the following code create a new selection named *myselection*

```sql
CREATE myselection FROM variants WHERE gene = 'CFTR' 
/* You can now select variants from CFTR gene without a filters */
SELECT chr,pos FROM myselection
```

You can also create a selection using set operation performed on 2 different selections.
Actually union, intersection and difference are supported 

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

### Import a wordset
VQL supports importation of different features. Currently, it supports only word WORDSETS. 
For example, using a simple text file containing a list of words : 

```sql 
IMPORT WORDSETS "gene.txt" AS mygenes
SELECT chr, pos FROM variants WHERE gene in WORDSET["mygenes"]

```

### Drop selection or wordset
This clause remove selection or wordset accoding to their names.

```sql
/* Remove selection named myselection */
DROP SELECTIONS myselection

/* Remove wordset named mygenes */
DROP WORDSETS mygenes
```
