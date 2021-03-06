#!/usr/bin/env python

from __future__ import print_function

import argparse
import os.path as osp
import pprint

import chainer
import skimage.io
import yaml

import chainer_mask_rcnn as mrcnn


def main():
    default_img = 'https://c1.staticflickr.com/5/4171/33823288584_4c058a3e7b_c.jpg'  # NOQA
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('log_dir', help='log dir')
    parser.add_argument('--img', '-i', default=default_img,
                        help='img file or url')
    parser.add_argument('--gpu', '-g', type=int, default=0, help='gpu id')
    args = parser.parse_args()

    print('Using image file: {}'.format(args.img))

    # XXX: see also evaluate.py
    # -------------------------------------------------------------------------
    # param
    params = yaml.load(open(osp.join(args.log_dir, 'params.yaml')))
    print('Training config:')
    print('# ' + '-' * 77)
    pprint.pprint(params)
    print('# ' + '-' * 77)

    # dataset
    test_data = mrcnn.datasets.COCOInstanceSegmentationDataset('minival')
    fg_class_names = test_data.class_names[1:]

    # model
    chainer.global_config.train = False
    chainer.global_config.enable_backprop = False

    if params['pooling_func'] == 'align':
        pooling_func = mrcnn.functions.roi_align_2d
    elif params['pooling_func'] == 'pooling':
        pooling_func = chainer.functions.roi_pooling_2d
    elif params['pooling_func'] == 'resize':
        pooling_func = mrcnn.functions.crop_and_resize
    else:
        raise ValueError

    min_size = 800
    max_size = 1333
    anchor_scales = [2, 4, 8, 16, 32]
    proposal_creator_params = dict(
        n_train_pre_nms=12000,
        n_train_post_nms=2000,
        n_test_pre_nms=6000,
        n_test_post_nms=1000,
        min_size=0,
    )

    pretrained_model = osp.join(args.log_dir, 'snapshot_model.npz')
    print('Using pretrained_model: %s' % pretrained_model)

    model = params['model']
    n_fg_class = len(fg_class_names)
    mask_rcnn = mrcnn.models.MaskRCNNResNet(
        n_layers=int(model.lstrip('resnet')),
        n_fg_class=n_fg_class,
        pretrained_model=pretrained_model,
        pooling_func=pooling_func,
        anchor_scales=anchor_scales,
        proposal_creator_params=proposal_creator_params,
        min_size=min_size,
        max_size=max_size)
    if args.gpu >= 0:
        chainer.cuda.get_device_from_id(args.gpu).use()
        mask_rcnn.to_gpu()
    # -------------------------------------------------------------------------

    img = skimage.io.imread(args.img)
    img_chw = img.transpose(2, 0, 1)
    bboxes, masks, labels, scores = mask_rcnn.predict([img_chw])
    bboxes, masks, labels, scores = bboxes[0], masks[0], labels[0], scores[0]

    captions = ['{}: {:.1%}'.format(fg_class_names[l], s)
                for l, s in zip(labels, scores)]
    viz = mrcnn.utils.draw_instance_bboxes(
        img, bboxes, labels + 1, n_class=n_fg_class + 1,
        captions=captions, masks=masks)
    out_file = 'result.jpg'
    skimage.io.imsave(out_file, viz)
    print('Saved result: {}'.format(out_file))


if __name__ == '__main__':
    main()
