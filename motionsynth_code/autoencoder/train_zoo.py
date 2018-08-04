import os
import sys
import numpy as np
import scipy.io as io

"""For logging by tensorboard"""
bLog = False  
try:
	sys.path.append('../utils')
	from logger import Logger
	bLog = True
except ImportError:
	pass

import torch
import torchvision
from torch import nn
from torch.autograd import Variable
from torch.utils.data import DataLoader
from torchvision import transforms
from torchvision.utils import save_image
from torchvision.datasets import MNIST
import os
import argparse

import modelZoo

def print_options(parse,opt):
    message = ''
    message += '----------------- Options ---------------\n'
    for k, v in sorted(vars(opt).items()):
        comment = ''
        default = parser.get_default(k)
        if v != default:
            comment = '\t[default: %s]' % str(default)
        message += '{:>25}: {:<30}{}\n'.format(str(k), str(v), comment)
    message += '----------------- End -------------------'
    print(message)

    return message

def save_options(checkpoints_dir, message):

    # save to the disk
    #expr_dir = os.path.join(checkpoints_dir, 'options.txt')
    #util.mkdirs(expr_dir)
    if not os.path.exists(checkpoints_dir):
        os.makedirs(checkpoints_dir)
    file_name = os.path.join(checkpoints_dir, 'opt.txt')
    with open(file_name, 'wt') as opt_file:
        opt_file.write(message)
        opt_file.write('\n')

        
parser = argparse.ArgumentParser(description='VAE MNIST Example')
parser.add_argument('--epochs', type=int, default=1001, metavar='N',
                    help='number of epochs to train (default: 1001)')

parser.add_argument('--gpu', type=int, default=0, metavar='N',
                    help='Select gpu (default: 0)')

parser.add_argument('--checkpoint_freq', type=int, default=10, metavar='N',
                    help='How frequently save the checkpoint (default: every 10 epoch)')

parser.add_argument('--model', type=str, default='autoencoder_first',
                    help='a model name in the model_zoo.py (default: autoencoder_first')


args = parser.parse_args()  

#args.checkpoint_dir = args.model

#print_options(parser,args)


torch.cuda.set_device(args.gpu)



rng = np.random.RandomState(23456)
torch.manual_seed(23456)
torch.cuda.manual_seed(23456)




"""All available dataset"""
#datapath ='/ssd/codes/pytorch_motionSynth/motionsynth_data' 
datapath ='../../motionsynth_data/data/processed/' 
dblist = ['data_cmu', 'data_hdm05', 'data_mhad', 'data_edin_locomotion', 'data_edin_xsens',
            'data_edin_misc', 'data_edin_punching']
#Xcmu = np.load(datapath +'/data/processed/data_cmu.npz')['clips'] # (17944, 240, 73)
# Xhdm05 = np.load(datapath +'/data/processed/data_hdm05.npz')['clips']	#(3190, 240, 73)
# Xmhad = np.load(datapath +'/data/processed/data_mhad.npz')['clips'] # (2674, 240, 73)
# #Xstyletransfer = np.load('/data/processed/data_styletransfer.npz')['clips']
# Xedin_locomotion = np.load(datapath +'/data/processed/data_edin_locomotion.npz')['clips'] #(351, 240, 73)
# Xedin_xsens = np.load(datapath +'/data/processed/data_edin_xsens.npz')['clips'] #(1399, 240, 73)
# Xedin_misc = np.load(datapath +'/data/processed/data_edin_misc.npz')['clips'] #(122, 240, 73)
# Xedin_punching = np.load(datapath +'/data/processed/data_edin_punching.npz')['clips'] #(408, 240, 73)
#h36m_training = np.load(datapath +'/data/processed/data_h36m_training.npz')['clips'] #(13156, 240, 73)

#X = np.concatenate([Xcmu, Xhdm05, Xmhad, Xstyletransfer, Xedin_locomotion, Xedin_xsens, Xedin_misc, Xedin_punching], axis=0)
#X = np.concatenate([Xcmu, Xhdm05, Xmhad, Xedin_locomotion, Xedin_xsens, Xedin_misc, Xedin_punching], axis=0) #(26088,  240, 73 )
#X = h36m_training\
#X = Xcmu
#X = np.concatenate([Xcmu, Xhdm05, Xmhad, Xedin_locomotion, Xedin_xsens, Xedin_misc, Xedin_punching, h36m_training], axis=0) #(26088,  240, 73 )

