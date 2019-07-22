#Author: Alexander Schwarz
#Version 1.0

#################################################################################
# Data preprocessing
#
# Functions to prerocess raw data and train one class classifier neural networks
# and decision trees for gesture recognition.
#


#################################################################################
# needed imports
#

import pandas as pd
import numpy as np
import math
import itertools
from sklearn.tree import DecisionTreeClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.utils.multiclass import unique_labels
import matplotlib.pyplot as plt
from joblib import dump


#################################################################################
# preprocessing
#

def preprocessing(raw_training_data, categories, threshold = 0.5, dimension_3D = True):
    """
    Preprocess a list of .csv files

    Parameters
    ----------
    raw_training_data : list of str
        a list of .csv files
    categories : list of str
        a list of class names for the gestures
    threshold : float
        sets absolute acceleration and gyro values below threshold to zero.
        This helps the neural networks to achieve a higher accuracy
        in gesture recognition.
    
    Returns
    -------
    list of str
        The list of file names of the preprocessed data.

    Notes
    -----
    the class names of the categories list must be in the same order
    as the file names in the raw_training_data list
    """
    #read data from .csv file into dataFrame
    for file, cat in zip(raw_training_data, categories):
        raw_training_df = pd.read_csv('./data/raw/' + file)

        #remove leading whitespaces from column names
        raw_training_df.columns = raw_training_df.columns.str.replace(" ", "")

        #add 'run' column to dataFrame
        raw_training_df['run'] = 1

        change = False
        changePrev = False
        run = 0

        #divide data into runs, each run is a single gesture
        for i, row in raw_training_df.iterrows():
            if raw_training_df.at[i, 'button'] == 0:
                change = False
            else:
                change = True

            if change != changePrev and raw_training_df.at[i, 'button'] == 1:
                run += 1
            
            if raw_training_df.at[i, 'button'] == 1:
                raw_training_df.at[i, 'run'] = run
            else:
                raw_training_df.at[i, 'run'] = 0

            changePrev = change

        #remove rows that don't belong to gestures
        raw_training_df = raw_training_df[raw_training_df.run != 0]

        count = 0
        run = 1

        #normalize timestamp, each run starts at timestamp 1
        for i, row in raw_training_df.iterrows():
            if run != raw_training_df.at[i, 'run']:
                count = 0
            
            run = raw_training_df.at[i, 'run']

            count += 1
            raw_training_df.at[i, 'timestamp'] = count


        #fixed number of timestamps for each gesture
        #only the first 80 timestamps of each gesture are used
        raw_training_df = raw_training_df[raw_training_df.timestamp <= 80]


        #set values below threshold to zero
        if dimension_3D:
            for i, row in raw_training_df.iterrows():
                if abs(raw_training_df.at[i, 'accX']) <= threshold:
                    raw_training_df.at[i, 'accX'] = 0.0
                if abs(raw_training_df.at[i, 'accY']) <= threshold:
                    raw_training_df.at[i, 'accY'] = 0.0
                if abs(raw_training_df.at[i, 'accZ']) <= threshold:
                    raw_training_df.at[i, 'accZ'] = 0.0
                if abs(raw_training_df.at[i, 'gyroX']) <= threshold:
                    raw_training_df.at[i, 'gyroX'] = 0.0
                if abs(raw_training_df.at[i, 'gyroY']) <= threshold:
                    raw_training_df.at[i, 'gyroY'] = 0.0
                if abs(raw_training_df.at[i, 'gyroZ']) <= threshold:
                    raw_training_df.at[i, 'gyroZ'] = 0.0

        if not dimension_3D:
            for i, row in raw_training_df.iterrows():
                if abs(raw_training_df.at[i, 'accX']) <= threshold:
                    raw_training_df.at[i, 'accX'] = 0.0
                if abs(raw_training_df.at[i, 'accY']) <= threshold:
                    raw_training_df.at[i, 'accY'] = 0.0
                if abs(raw_training_df.at[i, 'gyroZ']) <= threshold:
                    raw_training_df.at[i, 'gyroZ'] = 0.0


        #create dataFrame for processed data
        processed_df = pd.DataFrame()

        #transpose raw data into one row for each gesture
        run = 1
        runs = raw_training_df['run'].max()

        while run <= runs:
            trans_df = pd.DataFrame()
            run_group_df = pd.DataFrame()

            #take only the data of one run (gesture)
            for i, row in raw_training_df.iterrows():
                if raw_training_df.at[i, 'run'] == run:
                    run_group_df = run_group_df.append(row)


            #remove colums 'button', 'run' and 'timestamp'
            run_group_df = run_group_df.drop(columns=['button', 'run', 'timestamp'])

            #transpose each column of a single run and rename the new comlumns
            for j, column in run_group_df.iteritems():
                transposed_df = pd.DataFrame()
                transposed_df[column.name] = column
                transposed_df = transposed_df.transpose()
                transposed_df.columns = np.arange(transposed_df.shape[1])
                transposed_df = transposed_df.rename(columns=lambda x: '0' + str(x) if x < 10 else x)
                transposed_df = transposed_df.add_suffix('_' + column.name)
                trans_df = pd.concat([trans_df, transposed_df], axis=0, sort=True)
            
            trans_df = trans_df.fillna(method = 'bfill')
            trans_df = trans_df.dropna()

            processed_df = processed_df.append(trans_df)
            run += 1


        #add class column 'category' to data
        processed_df = processed_df.assign(category=cat)


        #write processed dataFrame to .csv file
        processed_df.to_csv('./data/preprocessed/' + file)

    return raw_training_data



