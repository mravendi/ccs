#%% classify positive nodes and negative nodes
import numpy as np
import cv2
import time
import os
import matplotlib.pylab as plt
#from skimage import measure
import models
import utils
#from keras import backend as K
from keras.utils import np_utils
#from sklearn.model_selection import train_test_split
#from sklearn.model_selection import KFold
import h5py
from glob import glob
#from image import ImageDataGenerator
from keras.preprocessing.image import ImageDataGenerator
from keras.utils import np_utils
#from sklearn.model_selection import train_test_split
import datetime
import pandas as pd
#from sklearn.cross_validation import StratifiedKFold
from sklearn.model_selection import StratifiedKFold
#from sklearn.model_selection import KFold
#%%
# settings

# path to data
path2root='/media/mra/win71/data/misc/kaggle/intel/data/'
path2trainhdf5='/media/mra/win71/data/misc/kaggle/intel/data/train.hdf5'
#path2testhdf5='/media/mra/win71/data/misc/kaggle/intel/data/test.hdf5'
path2testhdf5='/media/mra/win71/data/misc/kaggle/intel/data/test_stg2.hdf5'

#%%

# pre-processed data dimesnsion
z,h,w=3,256,256


# batch size
batch_size=32

# number of classes
num_classes=3

# seed point
seed = 4243
seed = np.random.randint(seed)

# histogram equlization
hist_eq=False

# pre train
pre_train=False

#%%

# random data generator
datagen = ImageDataGenerator(featurewise_center=False,
        samplewise_center=False,
        #rescale=1/255.,
        featurewise_std_normalization=False,
        samplewise_std_normalization=False,
        zca_whitening=False,
        rotation_range=45,
        width_shift_range=0.1,
        height_shift_range=0.1,
        shear_range=0.0,
        zoom_range=0.05,
        channel_shift_range=0.0,
        fill_mode='constant',
        cval=0.0,
        horizontal_flip=True,
        vertical_flip=True,
        dim_ordering='th') 


# load train data
def load_data(ids,data_type='train'):
    X=[]
    y=[]
    
    if data_type=='train':
        ff=h5py.File(path2trainhdf5,'r')
        #print len(ff_test.keys())
    else:
        ff=h5py.File(path2testhdf5,'r')        
    
    ids_out=[]
    for k,id1 in enumerate(ids):
        print k,id1
        try:
            X0=ff[id1]['X'].value
            #plt.subplot(1,2,1)
            #plt.imshow(X0[:,:,0],cmap='gray')
            H,W,_=X0.shape
            # cropping ratio            
            alfah,alfaw=0.0,0.0                
            # roi coordinates
            h1,h2=int(alfah*H),int(H-alfah*H)
            w1,w2=int(alfaw*W),int(W-alfaw*W)
            # crop ROI
            X0=X0[h1:h2,w1:w2]
            #plt.subplot(1,2,2)
            #plt.imshow(X0[:,:,0],cmap='gray')
            #print X0.shape
            X0 = cv2.resize(X0, (w, h), interpolation=cv2.INTER_CUBIC)
            #print X0.shape
            if data_type=='train':
                y0=ff[id1]['y'].value
            else:
                y0=0
            X.append(X0)
            y.append(y0)
            ids_out.append(id1)
        except:
            print 'skip this!'
    ff.close()    
    X=np.stack(X) 
    X=np.transpose(X,(0,3,1,2))
    y=np.hstack(y)
    
    # convert labels to numbers
    try:    
        y[y=='Type_1']=0
        y[y=='Type_2']=1
        y[y=='Type_3']=2
    except:
        print 'skip this step!'
    y=y.astype('int')
    
    return X,y,ids_out

def preprocess_input(x):
    x=np.array(x,'float32')
    x /= 255.
    #x -= 0.5
    #x *= 2.
    return x    


