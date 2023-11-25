from abc import ABC, abstractmethod
from typing import Tuple, List, Set, Dict
import os
import pickle
import copy
import json


def remove_probs(preds: List[List[Tuple[float, str]]]) -> List[List[str]]:
    new_preds = []
    for pred_line in preds:
        new_preds_line = []
        for _, word in pred_line:
            new_preds_line.append(word)
        new_preds.append(new_preds_line)
    return new_preds


def separate_out_vocab_hypotheses(hypotheses_list: List[str],
                                  vocab_set: Set[str],
                                  ) -> Tuple[List[str], List[str]]:
    """
    Separates list of a single word hypotheses into a
    list of in vocab words and a list of out vocab words.
    """
    in_vocab_words = []
    out_vocab_words = []

    for word in hypotheses_list:
        if word in vocab_set:
            in_vocab_words.append(word)
        else:
            out_vocab_words.append(word)
    # if limit != None:
    #     in_vocab_words = in_vocab_words[:limit]
    return in_vocab_words, out_vocab_words


def separate_invalid_preds(dataset_preds: List[List[str]],
                           vocab_set: Set[str]
                           ) -> Tuple[List[List[str]], Dict[int, List[str]]]:
    
    all_in_vocab_preds = []
    all_errorous_word_preds = {}

    for i, hypotheses_lst in enumerate(dataset_preds):
        in_vocab_words, out_vocab_words = separate_out_vocab_hypotheses(
            hypotheses_lst, vocab_set)

        all_in_vocab_preds.append(in_vocab_words)
        all_errorous_word_preds[i] = out_vocab_words

    return all_in_vocab_preds, all_errorous_word_preds


def augment_predictions(preds:List[List[str]],
                        augment_list: List[List[str]],
                        limit: int):
    augmented_preds = copy.deepcopy(preds)
    for pred_line, aug_l_line in zip(augmented_preds, augment_list):
        for aug_el in aug_l_line:
            if len(pred_line) >= limit:
                break
            if not aug_el in pred_line:
                pred_line.append(aug_el)
    return augmented_preds


def merge_preds(default_preds,
                extra_preds,
                default_idxs,
                extra_idxs):
    preds = [None] * (len(default_preds) + len(extra_preds))

    for i, val in zip(default_idxs, default_preds):
        preds[i] = copy.deepcopy(val)
    for i, val in zip(extra_idxs, extra_preds):
        preds[i] = copy.deepcopy(val)

    return preds


def get_vocab_set(vocab_path: str):
    with open(vocab_path, 'r', encoding = "utf-8") as f:
        return set(f.read().splitlines())


