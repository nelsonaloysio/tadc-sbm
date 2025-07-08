#!/usr/bin/env python

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
from sys import argv

import networkx as nx
import numpy as np
import torch
from torch_geometric.utils import from_networkx

from tadcsbm import (
    tadcsbm_simulator,
    generate_block_matrix,
    generate_transition_matrix,
    # generate_degree_vector,
    generate_community_vector,
    gt_to_nx,
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
                        dest="k",
                        type=int,
                        required=True,
                        help="Number of communities")

    parser.add_argument("-t", "--snapshots",
                        type=int,
                        default=1,
                        help="Number of snapshots")

    # parser.add_argument("--min-deg",
    #                     type=int,
    #                     help="Minimum expected vertex degree")

    # parser.add_argument("--max-deg",
    #                     type=int,
    #                     help="Maximum expected vertex degree")

    parser.add_argument("--eta",
                        type=float,
                        default=1.0,
                        help="Transition probability factor (0.0 to 1.0)")

    parser.add_argument("--gamma",
                        type=int,
                        choices=[0, 1],
                        default=0,
                        dest="fixed_probabilities",
                        help="Fix transition probabilities (default: 0 for current memberships)")

    parser.add_argument("--beta",
                        type=float,
                        default=1.0,
                        dest="edge_sampling_rate",
                        help="Edge sampling rate (0.0 to 1.0)")

    parser.add_argument("--feature-dim",
                        type=int,
                        default=None,
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
                        help="Number of feature groups (default: k)")

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

    parser.add_argument("--fix-probabilities",
                        action="store_true",
                        dest="fixed_probabilities",
                        help="Use fixed transition probabilities (default: False)")

    parser.add_argument("--no-reverse",
                        action="store_false",
                        dest="reverse_snapshot_order",
                        help="Keep the generation order of snapshots (default: reversed)")

    parser.add_argument("--uniform-all",
                        action="store_true",
                        help="Uniform transition probabilities (i.e., including current community)")

    return parser.parse_args(args)


if __name__ == "__main__":
    args = getargs()

    mat = generate_block_matrix(args.k)
    tau = generate_transition_matrix(args.k, args.eta, uniform_all=args.uniform_all)
    # deg = generate_degree_vector(args.num_vertices, args.min_deg, args.max_deg, shuffle=True)
    z = generate_community_vector(args.num_vertices, args.k, shuffle=False)

    sbm = tadcsbm_simulator(
        snapshots=args.snapshots,
        num_vertices=args.num_vertices,
        num_edges=args.num_edges,
        # num_edges=sum(deg),
        pi=[v/len(z) for k, v in Counter(z).items()],
        prop_mat=mat,
        tau_mat=tau,
        num_feature_groups=args.feature_groups or args.k,
        feature_dim=args.feature_dim,
        feature_center_distance=args.feature_center_distance,
        feature_cluster_variance=args.feature_cluster_variance,
        edge_feature_dim=args.edge_feature_dim,
        edge_center_distance=args.edge_center_distance,
        edge_cluster_variance=args.edge_cluster_variance,
        fixed_probabilities=args.fixed_probabilities,
        reverse_snapshot_order=args.reverse_snapshot_order,
        edge_sampling_rate=args.edge_sampling_rate,
    )

    # Compose graph-tool graphs as a single NetworkX multigraph.
    # list(graph.save(f"output/snapshot_t={t}.graphml") for t, graph in enumerate(sbm.graph))
    G = nx.compose_all([gt_to_nx(graph, time=t) for t, graph in enumerate(sbm.graph)])
    nx.set_node_attributes(G, {v: y for v, y in zip(G.nodes(), sbm.graph_memberships)}, "y")
    nx.write_graphml(G, "output/graph.graphml")

    # Save node and edge features as NumPy arrays.
    np.save("output/features_node.npy", sbm.node_features1)
    if args.edge_feature_dim > 0:
        np.save("output/features_edge.npy", sbm.edge_features)

    # Set node and edge attributes in the NetworkX graph.
    nx.set_node_attributes(G, {v: x for v, x in zip(G.nodes(), sbm.node_features1)}, "x")
    if args.edge_feature_dim > 0:
        nx.set_node_attributes(G, {e: x for e, x in zip(G.edges(), sbm.edge_features)}, "edge_attr")

    # Save as PyTorch Geometric data object.
    data = from_networkx(G)
    torch.save(data, "output/data.pt")

    print(G)
    print(data)
