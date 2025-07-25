import os
import os.path as path
import sys
import json
import random
sys.path.append('..')
from easyeditor import (
    AlphaEditHyperParams,
    FTHyperParams,  
    MEMITHyperParams, 
    ROMEHyperParams, 
    LoRAHyperParams,
    GraceHyperParams,
    MENDHyperParams
    )
from easyeditor import BaseEditor
from easyeditor import LongFormEditDataset

import argparse
import numpy as np

def eval_longform(result_path, dataset_type="zsre"):
    if path.exists(result_path):
        
        with open(result_path,'r') as file:
            datas=json.load(file)

        Edit_Succ_list=[data_longform['post']['rewrite_acc'][0] for data_longform in datas]
        Edit_Succ=sum(Edit_Succ_list)/len(Edit_Succ_list)*100
        print('Edit_Succ:',Edit_Succ)
        
        Rephrase_Succ_list=[data_longform['post']['rephrase_acc'][0] for data_longform in datas]
        Rephrase_Succ=sum(Rephrase_Succ_list)/len(Rephrase_Succ_list)*100
        print('Rephrase_Succ:',Rephrase_Succ)

        Locality_list=[]
        for data_longform in datas:
            case_list=[]
            for key in data_longform['post']['locality'].keys():
                case_list.append(sum(data_longform['post']['locality'][key])/len(data_longform['post']['locality'][key])*100)
            if len(case_list) != 0:
                Locality_list.append(np.mean(case_list))
        Overall_locality = np.mean(Locality_list)
        print('Overall_locality:',Overall_locality)
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--editing_method', required=True, type=str)
    parser.add_argument('--hparams_dir', required=True, type=str)
    parser.add_argument('--data_dir', required=True, type=str)
    parser.add_argument('--dataset_type', default='zsre', choices=['zsre', 'counterfact'], type=str)
    parser.add_argument('--ds_size', default=None, type=int)
    parser.add_argument('--metrics_save_dir', default='./output', type=str)
    parser.add_argument('--sequential_edit', action="store_true")
    args = parser.parse_args()

    if args.editing_method == 'FT':
        editing_hparams = FTHyperParams
    elif args.editing_method == 'AlphaEdit':
        editing_hparams = AlphaEditHyperParams
    elif args.editing_method == 'MEMIT':
        editing_hparams = MEMITHyperParams
    elif args.editing_method == 'ROME':
        editing_hparams = ROMEHyperParams
    elif args.editing_method == 'LoRA':
        editing_hparams = LoRAHyperParams
    elif args.editing_method == 'GRACE':
        editing_hparams = GraceHyperParams
    elif args.editing_method == 'MEND':
        editing_hparams = MENDHyperParams
    else:
        raise NotImplementedError
    
    datas = LongFormEditDataset(args.data_dir, dataset_type=args.dataset_type, size=args.ds_size)
    prompts=[data['prompt'] for data in datas]
    target_new = [data['target_new'] for data in datas]
    ground_truth = [data['ground_truth'] for data in datas]
    subject = [data['subject'] for data in datas]
    rephrase_prompts = [data['rephrase'] for data in datas]
    portability_personas_prompts = [[data['portability_personas']] if isinstance(data['portability_personas'], str) else None for data in datas]
    portability_personas_answers = [[data['target_new']] for data in datas]
    portability_hop_prompts = [[data['portability_hop']] if isinstance(data['portability_hop'], str) else None for data in datas]
    portability_hop_answers = [[data['portability_hop_ans']] if isinstance(data['portability_hop_ans'], str) else None for data in datas]
    if args.dataset_type == 'zsre':
        locality_prompts = [[data['locality']] for data in datas]
        locality_answers = [[data['locality_ans']] for data in datas]
    elif args.dataset_type == 'counterfact':
        locality_prompts = [data['locality'] for data in datas]
        locality_answers = [data['locality_ans'] for data in datas]
    assert len(prompts)==len(portability_personas_prompts)==len(portability_personas_answers)==len(portability_hop_prompts)==len(portability_hop_answers)

    assert len(prompts)==len(locality_prompts)==len(locality_answers)

    locality_inputs = {}
    portability_inputs = {}
    locality_inputs = {
        'locality':{
            'prompt': locality_prompts,
            'ground_truth': locality_answers
        }
    }
    portability_inputs = None

    hparams = editing_hparams.from_hparams(args.hparams_dir)
    editor = BaseEditor.from_hparams(hparams)
    metrics, edited_model, _ = editor.edit(
        prompts=prompts,
        target_new=target_new,
        ground_truth=ground_truth,
        rephrase_prompts=rephrase_prompts,
        locality_inputs=locality_inputs,
        # portability_inputs=portability_inputs,
        subject = subject,
        keep_original_weight=True,
        sequential_edit=args.sequential_edit
    )
    if not os.path.exists(args.metrics_save_dir):
        os.makedirs(args.metrics_save_dir)        
    result_path = os.path.join(args.metrics_save_dir, f'{args.editing_method}_{hparams.model_name.split("/")[-1]}_LongForm_{args.dataset_type}_results.json')
    json.dump(metrics, open(result_path, 'w'), indent=4)
    print(f"Results saved to: {result_path}")
    eval_longform(result_path, args.dataset_type)