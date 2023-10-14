# Adapted from https://machinelearningmastery.com/building-a-multiclass-classification-model-in-pytorch/
import copy

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import tqdm
from sklearn.model_selection import train_test_split

from network.Network import Network
import network.SpectrumCompressor as SpectrumCompressor
import Configurator as cfg
#import SpectrumCompressor

DEVICE = "cuda"

INPUT_SIZE = 6222
OUTPUT_SIZE = 88


TRAIN_TEST_PERCENTAGE = 0.7



EPOCH_COUNT = 250
BATCH_SIZE = 5


def __accuracy(output, target) -> float:
    pred = (output > 0.5).float()

    maxScore = target.sum()
    score = maxScore

    mistakes = (pred != target).sum()


    return (score - mistakes)/maxScore
    

def __save_model(model,dataPath) -> None:
    if not cfg.CONFIG["DEBUG"]['save_model']:
        return

    netPath = dataPath.split(".")[0] + ".mdl"
    torch.save(model.state_dict(), netPath)

def __eval_debug_samples(model,spectra,notes):
    for i in range(20):
        out = model(spectra[i].to(DEVICE))
        for x in range(len(out)):
            if out[x] > 0.5:
                print(x)
        print("TARGET")

        for x in range(len(notes[i])):
            if notes[i][x] > 0.5:
                print(x)
        
        print(__accuracy(out,notes[i].to(DEVICE)))

def __generate_noise(batchSize):
    DEVIATION = 3.5
    return (torch.rand((batchSize,6222)) * (DEVIATION*2)) - DEVIATION







def train():
    dataPath = cfg.CONFIG["ARGS"]['training_data']

    notes,spectrum = SpectrumCompressor.decompress(dataPath)




    spectrum = torch.tensor(spectrum, dtype=torch.float32)
    notes = torch.tensor(notes, dtype=torch.float32)

    # split
    spectrumTrain, spectrumTest, notesTrain, notesTest = train_test_split(spectrum, notes, train_size=TRAIN_TEST_PERCENTAGE, shuffle=True)






    model = Network().to(DEVICE)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = optim.SGD(model.parameters(), lr=1e-3)



    # prepare model and training parameters

    batchesPerEpoch = len(spectrumTrain) // BATCH_SIZE

    best_acc = -np.inf   # init to negative infinity
    best_weights = None
    train_loss_hist = []
    train_acc_hist = []
    test_loss_hist = []
    test_acc_hist = []




    # training loop
    for epoch in range(EPOCH_COUNT):
        epoch_loss = []
        epoch_acc = []
        # set model in training mode and run through each batch
        model.train()
        with tqdm.trange(batchesPerEpoch, unit="batch", mininterval=0) as bar:
            bar.set_description(f"Epoch {epoch}")
            for i in bar:

                # Get batch                
                start = i * BATCH_SIZE
                spectrumBatch = spectrumTrain[start:start+BATCH_SIZE]
                noteBatch = notesTrain[start:start+BATCH_SIZE]


                # Add some noise to help prevent overfitting, and to hopefully give better results
                noise = __generate_noise(BATCH_SIZE)

                # Forward
                prediction = model((spectrumBatch + noise).to(DEVICE))

                # Derivatives
                loss = criterion(prediction.to(DEVICE), noteBatch.to(DEVICE))

                # Backward
                optimizer.zero_grad()
                loss.backward()

                optimizer.step()

                # compute and store metrics
                accuracy = __accuracy(prediction,noteBatch.to(DEVICE))


                epoch_loss.append(float(loss))
                epoch_acc.append(float(accuracy))
                bar.set_postfix(
                    loss=float(loss),
                    acc=float(accuracy)
                )

        # Set model in evaluation mode and run through the test set
        model.eval()
        prediction = model(spectrumTest.to(DEVICE))
        ce = criterion(prediction.to(DEVICE), notesTest.to(DEVICE))

        acc = __accuracy(prediction,notesTest.to(DEVICE))
        ce = float(ce)
        acc = float(acc)
        train_loss_hist.append(np.mean(epoch_loss))
        train_acc_hist.append(np.mean(epoch_acc))
        test_loss_hist.append(ce)
        test_acc_hist.append(acc)
        if acc > best_acc:
            best_acc = acc
            best_weights = copy.deepcopy(model.state_dict())
        print(f"Epoch {epoch} validation: Cross-entropy={ce:.2f}, Accuracy={acc*100:.1f}%")

    # Restore best model
    model.load_state_dict(best_weights)

    __save_model(model,dataPath)

    model.eval()


    __eval_debug_samples()


    # Plot the loss and accuracy
    plt.plot(train_loss_hist, label="train")
    plt.plot(test_loss_hist, label="test")
    plt.xlabel("epochs")
    plt.ylabel("cross entropy")
    plt.legend()
    plt.show()

    plt.plot(train_acc_hist, label="train")
    plt.plot(test_acc_hist, label="test")
    plt.xlabel("epochs")
    plt.ylabel("accuracy")
    plt.legend()
    plt.show()