from teradataml import create_context
from tdextensions.distributed import DistDataFrame, DistMode
from teradataml.dataframe.dataframe import DataFrame
from .util import save_metadata

import random
import os
import numpy as np
import json


def score(data_conf, model_conf, **kwargs):
    pass


def eval_partition(partition):

    # do evaluation

    partition_id = partition.species.iloc[0]

    # whatever evaluation metadata you want to record goes here. Like the evaluation metrics, etc
    partition_metadata = json.dumps({
        "num_rows": partition.shape[0],
        "metrics": {
            "accuracy": random.uniform(60.0, 95.0),
            "precision": random.uniform(60.0, 95.0)
        }
    })

    return np.array([[partition_id, partition.shape[0], partition_metadata]])


def evaluate(data_conf, model_conf, **kwargs):
    model_version = kwargs["model_version"]

    create_context(host="host.docker.internal", username=os.environ['TD_USERNAME'], password=os.environ['TD_PASSWORD'])

    df = DataFrame.from_query("""
    SELECT i.*, m.model_artefact FROM iris_train i 
        LEFT JOIN aoa_sto_models m ON i.species = m.partition_id 
        WHERE model_version='{}'
    """.format(model_version))

    df = DistDataFrame(df._table_name, dist_mode=DistMode.STO, sto_id="my_model")
    eval_df = df.map_partition(lambda partition: eval_partition(partition),
                               partition_by="species",
                               returns=[["partition_id", "VARCHAR(255)"],
                                        ["num_rows", "BIGINT"],
                                        ["partition_metadata", "CLOB"]])

    eval_df.to_sql("aoa_sto_models", if_exists="append")

    save_metadata(eval_df)
