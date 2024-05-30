

## Train
Run
```python ./train.py --dataset [DATASETNAME] --model [BACKBONENAME] --method [METHODNAME] [--OPTIONARG]```

For example, run `python ./train.py --dataset Smear --model Conv4 --method tra_maml --tra 1-5-0.4 --train_n_way 3 --test_n_way 3 --n_shot 1 --stop_epoch 200 --train_aug `  
Commands below follow this example, and please refer to io_utils.py for additional options.

## Save features
Save the extracted feature before the classifaction layer to increase test speed. This is not applicable to MAML-based methods, but are required for other methods.
Run
```python ./save_features.py --dataset Smear --model Conv4 --method relationnet  --train_n_way 3 --n_shot 5 --test_n_way 3 --train_aug ```

## Test
Run
```python ./test.py --dataset Smear --model Conv4 --method tra_maml  --tra 1-5-0.4 --train_n_way 3 --test_n_way 3 --n_shot 1 --train_aug ```

## Results
* The test results will be recorded in `./record/results.txt`

## References
* Main Framework
https://github.com/wyharveychen/CloserLookFewShot
* Framework, Backbone, Method: Matching Network
https://github.com/facebookresearch/low-shot-shrink-hallucinate 
* Omniglot dataset, Method: Prototypical Network
https://github.com/jakesnell/prototypical-networks
* Method: Relational Network
https://github.com/floodsung/LearningToCompare_FSL
* Method: MAML
https://github.com/cbfinn/maml  
https://github.com/dragen1860/MAML-Pytorch  
https://github.com/katerakelly/pytorch-maml