#################################################################################
# merge preprocessed data
#

def merge(preprocessed_training_data, output_file):
    """
    Merge multiple files with gestures into one file.

    Parameters
    ----------
    preprocessed_training_data : list of str
        A list of file names.
    output_file : str
        File name to save the merged input data.

    Returns
    -------
    Dataframe
        Returns a Dataframe with the merged input data.

    Notes
    -----
    The merged data will be saved in folder ./data/merged/output_file
    """

    dataframes = []
    all_data_df = pd.DataFrame(index=[], columns=[])

    for file in preprocessed_training_data:
        dataframes.append(pd.read_csv('./data/preprocessed/' + file))

    for df in dataframes:
        all_data_df = all_data_df.append(df)

    #remove unnamed column
    all_data_df = all_data_df.drop(all_data_df.columns[all_data_df.columns.str.contains('unnamed',case = False)],axis = 1)

    #fill missing values with zero
    all_data_df = all_data_df.fillna(value=0)

    #write merged data to .csv file
    all_data_df.to_csv('./data/merged/' + output_file)

    return all_data_df



#################################################################################
# train one class classifier neural networks
#

def train_one_class_classifier_nn(merged_training_data, categories, timeframe):
    """
    Train one class classifier neural networks for each category.

    Parameters
    ----------
    merged_training_data : DataFrame or str
        A DataFrame with samples of at least on gesture or
        a str with a file name '.csv'.
    categories : list of str
        A list with the categories of the gestures in the
        DataFrame or file.
    timeframe : int
        A timeframe for which the classifier should be trained.
        (20ms * timeframe=20) = 0.4s 
        
    Notes
    -----
    This uses the complete data to train the models. No split
    into training and twst data is done.
    Each trained model will be named after it's corresponding
    gesture concatenated with the timeframe. The trained models
    will be saved in a folder named models.
    """

    if isinstance(merged_training_data, str):
        #load data into dataFrame
        all_data_df = pd.read_csv('./data/merged/' + merged_training_data)
    else:
        all_data_df = merged_training_data
    
    
    #remove unnamed column
    all_data_df = all_data_df.drop(all_data_df.columns[all_data_df.columns.str.contains('unnamed',case = False)],axis = 1)


    #filter data to use only a fixed timeframe
    #for 0.4s from timestamp 0 to 19 (20 values * 20ms = 0.4s)
    last_timestamp = timeframe
    list_columns = []
    for i, column in all_data_df.iteritems():
        if column.name != "category":
            a = int(column.name[:2])
        
            if a >= last_timestamp:
                list_columns.append(column.name)

    all_data_df = all_data_df.drop(list_columns, axis=1)

    dataframes = []

    for cat in categories:
        df = all_data_df.copy()
        df.loc[df['category'] != cat, 'category'] = 'unknown'
        dataframes.append(df)
    
    classifiers = []

    for df in dataframes:
        X = df.iloc[:, all_data_df.columns != 'category']
        Y = df.iloc[:, all_data_df.columns == 'category']

        clf = MLPClassifier(solver='adam', alpha=1e-3, hidden_layer_sizes=(20, 20, 20), random_state=1, max_iter=200)
        clf.fit(X, np.ravel(Y))

        classifiers.append(clf)


    for clf, cat in zip(classifiers, categories):
        dump(clf, './models/' + cat + '_nn_' + str(timeframe) + '.joblib')



