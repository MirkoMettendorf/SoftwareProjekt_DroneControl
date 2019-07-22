import preprocessing as pre

raw_training_data = ['moveDown.csv',
                     'moveDownRetraction.csv',
                     'moveUp.csv',
                     'moveUpRetraction.csv',
                     'pullBack.csv',
                     'pullBackRetraction.csv',
                     'rotateLeft.csv',
                     'rotateRight.csv',
                     'swingAndPointForward.csv',
                     'swingAndPointForwardRetraction.csv']

categories = ['land',
              'landR',
              'start',
              'startR',
              'wp_back',
              'wp_backR',
              'wp_del',
              'wp_set',
              'wp_next',
              'wp_nextR']

#raw_training_data = ['swingAndPointForward_normalized_1.csv',
#                     'pullUp_normalized_1.csv',
#                     'moveUp_normalized_1.csv',
#                     'moveDown_normalized_1.csv',
#                     'rotateLeft_normalized_1.csv',
#                     'rotateRight_normalized_1.csv',
#                     'stillgesture.csv']

#categories = ['swingAndPointForward',
#              'pullUp',
#              'moveUp',
#              'moveDown',
#              'rotateLeft',
#              'rotateRight',
#              'stillGesture']



#pre.preprocessing(raw_training_data, categories)

#pre.merge(raw_training_data, 'crazyFlyGestures.csv')

#pre.train_one_class_classifier_nn('linMoves.csv', categories, 40)

#pre.train_one_class_classifier_dct_evaluation('linMoves.csv', categories, 20)

#pre.train_one_class_classifier_dct_evaluation('linMoves.csv', categories, 20)

#pre.accuracy_over_epochs_nn('crazyFlyGestures.csv', categories, 20, test_data_size=0.8, training_epochs=200)

pre.train_one_class_classifier_nn_evaluation('crazyFlyGestures.csv', categories, 20, test_data_size=0.2)
pre.accuracy_over_epochs_nn('crazyFlyGestures.csv', categories, 20, test_data_size=0.8, training_epochs=200)

#pre.train_one_class_classifier_nn('crazyFlyGestures.csv', categories, 40)

