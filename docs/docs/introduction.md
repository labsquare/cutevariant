
# What is cutevariant?

Cutevariant is a desktop application, useful to explore genetic variations from [Next Generation Sequencing](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3841808/){target=_blank} results stored in [VCF files](https://samtools.github.io/hts-specs/VCFv4.2.pdf){target=_blank}.
It has been designed so that everyone can easily visualize and filter genetic variations, even with no prior knowledge in IT.
Even though this software was especially tailored for panel and human [exome](https://en.wikipedia.org/wiki/Exome){target=_blank} analysis, it can be used with any VCF file. For now VCFs annotated with [SnpEff](http://pcingola.github.io/SnpEff/){target=_blank} and [VEP](https://www.ensembl.org/info/docs/tools/vep/index.html){target=_blank} are supported.

# How does it work?

## Local SQLite database
Cutevariant imports VCF file fields into a normalized [Sqlite3](https://www.sqlite.org/index.html){target=_blank} database. This is the first step to explore a VCF file, and is done exactly once for every project by pressing the :material-database-plus: `Create project` button in the toolbar. 
The database shema is available in the documentation. 

## VQL quick start
Once the variants are loaded into the database, you can retrieve their information in a language that looks like SQL that we've called [VQL](vql.md).

You can execute VQL requests directly inside the dedicated VQL editor to obtain the information you need, by specifying a `SELECT` clause with fields, a `FROM` clause for the source table and a `WHERE` clause with filters. For instance, the following query select chromosome and position with quality greater than 30: 

```sql
SELECT chr,pos FROM variants WHERE qual > 30
```

VQL supports special keywords. Check the [documentation](vql.md) for more information.

If you don't like VQL, you can select and filter your variants directly from dedicated controllers.
# Community

Cutevariant is an open source project created by passionate developers. Thanks to its modular architecture built around plugins, it is very easy for developers to participate in this project. The whole project is based on Qt for python (PySide2 for now), and requires very few dependencies to work.

Every contribution is welcome, we have an active [:material-discord:Discord server](https://discord.gg/7sSH4VSPKK) where we discuss about cutevariant 