#################################################################################
# train one class calssifier decision trees
#

def train_one_class_classifier_dct(merged_training_data, categories, timeframe):
    """
    Train one class classifier decision trees for each category.

    Parameters
    ----------
    merged_training_data : DataFrame or str
        A DataFrame with samples of at least on gesture or
        a str with a file name '.csv'.
    categories : list of str
        A list with the categories of the gestures in the
        DataFrame or file.
    timeframe : int
        A timeframe for which the classifier should be trained.
        (20ms * timeframe=20) = 0.4s 
        
    Notes
    -----
    This uses the complete data to train the models. No split
    into training and twst data is done.
    Each trained model will be named after it's corresponding
    gesture concatenated with the timeframe. The trained models
    will be saved in a folder named models.
    """

    if isinstance(merged_training_data, str):
        #load data into dataFrame
        all_data_df = pd.read_csv('./data/merged/' + merged_training_data)
    else:
        all_data_df = merged_training_data
    
    
    #remove unnamed column
    all_data_df = all_data_df.drop(all_data_df.columns[all_data_df.columns.str.contains('unnamed',case = False)],axis = 1)


    #filter data to use only a fixed timeframe
    #for 0.4s from timestamp 0 to 19 (20 values * 20ms = 0.4s)
    last_timestamp = timeframe
    list_columns = []
    for i, column in all_data_df.iteritems():
        if column.name != "category":
            a = int(column.name[:2])
        
            if a >= last_timestamp:
                list_columns.append(column.name)

    all_data_df = all_data_df.drop(list_columns, axis=1)

    dataframes = []

    for cat in categories:
        df = all_data_df.copy()
        df.loc[df['category'] != cat, 'category'] = 'unknown'
        dataframes.append(df)
    
    classifiers = []

    for df in dataframes:
        X = df.iloc[:, all_data_df.columns != 'category']
        Y = df.iloc[:, all_data_df.columns == 'category']

        clf = DecisionTreeClassifier(min_samples_split=20, random_state=99)
        clf.fit(X, np.ravel(Y))

        classifiers.append(clf)


    for clf, cat in zip(classifiers, categories):
        dump(clf, './models/' + cat + '_dct_' + str(timeframe) + '.joblib')



#################################################################################
# evaluate one class classifier neural networks
#

