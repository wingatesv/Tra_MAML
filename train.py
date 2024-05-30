import numpy as np
import torch
import torch.nn as nn
from torch.autograd import Variable
import torch.optim
import time
import os
import glob
import math
import collections


import configs
import backbone
from data.datamgr import SimpleDataManager, SetDataManager
from methods.baselinetrain import BaselineTrain
from methods.baselinefinetune import BaselineFinetune
from methods.protonet import ProtoNet
from methods.matchingnet import MatchingNet
from methods.relationnet import RelationNet
from methods.maml import MAML
from methods.tra_maml import TRA_MAML
import torch.multiprocessing as mp
from io_utils import model_dict, parse_args, get_resume_file, set_seed


def train(base_loader, val_loader, model, optimization, start_epoch, stop_epoch, params, patience_ratio=0.1, warmup_epochs_ratio = 0.25):    
    learning_rate = 0.0001
    if optimization == 'Adam':
          print(f'With scalar Learning rate, Adam LR:{learning_rate}')
          optimizer = torch.optim.Adam(model.parameters(), lr = learning_rate)
         
    else:
       raise ValueError('Unknown optimization, please define by yourself')
  
    max_acc = 0   
    total_training_time = 0
    scheduler = None
   
    # Initialize early stopping variables
    patience = int(patience_ratio * (stop_epoch - start_epoch))
    warmup_epochs = int(warmup_epochs_ratio * (stop_epoch - start_epoch))
    early_stopping_counter = 0
    
    timestamp_start = time.strftime("%Y%m%d-%H%M%S", time.localtime()) 
    with open(os.path.join(params.checkpoint_dir, 'training_logs.txt'), 'a') as log_file:
        log_file.write(f'Time: {timestamp_start}, Training Start\n')


    for epoch in range(start_epoch,stop_epoch):
        start_time = time.time() # record start time
        model.train()
        model.train_loop(epoch, base_loader,  optimizer) #model are called by reference, no need to return 


        model.eval()

        if not os.path.isdir(params.checkpoint_dir):
            os.makedirs(params.checkpoint_dir)

        acc, avg_loss = model.test_loop(val_loader)
   
        # Save validation accuracy and training time to a text file
        with open(os.path.join(params.checkpoint_dir, 'training_logs.txt'), 'a') as log_file:
          log_file.write(f'Epoch: {epoch}, Validation Accuracy: {acc:.4f}, Validation Loss: {avg_loss:.4f}\n')


        if acc > max_acc : #for baseline and baseline++, we don't use validation in default and we let acc = -1, but we allow options to validate with DB index
            print("best model! save...")
            max_acc = acc
            early_stopping_counter = 0
            outfile = os.path.join(params.checkpoint_dir, 'best_model.tar')
            torch.save({'epoch':epoch, 'state':model.state_dict()}, outfile)

        elif acc == -1: #for baseline and baseline++
          pass

        else:
          # Skip early stopping check during warm-up period
          if epoch >= warmup_epochs:
               early_stopping_counter += 1

        # If validation accuracy hasn't improved for patience epochs, increase patience
        if early_stopping_counter >= patience and epoch >= warmup_epochs:
            print(f"Early stopping at epoch {epoch}")

            stop_epoch = epoch
            break


        if (epoch % params.save_freq==0) or (epoch==stop_epoch-1):
            outfile = os.path.join(params.checkpoint_dir, '{:d}.tar'.format(epoch))
            torch.save({'epoch':epoch, 'state':model.state_dict()}, outfile)

            
        elapsed_time = time.time() - start_time # calculate elapsed time
        total_training_time += elapsed_time
      
        
    elapsed_hours = total_training_time / 3600.0 # convert to hours
    print(f"Total Training Time: {elapsed_hours:.2f} h") # print elapsed time for current epoch in hours

    timestamp_end = time.strftime("%Y%m%d-%H%M%S", time.localtime()) 
    # Save final training times to a text file
    with open(os.path.join(params.checkpoint_dir, 'training_logs.txt'), 'a') as log_file:
        log_file.write(f'Epoch: {epoch}, Training Time: {elapsed_hours:.4f} hours\n')
        log_file.write(f'Time: {timestamp_end}, Training End\n')
        
    return model

