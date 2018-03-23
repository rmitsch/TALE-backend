import threading
import time
import numpy
from MulticoreTSNE import MulticoreTSNE

from backend.data_generation import InputDataset
from backend.objectives.topology_preservation_objectives import *
from backend.objectives.distance_preservation_objectives import *


class TSNEThread(threading.Thread):
    """
    Class calculating a t-SNE model for the given distance matrix with the specified parametrizations.
    """

    def __init__(
            self,
            results: list,
            distance_matrices: dict,
            parameter_sets: list,
            high_dim_dataset: InputDataset,
            high_dimensional_neighbourhood_rankings: dict
    ):
        """
        Initializes thread instance that will calculate the low-dimensional representation of the specified distance
        matrices applying t-SNE.
        :param results:
        :param distance_matrices:
        :param parameter_sets:
        :param high_dimensional_data:
        :param labels: List of class labels for dataset.
        :param high_dimensional_neighbourhood_rankings: Neighbourhood rankings in original high-dimensional space. Dict.
        with one entry per distance metric.
        """
        threading.Thread.__init__(self)

        self._distance_matrices = distance_matrices
        self._parameter_sets = parameter_sets
        self._results = results
        self._high_dim_dataset = high_dim_dataset
        self._high_dimensional_neighbourhood_rankings = high_dimensional_neighbourhood_rankings

    def run(self):
        """
        Runs thread and calculates all t-SNE models specified in parameter_sets.
        :return: List of 2D-ndarrays containing coordinates of instances in low-dimensional space.
        """

        ###################################################
        # 1. Calculate embedding for each distance metric.
        ###################################################

        for parameter_set in self._parameter_sets:
            metric = parameter_set["metric"]

            # Calculate t-SNE.
            start = time.time()
            low_dimensional_projection = MulticoreTSNE(
                n_components=parameter_set["n_components"],
                perplexity=parameter_set["perplexity"],
                early_exaggeration=parameter_set["early_exaggeration"],
                learning_rate=parameter_set["learning_rate"],
                n_iter=parameter_set["n_iter"],
                # min_grad_norm=parameter_set["min_grad_norm"],
                angle=parameter_set["angle"],
                # Always set metric to 'precomputed', since distance matrices are calculated previously. If other
                # metrics are desired, the corresponding preprocessing step has to be extended.
                metric='precomputed',
                method='barnes_hut' if parameter_set["n_components"] < 4 else 'exact',
                # Set n_jobs to 1, since we parallelize at a higher level by splitting up model parametrizations amongst
                # threads.
                n_jobs=1
            ).fit_transform(self._distance_matrices[metric])

            ###################################################
            # 2. Calculate objectives.
            ###################################################

            # Start measuring runtime.
            runtime = time.time() - start

            # Define neighbourhood interval to be considered (if relevant).
            k_neighbourhood_interval = (2, 5)

            ############################################
            # 2. a. Topology-based metrics.
            ############################################

            # Create coranking matrix for topology-based objectives.
            coranking_matrix = CorankingMatrix(
                low_dimensional_data=low_dimensional_projection,
                high_dimensional_data=self._distance_matrices[metric],
                distance_metric=metric,
                high_dimensional_neighbourhood_ranking=self._high_dimensional_neighbourhood_rankings[metric]
            )

            # R_nx.
            r_nx = CorankingMatrixQualityCriterion(
                high_dimensional_data=self._distance_matrices[metric],
                low_dimensional_data=low_dimensional_projection,
                distance_metric=metric,
                coranking_matrix=coranking_matrix,
                k_interval=k_neighbourhood_interval
            ).compute()

            # B_nx.
            b_nx = CorankingMatrixQualityCriterion(
                high_dimensional_data=self._distance_matrices[metric],
                low_dimensional_data=low_dimensional_projection,
                distance_metric=metric,
                coranking_matrix=coranking_matrix,
                k_interval=(2, 5)
            ).compute()

            ############################################
            # 2. b. Distance-based metrics.
            ############################################

            stress = Stress(
                high_dimensional_data=self._distance_matrices[metric],
                low_dimensional_data=low_dimensional_projection,
                distance_metric=metric,
                use_geodesic_distances=False
            ).compute()

            ############################################
            # 2. c. Information-preserving metrics.
            ############################################

            classification_accuracy = 0

            ############################################
            # 2. d. Separability metrics.
            ############################################

            adjusted_mutual_information = 0

            ###################################################
            # 3. Collect data, terminate.
            ###################################################

            # Append runtime to set of objectives.
            objectives = {
                "runtime": runtime,
                "r_nx": r_nx,
                "b_nx": b_nx,
                "stress": stress,
                "classification_accuracy": classification_accuracy,
                "adjusted_mutual_information": adjusted_mutual_information
            }

            # Store parameter set, objective set and low dimensional projection in globally shared object.
            self._results.append({
                "parameter_set": parameter_set,
                "objectives": objectives,
                "low_dimensional_projection": low_dimensional_projection
            })
