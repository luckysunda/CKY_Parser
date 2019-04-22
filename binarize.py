#!/usr/bin/python


from tree import Tree
import sys

for line in sys.stdin:
    line = line.strip()
    t = Tree.parse(line)

    # convert to binary and print
    t.binarize()
    print t
