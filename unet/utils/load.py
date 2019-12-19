#
# load.py : utils on generators / lists of ids to transform from strings to
#           cropped images and masks

import os

import numpy as np
from PIL import Image
import torch
import h5py
import json
from PIL import Image, ImageDraw
import cv2
from unet.utils import *
from debug_tools import __benchmark_init, benchmark
import pycocotools.mask as mask_utils



class Xview2Detectron2Dataset(torch.utils.data.Dataset):
    '''
    Dataset for Detectron2 style labelled Dataset
    '''
    def __init__(self, file_path,
                 pre_or_post,
                 include_index=False,
                 include_image_weight = False,
                 transform = None,

                 ):
        super().__init__()

        ds_path = os.path.join(file_path,'labels.json')
        with open(ds_path) as f:
            ds = json.load(f)
        self.dataset_metadata = ds
        self.dataset_path = file_path

        self.length = len(ds)
        print('dataset length', self.length)
        self.include_index = include_index
        self.label_mask_cache = {}
        self.include_image_weight = include_image_weight
        self.transform = transform
        self.pre_or_post = pre_or_post


    def __getitem__(self, index):

        # TODO PRE or POST selection or both
        data_sample = self.dataset_metadata[index][self.pre_or_post]

        sample_name = data_sample['file_name']
        input =self._process_input(sample_name)
        label = self._extract_label(data_sample['annotations'], sample_name)
        # label = label[None, ...] # C x H x W

        if self.transform:
            input, label, _ = self.transform([input, label, sample_name])

        ret = [input, label, sample_name]
        if self.include_index:
            ret += [index]
        if self.include_image_weight:
            # Used for oversampling stats
            if hasattr(data_sample, 'image_weight'):
                ret += [data_sample['image_weight']]
            else:
                ret += [label.sum()]
        return ret

    def _extract_label(self, annotations_set, sample_name):

        # Load preprocessed mask if exist
        mask_path = os.path.join(self.dataset_path, 'label_mask',sample_name)
        if os.path.exists(mask_path):
            mask = cv2.imread(mask_path)[...,0].astype(np.float32)
            return mask

        building_polygons = []
        for anno in annotations_set:
            building_polygon_xy = np.array(anno['segmentation'][0], dtype=np.int32).reshape(-1, 2)
            building_polygons.append(building_polygon_xy)

        mask2 = np.zeros((1024, 1024), dtype=np.uint8)
        cv2.fillPoly(mask2, building_polygons, 1)
        mask = mask2.astype(np.float32)
        return mask

    def _process_input(self, image_filename):
        img_path = os.path.join(self.dataset_path, image_filename)
        img = cv2.imread(img_path)
        return img

    def __len__(self):
        return self.length

class Xview2Detectron2DamageLevelDataset(Xview2Detectron2Dataset):
    def _extract_label(self, annotations_set, sample_name):
        # TODO This data can be preprocessed

        building_polygons = [[] for _ in range(5)]
        for anno in annotations_set:
            building_polygon_xy = np.array(anno['segmentation'][0], dtype=np.int32).reshape(-1, 2)
            building_polygons.append(building_polygon_xy)

        mask2 = np.zeros((1024, 1024), dtype=np.uint8)
        cv2.fillPoly(mask2, building_polygons, 1)
        mask = mask2.astype(np.float32)
        return mask