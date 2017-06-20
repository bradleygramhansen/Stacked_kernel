#!/usr/bin/env python3
import matplotlib
matplotlib.use('Agg')
# -*- coding: utf-8 -*-
"""
Created on Tue May 16 14:26:48 2017

@author: bradley
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 26 10:26:36 2017

@author: bradley gram-hansen
1input dimension:  Deep GP for testing
Pseudo diagram:

input X, k1(x,x), h (hidden targets), x* test input

---------------- X -------------------
                 |
                 K1 | X hyperparams \theta1
                 |
                 K1, K2 | X kernel = K1 + K2 hyperparams \theta1 and \theta2
                 |
                 K1, K2, K3 | X kernel = K1 + K2 + K3 hyperparams \theta1, \theta2, \theta3
                 |
                 :
                 :    
When to stop: Using auto-correlation when the difference between 
the posterior mean and the orginba; data , is around the 0 axis, i.e
the abs(input data - posterior mean of layer) < 1 - white noise

The current model:

The current model now selects a new kernel optimises over that , then if there has been previous
kernels, adds its optimised self to that. Then we select a new kernel for the new layer and repeat.
Not optimising over all kernel parameters, just the kernel for that layer. We then combine all the prev
kernels together, plus that one, to do the GP regression. 

To do:
Add auto-correlation between the posterior mean and RMSE function

"""


import GPy
import os
import platform
if(platform.system() != 'Darwin'):
    os.environ["CUDA_VISIBLE_DEVICES"]="2"
    import pycuda
from matplotlib import pyplot as plt
import numpy as np
import dataprocessing2 as dp
import importdata as impdata
import intialisations as intial
#np.random.seed (seed = 0 )
plt.style.use('ggplot')

try:
    plt.close("all")
except:
    pass


def combine_kernels(K1,K2):
    """Creates the composite kernel"""
    return K1 + K2

def regression(input_data,prev_k, parameters):
    """GP regression module - uses GPy
       - Generates a new kernel, made from the previous
       kernel. 
       - Carries out GP regression + optimisation
       - Does the prediction for the output of the layer
       
       Inputs:
           
       Xtrain     - N  x 2 - split% training data
                           
       Ytrain     - N  x 1 - split% output from training data
                          
       Xval       - N* x 2 - Future times to predict
       
       Yval       - N* x 1 - So that it can be passed to plotting() for 
                            verification
                   
       prev_k     - Linear combination of the previous kernels
       
       layer_no   - 1 x 1
       
       Output:
           
       Posterior mean(Y_pred)  - N* x 1
       Posterior cov           - N* x N*
       Optimised parms         - Depenedent on Kernel
   """
    no_points    = parameters[0]
    option       = parameters[1]
    single_input = parameters[2]
    model        = parameters[3]
    data_keys    = parameters[4]
    layer_no     = parameters[5]
    kernel_name  = parameters[6]
    

    Xtest, Ytest        = impdata.import_data(no_points,option,1,predict_points=True)
    Ytest               = Ytest
#      Ytest               = dp.unit_data(Ytest)
    
    Xtrain                   = input_data['train']
    input_data['val']        = Xtest
    Ytrain                   = input_data[data_keys[0]]
    # Ytrain                   = dp.norm_data(input_data[data_keys[0]])
    input_data[data_keys[1]] = Ytest

#==============================================================================
#==============================================================================
    if layer_no >0:
        k,k_name,parameters[7][0],parameters[7][1]   = dp.select_kernel(single_input)
        k_add                = combine_kernels(prev_k,k)
        parameters[6]        = kernel_name + ' ' +k_name
    else:
        k_add = prev_k
#==============================================================================
    dp.plot_cov_ft(k_add,Xtrain,parameters)
#==============================================================================
#     # Enables us to get kernel parameters
    kernel_params = k_add.param_array
#==============================================================================
    m = GPy.models.GPRegression(Xtrain, Ytrain, k_add) 
    if layer_no == 0:
        k_samp = k_add.K(Xtrain,Xtrain)
        m['Gaussian_noise.variance'] = 0.0001*np.amax(k_samp)
        
    m.optimize(max_iters = 1000)
    print(prev_k.param_array)
    post_mean, post_var = m.predict(Xtest)
    m.plot()
