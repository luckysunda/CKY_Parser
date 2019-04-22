

from __future__ import division
from tree import Tree
from collections import defaultdict
import sys


freqs = defaultdict(int)
condCounts = defaultdict(int)

for line in sys.stdin:
    line = line.strip()

    t = Tree.parse(line)
  
    prods = t.getProductions()

    for (x,y) in prods:
        freqs[(x,y)] += 1
        condCounts[x] += 1

for (x,y), freq in freqs.iteritems():
    p = freq / condCounts[x]
    print "%s -> %s # %.4f" % (x,y,p)