# train test model
def train_test_model(X_train,y_train,X_test,y_test,foldnm=1):
    print 'fold %s training in progress ...' %foldnm
    # load last weights
    if pre_train:
        if  os.path.exists(path2weights):
            model.load_weights(path2weights)
            print 'previous weights loaded!'
        else:
            raise IOError('weights does not exist!!!')
    else:
        if  os.path.exists(path2weights):
            model.load_weights(path2weights)
            print 'previous weights loaded!'
            train_status='previous weights'
            return train_status
    
    # path to csv file to save scores
    path2scorescsv = weightfolder+'/scores.csv'
    first_row = 'train,test'
    with open(path2scorescsv, 'w+') as f:
        f.write(first_row + '\n')
           
    # Fit the model
    start_time=time.time()
    scores_test=[]
    scores_train=[]
    if params_train['loss']=='dice': 
        best_score = 0
        previous_score = 0
    else:
        best_score = 1e6
        previous_score = 1e6
    patience = 0
    
    # convert class vectors to binary class matrices
    y_train = np_utils.to_categorical(y_train, num_classes)
    y_test = np_utils.to_categorical(y_test, num_classes)
    
    
    for epoch in range(params_train['nbepoch']):
    
        print ('epoch: %s,  Current Learning Rate: %.1e' %(epoch,model.optimizer.lr.get_value()))
        #seed = np.random.randint(0, 999999)
    
        batches=0
        bs=X_train.shape[0]
        for X_batch, y_batch in datagen.flow(X_train, y_train, batch_size=bs):
            X_batch=preprocess_input(X_batch)
            hist = model.fit(X_batch, y_batch,verbose=0,batch_size=batch_size)
            batches += 1
            if batches >= len(X_train) / bs:
                # we need to break the loop by hand because
                # the generator loops indefinitely
                break
            
        #hist=model.fit_generator(datagen.flow(X_train, y_train, batch_size=batch_size),\
                                 #samples_per_epoch=len(X_train), nb_epoch=1, verbose=0,class_weight=class_weight)
    
        # evaluate on test and train data
        score_test=model.evaluate(X_test,y_test,verbose=0,batch_size=batch_size)
        score_train=np.mean(hist.history['loss'])
       
        print ('score_train: %s, score_test: %s' %(score_train,score_test))
        scores_test=np.append(scores_test,score_test)
        scores_train=np.append(scores_train,score_train)    

        # check for improvement    
        if (score_test<=best_score):
            print ("!!!!!!!!!!!!!!!!!!!!!!!!!!! viva, improvement!!!!!!!!!!!!!!!!!!!!!!!!!!!") 
            best_score = score_test
            patience = 0
            model.save_weights(path2weights)  
            model.save(weightfolder+'/model.h5')
            
        # learning rate schedule
        if score_test>previous_score:
            #print "Incrementing Patience."
            patience += 1

        # learning rate schedule                
        if patience == params_train['max_patience']:
            params_train['learning_rate'] = params_train['learning_rate']/2
            print ("Upating Current Learning Rate to: ", params_train['learning_rate'])
            model.optimizer.lr.set_value(params_train['learning_rate'])
            print ("Loading the best weights again. best_score: ",best_score)
            model.load_weights(path2weights)
            patience = 0
        
        # save current test score
        previous_score = score_test    
        
        # store scores into csv file
        with open(path2scorescsv, 'a') as f:
            string = str([score_train,score_test])
            f.write(string + '\n')
           
    
    print ('model was trained!')
    elapsed_time=(time.time()-start_time)/60
    print ('elapsed time: %d  mins' %elapsed_time)      

    # train test progress plots
    plt.figure(figsize=(15,10))
    plt.plot(scores_test)
    plt.plot(scores_train)
    plt.title('train-validation progress',fontsize=20)
    plt.legend(('test','train'), loc = 'lower right',fontsize=20)
    plt.xlabel('epochs',fontsize=20)
    plt.ylabel('loss',fontsize=20)
    plt.grid(True)
    plt.show()
    plt.savefig(weightfolder+'/train_val_progress.png')
    
    print 'training completed!'
    train_status='completed!'
    return train_status

def gamma_correction(img, correction):
    img = img/255.0
    img = cv2.pow(img, correction)
    return np.uint8(img*255)    
    
#%%

