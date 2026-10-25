"""Run the bundled SynthSeg with TensorFlow 2.16+ (Slicer's own Python).

SynthSeg was written for Keras 2 and imports `keras` directly. From TensorFlow 2.16 on, `keras` is Keras 3,
so this launcher maps the name `keras` (and the submodules SynthSeg uses) to `tf_keras`, the Keras 2 package,
before running SynthSeg_predict.py. The SynthSeg code itself is not changed.

Usage: PythonSlicer run_synthseg_tfkeras.py <path to SynthSeg_predict.py> [SynthSeg arguments...]

Verified (SynthSeg 2.0 + parcellation, one T1): TF 2.21 / tf-keras 2.21 / numpy 2.4.6 / Python 3.12 against
TF 2.4.1 / numpy 1.23.5 / Python 3.8 gave 100.0000% voxel agreement and at most 0.007% regional volume difference.
"""
import os
import runpy
import sys

os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")  # make tf.keras resolve to tf_keras as well

import tf_keras  # noqa: E402

sys.modules["keras"] = tf_keras
for _sub in ("layers", "models", "backend", "optimizers", "callbacks", "losses",
             "initializers", "regularizers", "activations", "utils"):
    if hasattr(tf_keras, _sub):
        sys.modules["keras." + _sub] = getattr(tf_keras, _sub)

if len(sys.argv) < 2:
    sys.exit("usage: run_synthseg_tfkeras.py <SynthSeg_predict.py> [arguments]")

_script = os.path.abspath(sys.argv[1])
sys.argv = [_script] + sys.argv[2:]  # SynthSeg finds its own folder from argv[0]
runpy.run_path(_script, run_name="__main__")
