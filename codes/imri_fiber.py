from dipy.core.gradients import gradient_table
from dipy.data import get_fnames, default_sphere
from dipy.direction import peaks_from_model
from dipy.io.gradients import read_bvals_bvecs
from dipy.io.image import load_nifti, load_nifti_data
from dipy.io.stateful_tractogram import Space, StatefulTractogram
from dipy.io.streamline import save_trk, load_trk
from dipy.reconst.csdeconv import auto_response_ssst
from dipy.reconst.shm import CsaOdfModel
from dipy.tracking.stopping_criterion import ThresholdStoppingCriterion
from dipy.tracking import utils
from dipy.tracking.local_tracking import LocalTracking
from dipy.tracking.streamline import Streamlines
from dipy.tracking.streamlinespeed import length
from dipy.tracking.streamline import select_random_set_of_streamlines
from dipy.viz import colormap
from dipy.viz import window, actor, has_fury, colormap
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import matplotlib.pyplot as plt

import numpy as np
import nibabel as nib


def fiber_tracking():
    # Enables/disables interactive visualization
    fname = "./dMRI/dMRI_LPI.nii.gz"
    bval_fname = "./dMRI/dMRI.bval"
    bvec_fname = "./dMRI/dMRI.bvec"
    data, affine, img = load_nifti(fname, return_img=True)

    bvals, bvecs = read_bvals_bvecs(bval_fname, bvec_fname)
    gtab = gradient_table(bvals, bvecs)

    label_path = "./dMRI/c2dMRI.nii"
    label_obj = nib.load(label_path)
    labels = label_obj.get_fdata()

    # response, ratio = auto_response_ssst(gtab, data, roi_radii=10, fa_thr=0.7)
    csa_model = CsaOdfModel(gtab, sh_order_max=6)
    csa_peaks = peaks_from_model(csa_model, data, default_sphere, relative_peak_threshold=0.8, min_separation_angle=45)
    stopping_criterion = ThresholdStoppingCriterion(csa_peaks.gfa, 0.35)

    seed_mask = labels >= 0.96
    seeds = utils.seeds_from_mask(seed_mask, affine, density=[2, 2, 2])

    # Initialization of LocalTracking. The computation happens in the next step.
    streamlines_generator = LocalTracking(csa_peaks, stopping_criterion, seeds, affine=affine, step_size=0.5)
    # Generate streamlines object
    streamlines = Streamlines(streamlines_generator)

    # length filter
    lengths = length(streamlines)
    filter_relative_lengths = 0.15
    filter_lengths = filter_relative_lengths * (lengths.max() - lengths.min())

    lengths_index = np.squeeze(np.argwhere(lengths > filter_lengths))
    streamlines = streamlines[lengths_index]

    # random select
    streamlines = select_random_set_of_streamlines(streamlines, 10000)

    # colors = colormap.line_colors(streamlines)
    def remove_short_streamlines(streamlines, min_length):
        return Streamlines([sl for sl in streamlines if len(sl) >= min_length])

    # 设定最小长度阈值
    min_length_threshold = 25  # 设定为您认为合适的最小长度阈值

    # 删除太短的纤维束
    streamlines = remove_short_streamlines(streamlines, min_length_threshold)
    interactive = True
    sft = StatefulTractogram(streamlines, img, Space.RASMM)
    save_trk(sft, f"allBrainFiber.trk", streamlines)
    if has_fury:
        # Prepare the display objects.
        color = colormap.line_colors(streamlines)

        streamlines_actor = actor.line(streamlines, colormap.line_colors(streamlines))

        return streamlines_actor

        # # Create the 3D display.
        # scene = window.Scene()
        # scene.add(streamlines_actor)

        # # Save still images for this static example. Or for interactivity use
        # window.record(scene, out_path="tractogram_EuDX.png", size=(800, 800))
        # if interactive:
        #     window.show(scene)


def getFiberActor(trk_file_path):
    try:
        data = load_trk(trk_file_path, reference="same")
        streams = data.streamlines
        # 将streamlines转换为Streamlines对象
        streamlines2 = Streamlines(streams)
        colors = colormap.line_colors(streamlines2)
        render_fiber = actor.line(streamlines2, colors, opacity=1, linewidth=3, fake_tube=True)
        return render_fiber
    except Exception as e:
        print("An error occurred:", e)
