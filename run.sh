#!bin/bash
# taking a random input 

# parsing this input
cat train.trees | python replace_onecounts.py > train.trees.unk 2> train.dict
cat train.trees.unk | python binarize.py > train.trees.unk.bin
cat train.trees.unk.bin | python learn_pcfg.py > grammar.pcfg.bin
cat test.txt | python cky.py grammar.pcfg.bin train.dict > test.parsed.new
python evalb.py test.trees test.parsed.new
