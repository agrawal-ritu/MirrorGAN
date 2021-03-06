from __future__ import print_function
from cfg.config import cfg, cfg_from_file
from datasets import TextDataset
from trainer import Trainer as trainer
import os
import sys
import time
import random
import pprint
import datetime
import dateutil.tz
import argparse
import numpy as np
import torch
import torchvision.transforms as transforms


dir_path = (os.path.abspath(os.path.join(os.path.realpath(__file__), './.')))
sys.path.append(dir_path)

class Main:

    # change
    def __init__(self):
        self.cfg_file = "/Users/nikunjlad/Github/MirrorGAN/cfg/train_bird.yml"
        self.gpu = 1
        self.data_dir = ""
        self.manualSeed = None


    # def parse_args():
    #     parser = argparse.ArgumentParser(description='Train a AttnGAN network')
    #     parser.add_argument('--cfg', dest='cfg_file',
    #                         help='optional config file',
    #                         default='cfg/bird_attn2.yml', type=str)
    #     parser.add_argument('--gpu', dest='gpu_id', type=int, default=-1)
    #     parser.add_argument('--data_dir', dest='data_dir', type=str, default='')
    #     parser.add_argument('--manualSeed', type=int, help='manual seed')
    #     args = parser.parse_args()
    #     return args


    def gen_example(self, wordtoix, algo):
        '''generate images from example sentences'''
        from nltk.tokenize import RegexpTokenizer
        filepath = '%s/example_filenames.txt' % (cfg.DATA_DIR)
        data_dic = {}
        with open(filepath, "r") as f:
            filenames = f.read().decode('utf8').split('\n')
            for name in filenames:
                if len(name) == 0:
                    continue
                filepath = '%s/%s.txt' % (cfg.DATA_DIR, name)
                with open(filepath, "r") as f:
                    print('Load from:', name)
                    sentences = f.read().decode('utf8').split('\n')
                    # a list of indices for a sentence
                    captions = []
                    cap_lens = []
                    for sent in sentences:
                        if len(sent) == 0:
                            continue
                        sent = sent.replace("\ufffd\ufffd", " ")
                        tokenizer = RegexpTokenizer(r'\w+')
                        tokens = tokenizer.tokenize(sent.lower())
                        if len(tokens) == 0:
                            print('sent', sent)
                            continue

                        rev = []
                        for t in tokens:
                            t = t.encode('ascii', 'ignore').decode('ascii')
                            if len(t) > 0 and t in wordtoix:
                                rev.append(wordtoix[t])
                        captions.append(rev)
                        cap_lens.append(len(rev))
                max_len = np.max(cap_lens)

                sorted_indices = np.argsort(cap_lens)[::-1]
                cap_lens = np.asarray(cap_lens)
                cap_lens = cap_lens[sorted_indices]
                cap_array = np.zeros((len(captions), max_len), dtype='int64')
                for i in range(len(captions)):
                    idx = sorted_indices[i]
                    cap = captions[idx]
                    c_len = len(cap)
                    cap_array[i, :c_len] = cap
                key = name[(name.rfind('/') + 1):]
                data_dic[key] = [cap_array, cap_lens, sorted_indices]
        algo.gen_example(data_dic)


if __name__ == "__main__":
    m = Main()   # change. object of Main class to handle code execution
    # args = parse_args()  # argument parser object

    # check if the passed config file is not None
    if m.cfg_file is not None:   # change
        # cf_file = "/Users/nikunjlad/Github/MirrorGAN/cfg/train_bird.yml"
        cfg_from_file(m.cfg_file)

    # update default configs and user given configs
    if m.data_dir != '':
        cfg.DATA_DIR = m.data_dir
    print('Using config:')
    pprint.pprint(cfg)

    # setting random seed fir numpy and torch tensors
    if not cfg.TRAIN.FLAG:
        m.manualSeed = 100
    elif m.manualSeed is None:
        m.manualSeed = random.randint(1, 10000)
    random.seed(m.manualSeed)
    np.random.seed(m.manualSeed)
    torch.manual_seed(m.manualSeed)

    # configure cuda with random manual seed
    if cfg.CUDA:
        torch.cuda.manual_seed_all(m.manualSeed)

    # setting datetime and time stamp for the output
    now = datetime.datetime.now(dateutil.tz.tzlocal())
    timestamp = now.strftime('%Y_%m_%d_%H_%M_%S')
    output_dir = '%s/output/%s_%s_%s' % \
        (cfg.OUTPUT_PATH, cfg.DATASET_NAME, cfg.CONFIG_NAME, timestamp)

    split_dir, bshuffle = 'train', True
    if not cfg.TRAIN.FLAG:
        # bshuffle = False
        split_dir = 'test'

    # Get image size to be set during resize operation (3 * (2 **
    imsize = cfg.TREE.BASE_SIZE * (2 ** (cfg.TREE.BRANCH_NUM - 1))

    # define the image transformations here
    image_transform = transforms.Compose([
        transforms.Resize(int(imsize * 76 / 64)),
        transforms.RandomCrop(imsize),
        transforms.RandomHorizontalFlip()])

    # create a pytorch dataset object using the Dataset class.
    dataset = TextDataset(cfg.DATA_DIR, split_dir,
                          base_size=cfg.TREE.BASE_SIZE,
                          transform=image_transform)
    imgs, caps, cap_len, cls_id, key = dataset[3]

    assert dataset
    dataloader = torch.utils.data.DataLoader(
        dataset, batch_size=cfg.TRAIN.BATCH_SIZE,
        drop_last=True, shuffle=bshuffle, num_workers=int(cfg.WORKERS))

    print(dataloader.dataset)
    # Define models and go to train/evaluate
    algo = trainer(output_dir, dataloader, dataset.n_words, dataset.ixtoword)

    start_t = time.time()
    if cfg.TRAIN.FLAG:
        algo.train()
    else:
        '''generate images from pre-extracted embeddings'''
        if cfg.B_VALIDATION:
            algo.sampling(split_dir)  # generate images for the whole valid dataset
        else:
            m.gen_example(dataset.wordtoix, algo)  # generate images for customized captions
    end_t = time.time()
    print('Total time for training:', end_t - start_t)
