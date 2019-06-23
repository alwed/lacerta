#!/bin/sh

# Adapted from: Peter Miller "Recursive Make Considered Harmful", 1997
# http://lcgapp.cern.ch/project/architecture/recursive_make.pdf#page=10

DIR="$1"
shift 1

case "$DIR" in
"" | ".")
	cc -MM -MG "$@" | sed -e 's@^\(.*\)\.o:@\1.d \1.o:@'
	;;
*)
	cc -MM -MG "$@" | sed -e "s@^\(.*\)\.o:@$DIR\1.d $DIR\1.o:@"
	;;
esac
