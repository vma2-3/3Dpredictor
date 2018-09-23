# Written by Minja, 2018-09
# Class Predictor, to tain and validate models
# Baseic functionality:
# 1. Loading files with predictors
# 2. Drop different sets of predictors
# 3. Train and validate models
# 4. Perform estimation and visualization of results (TODO)

import logging,os,re,pickle,sklearn
import numpy as np
import pandas as pd
from numpy import int64,float32
from sklearn import ensemble
from shared import str2hash,Interval
import matplotlib.pyplot as plt
from matrix_plotter import MatrixPlotter




class Predictor(object):
    #TODO check that as soon as one changes predictors, self.trained_mode becomes None
    def __setattr__(self, key, value):
        if key == "predictors":
            self.trained_model = None
        self.__dict__[key] = value

    def __represent_validation__(self):
        try:
            self.validation_file
        except:
            raise Exception("Please read validation data firts")
        return str2hash(os.path.basename(self.validation_file)+".model_"+str(self))

    def __repr__(self): # Representation should reflect all paramteres
                        # so that 2 models having same repr are identical
        try:
            self.apply_log
        except:
            raise Exception("Please train model first")
        representation = ".".join([self.shortcut,
                                   os.path.basename(self.input_file),
                                   ".".join(self.predictors),
                                   str(self.apply_log),
                                   str(self.alg.__class__.__name__)
                                   ]
                                  )
        return str2hash(representation)

    def __init__(self):
        self.predictors = None
        self.contacts = None
        self.input_file = None
        self.apply_log = None
        self.shortcut = "model"
        self.alg = None
        self.trained_model = None
        self.trained_model = None
        self.constant_nonpredictors = ["chr", "contact_st", "contact_en", "contact_count"]

    # Train model
    # if dump = True, save it to file dump_file
    # returns class instance with trained_model object
    def train(self, alg = ensemble.GradientBoostingRegressor(), shortcut = "model", apply_log = True,
              dump = True, out_dir = "out/models/", *args, **kwargs):

        try:
            self.input_file
            self.predictors
        except:
            raise Exception("Please read the data and set predictors first")

        self.predictors = sorted(self.predictors)
        self.alg = alg
        self.shortcut = shortcut
        self.apply_log = apply_log

        try:
            del self.validation_file
            del self.validation_data
        except:
            pass

        # First try to load model dump
        self.representation = str(self)
        dump_path = os.path.join(out_dir,self.representation)
        if os.path.exists(dump_path):
            logging.info("Found dump for model" + dump_path)
            return pickle.load(open(dump_path,"rb"))
        else:
            # read data
            self.input_data = self.read_file(self.inp_file)
            self.contacts = np.array(self.input_data["contact_count"].values)

            #fit new model
            if apply_log:
                self.contacts = np.log(self.contacts)
            logging.getLogger(__name__).info("Fitting model")
            alg.fit(self.input_data[self.predictors],self.contacts)
            self.trained_model = alg
            if dump:
                logging.getLogger(__name__).info("Saving to file "+dump_path)
                #Remove large variables before dump
                del self.contacts
                del self.input_data
                pickle.dump(self,open(dump_path,"wb"))

        #Save feature importances
        try:
            plt.plot(range(len(self.trained_model.feature_importances_)), self.trained_model.feature_importances_, marker="o")
            plt.xticks(range(len(self.trained_model.feature_importances_)), self.predictors, rotation='vertical')
            plt.xlabel("Feature")
            plt.ylabel("Importance")
            plt.title("Features importance for model " + self.representation)
            plt.savefig(dump_path + ".FeatureImportance.png", dpi=300)
            plt.show()
            plt.clf()
        except:
            logging.getLogger(__name__).warning(
                "Features importance is not avaliable for the model " + str(model.__class__.__name__))

        logging.getLogger(__name__).info("Done")
        return self


    def r2score(self,validation_data,predicted,out_dir):

        real = validation_data["contact_count"].values
        r2 = sklearn.metrics.r2_score(predicted, real)

        # Plot r2
        subset = max(len(predicted) // 5000, 1)
        if "contact_dist" in validation_data.columns.get_values():
            plt.scatter(predicted[::subset], real[::subset],
                        c=validation_data["contact_dist"].values[::subset])
        else:
            plt.scatter(predicted[::subset], real[::subset])
        plt.title("Test: Predicted vs real, r^2 score = " + str(r2) + "\n" + self.__represent_validation__())
        plt.xlabel("Predicted Contact")
        plt.ylabel("Real Contact")
        print("Saving file " + os.path.join(out_dir,self.__represent_validation__()) + ".r2scatter.png")
        plt.savefig(os.path.join(out_dir,self.__represent_validation__()) + ".r2scatter.png", dpi=300)
        plt.show()
        plt.clf()

    def plot_matrix(self,validation_data,predicted,out_dir):
        predicted_data = validation_data.copy(deep=True)
        predicted_data["contact_count"] = predicted
        mp = MatrixPlotter()
        mp.set_data(validation_data)
        mp.set_control(predicted_data)
        matrix = mp.getMatrix4plot(Interval(validation_data["chr"].iloc[0],
                                            min(validation_data["contact_st"].values),
                                            max(validation_data["contact_en"].values)))
        if not self.apply_log:
            matrix = np.log(matrix)

        tick_pos, tick_labels = mp.get_bins_strart_labels(maxTicksNumber=15)
        plt.xticks(tick_pos, tick_labels, rotation=45)
        plt.imshow(matrix, cmap="OrRd")
        plt.title(self.__represent_validation__())
        plt.imsave(os.path.join(out_dir,self.__represent_validation__()) + ".matrix.png", matrix,
                    cmap="OrRd", dpi=600)
        plt.show()

    # Validate model
    def validate(self, validation_file, out_dir = "out/pics/"):
        self.validation_file = validation_file
        self.validation_data = self.read_file(validation_file)
        if self.apply_log:
            self.validation_data["contact_count"] = np.log(self.validation_data["contact_count"].values)
        self.predicted = self.trained_model.predict(self.validation_data[self.predictors])
        self.plot_matrix(self.validation_data,self.predicted,out_dir)
        self.r2score(self.validation_data,self.predicted,out_dir)


    # Read header of predictors file, get list of avaliable predictors
    # Returns list of predictors
    def get_avaliable_predictors(self,fname):
        predictors = open(fname).readline().strip().split("\t")  # read avaliable features
        return predictors

    # Filter list of available predictors according to the filter rule
    # Rule should be a valid re expression
    def filter_predictors(self,rule):
        try:
            self.predictors
        except:
            raise Exception("Please read data first")
        expression = re.compile(rule)
        self.predictors = [p for p in self.predictors if expression.search(p) != None]


    def read_file(self,inp_file):
        # Pandas reads file much faster if it knows datatypes
        # Actually, we know that all predictors are float except chr (str)
        # and contact start/end/dist, which is int
        dtypes = {"chr": str, "contact_st": int64, "contact_en": int64,
                  "contact_dist": int64, "contact_count": float32}
        header = open(inp_file, "r").readline().strip().split("\t")

        fixed_dtypes_count = len(dtypes.keys())
        for i in header[fixed_dtypes_count:]:
            dtypes[i] = float32

        logging.getLogger(__name__).info("Reading file "+inp_file)
        input_data = pd.read_csv(inp_file, delimiter="\t", dtype=dtypes,
                                 header=1, names=header)
        input_data.fillna(value=0, inplace=True) # Filling N/A values TODO check why N/A appear
        return input_data

    # Read available predictors, drop non-predictors
    # Fill self.predictors
    def read_data_predictors(self,inp_file):
        header = self.get_avaliable_predictors(inp_file)
        self.predictors = [h for h in header if not h in self.constant_nonpredictors]
        self.input_file = inp_file
