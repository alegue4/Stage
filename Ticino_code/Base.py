import argparse
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn.functional as F
import torch.utils.data as data
from einops import rearrange, repeat  # , reduce
import pytorch_lightning as pl
from pytorch_lightning.callbacks.model_checkpoint import ModelCheckpoint
from pytorch_lightning.loggers import TensorBoardLogger
from pytorch_lightning.callbacks import RichProgressBar
from torchvision import utils  # transforms, models, utils
from Ticino_code.Dataset import Dataset
from torch.optim.lr_scheduler import StepLR
from pytorch_lightning.callbacks import LearningRateMonitor, EarlyStopping
import torchmetrics
from torchmetrics import MetricCollection
import os
import seaborn as sns
from pytorch_lightning import seed_everything

class Base(pl.LightningModule):

    def __init__(self, params):
        super(Base, self).__init__()
        # save params
        self.save_hyperparameters()
        self.conf = params
        # define transforms
        self.input_transforms = None
        # define network
        self.net = None

         # define common arguments
        common_args_macro_lu = {'average': 'macro', 'num_classes': self.conf['n_classes_landuse'], 'ignore_index':0, 'device':self.device}
        common_args_micro_lu = {'average': 'micro', 'num_classes': self.conf['n_classes_landuse'], 'ignore_index':0, 'device':self.device}

        common_args_macro_ag = {'average': 'macro', 'num_classes': self.conf['n_classes_agricolture'], 'ignore_index':0, 'device':self.device}
        common_args_micro_ag = {'average': 'micro', 'num_classes': self.conf['n_classes_agricolture'], 'ignore_index':0, 'device':self.device}
        
        # define metrics for object
        metrics_lu = MetricCollection({
            'macro/accuracy': torchmetrics.Accuracy(task="multiclass", **common_args_macro_lu),
            'macro/iou': torchmetrics.JaccardIndex(task="multiclass", **common_args_macro_lu),
            'macro/dice': torchmetrics.Dice(**common_args_macro_lu),
            'macro/precision': torchmetrics.Precision(task='multiclass', **common_args_macro_lu, top_k=1),
            'macro/recall': torchmetrics.Recall(task='multiclass', **common_args_macro_lu, top_k=1),
            'micro/accuracy': torchmetrics.Accuracy(task="multiclass", **common_args_micro_lu),
            'micro/iou': torchmetrics.JaccardIndex(task="multiclass", **common_args_micro_lu),
            'micro/dice': torchmetrics.Dice(**common_args_micro_lu),
            'micro/precision': torchmetrics.Precision(task='multiclass', **common_args_micro_lu, top_k=1),
            'micro/recall': torchmetrics.Recall(task='multiclass', **common_args_micro_lu, top_k=1),
            })

        metrics_ag = MetricCollection({
            'macro/accuracy': torchmetrics.Accuracy(task="multiclass", **common_args_macro_ag),
            'macro/iou': torchmetrics.JaccardIndex(task="multiclass", **common_args_macro_ag),
            'macro/dice': torchmetrics.Dice(**common_args_macro_ag),
            'macro/precision': torchmetrics.Precision(task='multiclass', **common_args_macro_ag, top_k=1),
            'macro/recall': torchmetrics.Recall(task='multiclass', **common_args_macro_ag, top_k=1),
            'micro/accuracy': torchmetrics.Accuracy(task="multiclass", **common_args_micro_ag),
            'micro/iou': torchmetrics.JaccardIndex(task="multiclass", **common_args_micro_ag),
            'micro/dice': torchmetrics.Dice(**common_args_micro_ag),
            'micro/precision': torchmetrics.Precision(task='multiclass', **common_args_micro_ag, top_k=1),
            'micro/recall': torchmetrics.Recall(task='multiclass', **common_args_micro_ag, top_k=1),
            })
        
        self.metrics_lu = metrics_lu.clone(prefix='landuse/')
        self.metrics_ag = metrics_ag.clone(prefix='agriculture/')

        # test metrics
        self.metrics_lu_test = metrics_lu.clone(prefix='test/landuse/')
        self.metrics_ag_test = metrics_ag.clone(prefix='test/agriculture/')
        self.confusionMat_lu = torchmetrics.ConfusionMatrix(task='multiclass', ignore_index=0, num_classes=self.conf['n_classes_landuse'], normalize='true')
        self.confusionMat_ag = torchmetrics.ConfusionMatrix(task='multiclass', ignore_index=0, num_classes=self.conf['n_classes_agricolture'], normalize='true')

        common_args_class_lu = {'average': 'none', 'num_classes': self.conf['n_classes_landuse'], 'ignore_index':0, 'device':self.device}
        common_args_class_ag = {'average': 'none', 'num_classes': self.conf['n_classes_agricolture'], 'ignore_index':0, 'device':self.device}
        
        metrics_class_lu = MetricCollection({
            'class/accuracy': torchmetrics.Accuracy(task="multiclass", **common_args_class_lu),
            'class/iou': torchmetrics.JaccardIndex(task="multiclass", **common_args_class_lu),
            'class/precision': torchmetrics.Precision(task='multiclass', **common_args_class_lu, top_k=1),
            'class/recall': torchmetrics.Recall(task='multiclass', **common_args_class_lu, top_k=1)
            })

        metrics_class_ag = MetricCollection({
            'class/accuracy': torchmetrics.Accuracy(task="multiclass", **common_args_class_ag),
            'class/iou': torchmetrics.JaccardIndex(task="multiclass", **common_args_class_ag),
            'class/precision': torchmetrics.Precision(task='multiclass', **common_args_class_ag, top_k=1),
            'class/recall': torchmetrics.Recall(task='multiclass', **common_args_class_ag, top_k=1)
            })
        
        self.metrics_class_lu = metrics_class_lu.clone(prefix='landuse/')
        self.metrics_class_ag = metrics_class_ag.clone(prefix='agriculture/')

        self.model_name = self.conf['encoder_name']
        self.experiment_folder = ''

    def forward(self, batch):
        raise NotImplementedError('Base must be extended by child class that specifies the forward method.')


    def training_step(self, batch, batch_nb):

        inputs, targets, _ = batch # for the name of the image

        # append
        logits = self(inputs)
        gt_lu, gt_ag = targets
     
        # split logits
        logits_lu = logits[:,:self.conf['n_classes_landuse']]
        logits_ag = logits[:,self.conf['n_classes_landuse']:self.conf['n_classes_landuse'] + self.conf['n_classes_agricolture']]
        # apply loss

        loss_lu = F.cross_entropy(logits_lu, gt_lu.squeeze(dim=1), weight=1-torch.tensor([1, 0.08169914,
                                                                                          0.05278166,
                                                                                          0.16236057,
                                                                                          0.02600136,
                                                                                          0.31404807,
                                                                                          0.33979217,
                                                                                          0.02331703], device=logits_lu.device), ignore_index=0)
        loss_ag = F.cross_entropy(logits_ag, gt_ag.squeeze(dim=1), weight=1-torch.tensor([1,
                                                                                          0.01157833,
                                                                                          0.06146465,
                                                                                          0.13093557,
                                                                                          0.0496246,
                                                                                          0.40127885,
                                                                                          0.01595872,
                                                                                          0.13955435,
                                                                                          0.01651926,
                                                                                          0.17308567], device=logits_lu.device), ignore_index=0)

        loss = self.conf['alpha']*loss_lu + (1-self.conf['alpha'])*loss_ag

        self.log("losses/landuse", loss_lu, on_step=False, on_epoch=True, prog_bar=True, batch_size=self.conf['batch_size'])
        self.log("losses/agricolture", loss_ag, on_step=False, on_epoch=True, prog_bar=True, batch_size=self.conf['batch_size'])
        self.log("losses/total", loss, on_step=False, on_epoch=True, prog_bar=True, batch_size=self.conf['batch_size'])

        # show images
        if batch_nb % 500 == 0:
            _, class_lu = torch.max(logits_lu, 1)
            _, class_ag = torch.max(logits_ag, 1)
            self.show_images(class_lu, class_ag, inputs, gt_lu, gt_ag)

        return loss
    
    def validation_step(self, batch, batch_idx):

        inputs, targets, _ = batch

        # get input and semantic layout
        logits = self(inputs)
        gt_lu, gt_ag = targets

        # split logits
        logits_lu = logits[:,:self.conf['n_classes_landuse']]
        logits_ag = logits[:,self.conf['n_classes_landuse']:self.conf['n_classes_landuse'] + self.conf['n_classes_agricolture']]

        # log validation loss
        loss_lu = F.cross_entropy(logits_lu, gt_lu.squeeze(dim=1), weight=1-torch.tensor([1-torch.finfo().eps,
                                                                                          0.08169914,
                                                                                          0.05278166,
                                                                                          0.16236057,
                                                                                          0.02600136,
                                                                                          0.31404807,
                                                                                          0.33979217,
                                                                                          0.02331703], device=logits_lu.device), ignore_index=0)        
        loss_ag = F.cross_entropy(logits_ag, gt_ag.squeeze(dim=1), weight=1-torch.tensor([1,
                                                                                          0.01157833,
                                                                                          0.06146465,
                                                                                          0.13093557,
                                                                                          0.0496246,
                                                                                          0.40127885,
                                                                                          0.01595872,
                                                                                          0.13955435,
                                                                                          0.01651926,
                                                                                          0.17308567], device=logits_lu.device), ignore_index=0)

        loss = self.conf['alpha']*loss_lu + (1-self.conf['alpha'])*loss_ag
        self.log("losses/val_landuse", loss_lu, on_step=False, on_epoch=True, prog_bar=True, batch_size=self.conf['batch_size'])
        self.log("losses/val_agricolture", loss_ag, on_step=False, on_epoch=True, prog_bar=True, batch_size=self.conf['batch_size'])
        self.log("losses/val_total", loss, on_step=False, on_epoch=True, prog_bar=True, batch_size=self.conf['batch_size'])

        # view images
        if batch_idx % 500 == 0:
            _, class_lu = torch.max(logits_lu, 1)
            _, class_ag = torch.max(logits_ag, 1)
            self.show_images(class_lu, class_ag, inputs, gt_lu, gt_ag, stage='val')

        self.metrics_lu.update(logits_lu, gt_lu)
        self.metrics_ag.update(logits_ag, gt_ag)

    def test_step(self, batch, batch_idx):

        self.experiment_folder = './torchmetrics_results/' + self.model_name + "_version_" + str(self.logger.version)

        if not(os.path.exists(self.experiment_folder)):
                os.mkdir(self.experiment_folder)

        inputs, targets, names = batch

        # get input and semantic layout
        logits = self(inputs)
        gt_lu, gt_ag = targets
        
        logits_lu = logits[:,:self.conf['n_classes_landuse']]
        logits_ag = logits[:,self.conf['n_classes_landuse']:self.conf['n_classes_landuse'] + self.conf['n_classes_agricolture']]

        # view images
        if batch_idx == 0:
            _, class_lu = torch.max(logits_lu, 1)
            _, class_ag = torch.max(logits_ag, 1)
            self.show_images(class_lu, class_ag, inputs, gt_lu, gt_ag, stage='test')

        self.metrics_lu_test.update(logits_lu, gt_lu)
        self.metrics_ag_test.update(logits_ag, gt_ag)
        self.confusionMat_lu.update(logits_lu, gt_lu)
        self.confusionMat_ag.update(logits_ag, gt_ag)
        self.metrics_class_lu.update(logits_lu, gt_lu)
        self.metrics_class_ag.update(logits_ag, gt_ag)

        # save landuse
        labels = ['Background','Building','Road','Residential','Industrial','Forest','Farmland','Water']
        self._show_and_save_predictions(inputs=inputs, logits=logits_lu, gt=gt_lu, num_classes=self.conf['n_classes_landuse'], names=names, label=labels, folder='Landuse/', mode='landuse')

        labels=[
            'Background',
            'Other agricultural crops',
            'Forage crops',
            'Corn',
            'Industrial plants',
            'Rice',
            'Seeds',
            'Man-made areas',
            'Water bodies',
            'Natural vegetation']

        self._show_and_save_predictions(inputs=inputs, logits=logits_ag, gt=gt_ag, num_classes=self.conf['n_classes_agricolture'], names=names, label=labels, folder='Agriculture/', mode='agriculture')
   

    def on_validation_epoch_end(self):

        output_lu = self.metrics_lu.compute()
        output_ag = self.metrics_ag.compute()

        self.log_dict(output_lu)
        self.log_dict(output_ag)

        self.metrics_lu.reset()
        self.metrics_ag.reset()

    def on_test_epoch_end(self):
 
        results_path = self.experiment_folder

        # confusion matrix
        confMat_lu = self.confusionMat_lu.compute()
        confMat_ag = self.confusionMat_ag.compute()

        labels = ['Background', 'Building', 'Roads', 'Residential', 'Industrial', 'Forest', 'Farmland', 'Water']
        self._save_confusionMatrix(confMat_lu, results_path, labels, mode='landuse')

        labels=[
            'Background',
            'Other agricultural crops',
            'Forage crops',
            'Corn',
            'Industrial plants',
            'Rice',
            'Seeds',
            'Man-made areas',
            'Water bodies',
            'Natural vegetation']
                    
        self._save_confusionMatrix(confMat_ag, results_path, labels, mode='agriculture')

        self.confusionMat_lu.reset()
        self.confusionMat_ag.reset()

        # Metrics

        output_lu = self.metrics_lu_test.compute()
        output_ag = self.metrics_ag_test.compute()

        self.log_dict(output_lu)
        self.log_dict(output_ag)

        results_to_save = ''
        for cur_metric_name in output_lu:
            results_to_save += cur_metric_name + ' : ' + str(output_lu[cur_metric_name].item()) + '\n'

        self._save_list_results(results_path, "/test_metrics_lu.txt", (results_to_save,)) # list is to not create a different save_list function

        results_to_save = ''
        for cur_metric_name in output_ag:
            results_to_save += cur_metric_name + ' : ' + str(output_ag[cur_metric_name].item()) + '\n'

        self._save_list_results(results_path, "/test_metrics_ag.txt", (results_to_save,)) # list is to not create a different save_list function

        self.metrics_lu_test.reset()
        self.metrics_ag_test.reset()

        # per class
        output_lu = self.metrics_class_lu.compute()
        output_ag = self.metrics_class_ag.compute()

        for metrics in output_lu:
            results_to_save = ''
            computed_metrics = output_lu[metrics]
            for metric_value in computed_metrics:
                results_to_save += str(metric_value.item()) + '\n'

            self._save_list_results(results_path, "/landuse_class_" + metrics.split('/')[-1] + ".txt", (results_to_save,)) # list is to not create a different save_list function

        for metrics in output_ag:
            results_to_save = ''
            computed_metrics = output_ag[metrics]
            for metric_value in computed_metrics:
                results_to_save += str(metric_value.item()) + '\n'

            self._save_list_results(results_path, "/agriculture_class_" + metrics.split('/')[-1] + ".txt", (results_to_save,)) # list is to not create a different save_list function

        self.metrics_class_lu.reset()
        self.metrics_class_ag.reset()


    def _save_confusionMatrix(self, confMat, results_path, labels, mode='landuse'):
        
        confMat = confMat.cpu().detach().numpy()
        
        # save confmat
        res_mat = ''
        for row_el in range(confMat.shape[0]):
            for col_el in range(confMat.shape[1]):
                res_mat += str(confMat[row_el, col_el].item()) +  " "
            res_mat += "\n"

        self._save_list_results(results_path, "/" + mode + "_confusion_matrix.txt", (res_mat,)) # list is to not create a different save_list function

        if mode == 'agriculture':
            sns.set(font_scale=0.3)

        sns.heatmap(confMat, annot=True, fmt='.2f', cmap='Blues', xticklabels=labels, yticklabels=labels)
        plt.tight_layout()
        plt.savefig(results_path + '/' + mode + '_confusion_matrix.png', dpi=200)

        plt.clf()


    def _show_and_save_predictions(self, inputs, logits, gt, num_classes, names, folder, label, mode='landuse'):

        ignore_index = 0
        im_mIoU = torchmetrics.JaccardIndex(task="multiclass", average='none', num_classes=num_classes, ignore_index=ignore_index)

        if not(self.conf['pca']):
            rgb, _, _, _, _ = inputs
        else:
            if mode == 'landuse':
                rgb, _, _ = inputs
            else:
                rgb, hs, _ = inputs


        fontsize = 15
        for im_batch in range(logits.shape[0]):

            rgb2show = rearrange(rgb[im_batch], 'c h w -> h w c').cpu().float().numpy()
            rgb2show = (rgb2show -  np.min(rgb2show)) / (np.max(rgb2show) - np.min(rgb2show))
            
            if not(mode == 'landuse'):
                hs2show = rearrange(hs[im_batch], 'c h w -> h w c').cpu().float().numpy()
                hs2show = hs2show[:,:,(50,39,30)]
                hs2show = (hs2show -  np.min(hs2show)) / (np.max(hs2show) - np.min(hs2show))

            out2show = logits[im_batch].argmax(dim=0).cpu().detach().float().numpy()/num_classes
            gt2show = gt[im_batch].squeeze().cpu().detach().float().numpy()/num_classes

            out2show[gt2show==0] = 0 # Masked

            color_map = 'Paired'
            if mode == 'landuse':
                fig, (ax1, ax6, ax7) = plt.subplots(1,3, figsize=(20,10))
            else:
                fig, (ax1, ax6, ax7) = plt.subplots(1,3, figsize=(20,10))

            mask_log = logits[im_batch].argmax(dim=0)
            mask_log[gt[im_batch]==0] = 0
            im_mIoU.update(mask_log.unsqueeze(dim=0).cpu(), gt[im_batch].unsqueeze(dim=0).cpu())
            mIoU = im_mIoU.compute()
            # consider only present classes
            present_classes = torch.cat((mask_log.unique(), gt[im_batch].unique())).unique().cpu()
            present_classes = present_classes[present_classes!=ignore_index]
            mIoU = mIoU[present_classes].mean()
            fig.suptitle(str(mIoU))
            im_mIoU.reset()
            
            ax1.imshow(rgb2show)
            ax1.axis('off')
            ax1.set_title('RGB', fontsize=fontsize)
            ax6.imshow(gt2show, cmap=color_map, vmin=0, vmax=1)
            ax6.axis('off')
            ax6.set_title('GT', fontsize=fontsize)

            ax7.imshow(out2show, cmap=color_map, vmin=0, vmax=1)
            ax7.axis('off')
            ax7.set_title('Prediction', fontsize=fontsize)

            # legend
            cmap = plt.get_cmap('Paired')
            norm = plt.Normalize(vmin=0, vmax=len(label))

            handles = [plt.Rectangle((0, 0), 0, 0, color=cmap(norm(i)), label=label[i]) for i in range(len(label))]
            ax7.legend(handles=handles, fontsize=fontsize, loc=(1.04, 0.1))
            plt.tight_layout()

            if not(os.path.exists(self.experiment_folder + '/test_images/')):
                os.mkdir(self.experiment_folder + '/test_images/')

            if not(os.path.exists(self.experiment_folder + '/test_images/' + folder)):
                os.mkdir(self.experiment_folder + '/test_images/' + folder)

            fig.savefig(self.experiment_folder + '/test_images/' + folder + names[im_batch].split('.')[0] + '.png', dpi=200)

            fig.clear()
            plt.clf()
            plt.close(fig)


    # SAVE MODEL RESULTS
    def _save_list_results(self, results_path, name_list, data):
        if not(os.path.exists(results_path)):
            os.mkdir(results_path)
        
        with open(results_path + name_list, 'w') as fp:
            for item in data:
                fp.write(str(item) + "\n")    

    # show images
    def color_coding(self, semlay, n_classes, cmap='Paired'):
        # get colormap
        cmap = plt.get_cmap('Paired')
        # apply colormap
        rgb_out = cmap((semlay.cpu().float()/n_classes).numpy())
        # fix dims
        rgb_out = rearrange(torch.from_numpy(rgb_out), 'b h w c -> b c h w')
        # return
        return rgb_out

    def show_images(self, out_lu, out_ag, inputs, gt_lu, gt_ag, stage='train'):
        
        # move to cpu and detach
        rgb, hs, dem = inputs

        out_lu = out_lu.cpu().detach()
        out_ag = out_ag.cpu().detach()
        rgb = rgb.cpu().detach()
        hs = hs.cpu().detach()
        dem = dem.cpu().detach()
        gt_lu = gt_lu.cpu().detach()
        gt_ag = gt_ag.cpu().detach()
        # create masked outputs
        out_lu_masked = torch.zeros_like(out_lu)
        out_ag_masked = torch.zeros_like(out_ag)
        # for each image, remove content in background
        for i in range(out_lu.shape[0]):
            cur_lu_masked = out_lu[i].clone()
            cur_lu_gt = gt_lu[i]
            cur_lu_masked[cur_lu_gt==0] = 0
            out_lu_masked[i] = cur_lu_masked
            cur_ag_masked = out_ag[i].clone()
            cur_ag_gt = gt_ag[i]
            cur_ag_masked[cur_ag_gt==0] = 0
            out_ag_masked[i] = cur_ag_masked
        # color coding
        out_lu = self.color_coding(out_lu, self.conf['n_classes_landuse'])
        out_ag = self.color_coding(out_ag, self.conf['n_classes_agricolture'])
        out_lu_masked = self.color_coding(out_lu_masked, self.conf['n_classes_landuse'])
        out_ag_masked = self.color_coding(out_ag_masked, self.conf['n_classes_agricolture'])
        gt_lu = self.color_coding(gt_lu, self.conf['n_classes_landuse'])
        gt_ag = self.color_coding(gt_ag, self.conf['n_classes_agricolture'])
        # normalize other images
        dem = (dem - dem.min()) / (dem.max() - dem.min())
        rgb = (rgb - rgb.min()) / (rgb.max() - rgb.min())
        hs = (hs - hs.min()) / (hs.max() - hs.min())
        # sanitize images with nan
        out_lu_masked = torch.nan_to_num(out_lu_masked, nan=0.0)
        out_ag_masked = torch.nan_to_num(out_ag_masked, nan=0.0)
        out_lu = torch.nan_to_num(out_lu, nan=0.0)
        out_ag = torch.nan_to_num(out_ag, nan=0.0)
        # clamp
        out_lu_masked = torch.clamp(out_lu_masked, min=0, max=1)
        out_ag_masked = torch.clamp(out_ag_masked, min=0, max=1)
        out_lu = torch.clamp(out_lu, min=0, max=1)
        out_ag = torch.clamp(out_ag, min=0, max=1)
        rgb = torch.clamp(rgb, min=0, max=1)
        hs = torch.clamp(hs, min=0, max=1)
        dem = torch.clamp(dem, min=0, max=1)
        # display semantic layouts
        self.logger.experiment.add_image(f'{stage}/landuse/out_masked', utils.make_grid(out_lu_masked), self.global_step)
        self.logger.experiment.add_image(f'{stage}/agricolture/out_masked', utils.make_grid(out_ag_masked), self.global_step)
        self.logger.experiment.add_image(f'{stage}/landuse/out', utils.make_grid(out_lu), self.global_step)
        self.logger.experiment.add_image(f'{stage}/agricolture/out', utils.make_grid(out_ag), self.global_step)
        self.logger.experiment.add_image(f'{stage}/landuse/gt', utils.make_grid(gt_lu), self.global_step)
        self.logger.experiment.add_image(f'{stage}/agricolture/gt', utils.make_grid(gt_ag), self.global_step)
        # display input images
        self.logger.experiment.add_image(f'{stage}/inputs/rgb', utils.make_grid(rgb), self.global_step)
        self.logger.experiment.add_image(f'{stage}/inputs/hs', utils.make_grid(hs.mean(1).unsqueeze(1)), self.global_step)
        self.logger.experiment.add_image(f'{stage}/inputs/dem', utils.make_grid(dem), self.global_step)

    def configure_optimizers(self):

        # set net parameters as optimization
        if self.conf['method'] == 'middle_fusion':
            params = [
                {'params': self.fusion_en.parameters()},
                {'params': self.net.parameters()},
            ]
        else:
            params = [
                {'params': self.net.parameters()},
            ]


        optimizer = torch.optim.Adam(
                            params,
                            weight_decay = self.conf['weight_decay'],
                            lr = self.conf['learning_rate'])

        LR_scheduler = {"scheduler": StepLR(optimizer, step_size=30, gamma=0.85), "monitor": "losses/val_total",
                        'name': 'Learning_rate'}
        
        return ([optimizer], [LR_scheduler])
        
        
    def train_dataloader(self):
        ds = Dataset(self.conf['root_dir'], self.conf['train_csv'], self.conf['pca'], self.train_transforms())
        dl = data.DataLoader(ds, batch_size=self.conf['batch_size'], num_workers=self.conf['num_workers'], shuffle=True)
        return dl
    
    def val_dataloader(self):
        ds = Dataset(self.conf['root_dir'], self.conf['val_csv'], self.conf['pca'], self.val_transforms())
        dl = data.DataLoader(ds, batch_size=self.conf['batch_size'], num_workers=self.conf['num_workers'], shuffle=False)
        return dl
    
    
    def test_dataloader(self):
        ds = Dataset(self.conf['root_dir'], self.conf['test_csv'], self.conf['pca'], self.test_transforms())
        dl = data.DataLoader(ds, batch_size=self.conf['batch_size'], num_workers=self.conf['num_workers'], shuffle=False)
        return dl

    def train_transforms(self):
        return None
    
    def val_transforms(self):
        return None

    def test_transforms(self):
        return None
    

    @staticmethod
    def main(cur_class):
        # define parser
        parser = argparse.ArgumentParser()
        # define arguments
        parser.add_argument("-json", "--json", help="Json (used only when training).",
                            default='', type=str)
        parser.add_argument("-ckp", "--checkpoint", help="Checkpoint (used only when regen/testing).",
                            default='', type=str)
        parser.add_argument("-out", "--out", help="Output filename.",
                            default='', type=str)
        parser.add_argument("-test", "--test", help="If set, computes metrics instead of regen.",
                            action='store_true')
        # parse args
        args = parser.parse_args()

        # check if we are in training or testing
        if not args.test:
            # if checkpoint not specified, load from json
            if args.checkpoint == '':
                # read json
                print(args.json)
                with open(args.json) as f:
                    conf = json.load(f)
                # init model
                model = cur_class(conf)
            else:
                # load from checkpoint
                model = cur_class.load_from_checkpoint(args.checkpoint)
                conf = model.conf

            # show model
            print(model)

            if conf['alpha'] == 0:
                callbacks = [
                        RichProgressBar(),
                        ModelCheckpoint(monitor='agriculture/macro/accuracy', mode='max', save_top_k=1, save_last=True, filename='agriculture/macro_accuracy'), # True
                        ModelCheckpoint(monitor='agriculture/macro/iou', mode='max', save_top_k=1, save_last=False, filename='agriculture/macro_iou'),
                        ModelCheckpoint(monitor='agriculture/micro/accuracy', mode='max', save_top_k=1, save_last=True, filename='agriculture/micro_accuracy'), # True
                        ModelCheckpoint(monitor='agriculture/micro/iou', mode='max', save_top_k=1, save_last=False, filename='agriculture/micro_iou'),
                        LearningRateMonitor(logging_interval='epoch'),
                        # EarlyStopping(monitor="val_loss", mode="min", patience=20)
                    ]
            elif conf['alpha'] == 1:
                callbacks = [
                        RichProgressBar(),
                        ModelCheckpoint(monitor='landuse/macro/accuracy', mode='max', save_top_k=1, save_last=False, filename='landuse/macro_accuracy'),
                        ModelCheckpoint(monitor='landuse/macro/iou', mode='max', save_top_k=1, save_last=True, filename='landuse/macro_iou'),
                        ModelCheckpoint(monitor='landuse/micro/accuracy', mode='max', save_top_k=1, save_last=False, filename='landuse/micro_accuracy'),
                        ModelCheckpoint(monitor='landuse/micro/iou', mode='max', save_top_k=1, save_last=True, filename='landuse/micro_iou'),
                        LearningRateMonitor(logging_interval='epoch'),
                    ]
            else:
                callbacks = [
                        RichProgressBar(),
                        ModelCheckpoint(monitor='landuse/macro/accuracy', mode='max', save_top_k=1, save_last=False, filename='landuse/macro_accuracy'),
                        ModelCheckpoint(monitor='landuse/macro/iou', mode='max', save_top_k=1, save_last=True, filename='landuse/macro_iou'),
                        ModelCheckpoint(monitor='landuse/micro/accuracy', mode='max', save_top_k=1, save_last=False, filename='landuse/micro_accuracy'),
                        ModelCheckpoint(monitor='landuse/micro/iou', mode='max', save_top_k=1, save_last=True, filename='landuse/micro_iou'),
                        ModelCheckpoint(monitor='agriculture/macro/accuracy', mode='max', save_top_k=1, save_last=True, filename='agriculture/macro_accuracy'), # True
                        ModelCheckpoint(monitor='agriculture/macro/iou', mode='max', save_top_k=1, save_last=False, filename='agriculture/macro_iou'),
                        ModelCheckpoint(monitor='agriculture/micro/accuracy', mode='max', save_top_k=1, save_last=True, filename='agriculture/micro_accuracy'), # True
                        ModelCheckpoint(monitor='agriculture/micro/iou', mode='max', save_top_k=1, save_last=False, filename='agriculture/micro_iou'),
                        LearningRateMonitor(logging_interval='epoch'),
                    ]

           # define trainer
            trainer = pl.Trainer(
                            accelerator='gpu',
                            devices=1,
                            max_epochs=conf['n_epochs'] if 'n_epochs' in conf else 10000000,
                            # max_epochs=250,
                            num_sanity_val_steps = 2 if args.checkpoint == '' else 0,
                            logger=TensorBoardLogger('checkpoints', name=conf['experiment_name']),
                            profiler="simple",
                            callbacks=callbacks,
                            deterministic='warn')
            if args.checkpoint == '':
                trainer.fit(model)
            else:
                trainer.fit(model,ckpt_path=args.checkpoint)

            # test

            trainer.test(model)
        else:

            #test
            model = cur_class.load_from_checkpoint(args.checkpoint)
            conf = model.conf
            
            tester = pl.Trainer()
            tester.test(model)
            
