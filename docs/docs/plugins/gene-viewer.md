# Introduction

The gene viewer is a cutevariant plugin that displays the variants [you selected](../plugins/variant-view.md) in the context of their associated gene.
Each variant is shown as a lollipop, representing its position in the gene, and 

# Using the gene viewer



# Setting up the annotation reference database


In order for this plugin to display annotations correctly, you need to provide a database file with the same annotations as the ones provided in the 'gene' field of your VCF.

Here is a step-by-step tutorial on how to download and setup the gene viewer so you can see annotations with the same ontology as the one that was used to produce your VCF.

## Downloading an annotation reference file

### User-friendly UCSC table download page

If you'd like to download a whole genome in a user-friendly way, then go to [https://genome.ucsc.edu/cgi-bin/hgTables](https://genome.ucsc.edu/cgi-bin/hgTables).

You will find a form that will prompt you for the annotation file you'd like to use for the gene viewer.

### Manual downloading

You can find lots of reference annotation files at [https://hgdownload.soe.ucsc.edu/downloads.html](https://hgdownload.soe.ucsc.edu/downloads.html). Here is what it looks like as of May 2021 :

![UCSC download page](../images/ucsc_download_page_1.png)

Choose the species you are interested in, then browse to the 'annotations' section.

Click on SQL table dump annotations, which will lead you to a page with loads of download links.

If you know the name of the database you are looking for, you can search for its name (<kbd>Ctrl</kbd> + <kbd>F</kbd>) in firefox and chrome.

Be sure to download the `.txt.gz` file and not the `sql` one, as cutevariant only supports the zipped text file.


## Converting the .txt.gz file into a .db (sqlite3) database file

Luckily enough, cutevariant can convert the zipped text file that you downloaded in the previous step to a sqlite3 database. This is the file that you must provide to the gene viewer plugin under Settings/Gene viewer.

