import argparse
import os

import torch


def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


def ckpt_to_torch_state(ckpt):
    return {remove_prefix(k, 'model.'): v for k, v in ckpt['state_dict'].items()}


######################################################################################


def convert_and_save_dir(ckpt_root: str, out_root: str, 
                         device: torch.device) -> None:
    """
    Given a nested directory of .ckpt files, converts each to .pt 
    and saves them to out_root preserving the directory structure.
    """
    for root, dirs, files in os.walk(ckpt_root):
        for file in files:
            if not file.endswith('.ckpt'):
                continue

            ckpt_path = os.path.join(root, file)
            orig_path_no_ext, orig_ext = os.path.splitext(ckpt_path)
            assert orig_ext == '.ckpt'

            out_path = os.path.join(out_root, orig_path_no_ext + '.pt')
            out_parent = os.path.dirname(out_path)
            if not os.path.exists(out_parent):
                os.makedirs(out_parent)
            convert_and_save_file(ckpt_path, out_path, device)


def convert_and_save_file(ckpt_path: str, out_path: str, 
                          device: torch.device) -> None:
    ckpt = torch.load(ckpt_path, map_location=device)
    state_dict = ckpt_to_torch_state(ckpt)
    torch.save(state_dict, out_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('--ckpt-path', type=str, required=True)
    parser.add_argument('--out-path', type=str, required=True)
    parser.add_argument('--device', type=str, default='cpu')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()

    assert os.path.exists(args.ckpt_path), f"ckpt_path does not exist: {args.ckpt_path}"
    assert not os.path.exists(args.out_path), f"out_path already exists: {args.out_path}"

    device = torch.device(args.device)

    if os.path.isfile(args.ckpt_path):
        convert_and_save_file(args.ckpt_path, args.out_path, device)
    else:
        convert_and_save_dir()





### Alternative script below

# MODEL_NAME = 
# CPT_PATH = 

# import torch

# from model import MODEL_GETTERS_DICT
# from pl_module import LitNeuroswipeModel



# def cross_entropy_with_reshape(pred, target, ignore_index=-100, label_smoothing=0.0):
#     """
#     pred - BatchSize x TargetLen x VocabSize
#     target - BatchSize x TargetLen
#     """
#     pred_flat = pred.view(-1, pred.shape[-1])  # BatchSize*TargetLen x VocabSize
#     target_flat = target.reshape(-1)  # BatchSize*TargetLen
#     return F.cross_entropy(pred_flat,
#                            target_flat,
#                            ignore_index=ignore_index,
#                            label_smoothing=label_smoothing)


# pl_model = LitNeuroswipeModel.load_from_checkpoint(
#     CPT_PATH, model_name = MODEL_NAME, 
#     criterion = cross_entropy_with_reshape, 
#     num_classes = 35)

# model = pl_model.model

# torch.save(model.state_dict(), CPT_PATH + ".pt")