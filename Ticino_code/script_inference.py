import numpy as np
import torch
import argparse
import json
from PIL import Image


from einops import rearrange, repeat # , reduce

import segmentation_models_pytorch as smp
from Ticino_code.Base import Base
import albumentations as A
from albumentations.pytorch.transforms import ToTensorV2
import torchvision.transforms as transforms
from torchvision.transforms.functional import InterpolationMode

import pickle

from Ticino_code.middle_fusion_rgb_hs import Middle_fusion_en as mf_rgb_hs
from Ticino_code.middle_fusion_rgb_dem import Middle_fusion_en as mf_rgb_dem
from Ticino_code.middle_fusion_rgb_hs_dem import Middle_fusion_en as mf_rgb_hs_dem

# seed
import random
from pytorch_lightning import seed_everything

from pytorch_lightning.utilities import measure_flops

class KnownArchitectures(Base):
    def __init__(self, params):
        # init base
        super(KnownArchitectures, self).__init__(params)

        self.conf['mode'] = 'land_cover'
        self.conf['sources'] = ['rgb']
        self.conf['mean_dict_01'] = './Ticino_code/dictionary/mean_dict_01.pkl'
        self.conf['std_dict_01'] = './Ticino_code/dictionary/std_dict_01.pkl'
        self.conf['max_dict_01'] = './Ticino_code/dictionary/max_dict_01.pkl'
        self.conf['max_dict'] = './Ticino_code/dictionary/max_dict.pkl'
        self.conf['min_dict'] = './Ticino_code/dictionary/min_dict.pkl'

        # early fusion
        if self.conf['method'] == 'early_fusion':

            input_channels = 0
            for source in self.conf['sources']:
                if source == 'rgb':
                    input_channels = input_channels + 3
                if source == 'dtm':
                    input_channels = input_channels + 1
                if source == 'hs':
                    input_channels = input_channels + 182

            # define architecture
            self.net = smp.Unet(
                encoder_name=self.conf['encoder_name'],
                encoder_weights= (self.conf['encoder_weights'] if self.conf['encoder_weights'] != "None" else None),
                in_channels=input_channels,
                classes=self.conf['n_classes_landuse'] + self.conf['n_classes_agricolture'],
            )

            torch.nn.init.xavier_uniform_(self.net.encoder.conv1.weight) # reinitialize first layer

        # middle fusion
        elif self.conf['method'] == 'middle_fusion':
            if 'rgb' in self.conf['sources'] and 'hs' in self.conf['sources']:
                self.fusion_en = mf_rgb_hs(conf_rgb={'channels':[3,16,32,64], 'kernels':[3,3,3]},
                                        conf_hs={'channels':[182,128,64], 'kernels':[3,3]})
                in_channels_middle_fusion = 64+64
            elif 'rgb' in self.conf['sources'] and 'hs' in self.conf['sources'] and 'dtm' in self.conf['sources']:
                self.fusion_en = mf_rgb_hs_dem(conf_rgb={'channels':[3,16,32,64], 'kernels':[3,3,3]},
                                            conf_hs={'channels':[182,128,64], 'kernels':[3,3]},
                                            conf_dem={'channels':[1,16,32,64], 'kernels':[3,3,3]})
                in_channels_middle_fusion = 64+64+64
            elif 'rgb' in self.conf['sources'] and 'dtm' in self.conf['sources']:
                self.fusion_en = mf_rgb_dem(conf_rgb={'channels':[3,16,32,64], 'kernels':[3,3,3]},
                                            conf_dem={'channels':[1,16,32,64], 'kernels':[3,3,3]})
                in_channels_middle_fusion = 64+64

            # define architecture
            self.net = smp.Unet(
                encoder_name=self.conf['encoder_name'],
                encoder_weights= (self.conf['encoder_weights'] if self.conf['encoder_weights'] != "None" else None),
                in_channels=in_channels_middle_fusion,
                classes=self.conf['n_classes_landuse'] + self.conf['n_classes_agricolture'],
            )

            torch.nn.init.xavier_uniform_(self.net.encoder.conv1.weight) # reinitialize first layer

        self.mean_dict = self.load_dict(self.conf['mean_dict_01'])
        self.std_dict = self.load_dict(self.conf['std_dict_01'])
        self.max_dict = self.load_dict(self.conf['max_dict_01'])
        self.loaded_min_dict_before_normalization = self.load_dict(self.conf['min_dict'])
        self.loaded_max_dict_before_normalization = self.load_dict(self.conf['max_dict'])

    def load_dict(self, name):
        with open(name, 'rb') as f:
            loaded_dict = pickle.load(f)

        return loaded_dict
        
    # # Original forward
    def forward(self, batch):

        if 'rgb' in self.conf['sources'] and 'hs' in self.conf['sources'] and 'dtm' in self.conf['sources']:
            rgb, hs, dtm = batch
            additional_targets={'hs': 'image',
                                'dtm': 'image'}
        elif 'rgb' in self.conf['sources'] and 'hs' in self.conf['sources']:
            rgb, hs = batch
            additional_targets={'hs': 'image'}
        elif 'rgb' in self.conf['sources'] and 'dtm' in self.conf['sources']:
            rgb, dtm = batch
            additional_targets={'dtm': 'image'}
        elif 'hs' in self.conf['sources'] and 'dtm' in self.conf['sources']:
            hs, dtm = batch
            additional_targets={'dtm': 'image'}
        elif 'rgb' in self.conf['sources']:
            rgb = batch
        elif 'hs' in self.conf['sources']:
            hs = batch
        elif 'dtm' in self.conf['sources']:
            dtm = batch

                   
        # model application
        if self.conf['method'] == 'early_fusion':
            first_flag = True
            if 'rgb' in self.conf['sources']:
                if first_flag:
                    inp = rgb
                    first_flag = False
                else:
                    inp = torch.cat([inp, rgb], axis=1)
            if 'hs' in self.conf['sources']:
                if first_flag:
                    inp = hs
                    first_flag = False
                else:
                    inp = torch.cat([inp, hs], axis=1)
            if 'dtm' in self.conf['sources']:
                if first_flag:
                    inp = dtm
                    first_flag = False
                else:
                    inp = torch.cat([inp, dtm], axis=1)

            # apply
            return self.net(inp)
        
        # middle fusion
        elif self.conf['method'] == 'middle_fusion':
            if 'rgb' in self.conf['sources'] and 'hs' in self.conf['sources']:
                inp = rgb, hs
            elif 'rgb' in self.conf['sources'] and 'hs' in self.conf['sources'] and 'dtm' in self.conf['sources']:
                inp = rgb, hs, dtm
            elif 'rgb' in self.conf['sources'] and 'dtm' in self.conf['sources']:
                inp = rgb, dtm

            inp = self.fusion_en(inp)

            return self.net(inp)
            

