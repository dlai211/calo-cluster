class BaseClusterer:
    print("running base_clusterer.py")
    def __init__(self, use_semantic, ignore_semantic_labels):
        self.use_semantic = use_semantic
        self.ignore_semantic_labels = ignore_semantic_labels

    def cluster(self, embedding, semantic_labels=None):
        raise NotImplementedError()