# train data ids are loaded to be split into k-fold train-test
ff_train=h5py.File(path2trainhdf5,'r')
ids=ff_train.keys()
print 'total train', len(ff_train.keys())

# k-fold cross-validation data split
n_folds=5
#kf = KFold(n_splits=n_folds,random_state=seed)

#% model
print('-'*30)
# path to train-test.hdf5, first checking if it exists
path2traintest=path2root+'traintest'+str(h)+'by'+str(w)+'.hdf5'
if not os.path.exists(path2traintest):
    X,y,ids_out=load_data(ids)
    ff_traintest=h5py.File(path2traintest,'w')
    ff_traintest['X']=X
    ff_traintest['y']=y    
    ff_traintest['ids']=np.array(ids_out,'string')    
    ff_traintest.close()
    print 'hdf5 saved!'

# load train-test data
ff_traintest=h5py.File(path2traintest,'r')
ids=ff_traintest['ids']

# k-fold cross-validation data split
y=ff_traintest['y'].value  
X=ff_traintest['X']
skf = StratifiedKFold(n_splits=5,random_state=123,shuffle=True)
skf.get_n_splits(X,y)

# class weights
#cw_y0=1.*len(y)/np.count_nonzero(y==0)
#cw_y1=1.*len(y)/np.count_nonzero(y==1)
#cw_y2=1.*len(y)/np.count_nonzero(y==2)
#class_weight={0:cw_y0,1:cw_y1,2:cw_y2}
class_weight={0:1,1:1,2:1}


# loop over folds
foldnm=0
for train, test in skf.split(X,y):
    foldnm+=1    
    print("fold %s, train: %s test: %s" % (foldnm,train, test))

    # training params
    params_train={
        'h': h,
        'w': w,
        'z': z,
        'c':1,           
        'learning_rate': 5e-5,
        'optimizer': 'Adam',
        'loss': 'categorical_crossentropy',
        'nbepoch': 300,
        'num_classes': num_classes,
        'nb_filters': 16,    
        'max_patience': 30,
        'stride': 2,
            }
        
    train=list(np.sort(train))
    test=list(np.sort(test))
    X_train=X[train]
    y_train=y[train]       
        
    X_test=X[test]
    y_test=y[test]    
    
    # histogram equalization
    if hist_eq is True:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        for k in range(X_train.shape[0]):
            for k1 in range(X_train.shape[1]):
                X_train[k,k1] = clahe.apply(X_train[k,k1])

        for k1 in range(X_test.shape[1]):
            for k in range(X_test.shape[0]):
                X_test[k,k1] = clahe.apply(X_test[k,k1])
            
    # normalize test data
    X_test=preprocess_input(np.array(X_test,'float32'))
    
    
    #model = models.model(params_train)
    model = models.vgg_model(params_train)
    model.summary()


    # exeriment name to record weights and scores
    netinfo='_VGG_FC'
    experiment='fold'+str(foldnm)+netinfo+'_hw_'+str(h)+'by'+str(w)+'nbfilters_'+str(params_train['nb_filters'])
    print ('experiment:', experiment)

    # checkpoint
    weightfolder='./output/weights/'+experiment
    if  not os.path.exists(weightfolder):
        os.makedirs(weightfolder)
        print ('weights folder created')

    ########## log
    path2logs=weightfolder+'/logs/'
    if  not os.path.exists(path2logs):
        os.makedirs(path2logs)
        print ('log folder created')
        
    now = datetime.datetime.now()
    info='log_trainval_'
    suffix = info + '_' + str(now.strftime("%Y-%m-%d-%H-%M"))
    # Direct the output to a log file and to screen
    loggerFileName = os.path.join(path2logs,  suffix + '.txt')
    utils.initialize_logger(loggerFileName)
        

    # path to weights
    path2weights=weightfolder+"/weights.hdf5"
    path2model=weightfolder+"/model.hdf5"
    
    # train test on fold #
    train_test_model(X_train,y_train,X_test,y_test,foldnm)


    # loading best weights from training session
    if  os.path.exists(path2weights):
        model.load_weights(path2weights)
        print 'weights loaded!'
    else:
        raise IOError('weights does not exist!!!')
    y_test = np_utils.to_categorical(y_test, num_classes)
    score_test=model.evaluate(X_test,y_test,verbose=0,batch_size=8)
    print ('score_test: %.2f' %(score_test))
    



