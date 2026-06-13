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

import numpy as np

try:
    import graph_tool as gt
except ImportError as e:
    raise ImportError(
      "graph-tool is required to run the TADC-SBM simulator; for installation instructions, see:\n"
      "> https://graph-tool.skewed.de/installation.html"
    ) from e

from .simulations import (
    StochasticBlockModel,
    SimulateSbm,
    SimulateFeatures,
    SimulateEdgeFeatures,
    GetPropMat,
    MatchType,
)


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
    random_seed = None,
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
        random_seed: (int) random seed for reproducibility.

    Returns:
        result: a StochasticBlockModel data class.

    Raises:
        ValueError: if neither of prop_mat or edge_probability_profile are provided.
    """
    if random_seed is not None:
        gt.seed_rng(random_seed)
        np.random.seed(random_seed)

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

    print("Simulating SBM...", end="\r")
    SimulateSbm(sbm,
                num_vertices,
                num_edges,
                pi,
                prop_mat,
                out_degs,
                pi2)

    sbm.graph.vp["community"] = sbm.graph.new_vp(
        "int32_t",
        vals=np.asarray(sbm.graph_memberships, dtype=np.int32)
    )

    if feature_dim > 0:
        print("Simulating node features...", end="\r")
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
        print("Simulating edge features...", end="\r")
        SimulateEdgeFeatures(
                sbm,
                edge_feature_dim,
                edge_center_distance,
                edge_cluster_variance)

    graph = []
    graph.append(sbm.graph.copy())
    graph_memberships = [sbm.graph_memberships.copy()]

    # Simulate snapshots with node transitions according to fixed_probabiltiies (gamma parameter).
    for t in range(snapshots-1):
        print(f"Simulating snapshot {t+2}/{snapshots}...", end="\r")
        SimulateSbm(
            sbm,
            num_vertices,
            num_edges,
            pi,
            prop_mat,
            out_degs,
            pi2,
            tau_mat=tau_mat,
            graph_memberships=graph_memberships[0 if fixed_probabilities else -1],
        )
        # Store graph and memberships for current snapshot.
        graph.append(sbm.graph.copy())
        graph_memberships.append(sbm.graph_memberships.copy())
        # Store community memberships as vertex property maps in graph object.
        graph[-1].vp["community"] = graph[-1].new_vp(
            "int32_t",
            vals=np.asarray(graph_memberships[-1], dtype=np.int32)
        )

    # Build node index for edge sampling with isolate removal.
    for t, g in enumerate(graph):
        orig_idx = g.new_vp("int64_t")
        orig_idx.a = np.arange(g.num_vertices(), dtype=np.int64)
        g.vp["orig_idx"] = orig_idx
        # Sample edges according to edge_sampling_rate (beta parameter).
        if edge_sampling_rate < 1.0:
            print(f"Edge sampling snapshot {t + 1}/{snapshots}...", end="\r")
            # If there are no edges, skip sampling to avoid errors.
            n_edges = g.num_edges()
            if n_edges == 0:
                continue
            # Sample which edges to keep.
            keep_mask = np.random.random(n_edges) < edge_sampling_rate
            if np.all(keep_mask):
                continue
            # Get edge indices, create a boolean mask of edges to keep and apply it to the graph.
            edge_idx = g.get_edges([g.edge_index])[:, 2]
            keep = g.new_ep("bool", val=True)
            keep.a[edge_idx] = keep_mask
            g.set_edge_filter(keep)
            g.purge_edges()
            g.clear_filters()
            # Get node isolates after edge sampling and remove them.
            is_not_isolate = g.new_vp("bool")
            is_not_isolate.a = g.degree_property_map("total").a > 0
            g.set_vertex_filter(is_not_isolate)
            g.purge_vertices()
            g.clear_filters()

    sbm.graph = (
        graph[::-1] if reverse_snapshot_order else graph)
    sbm.graph_memberships = (
        graph_memberships[::-1] if reverse_snapshot_order else graph_memberships)

    return sbm
