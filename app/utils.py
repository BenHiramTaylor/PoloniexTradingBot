import yaml

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


__all__ = ["load_config"]
