#import h5py
import numpy as np
import tensorflow as tf
from tensorflow.python.framework.ops import EagerTensor
from tensorflow.python.ops.resource_variable_ops import ResourceVariable


def model_wrapper(x_train, y_train, x_test, y_test, learning_rate = 0.0001,
          num_epochs = 1500, minibatch_size = 32, print_cost = True, start_epoch = 0, nn_weights = {}, hidden_units1=25, hidden_units2=20):

    if start_epoch == 0:
        # Initialize your parameters
        parameters = initialize_parameters(x_train.shape[1], y_train.shape[1], hidden_units1, hidden_units2)
    else:
        parameters = {}
        keys = nn_weights.keys()
        for key in keys:
            parameters[key] = tf.Variable(nn_weights[key])

    X_train = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(x_train, dtype=tf.float32))
    Y_train = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(y_train, dtype=tf.float32))
    X_test = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(x_test, dtype=tf.float32))
    Y_test = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(y_test, dtype=tf.float32))

    parameters, costs, train_acc, test_acc, epochs = model(X_train, Y_train, X_test, Y_test, parameters, learning_rate, num_epochs, minibatch_size, print_cost, start_epoch)

    numpy_parameters = {}
    keys = parameters.keys()
    for key in keys:
        numpy_parameters[key] = parameters[key].numpy()

    return numpy_parameters, np.squeeze(costs), np.squeeze(train_acc), np.squeeze(test_acc), epochs



# Taken from Coursera by deeplearning.AI Andrew Ng:
# https://www.coursera.org/specializations/deep-learning?skipBrowseRedirect=true
def model(X_train, Y_train, X_test, Y_test, parameters, learning_rate,
          num_epochs, minibatch_size, print_cost, start_epoch):
    """
    Implements a three-layer tensorflow neural network: LINEAR->RELU->LINEAR->RELU->LINEAR->SIGMOID.

    Arguments:
    X_train -- training set, of shape (input size, number of training examples)
    Y_train -- test set, of shape (output size = 12, number of training examples)
    X_test -- training set, of shape (input size, number of training examples)
    Y_test -- test set, of shape (output size = 12, number of test examples)
    learning_rate -- learning rate of the optimization
    num_epochs -- number of epochs of the optimization loop
    minibatch_size -- size of a minibatch
    print_cost -- True to print the cost every 10 epochs

    Returns:
    parameters -- parameters learnt by the model. They can then be used to predict.
    """

    optimizer = tf.keras.optimizers.Adam(learning_rate)

    # The CategoricalAccuracy will track the accuracy for this multiclass problem
    test_accuracy = tf.keras.metrics.MeanAbsoluteError()
    train_accuracy = tf.keras.metrics.MeanAbsoluteError()

    dataset = tf.data.Dataset.zip((X_train, Y_train))
    test_dataset = tf.data.Dataset.zip((X_test, Y_test))

    # We can get the number of elements of a dataset using the cardinality method
    m = dataset.cardinality().numpy()

    minibatches = dataset.batch(minibatch_size).prefetch(8)
    test_minibatches = test_dataset.batch(minibatch_size).prefetch(8)
    #X_train = X_train.batch(minibatch_size, drop_remainder=True).prefetch(8)# <<< extra step
    #Y_train = Y_train.batch(minibatch_size, drop_remainder=True).prefetch(8) # loads memory faster

    # To keep track of the cost
    costs = []
    train_acc = []
    test_acc = []

    W1 = parameters['W1']
    b1 = parameters['b1']
    W2 = parameters['W2']
    b2 = parameters['b2']
    W3 = parameters['W3']
    b3 = parameters['b3']

    # Save pre-training cost and accuracy
    for (minibatch_X, minibatch_Y) in test_minibatches:
        Z3 = forward_propagation(tf.transpose(minibatch_X), parameters)
        test_accuracy.update_state(minibatch_Y, tf.transpose(Z3))
    tf.print("Mean abs error for initialialized weights (test):", test_accuracy.result())
    test_acc = [test_accuracy.result()]
    test_accuracy.reset_states()

    epoch_cost = 0.0
    for (minibatch_X, minibatch_Y) in minibatches:
        Z3 = forward_propagation(tf.transpose(minibatch_X), parameters)
        train_accuracy.update_state(minibatch_Y, tf.transpose(Z3))
        minibatch_cost = calculate_cost(minibatch_Y, tf.transpose(Z3))
        epoch_cost += minibatch_cost
    epoch_cost /= m
    tf.print("Mean abs error for initialialized weights (train):", train_accuracy.result())
    costs = [epoch_cost]
    epochs = [start_epoch]
    train_acc = [train_accuracy.result()]
    train_accuracy.reset_states()

    # Do the training loop
    for epoch in range(start_epoch+1, num_epochs+1):

        epoch_cost = 0.0

        #We need to reset object to start measuring from 0 the accuracy each epoch
        train_accuracy.reset_states()

        for (minibatch_X, minibatch_Y) in minibatches:

            with tf.GradientTape() as tape:
                # 1. predict
                Z3 = forward_propagation(tf.transpose(minibatch_X), parameters)

                # 2. loss
                minibatch_cost = calculate_cost(minibatch_Y, tf.transpose(Z3))

            # We accumulate the accuracy of all the batches
            train_accuracy.update_state(minibatch_Y, tf.transpose(Z3))

            trainable_variables = [W1, b1, W2, b2, W3, b3]
            grads = tape.gradient(minibatch_cost, trainable_variables)
            optimizer.apply_gradients(zip(grads, trainable_variables))
            epoch_cost += minibatch_cost

        # We divide the epoch cost over the number of samples
        epoch_cost /= m

        # Print the cost every 10 epochs
        if print_cost == True and (epoch) % 10 == 0:
            print ("Cost after epoch %i: %f" % (epoch, epoch_cost))
            tf.print("Mean abs error on train:", train_accuracy.result())

            # We evaluate the test set every 10 epochs to avoid computational overhead
            for (minibatch_X, minibatch_Y) in test_minibatches:
                Z3 = forward_propagation(tf.transpose(minibatch_X), parameters)
                test_accuracy.update_state(minibatch_Y, tf.transpose(Z3))
            tf.print("Mean abs error on test:", test_accuracy.result())

            costs.append(epoch_cost)
            train_acc.append(train_accuracy.result())
            test_acc.append(test_accuracy.result())
            epochs.append(epoch)
            test_accuracy.reset_states()

    return parameters, costs, train_acc, test_acc, epochs



