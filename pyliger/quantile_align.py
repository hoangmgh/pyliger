import numpy as np
import pandas as pd

from .utilities import refine_clusts_knn
#######################################################################################
#### Quantile Alignment/Normalization
    
def quantile_norm(liger_object, 
                  quantiles = 50, 
                  ref_dataset = None, 
                  min_cells = 20, 
                  dims_use = None, 
                  do_center = False, 
                  max_sample = 1000, 
                  eps = 0.9, 
                  refine_knn = True,
                  knn_k = 20):
    """Quantile align (normalize) factor loadings
    
    This process builds a shared factor neighborhood graph to jointly cluster cells, then quantile
    normalizes corresponding clusters.

    The first step, building the shared factor neighborhood graph, is performed in SNF(), and
    produces a graph representation where edge weights between cells (across all datasets)
    correspond to their similarity in the shared factor neighborhood space. An important parameter
    here is knn_k, the number of neighbors used to build the shared factor space. 
    
    Next we perform quantile alignment for each dataset, factor, and cluster (by
    stretching/compressing datasets' quantiles to better match those of the reference dataset). These
    aligned factor loadings are combined into a single matrix and returned as H_norm.
    
    Parameters
    ----------
    liger_object : liger
        Should run optimizeALS before calling.
    quantiles : int, optional, (default 50)
        Number of quantiles to use for quantile normalization.
    ref_dataset : str, optional, (default None)
        Name of dataset to use as a "reference" for normalization. By default,
        the dataset with the largest number of cells is used.
    min_cells : int, optional, (default 20)
        Minimum number of cells to consider a cluster shared across datasets.
    dims_use : list, optional, (default list(range(liger_object.adata_list[0].varm['H'].shape[1])))
        Indices of factors to use for shared nearest factor determination.
    do_center : bool, optional, (default False)
        Centers the data when scaling factors (useful for less sparse modalities like
        methylation data).
    max_sample : int, optional, (default 1000)
        Maximum number of cells used for quantile normalization of each cluster 
        and factor.
    eps : float, optional, (default 0.9)
        The error bound of the nearest neighbor search. Lower values give more 
        accurate nearest neighbor graphs but take much longer to computer.
    refine_knn : bool, optional, (default True)
        whether to increase robustness of cluster assignments using KNN graph.
    knn_k : int, optional, (default 20)
        Number of nearest neighbors for within-dataset knn graph. 

    Returns
    -------
    liger_object : liger
        liger_object with 'H_norm' and 'clusters' attributes.

    Usage
    -----
    ligerex = quantile_norm(ligerex) # do basic quantile alignment
    ligerex = quantile_norm(ligerex, resolution = 1.2) # higher resolution for more clusters (note that SNF is conserved)
    ligerex = quantile_norm(ligerex, knn_k = 15, resolution = 1.2) # change knn_k for more fine-grained local clustering
    """
    
    num_samples = len(liger_object.adata_list)
    
    # set reference dataset
    if ref_dataset is None:
        ns = [adata.shape[1] for adata in liger_object.adata_list]
        ref_dataset_idx = np.argmax(ns)
    else:
        for i in range(num_samples):
            if liger_object.adata_list[i].uns['sample_name'] == ref_dataset:
                ref_dataset_idx = i
                break
    
    # set indices of factors
    if dims_use is None:
        use_these_factors = list(range(liger_object.adata_list[0].varm['H'].shape[1]))
    else:
        use_these_factors = dims_use
    
    Hs = [adata.varm['H'] for adata in liger_object.adata_list]
    num_clusters = Hs[ref_dataset_idx].shape[1]
    
    # Max factor assignment
    clusters = []
    col_name = []
    for i in range(num_samples):
        # scale the H matrix by columns
        scale_H = (Hs[i]-np.mean(Hs[i], axis=0))/np.std(Hs[i], axis=0, ddof=1)
        
        # get the index of maximum value for each cell
        clusts = np.argmax(scale_H, axis=1)
        
        # increase robustness of cluster assignments using knn graph
        if refine_knn:
            clusts = refine_clusts_knn(Hs[i], clusts, k=knn_k, eps=eps)
            
        clusters.append(clusts)
        col_names.append(liger_object.adata_list[i].var['barcodes'])

    # Perform quantile alignment
    for k in range(num_samples):
        for j in range(num_clusters):
            cells2 = clusters[k] == j
            cells1 = clusters[ref_dataset_idx] == j
            for i in range(dims):
                num_cells2 = np.sum(cells2)
                num_cells1 = np.sum(cells1)
                if num_cells1 < min_cells and num_cells2 < min_cells:
                    continue
                if num_cells2 == 1:
                    Hs[k][cells2, i] = np.mean(Hs[ref_dataset_idx][cells1,i])
                    continue
                if num_cells2 > max_sample and num_cells1 > max_sample:
                    q2 = np.quantile(np.random.permutation(Hs[k][cells2, i])[0:min(num_cells2, max_sample)], np.linspace(0,1,num=quantiles))
                    q1 = np.quantile(np.random.permutation(Hs[ref_dataset_idx][cells1, i])[0:min(num_cells1, max_sample)], np.linspace(0,1,num=quantiles))
                else:
                    q2 = np.quantile(np.random.permutation(Hs[k][cells2, i])[0:min(num_cells2, max_sample)], np.linspace(0,1,num=quantiles))
                    q1 = np.quantile(np.random.permutation(Hs[ref_dataset_idx][cells1, i])[0:min(num_cells1, max_sample)], np.linspace(0,1,num=quantiles))
                if np.sum(q1) == 0 and np.sum(q2) and len(np.unique(q1)) < 2 and len(np.unique(q2)) < 2:
                    new_vals = np.repeat(0, num_cells2)
                else:
                    warp_func = 
                    new_vals = 
                Hs[k][cells, i] = new_vals
                
    # combine clusters into one
    clusters = np.array(clusters).flatten()
    col_name = np.array(col_name).flatten()
    # assign clusters and H_norm attributes to liger_object
    liger_object.clusters = pd.DataFrame(labels, columns=col_names)
    liger_object
        
    return liger_object


