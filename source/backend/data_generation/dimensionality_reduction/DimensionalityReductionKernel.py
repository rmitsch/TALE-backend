import os
import itertools
from tables import *
import numpy
from MulticoreTSNE import MulticoreTSNE
from sklearn.decomposition import TruncatedSVD
import umap

from . import hdf5_descriptions


class DimensionalityReductionKernel:
    """
    Represents an instance of a dimensionality reduction method.
    Currently supported: TSNE, SVD and UMAP.
    """
    # Supported dimensionality reduction algorithms and their parameters.
    # Note that the
    DIM_RED_KERNELS = {
        "TSNE": {
            "parameters": [
                {"name": "n_components", "type": "numeric", "values": [1, 2]},
                {"name": "perplexity", "type": "numeric", "values": [10, 25]},
                {"name": "early_exaggeration", "type": "numeric", "values": [5, 10]},
                {"name": "learning_rate", "type": "numeric", "values": [10, 250]},
                {"name": "n_iter", "type": "numeric", "values": [100, 250, 500]},
                {"name": "angle", "type": "numeric", "values": [0.1, 0.35]},
                {"name": "metric", "type": "categorical", "values": ['cosine', 'euclidean']}
            ],
            "hdf5_description": hdf5_descriptions.TSNEDescription
        },
        "SVD": {
            "parameters": [
                {"name": "n_components", "type": "numeric", "values": [1, 2]},
                {"name": "n_iter", "type": "numeric", "values": [5, 10, 20]},
                {"name": "metric", "type": "categorical", "values": ['cosine', 'euclidean']}
            ],
            "hdf5_description": hdf5_descriptions.SVDDescription
        },
        "UMAP": {
            "parameters": [
                {"name": "n_components", "type": "numeric", "values": [1, 2]},
                {"name": "n_neighbors", "type": "numeric", "values": [5, 15]},
                {"name": "n_epochs", "type": "numeric", "values": [200, 400]},
                {"name": "learning_rate", "type": "numeric", "values": [0.5, 1]},
                {"name": "min_dist", "type": "numeric", "values": [0.05, 0.1]},
                {"name": "local_connectivity", "type": "numeric", "values": [1, 5]},
                {"name": "metric", "type": "categorical", "values": ['cosine', 'euclidean']}
            ],
            "hdf5_description": hdf5_descriptions.UMAPDescription
        }
    }

    def __init__(self, dim_red_kernel_name: str):
        """
        Initializes new DimensionalityReductionKernel.
        :param dim_red_kernel_name:
        """

        self._dim_red_kernel_name = dim_red_kernel_name
        self._high_dim_data = None
        self._parameter_set = None

    def run(self, high_dim_data: numpy.ndarray, parameter_set: dict):
        """
        Applies chosen DR kernel on specified high dimensional data set with this parametrization.
        :param high_dim_data:
        :param parameter_set:
        :return: Low-dimensional projection of high-dimensional data.
        """

        self._high_dim_data = high_dim_data
        self._parameter_set = parameter_set

        ###################################################
        # Calculate low-dim. projection.
        ###################################################

        if self._dim_red_kernel_name == "TSNE":
            return MulticoreTSNE(
                n_components=parameter_set["n_components"],
                perplexity=parameter_set["perplexity"],
                early_exaggeration=parameter_set["early_exaggeration"],
                learning_rate=parameter_set["learning_rate"],
                n_iter=parameter_set["n_iter"],
                angle=parameter_set["angle"],
                # Always set metric to 'precomputed', since distance matrices are calculated previously. If other
                # metrics are desired, the corresponding preprocessing step has to be extended.
                metric='precomputed',
                method='barnes_hut' if parameter_set["n_components"] < 4 else 'exact',
                # Set n_jobs to 1, since we parallelize at a higher level by splitting up model parametrizations amongst
                # threads.
                n_jobs=1
            ).fit_transform(high_dim_data)

        elif self._dim_red_kernel_name == "SVD":
            return TruncatedSVD(
                n_components=parameter_set["n_components"],
                n_iter=parameter_set["n_iter"]
            ).fit_transform(high_dim_data)

        elif self._dim_red_kernel_name == "UMAP":
            return umap.UMAP(
                n_components=parameter_set["n_components"],
                n_neighbors=parameter_set["n_neighbors"],
                n_epochs=parameter_set["n_epochs"],
                learning_rate=parameter_set["learning_rate"],
                min_dist=parameter_set["min_dist"],
                spread=parameter_set["spread"],
                # Always set metric to 'precomputed', since distance matrices are calculated previously. If other
                # metrics are desired, the corresponding preprocessing step has to be extended.
                metric='precomputed',
            ).fit_transform(high_dim_data)

        return None

    @staticmethod
    def generate_parameter_sets_for_testing(data_file_path: str, dim_red_kernel_name: str):
        """
        Generates parameter sets for testing. Intervals and records are hardcoded.
        Ignores records already in specified file.
        :param data_file_path: Path to file holding all records generated so far.
        :param dim_red_kernel_name: Name of dimensionality reduction kernel used for file.
        :return:
        """

        parameter_sets = []
        parameter_config = DimensionalityReductionKernel.DIM_RED_KERNELS[dim_red_kernel_name]["parameters"]
        existent_parameter_sets = []

        ###############################################
        # 1. Load already existent parameter sets.
        ###############################################
        if os.path.isfile(data_file_path):
            h5file = open_file(filename=data_file_path, mode="r+")
            # Note: We don't use the model ID here, since that would never lead to comparison hits.
            existent_parameter_sets = [
                {
                    # Parse as UTF-8 string, if parameter is categorical.
                    param_config["name"]:
                        row[param_config["name"]] if param_config["type"] is not "categorical"
                        else str(row[param_config["name"]], "utf-8")
                    for param_config in parameter_config
                }
                for row in h5file.root.metadata
            ]
            # Close file after reading parameter set data.
            h5file.close()

        ###############################################
        # 2. Produce all parameter combinations as
        #    Cartesian prodcut.
        ###############################################

        parameter_combinations = [
            combination for combination in itertools.product(*[
                param_desc["values"] for param_desc in parameter_config
            ])
        ]

        ###############################################
        # 3. Recast paramter combination lists as
        #    dicts.
        ###############################################

        current_id = 0
        for parameter_combination in parameter_combinations:
            parameter_set = {
                parameter_config[i]["name"]: parameter_combination[i]
                for i in range(0, len(parameter_combination))
            }

            # Filter out already existing model parametrizations.
            if parameter_set not in existent_parameter_sets:
                parameter_set["id"] = current_id
                parameter_sets.append(parameter_set)

            # Keep track of number of generated parameter sets.
            current_id += 1

        return parameter_sets

    @staticmethod
    def get_metric_values(dim_red_kernel_name: str):
        """
        Auxiliary function to retrieve possible values for attribute "metric" in specified dim. red. kernel.
        :param dim_red_kernel_name:
        :return:
        """
        for param_desc in DimensionalityReductionKernel.DIM_RED_KERNELS[dim_red_kernel_name]["parameters"]:
            if param_desc["name"] == "metric":
                return param_desc["values"]

        return None