#%%

# test on leaderboard data
df_solution_stg1 = pd.read_csv('../data/solution_stg1_release.csv')
df_solution_stg1.head()

df_stg1 = pd.read_csv('../data/sample_submission.csv')
df_stg2 = pd.read_csv('../data/sample_submission_stg2.csv')
print('Number of training patients: {}'.format(len(df_stg1)))
print('Number of training patients: {}'.format(len(df_stg2)))
df_stg1.head()
df_stg2.head()

path2test_leader_stg1=path2root+'test_leader_'+str(h)+'by'+str(w)+'.hdf5'
path2test_leader_stg2=path2root+'test_leader_stg2_'+str(h)+'by'+str(w)+'.hdf5'

# load data
if not os.path.exists(path2test_leader_stg1):
    X_test_leader,_,ids_test_leader=load_data(df_stg1.image_name,'test')
    ff_test_leader=h5py.File(path2test_leader_stg1,'w')
    ff_test_leader['X']=X_test_leader
    ff_test_leader['ids']=ids_test_leader
    ff_test_leader.close()
else:
    # load
    ff_test_leader=h5py.File(path2test_leader_stg1,'r')
    X_test_leader=ff_test_leader['X'].value
    id_test_leader=ff_test_leader['ids']
    print 'test leaderboard loaded!'

# normalize
X_test_leader_stg1=preprocess_input(X_test_leader)


# load data
if not os.path.exists(path2test_leader_stg2):
    X_test_leader,_,ids_test_leader=load_data(df_stg2.image_name,'test')
    ff_test_leader=h5py.File(path2test_leader_stg2,'w')
    ff_test_leader['X']=X_test_leader
    ff_test_leader['ids']=ids_test_leader
    ff_test_leader.close()
else:
    # load
    ff_test_leader=h5py.File(path2test_leader_stg2,'r')
    X_test_leader=ff_test_leader['X'].value
    id_test_leader=ff_test_leader['ids']
    print 'test leaderboard loaded!'

# normalize
X_test_leader_stg2=preprocess_input(X_test_leader)

X_test_leader=np.append(X_test_leader_stg1,X_test_leader_stg2,axis=0)

#%%
# prediction for nfolds
y_pred=[]
for foldnm in range(1,6):
    
    # load weights
    #netinfo='_simpleVGG'
    experiment='fold'+str(foldnm)+netinfo+'_hw_'+str(h)+'by'+str(w)+'nbfilters_'+str(params_train['nb_filters'])
    print ('experiment:', experiment)
    weightfolder='./output/weights/'+experiment
    # path to weights
    path2weights=weightfolder+"/weights.hdf5"
    if  os.path.exists(path2weights):
        model.load_weights(path2weights)
    else:
        raise IOError ('weights does not exist!')


    # prediction
    y_pred_perfold=model.predict(X_test_leader)
    print y_pred_perfold.shape    
    y_pred.append(y_pred_perfold)
    
# 
y_pred1=np.array(y_pred)
y_pred2=np.mean(y_pred1,axis=0)

# combine all predictions
#df.Type_1[:512]=df_solution_stg1.Type_1
#df.Type_2[:512]=df_solution_stg1.Type_2
#df.Type_3[:512]=df_solution_stg1.Type_3

#df.Type_1[512:]=y_pred2[:,0]
#df.Type_2[512:]=y_pred2[:,1]
#df.Type_3[512:]=y_pred2[:,2]

df_stg2.Type_1=y_pred2[:,0]
df_stg2.Type_2=y_pred2[:,1]
df_stg2.Type_3=y_pred2[:,2]

# make submission
now = datetime.datetime.now()
info='nfolds'
suffix = info + '_' + str(now.strftime("%Y-%m-%d-%H-%M"))
sub_file = os.path.join('./output/submission', 'submission_' + suffix + '.csv')

df_stg2.to_csv(sub_file, index=False)
print(df_stg2.head()) 




