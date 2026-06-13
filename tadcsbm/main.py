# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from argparse import ArgumentParser
from collections import Counter
from os import mkdir
from os.path import isdir
from sys import argv

import networkx_temporal as tx
import numpy as np

from .tadcsbm_simulator import tadcsbm_simulator
from .utils import (
    generate_block_matrix,
    generate_transition_matrix,
    generate_community_vector,
    gt_to_nx_temporal,
)


def getargs(args: list = argv[1:]):
    """Get command line arguments."""
    parser = ArgumentParser(description="TADCSBM Simulator")

    parser.add_argument("-n", "--num-vertices",
                        type=int,
                        required=True,
                        help="Number of vertices (nodes)")

    parser.add_argument("-e", "--num-edges",
                        type=int,
                        required=True,
                        help="Number of edges per snapshot")

    parser.add_argument("-k", "--communities",
                        dest="communities",
                        type=int,
                        required=True,
                        help="Number of communities")

    parser.add_argument("-t", "--snapshots",
                        type=int,
                        default=1,
                        help="Number of snapshots")

    parser.add_argument("-p", "--intra-probability",
                        type=float,
                        help="Intra-community edge probability")

    parser.add_argument("-q", "--inter-probability",
                        type=float,
                        help="Inter-community edge probability")

    parser.add_argument("--eta",
                        type=float,
                        metavar="COMMUNITY_STABILITY",
                        default=1.0,
                        help="Community stability factor (0.0 to 1.0, default: 1.0)")

    parser.add_argument("--gamma",
                        type=int,
                        choices=[0, 1],
                        default=0,
                        dest="fixed_probabilities",
                        help="Set transition probabilities based on initial "
                              "ground truths (0, default) or current (1) node memberships")

    parser.add_argument("--beta",
                        type=float,
                        default=1.0,
                        dest="edge_sampling_rate",
                        help="Edge sampling rate (0.0 to 1.0)")

    parser.add_argument("--feature-dim",
                        type=int,
                        default=0,
                        help="Dimensionality of node features")

    parser.add_argument("--feature-center-distance",
                        type=float,
                        default=None,
                        help="Distance between feature clusters")

    parser.add_argument("--feature-cluster-variance",
                        type=float,
                        default=1.0,
                        help="Variance of feature clusters (default: 1.0)")

    parser.add_argument("--feature-groups",
                        type=int,
                        default=None,
                        metavar="hat_k",
                        help="Number of feature groups (default: k communities)")

    parser.add_argument("--edge-feature-dim",
                        type=int,
                        default=0,
                        help="Dimensionality of edge features")

    parser.add_argument("--edge-center-distance",
                        type=float,
                        help="Distance between edge feature clusters")

    parser.add_argument("--edge-cluster-variance",
                        type=float,
                        default=1.0,
                        help="Variance of edge feature clusters (default: 1.0)")

    parser.add_argument("--reverse-order",
                        action="store_true",
                        dest="reverse_snapshot_order",
                        help="Reverse generation order of snapshots (i.e., so the " \
                             "initial ground truths correspond to the last snapshot)")

    parser.add_argument("--uniform-all",
                        action="store_true",
                        help="Uniform transition probabilities (including current community, "
                              "i.e., like in Ghasemian et al. 2016)")

    parser.add_argument("--dir", "--output-dir",
                        type=str,
                        dest="output_dir",
                        default="output",
                        help="Directory to save output files (default: 'output')")

    parser.add_argument("--ext", "--output-ext",
                        type=str,
                        dest="output_ext",
                        default="gexf",
                        help="Extension for output files (default: 'gexf')")

    parser.add_argument("--random-seed", "--seed",
                        type=int,
                        default=None,
                        help="Random seed for reproducible results")

    parser.add_argument("--silent",
                        action="store_false",
                        dest="verbose",
                        help="Suppress verbose output at the end of simulation")

    return parser.parse_args(args)


def main():
    args = getargs()

    if not isdir(args.output_dir):
        mkdir(args.output_dir)

    mat = generate_block_matrix(
        args.communities, p=args.intra_probability, q=args.inter_probability)
    tau = generate_transition_matrix(
        args.communities, args.eta, uniform_all=args.uniform_all)
    z = generate_community_vector(
        args.num_vertices, args.communities, shuffle=False)

    sbm = tadcsbm_simulator(
        snapshots=args.snapshots,
        num_vertices=args.num_vertices,
        num_edges=args.num_edges,
        pi=[v/len(z) for _, v in Counter(z).items()],
        prop_mat=mat,
        tau_mat=tau,
        num_feature_groups=args.feature_groups or args.communities,
        feature_dim=args.feature_dim,
        feature_center_distance=args.feature_center_distance,
        feature_cluster_variance=args.feature_cluster_variance,
        edge_feature_dim=args.edge_feature_dim,
        edge_center_distance=args.edge_center_distance,
        edge_cluster_variance=args.edge_cluster_variance,
        fixed_probabilities=args.fixed_probabilities,
        reverse_snapshot_order=args.reverse_snapshot_order,
        edge_sampling_rate=args.edge_sampling_rate,
        random_seed=args.random_seed,
    )

    # Compose graph-tool graphs as a single NetworkX multigraph.
    print("Composing graph snapshots...", end="\r")
    TG = gt_to_nx_temporal(sbm.graph)

    # Save graph as compressed file and node and edge features as NumPy arrays.
    print("Saving graph snapshots...", end="\r")
    tx.write_graph(TG, f"{args.output_dir}/graphs.{args.output_ext}.zip")
    if args.feature_dim > 0:
        print("Saving node features...", end="\r")
        np.save(f"{args.output_dir}/features_node.npy", sbm.node_features1)
    if args.edge_feature_dim > 0:
        print("Saving edge features...", end="\r")
        np.save(f"{args.output_dir}/features_edge.npy", sbm.edge_features)

    print(TG)
    if args.verbose:
        V, E, T = 0, 0, 0

        p = np.diag(mat).mean()
        q = mat[~np.eye(mat.shape[0], dtype=bool)].sum()/mat.shape[0]

        ratios = []
        expected_ratio = p / q if q > 0 else 1

        for i, (g, memberships) in enumerate(zip(sbm.graph, sbm.graph_memberships)):
            V += g.num_vertices()
            E += g.num_edges()
            T += np.sum(memberships != sbm.graph_memberships[i-1]) if i > 0 else 0

            D = {}
            for (u, v) in TG[i].edges():
                c_u = TG[i].nodes[u]["community"]
                c_v = TG[i].nodes[v]["community"]
                D[c_u == c_v] = D.get(c_u == c_v, 0) + 1

            within = sum(v for k, v in D.items() if k is True)
            between = sum(v for k, v in D.items() if k is False)
            ratio = within / between if between > 0 else 1
            ratios.append(ratio)

            print(f"- Snapshot {i+1}/{len(sbm.graph)}: "
                  f"{g.num_vertices()} nodes, {g.num_edges()} edges, "
                  f"communities: {np.bincount(memberships)}, "
                  f"within-/between-edge ratio: {ratio:.2f}")

        print(f"Total nodes across snapshots: {V}",
              f"\nTotal edges across snapshots: {E}",
              f"\nTotal transitions across snapshots: {T} ({T/(V-g.num_vertices()):.2%})",
              f"\nAverage within/between ratio across snapshots: {np.mean(ratios):.2f}",
              f"\nExpected within/between ratio (p/q) overall: {expected_ratio:.2f}")
