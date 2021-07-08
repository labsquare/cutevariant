Selections in cutevariant is used to create new source tables for your requests (the FROM part in a VQL statement).

There are three main ways to create a selection, they are lsited below.

## Create source from current selection

In the variant view, you can see the results of your query. If you've just applied a filter that took some time to compute, there is a way to save all the variants that just passed the test, so you won't have to wait again.

To save a selection, just click the '' button in the source editor.

## Create source from intersection with a BED file

You can also create sources from a BED file. These files are just tab seperated text, where the first column identifies the contig ID (*i.e.* the chromosome name usually), and the next two columns indicate the range the feature is in (the latter is decribed by every following column).

Creating an intersection with a BED file means that you will deselect variants that fall outside the features described by the BED file, and save it to a new table.

## Create source from set operations with others

If you've selected interesting variants into two separated sources, then you can combine these two by using available set operations. There are three set operations: intersect, union, and difference. Please keep in mind that the latter is not symetrical, so the resulting table will depend on the order you applied the operation.