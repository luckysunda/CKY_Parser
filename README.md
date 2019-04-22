# CKY Parser and Experiments
This is the third assignment of NLU. In this assignment we have two tasks, first is to implement CKY and then second task is to compare two short and two long sentences with existing online parsers. 

## How to run
First preprocess the tree bank to replace single occurence terminals with "\<unk\>"
```
cat train.trees | python replace_onecounts.py > train.trees.unk 2> train.dict
```

Then binarize the trees in the new tree bank
```
cat train.trees.unk | python binarize.py > train.trees.unk.bin
```

To learn the PCFG
```
cat train.trees.unk.bin | python learn_pcfg.py > grammar.pcfg.bin
```

To run the CKY parser
```
cat test.txt | python cky.py grammar.pcfg.bin train.dict > test.parsed.new
```
To evaluate
```
python evalb.py test.trees test.parsed.new
```


Or we can also run it by the shell script:
 
 ```
 chmod +x run.sh
 
 bash run.sh
 
 ```
 It will take sentences from test file and produce output in separate text file.