def execute_model(model, image):

    # get original size of the image
    width, height = image.size
    image = np.array(image)

    # Preprocess
    image = (image - model.loaded_min_dict_before_normalization['rgb']) / (model.loaded_max_dict_before_normalization['rgb'] - model.loaded_min_dict_before_normalization['rgb'])
    normalize_image = A.Normalize(mean=model.mean_dict['rgb'], std=model.std_dict['rgb'], max_pixel_value=model.max_dict['rgb'])
    image = normalize_image(image=image)['image']

    # normalize and transform initialization

    preprocess_transforms = A.Compose([A.Resize(*model.conf['input_size']),
                                        ToTensorV2()
                                        ])

    sample = preprocess_transforms(image=image)
    image = sample['image']

    reverse_resize = transforms.Resize((height, width), interpolation=InterpolationMode.NEAREST)
    to_pil = transforms.ToPILImage()

    output = model(image.unsqueeze(dim=0).to(model.device))
    if model.conf['mode'] == 'land_cover':
        output = output[[0], :model.conf['n_classes_landuse']].argmax(dim=1)
    else:
        output = output[[0], model.conf['n_classes_landuse']:].argmax(dim=1)
    output = reverse_resize(output.unsqueeze(dim=1))
    output = to_pil(output[0,0].float()/output.max())

    return output

def load_model(checkpoint):
    return KnownArchitectures.load_from_checkpoint(checkpoint)


def load_and_execute(image, checkpoint='./checkpoints/rgb_only_lc/checkpoints/last.ckpt'):
    model = load_model(checkpoint)
    model.eval()

    with torch.no_grad():
        result = execute_model(model, image)

    return result    


if __name__ == '__main__':

    original_image = Image.open('./Images/67.tif')
    result = load_and_execute(original_image)
    result.show()
    # result is between 0 and 1
    