if __name__=='__main__':
    mp.set_start_method('spawn')
   
    # set a fixed seed for reproducibility 
    set_seed(seed=10)

    # get the training argument parser
    params = parse_args('train')

   
    if params.dataset == 'BreaKHis_40x' or params.dataset == 'cross_IDC':
        base_file = configs.data_dir['BreaKHis_40x'] + 'base.json' 
        val_file   = configs.data_dir['BreaKHis_40x'] + 'val.json' 
    elif params.dataset == 'ISIC':
        base_file = configs.data_dir['ISIC'] + 'base.json' 
        val_file   = configs.data_dir['ISIC'] + 'val.json' 
    elif params.dataset == 'Smear':
        base_file = configs.data_dir['Smear'] + 'base.json' 
        val_file   = configs.data_dir['Smear'] + 'val.json'

    else:
        raise ValueError(f"Unsupported dataset: {params.dataset}")

    # Set number of classes for baseline training
    if params.dataset == 'Smear' or params.dataset == 'ISIC':
      params.num_classes = 7
    else:
      params.num_classes = 8

    # Set Image Size  
    if 'Conv' in params.model:
      image_size = 84
    else:
      image_size = 224

    optimization =  params.optimizer

    if params.stop_epoch == -1: 
        if params.method in ['baseline', 'baseline++'] :
            params.stop_epoch = 200
     
        else: # other meta-learning methods
         params.stop_epoch = 200 

    print('Dataset:', params.dataset, 'N-SHOT: ', params.n_shot)
    print(f'Applying {params.train_aug} Data Augmentation ......')
    
    if params.method in ['baseline', 'baseline++'] :
      base_datamgr    = SimpleDataManager(image_size, batch_size = 16)
      base_loader     = base_datamgr.get_data_loader( base_file , aug = params.train_aug)
      val_datamgr     = SimpleDataManager(image_size, batch_size = 64)
      val_loader      = val_datamgr.get_data_loader( val_file, aug = 'none')
     
      if params.method == 'baseline':
            model           = BaselineTrain( model_dict[params.model], params.num_classes)
      elif params.method == 'baseline++':
            model           = BaselineTrain( model_dict[params.model], params.num_classes, loss_type = 'dist')

    elif params.method in ['protonet','matchingnet','relationnet', 'relationnet_softmax', 'maml', 'maml_approx', 'tra_maml']:
       
        n_query = max(1, int(16* params.test_n_way/params.train_n_way)) #if test_n_way is smaller than train_n_way, reduce n_query to keep batch size small

        train_few_shot_params    = dict(n_way = params.train_n_way, n_support = params.n_shot) 
        test_few_shot_params     = dict(n_way = params.test_n_way, n_support = params.n_shot) 

        base_datamgr = SetDataManager(image_size, n_query = n_query,  **train_few_shot_params)
        base_loader  = base_datamgr.get_data_loader( base_file , aug = params.train_aug)
        
        val_datamgr = SetDataManager(image_size, n_query = n_query, **test_few_shot_params)
        val_loader = val_datamgr.get_data_loader( val_file, aug = 'none') 
        #a batch for SetDataManager: a [n_way, n_support + n_query, dim, w, h] tensor  

        if params.method == 'protonet':
            model = ProtoNet( model_dict[params.model], **train_few_shot_params )
        elif params.method == 'matchingnet':
            model = MatchingNet( model_dict[params.model], **train_few_shot_params )
        elif params.method in ['relationnet', 'relationnet_softmax']:
            if params.model == 'Conv4': 
                feature_model = backbone.Conv4NP
            elif params.model == 'Conv6': 
                feature_model = backbone.Conv6NP
            else:
                feature_model = lambda: model_dict[params.model]( flatten = False )
            loss_type = 'mse' if params.method == 'relationnet' else 'softmax'

            model = RelationNet( feature_model, loss_type = loss_type , **train_few_shot_params )


        elif params.method in ['maml' , 'maml_approx', 'tra_maml']:
          backbone.ConvBlock.maml = True
          backbone.SimpleBlock.maml = True
          backbone.BottleneckBlock.maml = True
          backbone.ResNet.maml = True

          if params.method in ['maml', 'maml_approx']:
            model = MAML(  model_dict[params.model], approx = (params.method == 'maml_approx') , **train_few_shot_params )
       

          elif params.method == 'tra_maml':
            if params.tra != 'none':
                tra = params.tra.split('-')
            else:
                raise ValueError('Unknown TRA configs')
            model = TRA_MAML(  model_dict[params.model], 
                             min_step = int(tra[0]), 
                             max_step = int(tra[1]), 
                             width = float(tra[2]),
                             test_mode = False,
                             approx = False, 
                             **train_few_shot_params )

       
              
        else:
          raise ValueError('Unknown method')


    
    model = model.cuda()

    params.checkpoint_dir = '%s/checkpoints/%s/%s_%s' %(configs.save_dir, params.dataset, params.model, params.method)
    if params.train_aug:
        params.checkpoint_dir += f'_{params.train_aug}'
   
    if params.tra != 'none':
        params.checkpoint_dir += f'_{params.tra}'
    if not params.method  in ['baseline', 'baseline++']: 
        params.checkpoint_dir += '_%dway_%dshot' %( params.train_n_way, params.n_shot)

    if not os.path.isdir(params.checkpoint_dir):
        os.makedirs(params.checkpoint_dir)

    start_epoch = params.start_epoch
    stop_epoch = params.stop_epoch
   

    if params.resume:
        resume_file = get_resume_file(params.checkpoint_dir)
        if resume_file is not None:
            tmp = torch.load(resume_file)
            start_epoch = tmp['epoch']+1
            model.load_state_dict(tmp['state'])


    model = train(base_loader, val_loader,  model, optimization, start_epoch, stop_epoch, params)
