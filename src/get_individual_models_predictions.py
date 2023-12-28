# Сейчас предсказания отдельных моделей сохраняются как список списков
# кортежей (-log(prob), pred_word).  Пусть модель заточена под раскладку
# клавиатуры grid_name.  Пусть dataset[grid_name] – это датасет,
# сохраняющий порядок исходного датасета, но исключающий все экземпляры
# с другой раскладкой.  Пусть предсказание хранится в переменной preds.
# Тогда preds[i] - это список предсказаний для кривой dataset[grid_name][i].
# Данный список представлен кортежами (-log(prob), pred_word).




# Итак, у на входе у нас есть:
# * модели, от которых мы хотим получить предсказания. Модели имеют:
#   * название раскладки
#   * название архитктуры
#   * путь к весам
# * датасет в виде JSON, для которого хотим получить предсказания
#
#
# Гипотетически могут быть модели, умеющие работать сразу с множеством раскладок.
#
# Мы хотим получить предсказания пригодные для дальнейшей аггрегации,
# а также для подсчета метрик в случае наличия refs.
#
#
# Сейчас я вижу три варианта представдения предсказаний: 
# 1. список предсказаний длиной с исходный датасет. Для строк с расскаладками,
#       с которыми модель не умеет работать она предсказывает пустой список.
# 2. список предсказаний длиной с число элементов данной раскладки.
# 3. словарь длиной с число элементов данной раскладки 
#       `индекс в исходном датасете` -> список предсказаний для данной кривой.
#       Сюда же отнесу вариант, где предсказания представлены списком, каждый
#       элемент которого - кортеж (номер_строки_в_исходном_датасете, список_предсказаний).
# Также может быть добавлена метаинформация:
# * название архтиектуры
# * путь к весам
# * название раскладки
# * список индексов
#
#
# Вариант, когда каждая модель выдает все 10_000 строк кажется
# не совсем удобным: Когда мы подбираем наилучшие гиперпараметры
# для аггрегации, удобно оценивать гиперпараметры по результатам
# метрик именно на данной раскладке.
# 
#
# Если предсказания были получены для валидационного датасета, хочется уметь
# Считать метрики. 




from typing import Callable, List, Dict
import os
import json
import pickle
import argparse

import torch
from torch.utils.data import Dataset
from tqdm import tqdm

from model import get_m1_model, get_m1_bigger_model, get_m1_smaller_model
from tokenizers import CharLevelTokenizerv2
from dataset import NeuroSwipeDatasetv3, NeuroSwipeGridSubset
from tokenizers import KeyboardTokenizerv1
from word_generation_v2 import predict_raw_mp
from word_generators import BeamGenerator, GreedyGenerator


MODEL_GETTERS_DICT = {
    "m1": get_m1_model,
    "m1_bigger": get_m1_bigger_model,
    "m1_smaller": get_m1_smaller_model
}

GENERATOR_CTORS_DICT = {
    "greedy": GreedyGenerator,
    "beam": BeamGenerator
}


def get_grid(grid_name: str, grids_path: str) -> dict:
    with open(grids_path, "r", encoding="utf-8") as f:
        return json.load(f)[grid_name]


def weights_to_raw_predictions(grid_name: str,
                               model_getter: Callable,
                               weights_path: str,
                               word_char_tokenizer: CharLevelTokenizerv2,
                               dataset: Dataset,
                               generator_ctor,
                               n_workers: int = 4,
                               generator_kwargs = None
                               ):
    DEVICE = torch.device('cpu')  # Avoid multiprocessing with GPU
    if generator_kwargs is None:
        generator_kwargs = {}

    model = model_getter(DEVICE, weights_path)
    grid_name_to_greedy_generator = {grid_name: generator_ctor(model, word_char_tokenizer, DEVICE)}
    raw_predictions = predict_raw_mp(dataset,
                                    grid_name_to_greedy_generator,
                                    num_workers=n_workers,
                                    generator_kwargs=generator_kwargs)
    return raw_predictions


def get_grid_name_to_grid(grid_name_to_grid__path: str) -> dict:
    # In case there will be more grids in "grid_name_to_grid.json"
    grid_name_to_grid = {
        grid_name: get_grid(grid_name, grid_name_to_grid__path)
        for grid_name in ("default", "extra")
    }
    return grid_name_to_grid


def get_config(config_path: str) -> dict:
    with open(config_path, 'r') as f:
        full_config = json.load(f)
    return full_config['prediction_config']

def get_gridname_to_dataset(config,
                             kb_tokenizer,
                             word_char_tokenizer,
                             max_traj_len) -> Dict[str, Dataset]:
    
    grid_name_to_grid = get_grid_name_to_grid(
        config['grid_name_to_grid__path'])
    
    print("Loading dataset...")
    dataset = NeuroSwipeDatasetv3(
        data_path = config['data_path'],
        gridname_to_grid = grid_name_to_grid,
        kb_tokenizer = kb_tokenizer,
        word_tokenizer = word_char_tokenizer,
        include_time = False,
        include_velocities = True,
        include_accelerations = True,
        has_target=False,
        has_one_grid_only=False,
        include_grid_name=True,
        keyboard_selection_set=keyboard_selection_set,
        total = 10_000
    )

    gridname_to_dataset = {
        'default': NeuroSwipeGridSubset(dataset, grid_name='default'),
        'extra': NeuroSwipeGridSubset(dataset, grid_name='extra'),
    }

    return gridname_to_dataset


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument('--num-workers', type=int, default=1)
    p.add_argument('--config', type=str)
    args = p.parse_args()
    return args 


if __name__ == '__main__':
    MAX_TRAJ_LEN = 299  # ! Лучше, чтобы вычислялся по датасету

    args = parse_args()
    config = get_config(args.config)

    kb_tokenizer = KeyboardTokenizerv1()
    word_char_tokenizer = CharLevelTokenizerv2(
        config['voc_path'])
    keyboard_selection_set = set(kb_tokenizer.i2t)

    gridname_to_dataset = get_gridname_to_dataset(
        config, kb_tokenizer, word_char_tokenizer, MAX_TRAJ_LEN)
    
    for _, _, w_fname in config['model_params']:
        if not os.path.exists(os.path.join(config['models_root'], w_fname)):
            raise ValueError(f"Path {w_fname} does not exist.")


    for grid_name, model_getter_name, weights_f_name in config['model_params']:

        out_path = os.path.join(config['out_path'],
                                f"{weights_f_name.replace('/', '__')}.pkl")
        
        if os.path.exists(out_path):
            print(f"Path {out_path} exists. Skipping.")
            continue

        predictions = weights_to_raw_predictions(
            grid_name = grid_name,
            model_getter=MODEL_GETTERS_DICT[model_getter_name],
            weights_path = os.path.join(config['models_root'], weights_f_name),
            word_char_tokenizer=word_char_tokenizer,
            dataset=gridname_to_dataset[grid_name],
            generator_ctor=GENERATOR_CTORS_DICT[config['generator']],
            n_workers=args.num_workers,
            generator_kwargs=config['generator_kwargs']
        )

        with open(out_path, 'wb') as f:
            pickle.dump(predictions, f, protocol=pickle.HIGHEST_PROTOCOL)