def get_default_and_extra_idxs(test_dataset_path
                               ) -> Tuple[List[int], List[int]]:
    default_idxs = []
    extra_idx = []
    with open(test_dataset_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            line_data = json.loads(line)
            grid_name = line_data['curve']['grid_name']
            if grid_name == 'default':
                default_idxs.append(i)
            elif grid_name == 'extra':
                extra_idx.append(i)
            else:
                raise ValueError(f"Unexpected grid_name: {grid_name}.")
    
    return default_idxs, extra_idx


def create_submission(preds_list, out_path) -> None:
    if os.path.exists(out_path):
        raise ValueError(f"File {out_path} already exists")
    
    with open(out_path, "w", encoding="utf-8") as f:
        for preds in preds_list:
            pred_str = ",".join(preds)
            f.write(pred_str + "\n")
            



# Aggregators are basicly functions. They are impplemented
# as callable classes to define an interface
class PredictionsAgregator(ABC):
    # there may be a separate method that aggregates
    # predictions into same format (tuples(score, word))

    @abstractmethod
    def __call__(raw_preds_list: List[List[List[Tuple[float, str]]]],
                 max_n_hypothesis: int = 4,
                 ) -> List[List[str]]:
        """
        Aggregates a list of predictions into one prediciton.

        Arguments:
        ----------
        raw_preds_list: List[List[List[str]]]
            List of model_predictions_list several models predictions. 
            Each models prediction has `dataset_len` rows. Each row
            is a list with tuple elements: (score: float, word: str)
            where score = log(prob(word)). A row may be an empty list.
        max_n_hypothesis: int
            Maximum number of hypothesis per curve to output.
        
        Returns:
        agregated_predictions: List[List[Tuple[float, str]]]
            agregated_predictions[i][j] is j-th word hypothesis
            for i-th curve in the dataset. Each row consists of 0 to 
            `max_n_hypothesis` words.
        """
        pass



class AppendAgregator(PredictionsAgregator):
    def __call__(raw_preds_list: List[List[List[Tuple[float, str]]]],
                 max_n_hypothesis: int = 4,
                 ) -> List[List[Tuple[float, str]]]:
        """
        Aggregates predictions by poping leftmost element in raw_preds_list
        and appending all it's content to output except the elements that
        are alredy present in the output. It's supposed that raw_preds_list
        is sorted by corrsponding models MMR score on validation
        """
        pass


class WeightedAgregator(PredictionsAgregator):
    def __call__(raw_preds_list: List[List[List[Tuple[float, str]]]],
                 max_n_hypothesis: int = 4,
                 ) -> List[List[Tuple[float, str]]]:
        """
        Aggregates predictions by multiplying each probability in a models
        predictions by a corrsponding weight and than merging and sorting
        all rows.
        """
        pass
        


def get_list_of_individual_model_predictions(paths: List[str]
                                             ) -> List[List[List[Tuple[float, str]]]]:
    preds_to_aggregate = []
    for f_path in paths:
        with open(f_path, 'rb') as f:
            preds_to_aggregate.append(pickle.load(f))
    return preds_to_aggregate



# def aggregate_preds_raw_appendage(raw_preds_list):
#     pass

def aggregate_preds_processed_appendage(preds_to_aggregate: List[List[List[str]]],
                                        limit: int
                                        ) -> List[List[str]]:
    dataset_len = len(preds_to_aggregate[0])
    aggregated_preds = [] * dataset_len

    while preds_to_aggregate:
        aggregated_preds = augment_predictions(aggregated_preds,
                                              preds_to_aggregate.pop(0),
                                              limit = limit)
    
    return aggregated_preds




if __name__ == "__main__":
    DATA_ROOT = "data/data_separated_grid/"

    grid_name_to_ranged_bs_model_preds_paths = {
        'default': [
            "m1_bigger__m1_bigger_v2__2023_11_12__14_51_49__0.13115__greed_acc_0.86034__default_l2_0_ls0_switch_2.pt.pkl",
            "m1_bigger__m1_bigger_v2__2023_11_12__12_30_29__0.13121__greed_acc_0.86098__default_l2_0_ls0_switch_2.pt.pkl",
            "m1_bigger__m1_bigger_v2__2023_11_11__22_18_35__0.13542_default_l2_0_ls0_switch_1.pt.pkl",
            "m1_v2__m1_v2__2023_11_09__10_36_02__0.14229_default_switch_0.pt.pkl",
            "m1_bigger__m1_bigger_v2__2023_11_12__00_39_33__0.13297_default_l2_0_ls0_switch_1.pt.pkl",
            "m1_bigger__m1_bigger_v2__2023_11_11__14_29_37__0.13679_default_l2_0_ls0_switch_0.pt.pkl",
            
        ],
        'extra': [
            "m1_v2__m1_v2__2023_11_09__17_47_40__0.14301_extra_l2_1e-05_switch_0.pt.pkl",
            "m1_bigger__m1_bigger_v2__2023_11_12__02_27_14__0.13413_extra_l2_0_ls0_switch_1.pt.pkl"
        ]
    }

    vocab_set = get_vocab_set(os.path.join(DATA_ROOT, "voc.txt"))

    default_idxs, extra_idxs = get_default_and_extra_idxs(
        os.path.join(DATA_ROOT, "test.jsonl"))

    grid_name_to_augmented_preds = {}

    for grid_name in ('default', 'extra'):
        f_names = grid_name_to_ranged_bs_model_preds_paths[grid_name]
        f_paths = [os.path.join("data/saved_beamsearch_results/", f_name)
                   for f_name in f_names]
        
        preds_to_aggregate = get_list_of_individual_model_predictions(f_paths)
        preds_to_aggregate = [remove_probs(bs_preds) for bs_preds in preds_to_aggregate]
        preds_to_aggregate = [separate_invalid_preds(bs_preds, vocab_set)[0]
                              for bs_preds in preds_to_aggregate]


        aggregated_preds = aggregate_preds_processed_appendage(preds_to_aggregate,
                                                               limit = 4)

        grid_name_to_augmented_preds[grid_name] = aggregated_preds


    full_preds = merge_preds(
        grid_name_to_augmented_preds['default'],
        grid_name_to_augmented_preds['extra'],
        default_idxs,
        extra_idxs)
    

    baseline_preds = None
    with open(r"data\submissions\baseline.csv", 'r', encoding = 'utf-8') as f:
        baseline_preds = f.read().splitlines()
    baseline_preds = [line.split(",") for line in baseline_preds]

    full_preds = augment_predictions(full_preds, baseline_preds)

    create_submission(full_preds,
        f"data/submissions/id3_with_baseline_without_old_preds.csv")