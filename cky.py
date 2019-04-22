

from __future__ import division
import sys
from collections import defaultdict
import re
import itertools
from tree import Tree


class CKYSolver:
    def __init__(self, text):
        self.nonTerms = set()           
        self.allProds = set()            
        self.P = defaultdict(float)      
        self.score = defaultdict(float) 
        self.backPointers = {}           
        self.terminals = {}             
        self.text = text.split()       	
        self.origText = list(self.text)  
        if len(sys.argv) >= 3:
            trainDict = open(sys.argv[2])
            multiWords = [word.strip() for word in trainDict.readlines()]

            for i,word in enumerate(self.text):
                if word not in multiWords:
                    self.text[i] = "<unk>"

        self.n = len(self.text)



    def addUnary(self,begin, end):
       
        for A in self.nonTerms:
            for B in self.nonTerms:
                if (A,B) in self.allProds:
                    prob = self.P[(A,B)] * self.score[(begin,end,B)]
        
                    if prob > self.score[(begin,end,A)]:
                        self.score[(begin, end, A)] = prob
                        self.backPointers[(begin, end, A)] = (B,)
        

    def backtrack(self, n):
       
        if (0,n,'TOP') not in self.backPointers:
            #print "NONE"
            return None

        t = self._backtrack((0,n,'TOP'))

        t.deBinarize()
        return t


    def _backtrack(self, next):
        
        
        low = next[0]
        high = next[1]
        label = next[2]

        if next not in self.backPointers:
            if next in self.terminals:
        
                word = self.origText[next[0]]
                t = Tree(label=label, subs = None, wrd=word, span=(low, high))
        
            return t
        
        branches = self.backPointers[next]

        if len(branches) == 1:
            next = (low, high, branches[0])

            t1 = self._backtrack(next)
            t = Tree(label=label, subs = [t1], wrd=None, span=t1.span)
            return t
        elif len(next) == 3:
            (split, left, right) = branches
            next1 = (low, split, left)
            next2 = (split, high, right)

            t1 = self._backtrack(next1)     
            t2 = self._backtrack(next2)

            spanLow = t1.span[0]
            spanHigh = t2.span[1]
            t = Tree(label=label, subs = [t1,t2], wrd=None, span=(spanLow, spanHigh))
            return t



    def compute(self):
        for line in open(sys.argv[1]):
            data = re.split(r"\-\>|\#", line.strip())
            
            p = data[0].strip()
            q = data[1].strip()
            prob = float(data[2].strip())
            self.nonTerms.add(p)
            self.allProds.add( (p,q) )
            self.P[(p,q)] = prob
            
        self.nonTerms = sorted(list(self.nonTerms))

        n = self.n
        
        for ii in range(0,n):
            begin = ii
            end = ii + 1

            for A in self.nonTerms:
                word = self.text[begin]

                if (A,word) in self.allProds:
                    self.score[(begin,end,A)] = self.P[(A, word)]

                    self.terminals[(begin,end,A)] = word


            self.addUnary(begin,end)

        #Actual CYK algorithm
        for span in range(2,n+1):
            for begin in range(0,n-span+1):
                end = begin + span
                for split in range(begin+1,end):

                    for A,X in self.allProds:
                        # X is a pair of prodcutions, A -> X where X = L R
                        rhs = X.split()
                        if len(rhs) == 2:
                            B = rhs[0].strip()
                            C = rhs[1].strip()

                            prob = self.score[(begin,split,B)] * self.score[(split, end, C)] * self.P[(A, X)]

                            if prob > self.score[(begin, end,  A)]:
                                self.score[(begin, end, A)] = prob
                                self.backPointers[(begin, end, A)] = (split, B, C)


                self.addUnary(begin,end)

        t = self.backtrack(len(self.text))
        if t is not None:
            print t
        else:
            print "NONE"
        



if __name__ == "__main__":
    
    for line in sys.stdin:
        s = CKYSolver(line.strip())
        s.compute()
