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

import networkx as nx
import networkx_temporal as tx
import numpy as np
# import torch
# from torch_geometric.utils import from_networkx

from .tadcsbm_simulator import tadcsbm_simulator
from .utils import (
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
                        dest="communities",
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
                        help="Community stability factor (0.0 to 1.0)")

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

    parser.add_argument("--no-reverse",
                        action="store_false",
                        dest="reverse_snapshot_order",
                        help="Keep the generation order of snapshots (default: reversed)")

    parser.add_argument("--uniform-all",
                        action="store_true",
                        help="Uniform transition probabilities (i.e., including current community)")

    parser.add_argument("--dir", "--output-dir",
                        type=str,
                        dest="output_dir",
                        default="output",
                        help="Directory to save output files (default: 'output')")

    parser.add_argument("--ext", "--output-ext",
                        type=str,
                        dest="output_ext",
                        default="graphml",
                        help="Extension for output files (default: 'graphml')")

    return parser.parse_args(args)


def main():
    args = getargs()

    if not isdir(args.output_dir):
        mkdir(args.output_dir)

    mat = generate_block_matrix(args.communities)
    tau = generate_transition_matrix(args.communities, args.eta, uniform_all=args.uniform_all)
    # deg = generate_degree_vector(num_vertices, min_deg, max_deg, shuffle=True)
    z = generate_community_vector(args.num_vertices, args.communities, shuffle=False)

    sbm = tadcsbm_simulator(
        snapshots=args.snapshots,
        num_vertices=args.num_vertices,
        num_edges=args.num_edges,
        # num_edges=sum(deg),
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
    )

    # Compose graph-tool graphs as a single NetworkX multigraph.
    print("Composing graph snapshots...", end="\r")
    TG = tx.from_snapshots([gt_to_nx(graph, time=t) for t, graph in enumerate(sbm.graph)])

    # Set node attributes for community memberships and save to disk.
    print("Setting node memberships...", end="\r")
    list(nx.set_node_attributes(G, {v: y for v, y in zip(G.nodes(), sbm.graph_memberships)}, "y") for G in TG)

    # Save node and edge features as NumPy arrays.
    if args.feature_dim > 0:
        print("Saving node features...", end="\r")
        np.save(f"{args.output_dir}/features_node.npy", sbm.node_features1)
    if args.edge_feature_dim > 0:
        print("Saving edge features...", end="\r")
        np.save(f"{args.output_dir}/features_edge.npy", sbm.edge_features)

    # Save the composed graph to disk.
    print(f"Saving graph files to {args.output_dir}...", end="\r")
    tx.write_graph(TG, f"{args.output_dir}/graphs.{args.output_ext}.zip")
    tx.write_graph(TG.to_static(), f"{args.output_dir}/graph.{args.output_ext}.zip")
    print(TG)

    # Set node and edge attributes in the NetworkX graph.
    # print("Setting node and edge attributes...", end="\r")
    # if feature_dim > 0:
    #     nx.set_node_attributes(G, {v: x for v, x in zip(G.nodes(), sbm.node_features1)}, "x")
    # if edge_feature_dim > 0:
    #     nx.set_edge_attributes(G, {e: x for e, x in zip(G.edges(), sbm.edge_features)}, "edge_attr")

    # Save as PyTorch Geometric data object.
    # data = from_networkx(G)
    # torch.save(data, f"{output_dir}/data.pt")
    # print(data)
