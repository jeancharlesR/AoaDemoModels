from teradataml import create_context
from tdextensions.distributed import DistDataFrame, DistMode
from teradataml.dataframe.dataframe import DataFrame

import base64
import dill
import os
import numpy as np
import json


def score(data_conf, model_conf, **kwargs):
    """Python score method called by AOA framework batch mode

    Parameters:
    data_conf (dict): The dataset metadata
    model_conf (dict): The model configuration to use

    Returns:
    None:No return

    """


def save_metadata(df):
    # convert stats to dict and save to partitions.json
    metadata_df = df.select(["partition_id", "partition_metadata", "num_rows"]).to_pandas()
    metadata_dict = {r["partition_id"]: json.loads(r["partition_metadata"]) for r in
                     metadata_df.to_dict(orient='records')}

    with open("artifacts/output/partitions.json", 'w+') as f:
        json.dump(metadata_dict, f, indent=2)

    data_metadata = {
        "num_rows": int(metadata_df["num_rows"].sum())
    }

    with open("artifacts/output/data_stats.json", 'w+') as f:
        json.dump(data_metadata, f, indent=2)

    print("Finished saving artefacts")


def evaluate(data_conf, model_conf, **kwargs):
    model_version = kwargs["model_version"]

    create_context(host="host.docker.internal", username=os.environ['TD_USERNAME'], password=os.environ['TD_PASSWORD'])

    df = DataFrame.from_query("""
    SELECT i.*, m.model_artefact FROM iris_train i 
        LEFT JOIN aoa_sto_models m ON i.species = m.partition_id 
        WHERE model_version='{}'
    """.format(model_version))

    def eval_partition(partition):

        # do evaluation

        partition_id = partition.species.iloc[0]

        # whatever evaluation metadata you want to record goes here. Like the evaluation metrics, etc
        partition_metadata = json.dumps({
            "num_rows": partition.shape[0],
            "metrics": {
                "accuracy": 0.9,
                "precision": 0.87
            }
        })

        return np.array([[partition_id, partition.shape[0], partition_metadata]])

    df = DistDataFrame(df._table_name, dist_mode=DistMode.STO, sto_id="my_model")
    eval_df = df.map_partition(lambda partition: eval_partition(partition),
                               partition_by="species",
                               returns=[["partition_id", "VARCHAR(255)"],
                                        ["num_rows", "BIGINT"],
                                        ["partition_metadata", "CLOB"]])

    save_metadata(eval_df)
