VQL is a Domain Specific Language to perform several action on a cutevariant project. The main purpose is to filters variants in the same fashion as a SQL query. VQL language can be run from the user interface vql plugin or directly in command line. 

# SELECT clause 

*SELECT* clause is used to choose which fields are displayed.

- Display two fields from variants tables 
```sql 
SELECT chr, pos FROM variants
```

- Display annotations fields from variants tables 
```sql 
SELECT chr, pos, annotations.impact FROM variants
# You can omit annotations prefix 
SELECT chr, pos, impact FROM variants
```

- Display genotype field from "boby" sample 
```sql 
SELECT sample['boby'].gt FROM variants
# If you omit the field, by default it will takes gt 
SELECT sample['boby'] FROM variants
```

#### Special fields 
there is special computed fields which allow to perform operation on genotype 

* **count_hom** : count how many homozygous mutant within samples   
* **count_ref** : count how many homozygous wild within samples   
* **count_het** : count how many heterozygous mutant within samples   
* **count_var** : count how many variation (homozygous or heterozygous)  within samples   

For instance, with a variant dataset of two sample (boby and raymond), the following lines are equivalents : 

```sql 
SELECT chr, pos FROM variants WHERE sample["boby"].gt = 1 AND sample["raymond"].gt = 2
SELECT chr, pos FROM variants WHERE count_hom = 1 AND count_het=1
```

If your dataset has been imported with a pedigree, you can also filter with case and control status of samples

* **case_count_hom**    : count how many homozygous mutant within samples   
* **case_count_ref**    : count how many homozygous wild within samples   
* **case_count_het**    : count how many heterozygous mutant within samples   
* **control_count_hom** : count how many homozygous mutant within samples   
* **control_count_ref** : count how many homozygous wild within samples   
* **control_count_het** : count how many heterozygous mutant within samples   

For instance, with 4 affected samples and 6 normal samples, look for all variant which are heterozygous in affected samples and homozygous in normal samples : 

```sql
SELECT chr, pos FROM variants WHERE case_count_ref = 4 AND control_count_hom = 6
```

# WHERE clause 
*WHERE* clause is used to filter variants according to condition rules. 

## List of accepted operators
- Comparative operators:
```sql
WHERE field = "value" 
WHERE field = 234
WHERE field != 324
WHERE field > 34
WHERE field < 30
```

- Membership operators:
```sql
WHERE field IN ("CFTR", "boby")
WHERE field IN WORDSET["mylist"]  # See WORDSETS
WHERE field HAS "exonic" (apply to list-like fields, *eg.* `WHERE consequence HAS "stop_gained"`)
```

- String comparison operators (apply mostly to string-like fields):
```sql
WHERE field LIKE "test" (, *eg.* `WHERE gene LIKE "NTRK%"`, to filter variants on genes NTRK1, NTRK2...)
WHERE field NOT LIKE "test" (opposite of 'LIKE' operator)
WHERE field ~ "\d+"  # Regular expression 
```

- Special cases using 'NULL' SQL private word:
```sql
WHERE field IS NULL (the 'NULL' being a field with NO defined value ; 0 != NULL) 
WHERE field IS NOT NULL (opposite of 'IS NULL' expression)
```

## Examples using WHERE
- Filters fields using *WHERE*:
```sql 
SELECT chr,pos FROM variants WHERE pos > 3 
```
- *WHERE* can be a nested condition of OR/AND statements:
```sql 
SELECT chr,pos FROM variants WHERE (pos > 3 AND pos < 100) OR (impact = 'HIGH')
```

- *WHERE* supports regular expression. But this can be computing intensive:
```sql 
SELECT chr,pos FROM variants WHERE transcript ~ "NM.+"
```

- *HAS* operator looks for a word in a list separated by semicolon (exonic;intronic)
```sql 
SELECT chr,pos FROM variants WHERE consequence HAS "exonic"
```

- You can also filter using inline wordSet or a created one:
```sql 
SELECT chr,pos FROM variants WHERE gene IN ("CFTR", "GJB2")
SELECT chr,pos FROM variants WHERE gene IN WORDSET["genelist"] 
```

# CREATE clause 
*CREATE* clause is used to create a _selection_ or _tables_  of variants.
For instance the following code create a new selection named *myselection*

```sql
CREATE myselection FROM variants WHERE gene = 'CFTR' 
# You can now select variants from CFTR gene without a filters 
SELECT chr,pos FROM myselection
```

You can also create a selection using set operation performed on 2 different selections.
Actually union, intersection and difference are supported 

```sql
# Intersection between A and B 
CREATE myselection = A & B 
# Union between A and B 
CREATE myselection = A | B 
# Difference between A and B 
CREATE myselection = A - B 
```

You can also make an intersection with a bed file : 

```sql
CREATE myselection FROM variants INTERSECT "/home/boby/panel.bed"  
```

# IMPORT clause 
VQL supports importation of different features. Currently, it supports only word WORDSETS. 
For example, using a simple text file containing a list of words : 

```sql 
IMPORT WORDSETS "gene.txt" AS mygenes
SELECT chr, pos FROM variants WHERE gene in WORDSET["mygenes"]

```

# DROP clause 
This clause remove selection or wordset accoding to their names.

```sql
# Remove selection named myselection
DROP SELECTIONS myselection

# Remove wordset named mygenes
DROP WORDSETS mygenes
```





