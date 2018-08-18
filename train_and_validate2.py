import sklearn
import math
import pandas as pd
from sklearn import linear_model,ensemble
import matplotlib.pyplot as plt
from matrix_plotter import MatrixPlotter
import pickle
import os
from numpy import int64,float32
import numpy as np
from shared import Interval
import logging

logging.basicConfig(level=logging.DEBUG)
logFunc = True

def train(model,inp_file):
    dtypes = {"chr":str,"contact_st":int64,"contact_en":int64,
            "window_start":int64,"window_end":int64,
            "contacts_relative_start":int64,"contacts_relative_end":int64,
            "contact_count":float32}
    header = open(inp_file,"r").readline().split("\t")

    for i in header:
        if i.startswith("CTCF") or i.startswith("E1"):
            dtypes[i] = float32

    logging.info("Reading data")
    input_data = pd.read_csv(inp_file,delimiter="\t",dtype=dtypes)
    #input_data["contact_count"] = pd.to_numeric(input_data["contact_count"])
    #input_data.dropna(inplace=True)

    if logFunc:
        results = input_data["contact_count"].apply(math.log)
    else:
        results = input_data["contact_count"]
    drop = ["chr","contact_count"]
    #drop += ["contact.st","contact.en",
    #                 "window_start","window_end","contact_relative_start",
    #                 "contact_relative_end"]
    input_data.drop(drop,axis = 1,inplace=True)

    logging.info("Fitting model")
    model.fit(input_data,results)
    return model

def validate(model,inp_file):
    input_data = pd.read_csv(inp_file,delimiter="\t")
    if logFunc:
        results = input_data["contact_count"].apply(math.log)
    else:
        results = input_data["contact_count"]
    drop = ["chr","contact_count"]
    #drop += ["contact.st","contact.en",
    #                 "window_start","window_end","contact_relative_start",
    #                 "contact_relative_end"]
    input_data.drop(drop,axis = 1,inplace=True)
    predicted = model.predict(input_data)
    r2 = sklearn.metrics.r2_score(predicted, results)

    plt.scatter(predicted,results,c=(input_data["contact_en"]-input_data["contact_st"]).values)
    plt.title("Test: Predicted vs real, r^2 score = "+str(r2)+"\nModel: "+str(model.__class__))
    plt.xlabel("Log(Predicted Contact)")
    plt.ylabel("Log(Real Contact)")
    plt.savefig(inp_file+".scatter"+str(logFunc)+".png",dpi=300)
    plt.show()
    plt.clf()

    mp = MatrixPlotter()
    input_data = pd.read_csv(inp_file,delimiter="\t") #read again to get chr and conacts count
    predicted_data = input_data.copy(deep=True)
    input_data["contact_count"] = results
    predicted_data["contact_count"] = predicted
    mp.set_data(input_data)
    mp.set_control(predicted_data)
    matrix = mp.getMatrix4plot(Interval("chr2",38000000,48000000))
    if not logFunc:
        matrix = np.log(matrix)
    plt.imshow(matrix,cmap="OrRd")
    plt.show()
    plt.savefig(inp_file+".matrix"+str(logFunc)+".png")





#lm = linear_model.LinearRegression()
#lm = linear_model.Lasso(alpha=0.2)
#lm = linear_model.SGDRegressor()
#lm = linear_model.TheilSenRegressor()
#lm = linear_model.HuberRegressor()
#lm = ensemble.AdaBoostRegressor()
#lm = ensemble.RandomForestRegressor()
#training_file = "training.RandOnChr11000000.50001.1000000.5000.100000.txt"
training_file = "training.RandOnChr13000000.50001.3000000.10000.500000.txt"
#validation_file = "validating.38Mb_58MbOnChr21000000.50001.1000000.5000.100000.txt"
validation_file = "validating.38Mb_58MbOnChr23000000.50001.3000000.10000.500000.txt"
model_file = training_file + ".model.log"+str(logFunc)+".dump"
model = ensemble.GradientBoostingRegressor()

if 0:
#if os.path.exists(model_file):
    model = pickle.load(open(model_file,"rb"))
else:
    model = train(model,training_file)
    pickle.dump(model,open(model_file,"wb"))

logging.info("Validating model")
validate(model,validation_file)