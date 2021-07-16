
# What is cutevariant 
Pk ? 
Cutevariant est une application bureautique permettant d'explorer des variations génétique stocké dans des fichiers VCF.  
Il a été concu pour que n'importe qui puisse facillement visualier et filter des variations génétique. En particulier ceux qui analyse des panel et des exomes humain. Cependant, n'importe quel VCF peut etre utilisé. Actuellement, il support le VCF annoté avec SnpEff et VEP. 

# How it works ?

Cutevariants imports VCF file into an Sqlite database. It can be done depuis le bouton créer un projet. 
Les variants, les annotations ainsi que les samples sont stocké de façon normalisé. 

Une fois les variants chargé, vous pouvez interogger la base à partir d'un language ressemblant au SQL que nous avons appelé VQL. Executez ces requete directement depuis l'editeur VQL pour obtenir les variants voulu.

Si vous n'aimez pas le VQL, Vous pouvez crée votre selection de variant directement depuis les controlleurs présent sur l'interface. 

# Community 
Cutevariant is an open source project crée par des gens passionnée.
Grace à une architecture composé entierement de plugins, il est très facile pour les developpeur participer au projet. Nous utilisons Qt et python. 