db_loaded =list()
for dbname in dblist:
    X_temp = np.load(datapath + dbname + '.npz')['clips'] 
    db_loaded.append(X_temp)
X = np.concatenate(db_loaded, axis=0)


""" Training Network """
num_epochs = args.epochs#500
batch_size = 128
learning_rate = 1e-3

model = getattr(modelZoo,args.model)().cuda()
#model = modelZoo.autoencoder_first().cuda()
#model = modelZoo.autoencoder_vectorize().cuda()
#model = modelZoo.autoencoder_2convLayers().cuda()
#model = modelZoo.autoencoder_3convLayers_vect().cuda()
#model = modelZoo.autoencoder_3convLayers().cuda()

for param in model.parameters():
    print(type(param.data), param.size())

criterion = nn.MSELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate, weight_decay=1e-5)
#optimizer = torch.optim.SGD(model.parameters(), lr=learning_rate)
#optimizer = torch.optim.AMSGrad(model.parameters(), lr=learning_rate, weight_decay=1e-5)

#checkpointFolder = './autoenc_vect/'
checkpointFolder = model.__class__.__name__
if not os.path.exists(checkpointFolder):
    os.mkdir(checkpointFolder)

if bLog:
    logger = Logger(checkpointFolder+'/logs')

""" Save Option Info """
option_str = print_options(parser,args)

option_str += '\nDBList: \n'
for i, dbname in enumerate(dblist):
    option_str +=  '{0}:  {1}\n'.format(dbname,db_loaded[i].shape)
option_str += 'All: {0}'.format(X.shape)

save_options(checkpointFolder, option_str)


""" Compute mean and std"""
X = np.swapaxes(X, 1, 2).astype(np.float32)
feet = np.array([12,13,14,15,16,17,24,25,26,27,28,29])

Xmean = X.mean(axis=2).mean(axis=0)[np.newaxis,:,np.newaxis]
Xmean[:,-7:-4] = 0.0
Xmean[:,-4:]   = 0.5

Xstd = np.array([[[X.std()]]]).repeat(X.shape[1], axis=1)
Xstd[:,feet]  = 0.9 * Xstd[:,feet]
Xstd[:,-7:-5] = 0.9 * X[:,-7:-5].std()
Xstd[:,-5:-4] = 0.9 * X[:,-5:-4].std()
Xstd[:,-4:]   = 0.5

""" Data standardization """
X = (X - Xmean) / Xstd
I = np.arange(len(X))
rng.shuffle(I); X = X[I]
print('Input data size: {0}'.format(X.shape))

np.savez_compressed(checkpointFolder+'/preprocess_core.npz', Xmean=Xmean, Xstd=Xstd)

for epoch in range(num_epochs):

    batchinds = np.arange(X.shape[0] // batch_size)
    rng.shuffle(batchinds)
    
    for bii, bi in enumerate(batchinds):
        inputData = X[bi:(bi+batch_size),:,:]
        inputData = Variable(torch.from_numpy(inputData)).cuda()

        # ===================forward=====================
        output = model(inputData)
        loss = criterion(output, inputData)

        # ===================backward====================
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        # ===================log========================
        print('epoch [{}/{}], loss:{:.4f}'
                    .format(epoch + 1, num_epochs, loss.data[0]))

    if bLog:
	    # 1. Log scalar values (scalar summary)
	    info = { 'loss': loss.data[0] }
	
	    for tag, value in info.items():
	        logger.scalar_summary(tag, value, epoch+1)

    # # 2. Log values and gradients of the parameters (histogram summary)
    # for tag, value in model.named_parameters():
    #     tag = tag.replace('.', '/')
    #     logger.histo_summary(tag, value.data.cpu().numpy(), epoch+1)
    #     logger.histo_summary(tag+'/grad', value.grad.data.cpu().numpy(), epoch+1)
            
    if epoch % args.checkpoint_freq == 0:
        fileName = checkpointFolder+ '/checkpoint_e' + str(epoch) + '.pth'
        torch.save(model.state_dict(), fileName)
