import numpy as np
import torch
from einops import rearrange, repeat # , reduce

import segmentation_models_pytorch as smp
from Base import Base
import albumentations as A
from albumentations.pytorch.transforms import ToTensorV2

import pickle

from middle_fusion_rgb_hs import Middle_fusion_en as mf_rgb_hs
from middle_fusion_rgb_dem import Middle_fusion_en as mf_rgb_dem
from middle_fusion_rgb_hs_dem import Middle_fusion_en as mf_rgb_hs_dem

# seed
import random
from pytorch_lightning import seed_everything

from pytorch_lightning.utilities import measure_flops

class KnownArchitectures(Base):
    def __init__(self, params):
        # init base
        super(KnownArchitectures, self).__init__(params)

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

        rgb, hs, dtm = batch

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

            with torch.device("meta"):
                model = self.net
                x = inp

            model_fwd = lambda: model(x)
            fwd_flops = measure_flops(model, model_fwd)
            print("flops:" + str(fwd_flops))

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

            with torch.device("meta"):
                model = self.net
                x = inp

            model_fwd = lambda: model(x)
            fwd_flops = measure_flops(model, model_fwd)
            print("flops:" + str(fwd_flops))

            return self.net(inp)
            

    def create_transform_function(self, transform_list):
        # create function
        def transform_inputs(inps):
            # create transformation

            rgb, hs, dem, gt_lu, gt_ag = inps
            normalize_rgb, normalize_hs, normalize_dem, transforms_augmentation = transform_list

            # ipdb.set_trace()
            transforms = A.Compose([transforms_augmentation],
                                    additional_targets={'hs': 'image',
                                                        'dem': 'image',
                                                        'gt_ag': 'mask'})

            rgb = (rgb.permute(1,2,0).numpy() - self.loaded_min_dict_before_normalization['rgb']) / (self.loaded_max_dict_before_normalization['rgb'] - self.loaded_min_dict_before_normalization['rgb'])
            hs = (hs.permute(1,2,0).numpy() - self.loaded_min_dict_before_normalization['hs']) / (self.loaded_max_dict_before_normalization['hs'] - self.loaded_min_dict_before_normalization['hs'])
            dem = (dem.permute(1,2,0).numpy() - self.loaded_min_dict_before_normalization['dem']) / (self.loaded_max_dict_before_normalization['dem'] - self.loaded_min_dict_before_normalization['dem'])

            rgb = normalize_rgb(image=rgb)['image']
            hs = normalize_hs(image=hs)['image']
            dem = normalize_dem(image=dem)['image']

            sample = transforms(image=rgb,
                                mask=gt_lu.permute(1,2,0).numpy(),
                                hs=hs,
                                dem=dem,
                                gt_ag=gt_ag.permute(1,2,0).numpy()
                                )
            
            # get images
            rgb = sample['image']
            gt_lu = sample['mask'].long().permute(2,0,1).squeeze(dim=0)
            gt_ag = sample['gt_ag'].long().permute(2,0,1).squeeze(dim=0)
            hs = sample['hs']
            dem = sample['dem']

            # return results
            return rgb, hs, dem, gt_lu, gt_ag # Change back

        # return the function
        return transform_inputs

    def train_transforms(self):
        # define training size
        train_size = self.conf['train_size'] if 'train_size' in self.conf else self.conf['input_size']
        # create transformation

        normalize_rgb = A.Normalize(mean=self.mean_dict['rgb'], std=self.std_dict['rgb'], max_pixel_value=self.max_dict['rgb'])
        normalize_hs = A.Normalize(mean=self.mean_dict['hs'], std=self.std_dict['hs'], max_pixel_value=self.max_dict['hs'])
        normalize_dem = A.Normalize(mean=self.mean_dict['dem'], std=self.std_dict['dem'], max_pixel_value=self.max_dict['dem'])

        transforms_augmentation = A.Compose([A.Resize(*self.conf['input_size']),
            A.crops.transforms.RandomCrop(*train_size),
            A.Rotate(limit=[-180, 180]),
            A.HorizontalFlip(p=0.5),
            A.VerticalFlip(p=0.5),
            A.Transpose(p=0.5),
            ToTensorV2()
        ])

        transforms = normalize_rgb, normalize_hs, normalize_dem, transforms_augmentation

        # create transform function
        return self.create_transform_function(transforms)
        

    def val_transforms(self):

        # create transformation
        normalize_rgb = A.Normalize(mean=self.mean_dict['rgb'], std=self.std_dict['rgb'], max_pixel_value=self.max_dict['rgb'])
        normalize_hs = A.Normalize(mean=self.mean_dict['hs'], std=self.std_dict['hs'], max_pixel_value=self.max_dict['hs'])
        normalize_dem = A.Normalize(mean=self.mean_dict['dem'], std=self.std_dict['dem'], max_pixel_value=self.max_dict['dem'])

        transforms_augmentation = A.Compose([
            A.Resize(*self.conf['input_size']),
            ToTensorV2()
        ])

        transforms = normalize_rgb, normalize_hs, normalize_dem, transforms_augmentation
    
        # create transform function
        return self.create_transform_function(transforms)
    
    def test_transforms(self):
        return self.val_transforms()
        

if __name__ == '__main__':

    torch.autograd.set_detect_anomaly(True)

    # train or test
    seed = 42
    random.seed(seed)
    torch.manual_seed(seed)
    np.random.seed(seed)
    seed_everything(seed, workers=True)
    torch.backends.cudnn.deterministic = True

    Base.main(KnownArchitectures)
        