
# What is cutevariant?

Cutevariant is a desktop application, useful to explore genetic variations stored into VCF files.
It has been designed so that everyone can easily visualize and filter genetic variations, even with no prior knowledge in IT.
Even though this software was especially tailored for panel and human exome analysis, it can be used with any VCF file. For now, only VCFs annotated with SnpEff and VEP are supported.

# How dot it work?

Cutevariant imports VCF file fields into a Sqlite3 database. This is the first step to explore a VCF file, and is done exactly once for every project by pressing the ':material-database-plus: Create project' button in the toolbar. Variants, annotations and sample fields are stored in a normalized fashion.

Once the variants are loaded into the database, you can retrieve their information in a language that looks like SQL that we've called VQL.

You can execute VQL requests directly inside the dedicated VQL editor, to obtain the information you need by specifying what fields you need, and what conditions they should meet.

If you don't like VQL, you can select and filter your variants directly from dedicated controllers.
# Community

Cutevariant is an open source project created by passionate developers. Thanks to its modular architecture built around plugins, it is very easy for developers to participate in this project. The whole project is based on Qt for python (PySide2 for now), and requires very few dependencies to work.

Every contribution is welcome, we have an active [:material-discord:Discord server](https://discord.gg/7sSH4VSPKK) where we discuss about cutevariant 
