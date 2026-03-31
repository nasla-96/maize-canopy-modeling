from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
import numpy as np

N_TRAIT_GROUPS = 4
DEFAULT_N_LEAVES = 12
TRAIT_NAMES = ("lengths", "widths", "theta", "phi")


@dataclass(frozen=True)
class TraitBounds:
    low: float
    high: float


DEFAULT_BOUNDS = {
    "lengths": TraitBounds(40.0, 110.0),
    "widths": TraitBounds(5.0, 14.0),
    "theta": TraitBounds(0.0, 360.0),
    "phi": TraitBounds(-45.0, 45.0),
}


def expected_num_genes(n_leaves: int = DEFAULT_N_LEAVES) -> int:
    return N_TRAIT_GROUPS * n_leaves



def validate_chromosome_length(chromosome: Sequence[float], n_leaves: int = DEFAULT_N_LEAVES) -> None:
    n_expected = expected_num_genes(n_leaves)
    if len(chromosome) != n_expected:
        raise ValueError(f"Expected chromosome with {n_expected} genes, got {len(chromosome)}.")



def decode_chromosome(
    chromosome: Sequence[float],
    n_leaves: int = DEFAULT_N_LEAVES,
    dtype=np.float64,
) -> dict[str, np.ndarray]:
    """
    Decode notebook-order chromosomes:
    [12 lengths, 12 widths, 12 theta, 12 phi].
    """
    validate_chromosome_length(chromosome, n_leaves=n_leaves)
    arr = np.asarray(chromosome, dtype=dtype).reshape(N_TRAIT_GROUPS, n_leaves)
    return {
        "lengths": arr[0].copy(),
        "widths": arr[1].copy(),
        "theta": arr[2].copy(),
        "phi": arr[3].copy(),
    }



def encode_chromosome(
    lengths: Sequence[float],
    widths: Sequence[float],
    theta: Sequence[float],
    phi: Sequence[float],
    dtype=np.float64,
) -> np.ndarray:
    lengths = np.asarray(lengths, dtype=dtype)
    widths = np.asarray(widths, dtype=dtype)
    theta = np.asarray(theta, dtype=dtype)
    phi = np.asarray(phi, dtype=dtype)

    n_leaves = len(lengths)
    for name, values in [("widths", widths), ("theta", theta), ("phi", phi)]:
        if len(values) != n_leaves:
            raise ValueError(f"All trait arrays must have the same length. {name} has length {len(values)} vs {n_leaves}.")

    return np.concatenate([lengths, widths, theta, phi])



def make_gene_space(n_leaves: int = DEFAULT_N_LEAVES) -> list[dict[str, float]]:
    gene_space: list[dict[str, float]] = []
    for trait_name in TRAIT_NAMES:
        bounds = DEFAULT_BOUNDS[trait_name]
        gene_space.extend([{"low": bounds.low, "high": bounds.high} for _ in range(n_leaves)])
    return gene_space



def gene_labels(n_leaves: int = DEFAULT_N_LEAVES) -> list[str]:
    labels = []
    for trait_name in TRAIT_NAMES:
        base = trait_name[:-1] if trait_name.endswith("s") else trait_name
        for leaf_idx in range(1, n_leaves + 1):
            labels.append(f"{base}_{leaf_idx}")
    return labels
