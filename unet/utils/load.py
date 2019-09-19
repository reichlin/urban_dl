#
# load.py : utils on generators / lists of ids to transform from strings to
#           cropped images and masks

import os

import numpy as np
from PIL import Image
import torch
import h5py

from .utils import resize_and_crop, get_square, normalize, hwc_to_chw




class SloveniaDataset(torch.utils.data.Dataset):
    def __init__(self, file_path):
        super().__init__()
        self.dataset = h5py.File(file_path, 'r', libver='latest', swmr=True)
        self.dataset_indices = list(self.dataset.keys())
        self.episode = None

    def __getitem__(self, index):

        subset_name = self.dataset_indices[index]
        subset = self.dataset[subset_name]
        subset.refresh()

        obs = subset['data_bands']
        # move from (x, y, c) to (c, x, y) PyTorch style
        obs = np.moveaxis(obs, -1, 1)
        # TODO For now, only pick the first image of each pixel
        obs = obs[0,...]

        label = subset['mask_timeless']['lulc'].value
        label = np.moveaxis(label, -1, 0).astype(np.float32)
        label = np.argmax(label, axis=0)
        return obs, label

    def __len__(self):

        return len(list(self.dataset.keys()))


def get_ids(dir):
    """Returns a list of the ids in the directory"""
    return (f[:-4] for f in os.listdir(dir))


def split_ids(ids, n=2):
    """Split each id in n, creating n tuples (id, k) for each id"""
    return ((id, i)  for id in ids for i in range(n))


def to_cropped_imgs(ids, dir, suffix, scale):
    """From a list of tuples, returns the correct cropped img"""
    for id, pos in ids:
        im = resize_and_crop(Image.open(dir + id + suffix), scale=scale)
        yield get_square(im, pos)

def get_imgs_and_masks(ids, dir_img, dir_mask, scale):
    """Return all the couples (img, mask)"""

    imgs = to_cropped_imgs(ids, dir_img, '.jpg', scale)

    # need to transform from HWC to CHW
    imgs_switched = map(hwc_to_chw, imgs)
    imgs_normalized = map(normalize, imgs_switched)

    masks = to_cropped_imgs(ids, dir_mask, '_mask.gif', scale)

    return zip(imgs_normalized, masks)


def get_full_img_and_mask(id, dir_img, dir_mask):
    im = Image.open(dir_img + id + '.jpg')
    mask = Image.open(dir_mask + id + '_mask.gif')
    return np.array(im), np.array(mask)
