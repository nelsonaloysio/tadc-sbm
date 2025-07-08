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

# from collections import Counter

import numpy as np

from .simulations import (
    StochasticBlockModel,
    SimulateSbm,
    SimulateFeatures,
    SimulateEdgeFeatures,
    GetPropMat,
    MatchType,
)

__version__ = "0.1.0"


def tadcsbm_simulator(
    num_vertices,
    num_edges,
    pi,
    snapshots = 1,
    prop_mat = None,
    tau_mat = None,
    out_degs = None,
    feature_center_distance = 0.0,
    feature_dim = 0,
    num_feature_groups = None,
    feature_group_match_type = MatchType.RANDOM,
    feature_cluster_variance = 1.0,
    edge_feature_dim = 0,
    edge_center_distance = 0.0,
    edge_cluster_variance = 1.0,
    pi2 = None,
    feature_center_distance2 = 0.0,
    feature_dim2 = 0,
    feature_type_correlation = 0.0,
    feature_type_center_distance = 0.0,
    edge_probability_profile = None,
    reverse_snapshot_order = True,
    fixed_probabilities = False,
    edge_sampling_rate = 1.0,
):
    """Generates stochastic block model (SBM) with node features.

    Args:
        num_vertices: number of nodes in the graph.
        num_edges: expected number of edges in the graph.
        pi: iterable of non-zero community size relative proportions. Community i
            will be pi[i] / pi[j] times larger than community j.
        prop_mat: square, symmetric matrix of community edge count rates. Example:
            if diagonals are 2.0 and off-diagonals are 1.0, within-community edges are
            twices as likely as between-community edges.
        tau_mat: square, symmetric matrix of community transition probabilities.
        out_degs: Out-degree propensity for each node. If not provided, a constant
            value will be used. Note that the values will be normalized inside each
            group, if they are not already so.
        feature_center_distance: distance between feature cluster centers. When this
            is 0.0, the signal-to-noise ratio is 0.0. When equal to
            feature_cluster_variance, SNR is 1.0.
        feature_dim: dimension of node features.
        num_feature_groups: number of feature clusters. This is ignored if
            num_vertices2 is provided, as the internal feature generators will assume
            a heterogeneous SBM model, which does not support differing # feature
            clusters from # graph clusters. In this case, # feature clusters
            will be set equal to # graph clusters. If left as default (None),
            and input sbm_data is homogeneous, set to len(pi1).
        feature_group_match_type: see MatchType.
        feature_cluster_variance: variance of feature clusters around their centers.
            centers. Increasing this weakens node feature signal.
        edge_feature_dim: dimension of edge features.
        edge_center_distance: per-dimension distance between the intra-class and
            inter-class means. Increasing this strengthens the edge feature signal.
        edge_cluster_variance: variance of edge clusters around their centers.
            Increasing this weakens the edge feature signal.
        pi2: This is the pi vector for the vertices of type 2. Type 2 community k
            will be pi2[k] / pi[j] times larger than type 1 community j. Supplying
            this argument produces a heterogeneous model.
            feature_center_distance2: feature_center_distance for type 2 nodes. Not used
            if len(pi2) = 0.
        feature_dim2: feature_dim for nodes of type 2. Not used if len(pi2) = 0.
        feature_type_correlation: proportion of each cluster's center vector that
            is shared with other clusters linked across types. Not used if len(pi2) =
            0.
        feature_type_center_distance: the variance of the generated centers for
            feature vectors that are shared across types. Not used if len(pi2) = 0.
        edge_probability_profile: This can be provided instead of prop_mat. If
            provided, prop_mat will be built according to the input p-to-q ratios. If
            prop_mat is provided, it will be preferred over this input.
        fixed_probabilities: (bool) if True, the node transition probabilities are
            assumed to be fixed over time, i.e., the same for every snapshot.
        reverse_snapshot_order: if True, the snapshots will be reversed in the output
            graph list. This is useful for training temporal-aware models.
        edge_sampling_rate: (float) rate at which edges are sampled. This is a
            multiplier on the expected number of edges, upper bounded by 1.0.
            For example, if this is 0.5, the expected number of edges will be
            num_edges * 0.5, and the actual number of edges will be sampled from a
            binomial distribution with that expected number of edges. This is useful
            for generating sparser graphs and benchmarking link prediction models.

    Returns:
        result: a StochasticBlockModel data class.

    Raises:
        ValueError: if neither of prop_mat or edge_probability_profile are provided.
    """
    sbm = StochasticBlockModel()

    if prop_mat is None and edge_probability_profile is None:
        raise ValueError(
            "One of prop_mat or edge_probability_profile must be provided.")

    if prop_mat is None and edge_probability_profile is not None:
        prop_mat = GetPropMat(
            num_clusters1=len(pi),
            p_to_q_ratio1=edge_probability_profile.p_to_q_ratio1,
            num_clusters2=0 if pi2 is None else len(pi2),
            p_to_q_ratio2=edge_probability_profile.p_to_q_ratio2,
            p_to_q_ratio_cross=edge_probability_profile.p_to_q_ratio_cross)

    SimulateSbm(sbm,
                num_vertices,
                num_edges,
                pi,
                prop_mat,
                out_degs,
                pi2)

    SimulateFeatures(
                sbm,
                feature_center_distance,
                feature_dim,
                num_feature_groups,
                feature_group_match_type,
                feature_cluster_variance,
                feature_center_distance2,
                feature_dim2,
                feature_type_correlation,
                feature_type_center_distance)

    if edge_feature_dim > 0:
        SimulateEdgeFeatures(
                sbm,
                edge_feature_dim,
                edge_center_distance,
                edge_cluster_variance)

    graph = []
    graph.append(sbm.graph.copy())
    graph_memberships = sbm.graph_memberships.copy()

    for t in range(snapshots):
        if not fixed_probabilities:
            graph_memberships = sbm.graph_memberships.copy()
        SimulateSbm(
            sbm,
            num_vertices,
            num_edges,
            pi,
            prop_mat,
            out_degs,
            pi2,
            tau_mat=tau_mat,
            graph_memberships=graph_memberships,
            )
        graph.append(sbm.graph.copy())
        # counter = Counter(list(sbm.graph_memberships))
        # counter = {k: counter[k] for k in sorted(counter)}
        # print(f"Snapshot {(snapshots-t-1) if reverse_snapshot_order else t}: {counter}")

    if edge_sampling_rate < 1.0:
        for g in graph:
            for e in g.edges():
                g.remove_edge(e) if np.random.random() < edge_sampling_rate else None

    sbm.graph = graph[::-1] if reverse_snapshot_order else graph
    return sbm
