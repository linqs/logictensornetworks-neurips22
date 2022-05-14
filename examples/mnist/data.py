import tensorflow as tf
import numpy as np

def get_mnist_data_as_numpy():
    """Returns numpy arrays of images and labels"""
    mnist = tf.keras.datasets.mnist
    (img_train, label_train), (img_test, label_test) = mnist.load_data()
    img_train, img_test = img_train/255.0, img_test/255.0
    img_train = img_train[...,tf.newaxis]
    img_test = img_test[...,tf.newaxis]
    return img_train,label_train, img_test,label_test

def get_mnist_dataset(
        count_train,
        count_test,
        buffer_size,
        batch_size):
    """Returns tf.data.Dataset instance for the mnist datasets.
    Iterating over it, we get (image,label) batches.
    """
    if count_train > 60000:
        raise ValueError("The MNIST dataset comes with 60000 training examples. \
            Cannot fetch %i examples for training." %count_train)
    if count_test > 10000:
        raise ValueError("The MNIST dataset comes with 10000 test examples. \
            Cannot fetch %i examples for testing." %count_test)
    img_train,label_train,img_test,label_test = get_mnist_data_as_numpy()
    ds_train = tf.data.Dataset.from_tensor_slices((img_train, label_train))\
            .take(count_train).shuffle(buffer_size).batch(batch_size)
    ds_test = tf.data.Dataset.from_tensor_slices((img_test, label_test))\
            .take(count_test).shuffle(buffer_size).batch(batch_size)
    return ds_train, ds_test

def add_overlap(overlap_resample_proportion, img_per_operand, label_per_operand):
    # Flatten the lists.
    n_operands = len(img_per_operand)
    num_pairs = len(img_per_operand[0])

    images = np.concatenate(img_per_operand)
    labels = np.concatenate(label_per_operand)

    num_digits = len(images)
    indexes = list(range(num_digits))

    for _ in range(int(overlap_resample_proportion * num_digits)):
        indexes.append(np.random.randint(0, num_digits))
    np.random.shuffle(indexes)

    final_images = [[] for _ in range(n_operands)]
    final_labels = [[] for _ in range(n_operands)]

    for i in range(num_pairs):
        for j in range(n_operands):
            final_images[j].append(images[indexes[i * 2 + j]])
            final_labels[j].append(labels[indexes[i * 2 + j]])

    for j in range(n_operands):
        final_images[j] = np.stack(final_images[j])
        final_labels[j] = np.stack(final_labels[j])

    return final_images, final_labels


def get_mnist_op_dataset(
        count_train,
        count_test,
        buffer_size,
        batch_size,
        overlap_resample_proportion = 0,
        n_operands=2,
        op=lambda args: args[0]+args[1]):
    """Returns tf.data.Dataset instance for an operation with the numbers of the mnist dataset.
    Iterating over it, we get (image_x1,...,image_xn,label) batches
    such that op(image_x1,...,image_xn)= label.

    Args:
        n_operands: The number of sets of images to return, 
            that is the number of operands to the operation.
        op: Operation used to produce the label. 
            The lambda arguments must be a list from which we can index each operand. 
            Example: lambda args: args[0] + args[1]
    """
    if count_train*n_operands > 60000:
        raise ValueError("The MNIST dataset comes with 60000 training examples. \
            Cannot fetch %i examples for each %i operands for training." %(count_train,n_operands))
    if count_test*n_operands > 10000:
        raise ValueError("The MNIST dataset comes with 10000 test examples. \
            Cannot fetch %i examples for each %i operands for testing." %(count_test,n_operands))

    img_train,label_train,img_test,label_test = get_mnist_data_as_numpy()

    img_per_operand_train = [img_train[i*count_train:i*count_train+count_train] for i in range(n_operands)]
    label_per_operand_train = [label_train[i*count_train:i*count_train+count_train] for i in range(n_operands)]
    label_result_train = np.apply_along_axis(op,0,label_per_operand_train)

    img_per_operand_test = [img_test[i*count_test:i*count_test+count_test] for i in range(n_operands)]
    label_per_operand_test = [label_test[i*count_test:i*count_test+count_test] for i in range(n_operands)]
    label_result_test = np.apply_along_axis(op,0,label_per_operand_test)

    if (overlap_resample_proportion > 0):
        img_per_operand_train, label_per_operand_train = add_overlap(overlap_resample_proportion, img_per_operand_train, label_per_operand_train)
        label_result_train = np.apply_along_axis(op,0,label_per_operand_train)

        img_per_operand_test, label_per_operand_test = add_overlap(overlap_resample_proportion, img_per_operand_test, label_per_operand_test)
        label_result_test = np.apply_along_axis(op,0,label_per_operand_test)

    ds_train = tf.data.Dataset.from_tensor_slices(tuple(img_per_operand_train)+(label_result_train,))\
            .take(count_train).shuffle(buffer_size).batch(batch_size)
    ds_test = tf.data.Dataset.from_tensor_slices(tuple(img_per_operand_test)+(label_result_test,))\
            .take(count_test).shuffle(buffer_size).batch(batch_size)

    return ds_train, ds_test
