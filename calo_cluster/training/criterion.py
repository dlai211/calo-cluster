import random

import torch
from torch import nn
from torch import float32
from torch.nn import functional as F
from typing import List

# from DS-Net (https://github.com/hongfz16/DS-Net)
def offset_loss(pt_offsets, gt_offsets, valid):
    pt_diff = pt_offsets - gt_offsets   # (N, 3)
    pt_dist = torch.sum(torch.abs(pt_diff), dim=-1)   # (N)
    valid = valid.view(-1).float()
    offset_norm_loss = torch.sum(pt_dist * valid) / (torch.sum(valid) + 1e-6)
    return offset_norm_loss

def centroid_instance_loss(outputs, labels, subbatch_indices, normalize, delta_d, delta_v):
        # Normalize each output vector.
        if normalize:
            outputs = outputs / (torch.linalg.norm(outputs, axis=1) + 1e-8)[...,None]

        # Iterate over each event within the batch.
        unique_subbatch_indices = torch.unique(subbatch_indices)
        B = unique_subbatch_indices.shape[0]
        loss = 0.0
        for subbatch_idx in unique_subbatch_indices:
            subbatch_mask = subbatch_indices == subbatch_idx
            subbatch_outputs = outputs[subbatch_mask]
            subbatch_labels = labels[subbatch_mask]

            unique_labels = torch.unique(subbatch_labels)
            mus = torch.zeros((unique_labels.shape[0], subbatch_outputs.shape[1]), device=subbatch_outputs.device)
            M = unique_labels.shape[0]

            L_pull = 0.0
            for m, label in enumerate(unique_labels):
                mask = subbatch_labels == label
                Nm = mask.sum()
                mu = subbatch_outputs[mask].mean(axis=0)
                mus[m] = mu
                L_pull += (F.relu(torch.norm(mu - subbatch_outputs[mask], p=1, dim=1) - delta_v)**2).sum() / (M * Nm)
            if M > 1:
                L_push = (F.relu(2 * delta_d - torch.norm(mus.unsqueeze(1) - mus, p=1, dim=2)).fill_diagonal_(0)**2).sum() / (M * (M - 1))
                loss += (L_pull + L_push) / B
            else:
                loss += L_pull / B
        return loss

class OffsetInstanceLoss(nn.Module):
    def __init__(self, valid_labels: List[int] = None) -> None:
        super().__init__()
        if valid_labels is not None:
            self.valid_labels = torch.tensor(valid_labels)

    def forward(self, pt_offsets: torch.Tensor, gt_offsets: torch.Tensor, semantic_labels: torch.Tensor = None):
        if self.valid_labels is not None:
            if self.valid_labels.device != semantic_labels.device:
                self.valid_labels = self.valid_labels.to(semantic_labels.device)
            valid = (semantic_labels[..., None] == self.valid_labels).any(-1)
        else:
            valid = torch.ones_like(semantic_labels).type(torch.bool)
        loss = offset_loss(pt_offsets, gt_offsets, valid)
        return loss

class CentroidInstanceLoss(nn.Module):
    def __init__(self, delta_v: float = 0.5, delta_d: float = 1.5, normalize: bool = True, method: str = None, ignore_labels: List[int] = None) -> None:
        """ If method == 'all', make no distinction between semantic classes.
            If method == 'ignore', ignore any point with a semantic label equal to the given ignore_labels.
            If method == 'separate', do the same as for 'ignore', but also calculate the loss for each semantic class separately.
        """
        super().__init__()
        self.delta_v = delta_v
        self.delta_d = delta_d
        self.normalize = normalize
        if method not in ['all', 'ignore', 'separate']:
            raise ValueError('invalid method!')
        self.method = method
        if method in ['ignore', 'separate']:
            assert ignore_labels is not None
        self.ignore_labels = torch.tensor(ignore_labels)

    def forward(self, outputs: torch.Tensor, labels: torch.Tensor, subbatch_indices: torch.Tensor, weights: torch.Tensor = None, semantic_labels: torch.Tensor = None):
        if self.ignore_labels.device != outputs.device:
            self.ignore_labels = self.ignore_labels.to(outputs.device)
        if self.method == 'all':
            loss = centroid_instance_loss(outputs, labels, subbatch_indices, self.normalize, self.delta_d, self.delta_v)
        elif self.method == 'ignore':
            valid = ~(semantic_labels[..., None] == self.ignore_labels).any(-1)
            if subbatch_indices is not None:
                s_subbatch_indices = subbatch_indices[valid]
            else:
                s_subbatch_indices = None
            loss = centroid_instance_loss(outputs[valid], labels[valid], s_subbatch_indices, self.normalize, self.delta_d, self.delta_v)
        elif self.method == 'separate':
            loss = 0.0
            unique_semantic_labels = torch.unique(semantic_labels)
            for semantic_label in unique_semantic_labels:
                if semantic_label in self.ignore_labels:
                    continue
                mask = (semantic_labels == semantic_label)
                if subbatch_indices is not None:
                    s_subbatch_indices = subbatch_indices[mask]
                else:
                    s_subbatch_indices = None
                loss += centroid_instance_loss(outputs[mask], labels[mask], s_subbatch_indices, self.normalize, self.delta_d, self.delta_v)
        return loss

def test_offset_loss():
    criterion = OffsetInstanceLoss(ignore_labels=[10, 18, 20])
    pt_offsets = torch.arange(15, dtype=float32).reshape((5, 3))
    gt_offsets = torch.arange(15, dtype=float32).reshape((5, 3))
    sem_labels = torch.Tensor([10, 0, 10, 0, 2])
    print(criterion(pt_offsets, gt_offsets, sem_labels))

def main():
    criterion = CentroidInstanceLoss(normalize=False, method='all')
    outputs = torch.arange(10, dtype=float32).reshape((5, 2))
    labels = torch.Tensor([2, 0, 2, 1, 2])
    subbatch_indices = torch.Tensor([0, 0, 0, 0, 0])
    print(outputs)
    print(labels)
    #print(criterion(outputs, labels, subbatch_indices))

    criterion = CentroidInstanceLoss(normalize=False, method='ignore', ignore_label=0)
    outputs = torch.arange(10, dtype=float32).reshape((5, 2))
    labels = torch.Tensor([2, 0, 2, 1, 2])
    subbatch_indices = torch.Tensor([0, 0, 0, 0, 0])
    semantic_labels = torch.Tensor([1, 1, 1, 0, 1])
    print(outputs)
    print(labels)
    print(semantic_labels)
    print(criterion(outputs, labels, subbatch_indices, semantic_labels=semantic_labels))

if __name__ == "__main__":
    test_offset_loss()
    #main()