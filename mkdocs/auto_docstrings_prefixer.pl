#!/usr/bin/perl
use warnings;
use strict;

# This program outputs, for every first-level python function in file_name, a line with the given prefix

my $file_name = $ARGV[0]; # File name, like sql.py
my $prefix = $ARGV[1]; # Prefix, like cutevariant.core.sql.

open(FH, '<', $file_name) or die $!;

while(<FH>)
{
    print "$prefix$1\n" if($_ =~ /^def ([^\(]+)/);
}
#print "::: cutevariant.core.sql.$1"


close(FH);