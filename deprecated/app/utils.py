import os

import pandas as pd
import yaml
from pandas import DataFrame

from app.api.exceptions import PoloniexError
from app.config import Config


def load_config(path: str) -> Config:
    """
      Сереализация конфигурации в формате .yaml
    :param path: путь до конфиги
    :return:
    """
    try:

        with open(file=path, mode="r", encoding="utf-8") as fh:
            return Config(**yaml.safe_load(fh))

    except (yaml.YAMLError, FileNotFoundError) as exc:
        print(exc)


def load_df_from_json(file_path) -> DataFrame:
    if not os.path.exists(file_path):
        raise PoloniexError(
            "File path does not exist, should not be trying to load DF."
        )
    df = pd.read_json(file_path, orient="index", convert_dates=False)
    df.index.name = "period"
    df.index = df.index.astype(str)
    return df


__all__ = ["load_config"]
