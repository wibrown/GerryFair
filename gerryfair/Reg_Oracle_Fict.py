# Version Created: 20 April 2018
import argparse
import numpy as np
import pandas as pd
from sklearn import linear_model
import random
import sys

import audit
import fairness_plots
import heatmap
import Reg_Oracle_Class
import clean




# Helper Functions
# -----------------------------------------------------------------------------------------------------------

#Parse arguments for user input
def setup():
    parser = argparse.ArgumentParser(description='Reg_Oracle_Fict input parser')
    parser.add_argument('-C', type=float, default=10, required=False, help='C is the bound on the maxL1 norm of the dual variables, (Default = 10)')
    parser.add_argument('-p', '--print_output', default=False, action='store_true', required=False,
                        help='Include this flag to determine whether output is printed, (Default = False)')
    parser.add_argument('-m', '--heatmap', default=False, action='store_true', required=False,
                        help='Include this flag to determine whether heatmaps are generated, (Default = False)')
    parser.add_argument('--heatmap_iters', type=int, default=1, required=False,
                         help='number of iterations heatmap data is saved after, (Default = 1)')
    parser.add_argument('-d', '--dataset', type=str,
                        help='name of the dataset that was input into clean (Required)')
    parser.add_argument('-i', '--iters', type=int, default=10, required=False, help='number of iterations to terminate after, (Default = 10)')
    parser.add_argument('-g', '--gamma_unfair', type=float, default=.01, required=False, help='approximate gamma disparity allowed in subgroups, (Default = .01)')
    parser.add_argument('--plots', default=False, action='store_true', required=False,
                        help='Include this flag to determine whether plots of error and unfairness are generated, (Default = False)')
    args = parser.parse_args()
    return [args.C, args.print_output, args.heatmap, args.heatmap_iters, args.dataset, args.iters, args.gamma_unfair, args.plots]


# Inputs:
# A: the previous set of decisions (probabilities) up to time iter - 1
# q: the most recent classifier found
# x: the dataset
# y: the labels
# iter: the iteration
# Outputs:
# error: the error of the average classifier found thus far (incorporating q)
def gen_a(q, x, y, A, iter):
    """Return the classifications of the average classifier at time iter."""

    new_preds = np.multiply(1.0 / iter, q.predict(x))
    ds = np.multiply((iter - 1.0) / iter, A)
    ds = np.add(ds, new_preds)
    error = np.mean([np.abs(ds[k] - y[k]) for k in range(len(y))])
    return [error, ds]

def learner_costs(c_1, f, X_prime, y, C, iteration, fp_disp, gamma):
    """Recursively update the costs from incorrectly predicting 1 for the learner."""
    # store whether FP disparity was + or -
    pos_neg = f[4]
    X_0_prime = pd.DataFrame([X_prime.iloc[u, :] for u,s in enumerate(y) if s == 0])
    g_members = f[0].predict(X_0_prime)
    m = len(c_1)
    n = float(len(y))
    g_weight_0 = np.sum(g_members)*(1.0/float(m))
    for t in range(m):
        new_group_cost = (1.0/n)*pos_neg*C*(1.0/iteration) * (g_weight_0 - g_members[t])
        if np.abs(fp_disp) < gamma:
            if t == 0:
                print('barrier')
            new_group_cost = 0
        c_1[t] = (c_1[t] - 1.0/n) * ((iteration-1.0)/iteration) + new_group_cost + 1.0/n
    return c_1


def learner_br(c_1t, X, y):
    """Solve the CSC problem for the learner."""
    n = len(y)
    c_1t_new = c_1t[:]
    c_0 = [0.0] * n
    c_1 = []
    for r in range(n):
        if y[r] == 1:
            c_1.append((-1.0/n))
        else:
            c_1.append(c_1t_new.pop(0))
    reg0 = linear_model.LinearRegression()
    reg0.fit(X, c_0)
    reg1 = linear_model.LinearRegression()
    reg1.fit(X, c_1)
    func = Reg_Oracle_Class.RegOracle(reg0, reg1)
    return func

# not currently printed out
def calc_unfairness(A, X_prime, y_g, FP_p):
    """Calculate unfairness in marginal sensitive subgroups (thresholded)."""
    unfairness = []
    n = X_prime.shape[1]
    sens_means = np.mean(X_prime, 0)
    for q in range(n):
        group_members = [X_prime.iloc[i, q] > sens_means[q]
                         for i in range(X_prime.shape[0])]
        # calculate FP rate on group members
        fp_g = [a for t, a in enumerate(
            A) if group_members[t] == 1 and y_g[t] == 0]
        if len(fp_g) > 0:
            fp_g = np.mean(fp_g)
        else:
            fp_g = 0
        # calculate the fp rate on non-group members
        group_members_neg = [1 - g for g in group_members]
        # calculate FP rate on group members
        fp_g_neg = [a for t, a in enumerate(
            A) if group_members_neg[t] == 1 and y_g[t] == 0]
        if len(fp_g_neg) > 0:
            fp_g_neg = np.mean(fp_g_neg)
        else:
            fp_g_neg = 0
        unfairness.append(
            np.max([np.abs(np.mean(fp_g) - FP_p), np.abs(np.mean(fp_g_neg) - FP_p)]))
    return unfairness


# -----------------------------------------------------------------------------------------------------------
# Fictitious Play Algorithm

