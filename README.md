# TADC-SBM: a Time-varying, Attributed, Degree-Corrected Stochastic Block Model

[![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/nelsonaloysio/tadc-sbm/blob/main/notebook.ipynb)
[![License](https://img.shields.io/pypi/l/tadc-sbm)](https://github.com/nelsonaloysio/tadc-sbm/blob/main/LICENSE.md)
[![PDF](https://img.shields.io/badge/pdf-Paper-red)](https://nelsonaloysio.github.io/files/tadcsbm2025.pdf)
[![DOI](https://img.shields.io/badge/doi-10.1109/ISCC65549.2025.11326334-blue)](https://doi.org/10.1109/ISCC65549.2025.11326334)

This is the code repository for the accompanying paper:

> Passos, N.A.R.A., Carlini, E., Trani, S. (2025). [TADC-SBM: a Time-varying, Attributed, Degree-Corrected Stochastic Block Model](https://ieeexplore.ieee.org/document/11326334). 2025 IEEE Symposium on Computers and Communications (ISCC), Bologna, Italy, 2025, pp. 1-6.

___

## About

TADC-SBM is a synthetic dataset generator based on [Ghasemian et al. (2016)](http://dx.doi.org/10.1103/PhysRevX.6.031005) and [Tsitsulin et al. (2021)](https://doi.org/10.48550/arXiv.2204.01376) that produces temporal graphs with varying community structures, attribute features, and mesoscale dynamics, suited for community detection and graph representation learning benchmarks under controlled experimental settings:

[![figure](https://github.com/nelsonaloysio/tadc-sbm/raw/main/extra/figure.png)]()

where $\mathbf{B}$ is the block matrix describing the probability of an edge being created among nodes in each community and $\boldsymbol{\tau}$ is the transition matrix with the probabilities of nodes switching communities over time.
Node- and edge-level attribute features are drawn from a multivariate distribution considering the node communities in either the first or the last graph snapshot, optionally representing hierarchical (nested) structures in the feature space.

## Install

The package is available on PyPI as `tadc-sbm` and can be installed with:

```bash
pip install tadc-sbm
```

A binary script `tadc-sbm` is included for command line usage, which can be run with `python -m tadc-sbm` or simply `tadc-sbm` if the package is installed. Note that it is not necessary to install the package to run the script.

### Requirements

Requirements may be installed from [PyPI (requirements.txt)](requirements.txt) or using [conda (environment.yml)](environment.yml).

It is **not** advised to install the [conda environment](environment.yml) as-is (but you certainly may!). Instead, try the following, more flexible environment to solve. Last tested with **Python 3.11** (but should work recent versions as well):

```bash
conda create -n tadcsbm -c conda-forge python=3.11 graph-tool  # tested with 2.96
conda activate tadc-sbm
pip install -r requirements.txt
```

> The [graph-tool](https://graph-tool.skewed.de/) library must be available in the user space: `conda install -c conda-forge graph-tool`.
> See also the [documentation](https://graph-tool.skewed.de) for other platforms and package managers, including Docker and Homebrew.

## Usage

To import the generator function in your code:

```python
from tadcsbm import tadcsbm_simulator
sbm = tadcsbm_simulator(...)
```

An interactive example may be found in the included [notebook](notebook.ipynb) file.

### Command line

A command line interface is included to stremaline graph generation:

```none
usage: tadc-sbm [-h] -n NUM_VERTICES -e NUM_EDGES -k COMMUNITIES
                [-t SNAPSHOTS] [-p INTRA_PROBABILITY] [-q INTER_PROBABILITY]
                [--eta COMMUNITY_STABILITY] [--gamma {0,1}]
                [--beta EDGE_SAMPLING_RATE] [--feature-dim FEATURE_DIM]
                [--feature-center-distance FEATURE_CENTER_DISTANCE]
                [--feature-cluster-variance FEATURE_CLUSTER_VARIANCE]
                [--feature-groups hat_k] [--edge-feature-dim EDGE_FEATURE_DIM]
                [--edge-center-distance EDGE_CENTER_DISTANCE]
                [--edge-cluster-variance EDGE_CLUSTER_VARIANCE]
                [--reverse-order] [--uniform-all] [--dir OUTPUT_DIR]
                [--ext OUTPUT_EXT] [--random-seed RANDOM_SEED] [--silent]

options:
  -h, --help            show this help message and exit
  -n NUM_VERTICES, --num-vertices NUM_VERTICES
                        Number of vertices (nodes)
  -e NUM_EDGES, --num-edges NUM_EDGES
                        Number of edges per snapshot
  -k COMMUNITIES, --communities COMMUNITIES
                        Number of communities
  -t SNAPSHOTS, --snapshots SNAPSHOTS
                        Number of snapshots
  -p INTRA_PROBABILITY, --intra-probability INTRA_PROBABILITY
                        Intra-community edge probability
  -q INTER_PROBABILITY, --inter-probability INTER_PROBABILITY
                        Inter-community edge probability
  --eta COMMUNITY_STABILITY
                        Community stability factor (0.0 to 1.0, default: 1.0)
  --gamma {0,1}         Set transition probabilities based on initial ground
                        truths (0, default) or current (1) node memberships
  --beta EDGE_SAMPLING_RATE
                        Edge sampling rate (0.0 to 1.0)
  --feature-dim FEATURE_DIM
                        Dimensionality of node features
  --feature-center-distance FEATURE_CENTER_DISTANCE
                        Distance between feature clusters
  --feature-cluster-variance FEATURE_CLUSTER_VARIANCE
                        Variance of feature clusters (default: 1.0)
  --feature-groups hat_k
                        Number of feature groups (default: k communities)
  --edge-feature-dim EDGE_FEATURE_DIM
                        Dimensionality of edge features
  --edge-center-distance EDGE_CENTER_DISTANCE
                        Distance between edge feature clusters
  --edge-cluster-variance EDGE_CLUSTER_VARIANCE
                        Variance of edge feature clusters (default: 1.0)
  --reverse-order       Reverse generation order of snapshots (i.e., so the
                        initial ground truths correspond to the last snapshot)
  --uniform-all         Uniform transition probabilities (including current
                        community, i.e., like in Ghasemian et al. 2016)
  --dir OUTPUT_DIR, --output-dir OUTPUT_DIR
                        Directory to save output files (default: 'output')
  --ext OUTPUT_EXT, --output-ext OUTPUT_EXT
                        Extension for output files (default: 'gexf')
  --random-seed RANDOM_SEED, --seed RANDOM_SEED
                        Random seed for reproducible results
  --silent              Suppress verbose output at the end of simulation
```

### Example

To generate graphs with the same configuration used in the experimental evaluation of the paper:

```bash
./tadc-sbm.py --communities 8 \
              --snapshots 8 \
              --num-vertices 1024 \
              --num-edges 10240 \
              --intra-prob 0.9 \
              --eta 0.75 \
              --gamma 0 \
              --feature-dim 32 \
              --feature-center 6.0 \
              --reverse-order
```

The following output is printed at the end of the simulation, unless the `--silent` flag is set:

```none
TemporalMultiGraph (t=8) with 1024 nodes and 39334 edges
Snapshot 1/8: 1024 nodes, 4871 edges, communities: [123 119 124 124 127 127 136 144]
Snapshot 2/8: 1024 nodes, 4996 edges, communities: [124 118 116 139 117 123 143 144]
Snapshot 3/8: 1024 nodes, 4827 edges, communities: [122 131 115 141 116 127 123 149]
Snapshot 4/8: 1024 nodes, 5008 edges, communities: [115 123 125 130 115 117 145 154]
Snapshot 5/8: 1024 nodes, 4950 edges, communities: [112 134 135 112 118 123 143 147]
Snapshot 6/8: 1024 nodes, 4964 edges, communities: [113 129 128 111 125 125 154 139]
Snapshot 7/8: 1024 nodes, 4846 edges, communities: [118 123 136 133 119 128 133 134]
Snapshot 8/8: 1024 nodes, 4872 edges, communities: [128 128 128 128 128 128 128 128]
Total nodes across snapshots: 8192
Total edges across snapshots: 39334
Total transitions across snapshots: 1844 (25.73%)
```

See the included [examples](examples) directory for sample outputs used in the accompanying paper.

> Varying the value of $\eta \in [0, 1]$ (`--eta`) produces snapshots with different community stability rates, while the value of $\gamma \in \\{0, 1\\}$ (`--gamma`) fixes the community transition probabilities for nodes in each snapshot.

### Data conversion

Resulting output is saved in compressed [NetworkX](https://networkx.org)-compatible and [NumPy](https://numpy.org) formats, and may be opened with a number of libraries and tools.
See also: the [`convert`](https://networkx-temporal.readthedocs.io/en/stable/api/utils.html#networkx_temporal.utils.convert.convert) and [`read_graph`](https://networkx-temporal.readthedocs.io/en/stable/api/readwrite.html#networkx_temporal.readwrite.read_graph) functions from [NetworkX-Temporal](https://networkx-temporal.org).

## Acknowledgements

Google Research for the [graph embedding simulations](https://github.com/google-research/google-research/tree/master/graph_embedding/simulations) that TADC-SBM is based on.

## Cite

In case this repository is useful for your research, kindly consider citing:

```
@inproceedings{tadcsbm2025,
  author={Passos, Nelson A. R. A. and Carlini, Emanuele and Trani, Salvatore},
  booktitle={2025 IEEE Symposium on Computers and Communications (ISCC)},
  title={TADC-SBM: a Time-varying, Attributed, Degree-Corrected Stochastic Block Model},
  year={2025},
  volume={},
  number={},
  pages={1-6},
  keywords={Representation learning;Systematics;Computational modeling;Perturbation methods;Stochastic processes;Transportation;Benchmark testing;Stability analysis;Recommender systems;Synthetic data;Temporal Graphs;Community Detection;Stochastic Block Modeling;Graph Representation Learning},
  doi={10.1109/ISCC65549.2025.11326334}
}
```
