import os
import sys
import vae
import plot
import numpy as np
import tensorflow as tf
from utils import get_mnist
from tensorflow.examples.tutorials.mnist import input_data

FEATURES = 4  # Number of scalar input features.
IMG_DIM = 28  # size of one side of the image. Total image variables = IMG_DIM * IMG_DIM

X_LENGTH = FEATURES + IMG_DIM ** 2

ARCHITECTURE = [X_LENGTH,   # total input layer dimension
                500, 500,   # intermediate encoding layer size - eg: 2 layers of 500 neurons
                2,          # latent space dims
                FEATURES]   # length of function features.

HYPERPARAMS = {
    "batch_size": 128,
    "learning_rate": 5E-4,
    "dropout": 0.9,
    "lambda_l2_reg": 1E-5,
    "nonlinearity": tf.nn.elu,
    "squashing": tf.nn.sigmoid
}

MAX_ITER = 1000
MAX_EPOCHS = np.inf

# LOG_DIR = "./log"
# METAGRAPH_DIR = "./out"
# PLOTS_DIR = "./png"
METAGRAPH_DIR = r"C:\Users\pw49398\School\CS229\vae-tf-master\vae-tf-master\out"
LOG_DIR = r"C:\Users\pw49398\School\CS229\vae-tf-master\vae-tf-master\log"
PLOTS_DIR = r"C:\Users\pw49398\School\CS229\vae-tf-master\vae-tf-master\png"

class DataSet(object):
    def __init__(self, img_data, nfeatures):
        self.img_data = img_data
        self.nfeatures = nfeatures
        self.epochs_completed = 0
        self.img_length = IMG_DIM**2
        self.images = None
        self.labels = None
        self._gen_images()

    def next_batch(self, batch_size):
        x, y = self.img_data.next_batch(batch_size)
        for _ in range(self.nfeatures):
            y_noise = np.add(np.random.rand(len(y)), y)
            x = np.concatenate((x, y_noise.reshape(len(y), 1)), axis=1)
        return x, y

    def _gen_images(self):
        x = self.img_data._images
        y = self.img_data._labels
        for _ in range(self.nfeatures):
            y_noise = np.add(np.random.rand(len(y)), y)
            x = np.concatenate((x, y_noise.reshape(len(y), 1)), axis=1)
        self.images = x
        self.labels = y


class InputData(object):
    """Object which combines image variables with functional features."""
    def __init__(self, nfeatures):
        self.nfeatures = nfeatures
        self.mnist = input_data.read_data_sets("./mnist_data")
        self.train = DataSet(self.mnist.train, nfeatures)
        self.test = DataSet(self.mnist.test, nfeatures)
        self.validation = DataSet(self.mnist.validation, nfeatures)


def all_plots(model, mnist):
    if model.architecture[-1] == 2:  # only works for 2-D latent
        print("Plotting in latent space...")
        plot_all_in_latent(model, mnist)

        print("Exploring latent...")
        plot.exploreLatent(model, nx=20, ny=20, range_=(-4, 4), outdir=PLOTS_DIR)
        for n in (24, 30, 60, 100):
            plot.exploreLatent(model, nx=n, ny=n, ppf=True, outdir=PLOTS_DIR,
                               name="explore_ppf{}".format(n))

    print("Interpolating...")
    interpolate_digits(model, mnist)

    print("Plotting end-to-end reconstructions...")
    plot_all_end_to_end(model, mnist)

    print("Morphing...")
    morph_numbers(model, mnist, ns=[9, 8, 7, 6, 5, 4, 3, 2, 1, 0])

    print("Plotting 10 MNIST digits...")
    for i in range(10):
        plot.justMNIST(get_mnist(i, mnist), name=str(i), outdir=PLOTS_DIR)


def plot_all_in_latent(model, mnist):
    names = ("train", "validation", "test")
    datasets = (mnist.train, mnist.validation, mnist.test)
    for name, dataset in zip(names, datasets):
        plot.plotInLatent(model, dataset.images, dataset.labels, name=name,
                          outdir=PLOTS_DIR)


def interpolate_digits(model, mnist):
    imgs, labels = mnist.train.next_batch(100)
    idxs = np.random.randint(0, imgs.shape[0] - 1, 2)
    mus, _ = model.encode(np.vstack(imgs[i] for i in idxs))
    plot.interpolate(model, *mus, name="interpolate_{}->{}".format(
        *(labels[i] for i in idxs)), outdir=PLOTS_DIR)


def plot_all_end_to_end(model, mnist):
    names = ("train", "validation", "test")
    datasets = (mnist.train, mnist.validation, mnist.test)
    for name, dataset in zip(names, datasets):
        x, _ = dataset.next_batch(10)
        x_reconstructed = model.vae(x)
        plot.plotSubset(model, x, x_reconstructed, n=10, name=name,
                        outdir=PLOTS_DIR)


def morph_numbers(model, mnist, ns=None, n_per_morph=10):
    if not ns:
        import random
        ns = random.sample(range(10), 10)  # non-in-place shuffle

    xs = np.squeeze([get_mnist(n, mnist) for n in ns])
    mus, _ = model.encode(xs)
    plot.morph(model, mus, n_per_morph=n_per_morph, outdir=PLOTS_DIR,
               name="morph_{}".format("".join(str(n) for n in ns)))


def main(to_reload=None):
    # mnist in a .Dataset object format
    # mnist = load_mnist()
    data = InputData(FEATURES)

    if to_reload:  # restore
        v = vae.VAE(ARCHITECTURE, HYPERPARAMS, meta_graph=to_reload)
        print("Loaded!")

    else:  # train
        v = vae.VAE(ARCHITECTURE, HYPERPARAMS, log_dir=LOG_DIR)
        v.train(data, max_iter=MAX_ITER, max_epochs=MAX_EPOCHS, cross_validate=False,
                verbose=True, save=True, outdir=METAGRAPH_DIR, plots_outdir=PLOTS_DIR,
                plot_latent_over_time=False)
        print("Trained!")

    all_plots(v, data)


if __name__ == "__main__":
    tf.reset_default_graph()

    for DIR in (LOG_DIR, METAGRAPH_DIR, PLOTS_DIR):
        try:
            os.mkdir(DIR)
        except(FileExistsError):
            pass

    try:
        to_reload = sys.argv[1]
        main(to_reload=to_reload)
    except(IndexError):
        main()