# Input: dataset cleaned into X, X_prime, y, and arguments from commandline
# Output: for each iteration, the error and the fp difference - heatmap can also be produced
def fictitious_play(X, X_prime, y, C=10, printflag=False, heatmapflag=False, heatmap_iter=10, max_iters=10, gamma=0.01):
    # subsample
    # if num > 0:
    #     X = X.iloc[0:num, 0:col]
    #     y = y[0:num]
    #     X_prime = X_prime.iloc[0:num, :]

    stop = False
    n = X.shape[0]
    m = len([s for s in y if s == 0])
    p = [learner_br([1.0 / n] * m, X, y)]
    iteration = 1
    errors_t = []
    fp_diff_t = []
    coef_t = []
    size_t = []
    groups = []
    cum_group_mems = []
    m = len([s for s in y if s == 0])
    c_1t = [1.0 / n] * m
    FP = 0
    A = [0.0] * n
    group_membership = [0.0] * n
    X_0 = pd.DataFrame([X_prime.iloc[u, :] for u, s in enumerate(y) if s == 0])

    vmin = None
    vmax = None

    while iteration < max_iters:
        print('iteration: {}'.format(int(iteration)))
        # get t-1 mixture decisions on X by randomizing on current set of p
        emp_p = gen_a(p[-1], X, y, A, iteration)
        # get the error of the t-1 mixture classifier
        err = emp_p[0]
        # Average decisions
        A = emp_p[1]

        # save heatmap every heatmap_iter iterations
        if heatmapflag and (iteration % heatmap_iter) == 0:
            
            A_heat = A
            # initial heat map
            X_prime_heat = X_prime.iloc[:, 0:2]
            eta = 0.2

            minmax = heatmap.heat_map(X, X_prime_heat, y, A_heat, eta, 'viz/heatmaps/heatmap_iteration_{}'.format(int(iteration)), vmin, vmax)
            if iteration == 1:
                vmin = minmax[0]
                vmax = minmax[1]

        # update FP to get the false positive rate of the mixture classifier
        A_recent = p[-1].predict(X)
        # FP rate of t-1 mixture on new group g_t
        FP_recent = np.mean([A_recent[i] for i, c in enumerate(y) if c == 0])
        FP = ((iteration - 1.0) / iteration) * FP + FP_recent * (1.0 / iteration)
        # dual player best responds to strategy up to t-1
        f = audit.get_group(A, X, X_prime, y, FP)
        # flag whether FP disparity was positive or negative
        pos_neg = f[4]
        fp_disparity = f[1]
        group_size_0 = np.sum(f[0].predict(X_0)) * (1.0 / n)

        # compute list of people who have been included in an identified subgroup up to time t
        group_membership = np.add(group_membership, f[0].predict(X_prime))
        group_membership = [g != 0 for g in group_membership]
        group_members_t = np.sum(group_membership)
        cum_group_mems.append(group_members_t)

        # primal player best responds: cost-sensitive classification
        p_t = learner_br(c_1t, X, y)
        A_t = p_t.predict(X)
        FP_t = np.mean([A_t[i] for i, c in enumerate(y) if c == 0])

        # append new group, new p, fp_diff of group found, coefficients, group size
        groups.append(f[0])
        p.append(p_t)
        fp_diff_t.append(np.abs(f[1]))
        errors_t.append(err)
        coef_t.append(f[0].b0.coef_ - f[0].b1.coef_)

        if iteration == 1:
            print(
                'most accurate classifier accuracy: {}, most acc-class unfairness: {}, most acc-class size {}'.format(
                    err,
                    fp_diff_t[0],
                    group_size_0))

        if printflag:
            print(
                'ave error: {}, gamma-unfairness: {}, group_size: {}, frac included ppl: {}'.format('{:f}'.format(err),
                                                                                                    '{:f}'.format(
                                                                                                        np.abs(f[1])),
                                                                                                    '{:f}'.format(
                                                                                                        group_size_0),
                                                                                                    '{:f}'.format(
                                                                                                        cum_group_mems[
                                                                                                            -1] / float(
                                                                                                            n))))


        # update costs: the primal player best responds
        c_1t = learner_costs(c_1t, f, X_prime, y, C, iteration, fp_disparity, gamma)
        sys.stdout.flush()
        iteration += 1
        iteration = float(iteration)
    return errors_t, fp_diff_t


# -----------------------------------------------------------------------------------------------------------
# Main method definition

if __name__ == "__main__":
    # get command line arguments
    C, printflag, heatmapflag, heatmap_iter, dataset, max_iters, gamma, plots = setup() #sys.argv[1:]
    random.seed(1)

    # Data Cleaning and Import
    X, X_prime, y = clean.get_data(dataset)

    # print out the invoked parameters
    print(
        'Invoked Parameters: C = {}, number of sensitive attributes = {}, random seed = 1, dataset = {}, gamma = {}'.format(
            C, X_prime.shape[1], dataset, gamma))

    # Run the fictitious play algorithm
    errors_t, fp_diff_t = fictitious_play(X, X_prime, y, C, printflag, heatmapflag, heatmap_iter, max_iters, gamma)

    if plots:
        fairness_plots.plot_single(errors_t, fp_diff_t, max_iters, gamma, C)


    # TODO: Decide on functionality for how pareto curve should be accessed.

def pareto(X, X_prime, y, gamma_list, C=10, max_iters=10):
    # Store errors and fp over time for each gamma
    all_errors = []
    all_fp = []
    for g in gamma_list:
        errors_gt, fp_diff_gt = fictitious_play(X, X_prime, y, C=C, max_iters=max_iters, gamma=g)

        all_errors.append(errors_gt[-1])
        all_fp.append(fp_diff_gt[-1])
    print(all_errors)
    print(all_fp)

    #fairness_plots.plot_pareto(all_errors, all_fp)