def calculate_cost(y_true, y_pred):
    """
    Calculate cost function
    """

    #cost = tf.reduce_mean(tf.keras.metrics.mean_squared_error(y_true, y_pred))
    cost = tf.reduce_mean(tf.keras.metrics.binary_crossentropy(y_true, y_pred))

    return cost



# Taken from Coursera by deeplearning.AI Andrew Ng:
# https://www.coursera.org/specializations/deep-learning?skipBrowseRedirect=true
# GRADED FUNCTION: forward_propagation
def forward_propagation(X, parameters):
    """
    Implements the forward propagation for the model: LINEAR -> RELU -> LINEAR -> RELU -> LINEAR

    Arguments:
    X -- input dataset placeholder, of shape (input size, number of examples)
    parameters -- python dictionary containing your parameters "W1", "b1", "W2", "b2", "W3", "b3"
                  the shapes are given in initialize_parameters

    Returns:
    Z3 -- the output of the last LINEAR unit
    """

    # Retrieve the parameters from the dictionary "parameters" 
    W1 = parameters['W1']
    b1 = parameters['b1']
    W2 = parameters['W2']
    b2 = parameters['b2']
    W3 = parameters['W3']
    b3 = parameters['b3']

    Z1 = tf.linalg.matmul(W1, X) + b1
    A1 = tf.keras.activations.relu(Z1)
    Z2 = tf.linalg.matmul(W2, A1) + b2
    A2 = tf.keras.activations.relu(Z2)
    Z3 = tf.linalg.matmul(W3, A2) + b3
    A3 = tf.keras.activations.sigmoid(Z3)

    return A3



# Taken from Coursera by deeplearning.AI Andrew Ng:
# https://www.coursera.org/specializations/deep-learning?skipBrowseRedirect=true
# GRADED FUNCTION: initialize_parameters
def initialize_parameters(input_size, output_size, hidden_units1, hidden_units2):
    """
    Initializes parameters to build a neural network with TensorFlow.
    Returns:
    parameters -- a dictionary of tensors containing W1, b1, W2, b2, W3, b3
    """
                         
    initializer = tf.keras.initializers.GlorotNormal(seed=1)

    W1 = tf.Variable(initializer(shape=([hidden_units1, input_size])))
    b1 = tf.Variable(initializer(shape=([hidden_units1, 1])))
    W2 = tf.Variable(initializer(shape=([hidden_units2, hidden_units1])))
    b2 = tf.Variable(initializer(shape=([hidden_units2, 1])))
    W3 = tf.Variable(initializer(shape=([output_size, hidden_units2])))
    b3 = tf.Variable(initializer(shape=([output_size, 1])))

    parameters = {"W1": W1,
                  "b1": b1,
                  "W2": W2,
                  "b2": b2,
                  "W3": W3,
                  "b3": b3}

    return parameters