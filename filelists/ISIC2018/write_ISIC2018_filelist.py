import numpy as np
from os import listdir
from os.path import isfile, isdir, join
import os
import json
import random

data_path = '/content/ISIC2018'
savedir = '/content/Tra_MAML/filelists/ISIC2018/'
dataset_list = ['base','val','novel']

folder_list = ['MEL', 'NV', 'BCC', 'AKIEC', 'BKL', 'DF', 'VASC']
folder_list.sort()
label_dict = dict(zip(folder_list,range(0,len(folder_list))))

classfile_list_all = []

for i, folder in enumerate(folder_list):
    folder_path = join(data_path, folder)
    classfile_list_all.append( [ join(folder_path, cf) for cf in listdir(folder_path) if (isfile(join(folder_path,cf)) and cf[0] != '.')])
    random.shuffle(classfile_list_all[i])

base_classes = ['MEL', 'NV', 'BCC', 'BKL']
novel_classes = ['AKIEC', 'DF', 'VASC']

for dataset in dataset_list:
    file_list = []
    label_list = []
    for i, classfile_list in enumerate(classfile_list_all):
        if folder_list[i] in base_classes:
            split_index = int(len(classfile_list) * 0.8)  # 80% for base, 20% for validation
            if dataset == 'base':
                file_list += classfile_list[:split_index]
                label_list += np.repeat(i, split_index).tolist()
            elif dataset == 'val':
                file_list += classfile_list[split_index:]
                label_list += np.repeat(i, len(classfile_list) - split_index).tolist()
        elif folder_list[i] in novel_classes and dataset == 'novel':
            file_list += classfile_list
            label_list += np.repeat(i, len(classfile_list)).tolist()

    with open(join(savedir, f"{dataset}.json"), "w") as fo:
        json.dump({"label_names": folder_list, "image_names": file_list, "image_labels": label_list}, fo)

    print(f"{dataset} - OK")