def louvainCluster(liger_object, 
                   resolution = 1.0, 
                   k = 20, 
                   prune = 1 / 15, 
                   eps = 0.1, 
                   nRandomStarts = 10,
                   nIterations = 100, 
                   random_seed = 1):
    """Louvain algorithm for community detection
    
    After quantile normalization, users can additionally run the Louvain algorithm 
    for community detection, which is widely used in single-cell analysis and excels at merging 
    small clusters into broad cell classes.

    Parameters
    ----------
    liger_object : liger
        Should run quantile_norm before calling.
    resolution : TYPE, optional
        DESCRIPTION. The default is 1.0.
    k : TYPE, optional
        DESCRIPTION. The default is 20.
    prune : TYPE, optional
        DESCRIPTION. The default is 1 / 15.
    eps : TYPE, optional
        DESCRIPTION. The default is 0.1.
    nRandomStarts : TYPE, optional
        DESCRIPTION. The default is 10.
    nIterations : TYPE, optional
        DESCRIPTION. The default is 100.
    random_seed : TYPE, optional
        DESCRIPTION. The default is 1.

    Returns
    -------
    None.

    """

# Impute the query cell expression matrix
def imputeKNN(liger_object, reference, queries, knn_k = 20, weight = True, norm = True, scale = False):
    """
    

    Parameters
    ----------
    liger_object : TYPE
        DESCRIPTION.
    reference : TYPE
        DESCRIPTION.
    queries : TYPE
        DESCRIPTION.
    knn_k : TYPE, optional
        DESCRIPTION. The default is 20.
    weight : TYPE, optional
        DESCRIPTION. The default is True.
    norm : TYPE, optional
        DESCRIPTION. The default is True.
    scale : TYPE, optional
        DESCRIPTION. The default is False.

    Returns
    -------
    None.

    """

# Perform Wilcoxon rank-sum test
def runWilcoxon(liger_object, compare_method, data_use = "all"):
    pass

# Linking genes to putative regulatory elements
def linkGenesAndPeaks(gene_counts, peak_counts, path_to_coords, genes_list = None, dist = "spearman", 
                      alpha = 0.05):
    pass

# Export predicted gene-pair interaction
def makeInteractTrack(corr_mat, genes_list, output_path, path_to_coords):
    pass

# Analyze biological interpretations of metagene
def runGSEA(liger_object, gene_sets = [], mat_w = True, mat_v = 0, custom_gene_sets = []):
    pass