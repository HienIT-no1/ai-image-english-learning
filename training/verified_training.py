"""YOLO11 training that ignores image/category pairs LVIS has not verified.

The standard detector and checkpoint format are retained. Only the training
criterion/dataset/validation proxy differ; Ultralytics strips criterion on save.
"""
from __future__ import annotations

import json
from copy import copy
from pathlib import Path

import torch
import torch.nn.functional as F
from ultralytics.data.dataset import YOLODataset
from ultralytics.models.yolo.detect import DetectionTrainer, DetectionValidator
from ultralytics.utils.loss import v8DetectionLoss
from ultralytics.utils.metrics import box_iou


def manifest_for(path) -> dict:
    return json.loads((Path(path) / 'manifest.json').read_text(encoding='utf-8'))


def verification_index(manifest: dict) -> dict:
    mapping={c['lvis_category_id']:c['class_id'] for c in manifest['classes']}
    return {Path(record['source_url']).stem: [mapping[c] for c in record['verified_categories']]
            for records in manifest['splits'].values() for record in records}


class VerifiedDataset(YOLODataset):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.verified_index=verification_index(manifest_for(self.data['path']))

    def __getitem__(self, index):
        item=super().__getitem__(index)
        mask=torch.zeros(self.data['nc'],dtype=torch.bool)
        key=Path(item['im_file']).stem
        mask[self.verified_index[key]]=True
        item['verified_classes']=mask
        return item

    @staticmethod
    def collate_fn(batch):
        masks=torch.stack([item['verified_classes'] for item in batch])
        stripped=[{key:value for key,value in item.items() if key!='verified_classes'} for item in batch]
        result=YOLODataset.collate_fn(stripped)
        result['verified_classes']=masks
        return result


class VerifiedBCE(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.known=None

    def forward(self, logits, targets):
        if self.known is None:
            raise RuntimeError('Missing LVIS verification mask; refusing unmasked training')
        # Even a non-exhaustive category has valid annotated positive anchors.
        active=self.known.to(logits.device).unsqueeze(1) | (targets>0)
        return F.binary_cross_entropy_with_logits(logits,targets,reduction='none')*active


class VerifiedLoss(v8DetectionLoss):
    def __init__(self, model):
        super().__init__(model)
        self.bce=VerifiedBCE()

    def __call__(self,preds,batch):
        self.bce.known=batch.get('verified_classes')
        try:
            return super().__call__(preds,batch)
        finally:
            self.bce.known=None


class VerifiedValidator(DetectionValidator):
    """A checkpoint-selection proxy; final reporting uses the official LVIS evaluator."""
    def update_metrics(self,preds,batch):
        filtered=[]
        for index,pred in enumerate(preds):
            prepared=self._prepare_batch(index,batch)
            verified=batch['verified_classes'][index].to(pred['cls'].device)
            keep=verified[pred['cls'].long()]
            if len(pred['cls']) and len(prepared['cls']):
                iou=box_iou(prepared['bboxes'],pred['bboxes'])
                same=prepared['cls'][:,None]==pred['cls'][None,:]
                keep=keep | ((iou>=.5)&same).any(0)
            filtered.append({key:value[keep] for key,value in pred.items()})
        super().update_metrics(filtered,batch)


class VerifiedTrainer(DetectionTrainer):
    def set_model_attributes(self):
        super().set_model_attributes()
        self.model.criterion=VerifiedLoss(self.model)

    def build_dataset(self,img_path,mode='train',batch=None):
        if self.args.mosaic or self.args.mixup or self.args.copy_paste or self.args.cutmix:
            raise ValueError('Mixed-image augmentation is disabled until verification masks can be merged safely')
        stride=max(int(self.model.stride.max()),32)
        return VerifiedDataset(img_path=img_path,imgsz=self.args.imgsz,batch_size=batch,
            augment=mode=='train',hyp=self.args,rect=mode=='val',cache=False,
            single_cls=False,stride=stride,pad=0.5 if mode=='val' else 0.0,
            prefix=f'{mode}: ',task='detect',classes=None,data=self.data,fraction=1.0)

    def get_validator(self):
        self.loss_names='box_loss','cls_loss','dfl_loss'
        return VerifiedValidator(self.test_loader,save_dir=self.save_dir,args=copy(self.args),_callbacks=self.callbacks)