def train_one_class_classifier_nn_evaluation(merged_training_data, categories, timeframe, test_data_size = 0.2):
    """
    Train one class classifier neural networks for each category and
    print the confusion matrix of each trained model.

    Parameters
    ----------
    merged_training_data : DataFrame or str
        A DataFrame with samples of at least on gesture or
        a str with a file name '.csv'.
    categories : list of str
        A list with the categories of the gestures in the
        DataFrame or file.
    timeframe : int
        A timeframe for which the classifier should be trained.
        (20ms * timeframe=20) = 0.4s
    test_data_size : float
        the percentage size of the test data after the split
        into training and test data. default = 0.2
        
    Notes
    -----
    This splits the training data into training and test data.
    The models will not be saved. This function is only for
    evaluation purposes.
    """
    if isinstance(merged_training_data, str):
        #load data into dataFrame
        all_data_df = pd.read_csv('./data/merged/' + merged_training_data)
    else:
        all_data_df = merged_training_data
    
    
    #remove unnamed column
    all_data_df = all_data_df.drop(all_data_df.columns[all_data_df.columns.str.contains('unnamed',case = False)],axis = 1)


    #filter data to use only a fixed timeframe
    #for 0.4s from timestamp 0 to 19 (20 values * 20ms = 0.4s)
    last_timestamp = timeframe
    list_columns = []
    for i, column in all_data_df.iteritems():
        if column.name != "category":
            a = int(column.name[:2])
        
            if a >= last_timestamp:
                list_columns.append(column.name)

    all_data_df = all_data_df.drop(list_columns, axis=1)

    dataframes = []

    for cat in categories:
        df = all_data_df.copy()
        df.loc[df['category'] != cat, 'category'] = 'unknown'
        dataframes.append(df)
    
    classifiers = []

    for df in dataframes:
        X = df.iloc[:, all_data_df.columns != 'category']
        Y = df.iloc[:, all_data_df.columns == 'category']

        X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=test_data_size, stratify=all_data_df['category'])

        clf = MLPClassifier(solver='adam', alpha=1e-3, hidden_layer_sizes=(20, 20, 20), random_state=1, max_iter=200)
        clf.fit(X_train, np.ravel(Y_train))

        y_pred = clf.predict(X_test)

        cats = [df['category'].unique()[np.where(df['category'].unique() != 'unknown')[0]][0], 'unknown']
        print_confusion_matrix(Y_test, y_pred, cats)
        classifiers.append(clf)


#################################################################################
# evaluate one class classifier decision trees
#

def train_one_class_classifier_dct_evaluation(merged_training_data, categories, timeframe, test_data_size = 0.2):
    """
    Train one class classifier decision trees for each category and
    print the confusion matrix of each trained model.

    Parameters
    ----------
    merged_training_data : DataFrame or str
        A DataFrame with samples of at least on gesture or
        a str with a file name '.csv'.
    categories : list of str
        A list with the categories of the gestures in the
        DataFrame or file.
    timeframe : int
        A timeframe for which the classifier should be trained.
        (20ms * timeframe=20) = 0.4s
    test_data_size : float
        the percentage size of the test data after the split
        into training and test data. default = 0.2
        
    Notes
    -----
    This splits the training data into training and test data.
    The models will not be saved. This function is only for
    evaluation purposes.
    """
    if isinstance(merged_training_data, str):
        #load data into dataFrame
        all_data_df = pd.read_csv('./data/merged/' + merged_training_data)
    else:
        all_data_df = merged_training_data
    
    
    #remove unnamed column
    all_data_df = all_data_df.drop(all_data_df.columns[all_data_df.columns.str.contains('unnamed',case = False)],axis = 1)


    #filter data to use only a fixed timeframe
    #for 0.4s from timestamp 0 to 19 (20 values * 20ms = 0.4s)
    last_timestamp = timeframe
    list_columns = []
    for i, column in all_data_df.iteritems():
        if column.name != "category":
            a = int(column.name[:2])
        
            if a >= last_timestamp:
                list_columns.append(column.name)

    all_data_df = all_data_df.drop(list_columns, axis=1)

    dataframes = []

    for cat in categories:
        df = all_data_df.copy()
        df.loc[df['category'] != cat, 'category'] = 'unknown'
        dataframes.append(df)
    
    classifiers = []

    for df in dataframes:
        X = df.iloc[:, all_data_df.columns != 'category']
        Y = df.iloc[:, all_data_df.columns == 'category']

        X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=test_data_size, stratify=all_data_df['category'])

        clf = DecisionTreeClassifier(min_samples_split=20, random_state=99)
        clf.fit(X_train, np.ravel(Y_train))

        y_pred = clf.predict(X_test)

        cats = [df['category'].unique()[np.where(df['category'].unique() != 'unknown')[0]][0], 'unknown']
        print_confusion_matrix(Y_test, y_pred, cats)
        classifiers.append(clf)


#################################################################################
# Helper function to print confusion matrix
#