#==============================================================================
#     Getting the scaling right
#==============================================================================
#    # To stop information about what the mean thinks it is predicting from
#    # disrupting future predictions, we instead return post_mean2 which is 
#    # only based on the data that the observer knows about.
    post_mean2  = post_mean[0:no_points]
#    post_mean2  = dp.norm_data(post_mean2)
###    post_mean2  = dp.unit_data(post_mean2)
    post_var2   = post_var[0:no_points]  
#    post_var2   = dp.norm_data(post_var2)
##    post_var2   = dp.unit_data(post_var2)
#
##==============================================================================
#    post_mean1           = post_mean[no_points:]    
##    post_mean1           = dp.norm_data(post_mean1)
##    post_mean1           = dp.unit_data(post_mean1)
#    assert post_var.shape[1] == 1
#    post_var1            = post_var[no_points:]
##    post_var1            = dp.norm_data(post_var1)
##    post_var1            = dp.unit_data(post_var1)
##=============================================================================  
#    post_mean            = np.concatenate((post_mean2,post_mean1),axis=0)
#    post_var             = np.concatenate((post_var2,post_var1),  axis=0)
#    post_mean            = dp.norm_data(post_mean)
#    post_var             = dp.norm_data(post_var)
#==============================================================================
#   Plotting, error and saving 
#==============================================================================
    # Ytest[0:no_points] = Ytrain
    nrmse              = dp.error(post_mean,Ytest)
    #parameters[7] = nrmse for all the 
#    parameters[7].append(nrmse)
    
    data    = [Xtrain, Ytrain, Xtest, Ytest, post_mean, post_var]
    dp.plotting(data,nrmse,parameters)
    dp.save_data(input_data,nrmse,kernel_params,post_mean,post_var,parameters)
#==============================================================================
    if model == 'Aug_Duvenaud':
        temp1 = Xtrain[0:no_points,1]
        temp1 = temp1[:,None]
        temp2 = post_mean2
        input_data['train'] = np.concatenate((temp2,temp1),axis=1)
#==============================================================================
    return k_add,input_data

def layers(input_data, prev_kernel,parameters):
    """ 
        - Do GP regression + optimization
        - Make prediction for layer_output
    Inputs:
        
        input_data         - Dictionary containing all training and validation
                             data arrays for X inputs and Y outputs
        prev_Kernel        - Either composite or if first layer non-composite
        parameters
           
    Outputs:
            
        kernel             - composed of all previous kernels
        input_data 
     """    
    # when using split 1, Xval = Yval = None when intially assigned,
    # it only gets a value when passed through regression
    # to fix later
    kernel,input_data = regression(input_data,prev_kernel,parameters)
    # Xval contains all training and test data if split = 1

    return input_data, kernel


def main():

#==============================================================================
#==============================================================================
# Initialisations
#==============================================================================
     Options      = ['sunspot','financial','mcglass','simple','weierstrass','heartbeat','stock']
     option       = Options[6]
     Models       = ['Aug_Duvenaud','Aug_inputs','Single_inputs']
     model        = Models[0]
#==============================================================================
#      User intialiations
#      Split the perectage of training points that you want. 
     split        = 0.7
     runs         = 2
#==============================================================================

     layer_no     =  0
#     nmrse        = []
     if model == 'Single_inputs':
         no_dims  = 1
         single_input = True
     else:
         no_dims  = 2
         single_input = False
     
     input_data, data_keys,no_points = intial.get_initial(split,option,no_dims)

     init_kernel,k_name,var,ls = dp.select_kernel(single_input)
     parameters   = [no_points,option, single_input,model,data_keys,layer_no,k_name,[var,ls]]
#==============================================================================
# Stacked DeepGP loop
#==============================================================================

#NOTE: Layer_output contains the new outputs coloumn '0' and the original inputs
#      will always be in coloum '1' - python indexing.

     for ii in range(runs):
         layer_no = ii
         if ii > 0:
             print("Now in layer number {0}".format(layer_no))
             parameters[5]      = ii
             input_data, kernel = layers(input_data,kernel,parameters)

         else:
             input_data, kernel = layers(input_data, init_kernel,parameters)


main()

