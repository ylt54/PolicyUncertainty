# -*- coding: utf-8 -*-
"""
Created on Wed Oct 11 16:55:35 2017
@author: Daryl Larsen
"""
'''
This program implements the Generalized Stochastic Simulation Algorthim from 
Judd, Maliar and Mailar (2011) "Numerically stable and accurate stochastic 
simulation approaches for solving dynamic economic models", Quantitative
Economics vol. 2, pp. 173-210.
'''
import numpy as np
import matplotlib.pyplot as plt
from LinApp_FindSS import LinApp_FindSS
from Simple_ILA_Model_Funcs import Modeldyn, Modeldefs

'''
We test the algorithm with a simple DSGE model with endogenous labor.
'''

'''
Choose the simulation length
'''
T = 10000

'''
Model's parameters
'''
alpha = .35
beta = .99
gam = 2.5
delta = .08
chi = 10.
theta = 2.
tau = .05 # The first stochastic shock
rho = .9
sigma = .01
mparams = ([alpha, beta, gam, delta, chi, theta, tau, rho, sigma])
nx = 1
ny = 1
nz = 1

def poly1(Xin, XYparams, pord=4):
    '''
    Includes polynomial terms up to order 'pord' for each element and quadratic 
    cross terms  One observation (row) at a time
    '''
    nX = nx + nz
    Xbasis = np.ones((1, 1))
    # generate polynomial terms for each element
    for i in range(1, pord):
        Xbasis = np.append(Xbasis, Xin**i)
    # generate cross terms
    for i in range (0, nX):
        for j in range(i+1, nX):
            temp = Xin[i]*Xin[j]
            Xbasis = np.append(Xbasis, temp)
    return Xbasis

def XYfunc(Xm, Zn, XYparams, coeffs):
    An = np.exp(Zn)
    XZin = np.append(Xm, An)
    XYbasis = np.append(1., XZin)
    for i in range(1, pord):
        XYbasis = poly1(XZin, XYparams)
    XYout = np.dot(XYbasis, coeffs)
    Xn = XYout[0:nx]
    Yn = XYout[nx:nx+ny]
    if Xn < 0:
        Xn = np.array([0])
    if Yn > 0.9999:
        Yn = np.array([0.9999])
    elif Yn < 0:
        Yn = np.array([0])
    return Xn, Yn
    
def MVOLS(Y, X):
    '''
    OLS regression with observations in rows
    '''
    XX = np.dot(np.transpose(X), X)
    XY = np.dot(np.transpose(X), Y)
    coeffs = np.linalg.solve(XX, XY)
    return coeffs
    
regtype = 'poly1' # functional form for X & Y functions 
fittype = 'MVOLS'   # regression fitting method
pord = 4  # order of polynomial for fitting function
ccrit = 1.0E-8  # convergence criteria for XY change
damp = 0.01  # damping paramter for fixed point algorithm
maxit = 500  # maximum number of iterations for fixed point algorithm

XYparams = (regtype, fittype, pord, nx, ny, nz, ccrit, damp)

# find model steady state
Zbar = np.zeros(nz)
guessXY = np.array([.1, .25])
XYbar = LinApp_FindSS(Modeldyn, mparams, guessXY, Zbar, nx, ny)
(kbar, ellbar) = XYbar

Xstart = kbar

# set up steady state input vector
theta0 = np.array([kbar, kbar, kbar, ellbar, ellbar, 0., 0.])

# check SS solution
check = Modeldyn(theta0, mparams)
print ('check SS: ', check)
if np.max(np.abs(check)) > 1.E-6:
    print ('Have NOT found steady state')

#create history of Z's
Z = np.zeros([T,nz])
for t in range(1,T):
    Z[t,:] = rho*Z[t-1] + np.random.randn(1)*sigma
if regtype == 'poly1':
    coeffs = np.array([[ 0.05*kbar,  0.05*ellbar], \
                       [ 0.5, 0.], \
                       [ 0., 0.5*ellbar], \
                       [ 0.05, 0.], \
                       [ 0., 0.3*ellbar], \
                       [ 0.01,  0.], \
                       [ 0., 0.01*ellbar], \
                       [ 0.001,  0.001]])
        
def GSSA(coeffs, pord):       
    dist = 1.
    distold = 2.
    count = 0
    damp = .01
    XYold = np.ones((T-1, nx+ny))

    while dist > 1e-6 and count < maxit:
        count = count + 1
        X = np.zeros((T+1, nx))
        Y = np.zeros((T+1, ny))
        Xin = np.zeros((T, nx+nz))
        A = np.exp(Z)
        x = np.zeros((T,pord*2))
        X[0], Y[0] = XYfunc(Xstart, Z[0], XYparams, coeffs)
        for t in range(1,T+1):
            X[t], Y[t] = XYfunc(X[t-1], Z[t-1], XYparams, coeffs)
            Xin[t-1,:] = np.concatenate((X[t-1], A[t-1]))
            x[t-1,:] = poly1(Xin[t-1,:], XYparams)
        X1 = X[0:T]
        Y1 = Y[0:T]
        # plot time series
        timeperiods = np.asarray(range(0,T))
        plt.plot(timeperiods, X1, label='X')
        plt.axhline(y=kbar, color='r')
        plt.plot(timeperiods, Y1, label='Y')
        plt.axhline(y=ellbar, color='g')
        plt.title('time series')
        plt.xlabel('time')
        plt.legend(loc=9, ncol=(nx+ny))
        plt.show()    
        
        # Generate consumption, lambda, and gamma series
        r = alpha*X[0:T]**(alpha-1)*(A[0:T]*Y[0:T])**(1-alpha)
        w = (1-alpha)*X[0:T]**alpha*(A[0:T]*Y[0:T])**(-alpha)
        c = (1-tau)*(w[0:T]*Y[0:T] + (r[0:T] - delta)*X[0:T]) + X[0:T] + tau*(w[0:T]*Y[0:T] + (r[0:T] - delta)*X[0:T]) - X[1:T+1]
        # T-by-1
        Lam = (c[0:T-1]**(-gam)*(1-tau)*w[0:T-1]) / (chi*Y[0:T-1]**theta)
        # (T-1)-by-1
        Gam = (beta*c[1:T]**(-gam)*(1 + (1-tau)*(r[1:T] - delta))) / (c[0:T-1]**(-gam))
        # (T-1)-by-1
        
        # update values for X and Y
        Xnew = (Gam)*X[1:T]
        Ynew = (Lam)*Y[1:T]
        XY = np.append(Xnew, Ynew, axis = 1)
        x = x[0:T-1,:]
        
        if fittype == 'MVOLS':
            coeffsnew = MVOLS(XY, x)
        
        # calculate distance between XY and XYold
        print('coeffs', coeffs)
        print('coeffsnew', coeffsnew)
        print('X', X)
    
        dist = np.mean(np.abs(1-XY/XYold))
        print('count ', count, 'distance', dist, 'damp', damp)
    
        if dist < distold:
            damp = damp*1.05
            if damp > 1.:
                damp = 1.
        else:
            damp = damp*.8
    
        distold = 1.*dist
    
        # update coeffs
        XYold = XY
        coeffs = (1-damp)*coeffs + damp*coeffsnew
    return coeffs

coeffs00 = GSSA(coeffs, pord)