def print_confusion_matrix(true_categories, predicted_categories, categories):
    """
    Helper function to print a confusion matrix
        
    Notes
    -----
    This funtion is used inside the decision tree and neural network
    evaluation functions.
    """
    cnf_matrix = confusion_matrix(true_categories, predicted_categories)
    np.set_printoptions(precision=2)

    classes = categories
    plt.figure()
    plt.imshow(cnf_matrix, interpolation='nearest', cmap=plt.cm.Blues)
    plt.title('Confusion matrix')
    plt.colorbar()
    tick_marks = np.arange(len(classes))
    plt.xticks(tick_marks, classes, rotation=45)
    plt.yticks(tick_marks, classes)

    print(cnf_matrix)

    thresh = cnf_matrix.max() / 2.
    for i, j in itertools.product(range(cnf_matrix.shape[0]), range(cnf_matrix.shape[1])):
        plt.text(j, i, cnf_matrix[i, j], horizontalalignment='center', color='white' if cnf_matrix[i, j] > thresh else 'black')

    accuracy = accuracy_score(true_categories, predicted_categories)
    plt.tight_layout()
    plt.ylabel('True label')
    plt.xlabel('Predicted label')
    plt.annotate('accuracy ' + str(accuracy), xy=(0.5, 0), xytext=(0, 10), xycoords=('axes fraction', 'figure fraction'), textcoords='offset points', size=14, ha='center', va='bottom')
    plt.show()


#################################################################################
# Test neural networks for overfitting
#

def accuracy_over_epochs_nn(merged_training_data, categories, timeframe, test_data_size = 0.2, training_epochs = 200):
    """
    Train one class classifier neural networks for each category and
    print the accuracy of training and test data and the loss over
    each epoch. For each one class classifier a seperate plot is shown.

    Parameters
    ----------
    merged_training_data : DataFrame or str
        A DataFrame with samples of at least on gesture or
        a str with a file name '.csv'.
    categories : list of str
        A list with the categories of the gestures in the
        DataFrame or file.
    timeframe : int
        A timeframe for which the classifier should be trained.
        (20ms * timeframe=20) = 0.4s
    test_data_size : float
        the percentage size of the test data after the split
        into training and test data. default = 0.2
    training_epochs : int
        max number of training epochs for the neural network
    Notes
    -----
    This splits the training data into training and test data.
    The models will not be saved. This function is only for
    evaluation purposes.
    """
    if isinstance(merged_training_data, str):
        #load data into dataFrame
        all_data_df = pd.read_csv('./data/merged/' + merged_training_data)
    else:
        all_data_df = merged_training_data
    
    
    #remove unnamed column
    all_data_df = all_data_df.drop(all_data_df.columns[all_data_df.columns.str.contains('unnamed',case = False)],axis = 1)


    #filter data to use only a fixed timeframe
    #for 0.4s from timestamp 0 to 19 (20 values * 20ms = 0.4s)
    last_timestamp = timeframe
    list_columns = []
    for i, column in all_data_df.iteritems():
        if column.name != "category":
            a = int(column.name[:2])
        
            if a >= last_timestamp:
                list_columns.append(column.name)

    all_data_df = all_data_df.drop(list_columns, axis=1)

    dataframes = []

    for cat in categories:
        df = all_data_df.copy()
        df.loc[df['category'] != cat, 'category'] = 'unknown'
        dataframes.append(df)
    
    classifiers = []

    for df in dataframes:
        X = df.iloc[:, all_data_df.columns != 'category']
        Y = df.iloc[:, all_data_df.columns == 'category']

        X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=test_data_size, stratify=all_data_df['category'])

        clf = MLPClassifier(solver='adam', alpha=1e-3, hidden_layer_sizes=(20, 20, 20), random_state=1, max_iter=200)

        scores_train = []
        scores_test = []

        epoch = 0
        classes = unique_labels(Y_train)
        
        while epoch < training_epochs:
            clf.partial_fit(X_train, np.ravel(Y_train), classes=classes)

            scores_train.append(clf.score(X_train, Y_train))
            scores_test.append(clf.score(X_test, Y_test))

            epoch += 1
        
        plt.plot(scores_train, color='green', alpha=0.8, label='train')
        plt.plot(scores_test, color='magenta', alpha=0.8, label='test')
        plt.plot(clf.loss_curve_, color='blue', alpha=0.8, label='loss')
        plt.title(classes [0] + ' Accuracy over epochs', fontsize=14)
        plt.xlabel('epochs')
        plt.legend(loc='center right')
        plt.show()

        classifiers.append(clf)
