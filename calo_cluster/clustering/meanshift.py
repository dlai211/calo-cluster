  
from sklearn import cluster
from calo_cluster.clustering.mean_shift_cosine_gpu import MeanShiftCosine
from calo_cluster.clustering.base_clusterer import BaseClusterer
import numpy as np

class MeanShift(BaseClusterer):
    print('running meanshift.py')
    def __init__(self, *, use_gpu=True, use_semantic=False, ignore_semantic_labels=None, **kwargs):
        if use_gpu:
            self.clusterer = MeanShiftCosine(**kwargs)
        else:
            self.clusterer = cluster.MeanShift(**kwargs)
        super().__init__(use_semantic, ignore_semantic_labels)

    def cluster(self, embedding, semantic_labels=None):
        print('meanshift.py cluster')
        """Clusters hits in event. If self.use_semantic, clusters only within each predicted semantic subset. 
           If self.ignore_semantic_labels, ignores hits with the given semantic labels."""
        if self.use_semantic:
            cluster_labels = np.full_like(semantic_labels, fill_value=-1)
            unique_semantic_labels = np.unique(semantic_labels)
            for l in unique_semantic_labels:
                if l in self.ignore_semantic_labels:
                    continue
                mask = (semantic_labels == l)
                self.clusterer.fit(embedding[mask])
                cluster_labels[mask] = self.clusterer.labels_
        else:
            self.clusterer.fit(embedding)
            cluster_labels = self.clusterer.labels_
        return cluster_labels
