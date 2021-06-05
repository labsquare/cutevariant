VQL is a Domain Specific Language to perform several actions on a cutevariant project. The main purpose is to filter variants in the same fashion as a SQL query. VQL language can be run from the user interface vql plugin or directly in command line. 

## SELECT clause

*SELECT* clause is used to choose which fields are displayed.

- Display two fields from variants tables 
```sql 
SELECT chr, pos FROM variants
```

- Display impact, which is an annotation field, from variants tables 
```sql 
SELECT chr, pos, ann.impact FROM variants
```

- Display genotype field from "boby" sample 
```sql 
SELECT samples['boby'].gt FROM variants
# If you omit the field, by default it will select gt 
SELECT samples['boby'] FROM variants
```

## Special fields
When importing a VCF file, cutevariant computes fields that are not usually present in VCF files. These fields describe genotype properties. Example:

:material-numeric: **count_hom** : counts how many homozygous mutant within samples   
:material-numeric: **count_ref** : counts how many homozygous wild within samples   
:material-numeric: **count_het** : counts how many heterozygous mutant within samples   
:material-numeric: **count_var** : counts how many variation (homozygous or heterozygous)  within samples   

For instance, with a variant dataset of two samples (boby and raymond), the following lines are equivalent:

```sql 
SELECT chr, pos FROM variants WHERE (samples["boby"].gt = 1 AND samples["raymond"].gt = 2) OR (samples["boby"].gt = 2 AND samples["raymond"].gt = 1)
SELECT chr, pos FROM variants WHERE count_hom = 1 AND count_het=1
```

If your dataset was imported with a pedigree, cutevariant counted case and control status of samples, along with their genotype

:material-numeric: **case_count_hom**    : count how many homozygous mutant within samples   
:material-numeric: **case_count_ref**    : count how many homozygous wild within samples   
:material-numeric: **case_count_het**    : count how many heterozygous mutant within samples   
:material-numeric: **control_count_hom** : count how many homozygous mutant within samples   
:material-numeric: **control_count_ref** : count how many homozygous wild within samples   
:material-numeric: **control_count_het** : count how many heterozygous mutant within samples   

For instance, with 4 affected samples and 6 unaffected samples, look for all variant which are heterozygous in affected samples and homozygous in unaffected samples:

```sql
SELECT chr,pos FROM variants WHERE case_count_ref = 4 AND control_count_hom = 6
```

## WHERE clause 
*WHERE* clause is used to filter variants according to condition rules. 

### List of accepted operators
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

## CREATE clause 
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

## IMPORT clause 
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


-------------------------------




!!! tip
- You can use as many parenthesis as needed to separate the statements.

Currently, cutevariant supports 4 data types:
- Strings
- Integers
- Decimal numbers
- Booleans

### String operators

The simplest operators on strings are `=` and `!=`, respectively equality and inequality operators.
They apply on string fields, and there must be a perfect match between the field's value and the right hand side value.
However, most of the time you don't know the exact name of the gene you're looking for beforehand.
For instance, you may be looking for variants involving a whole gene family, or a known biological pathway. In this case, you need more data to match the field against, and therefore, more complex operators.

Luckily enough, there are three ways to address these types of issues.

#### Using regular expressions

First, you can use regular expressions. In cutevariant, we use python regular expressions engine under the hood, so [here](https://docs.python.org/3/library/re.html#regular-expression-syntax){target=_blank} is a great reference to get you started with this syntax.

Below is an example of how to use regular expressions to select only [transversions](https://en.wikipedia.org/wiki/Transversion){target=_blank}.

In VQL, the regular expression operator is `~`. Let's see how to use it in order to select transversion variants.

```sql
SELECT chr,pos,ref,alt FROM variants WHERE ref ~ '^[AG]$' AND alt ~ '^[CT]$'
```

You can read this statement as SELECT chr,pos,ref,alt WHERE ref matches either A or G, **and** alt matches C or T (from table variants).

Note that an alternative to regular expressions, in this particular case, would be:

`SELECT chr,pos,ref,alt FROM variants WHERE (ref='A' OR ref='G') AND (ref='C' OR ref='T')` which is much more verbose and harder to read than the regex way.

For a more advanced exploration of regular expressions (if you're already familiar with them but need more in-depth approach), I would suggest you train on this
really cool [website](https://regex101.com/), that helps you build and test regular expressions.

#### Using wordsets

You can also define wordsets. These can contain any arbitrary number of strings, and can be loaded from a file.

Usage example:
`SELECT chr,pos,ref,alt,ann.gene FROM variants WHERE ann.gene IN WORDSET['My wordset']`

This will select every variant for which the gene annotation is in the wordset `My wordset`. Note the use of the `IN` operator, that can be negated with `NOT IN`.

To keep track of existing wordsets, create new ones, and modify them, there is a wordset plugin, which usage is described [here](../plugins/wordset.md).

#### Using string lists

Last but not least, you can use string lists. This is an intermediate solution between equality/inequality operators, where you specify the exact match, and the wordset operators where you can have very long list of strings to match against.

Let's say you have a few gene names that you want to look for, then this is the perfect use case for string list matching.
In VQL, this translates into :

`SELECT chr,pos,ref,alt,ann.gene FROM variants WHERE ann.gene IN ('gene A','gene B','gene C')`

You can specify as many values as you want, as long as you quote the reference strings, separate values with commas, and put the whole test expression between parenthesis.

Note though, that if you have too many strings to test against one field, you may end up cluttering the VQL expression and make it hard to read.

If you need to do really complex filtering operations, you can break them down by creating new [sources](../plugins/selections.md)[^1], *a.k.a.* selections.

### Number operators

You can use any comparison operator on number, the only limitation is that you need to apply them one at the time.
For instance, the following VQL statement is not valid:

`SELECT chr,pos,ref,alt FROM variants WHERE 1000 < pos < 3000`

Instead, you need to use logical operators (such as `AND` and `OR`). So here is one possible fix for the above statement:

`SELECT chr,pos,ref,alt FROM variants WHERE pos > 1000 AND pos < 3000`

### Boolean operators

Some fields are booleans. As of 2021.05.08 release, you still need a comparison operator with them, such as `=`/`!=` and compare against True/False or 1/0.

For instance, this command is not valid:

`SELECT chr,pos,ref,alt FROM variants WHERE favorite`

Where this is one possible fix:

`SELECT chr,pos,ref,alt FROM variants WHERE favorite=True`

Allowed boolean values are:
- `True`, `true`, or `1`
- `False`, `false`, or `0`

Please keep in mind that these are case sensitive, which means that TRUE won't evaluate to true, and so on.


