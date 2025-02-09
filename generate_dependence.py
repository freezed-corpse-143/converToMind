import os
import json
import sys
from util import client, extract_from_code_block, extract_json_from_str

dependence_prompt = '''Please read input json and follow these instructions:
1. Genertate the dependence between the elements of input json, where the "target" element should be more specific or a refined version of the "source" element.
2. Output should be in in the format of "```json\n<output>", where "<output>" is a placeholder. An output example is as follows:

```json
[
    {"source": "decision tree", "target": "C4.5 tre" },
    {"source": "linear regression", "target": "log-linear regression" },
]
```
'''

os.makedirs("./data", exist_ok=True)

fusion_prompt = '''Please read input two json, and follow these instructions:
1. Genertate the dependence between the elements of the first one and those of the second one, where "source" element should be in the first json and the "target" element should be in the second json.
2. Output should be in in the format of "```json\n<output>", where "<output>" is a placeholder. An output example is as follows:

```json
[
    {"source": "<element_name_1>", "target": "<element_name_2>" },
]
```

'''


def generate_dependece_graph(json_data):
    global dependence_prompt, client
    completion = client.chat.completions.create(
        model="qwen-plus",
        messages=[
            {'role': 'system', 'content': dependence_prompt},
            {'role': 'user', 'content': f'```input json\n{json.dumps(json_data)}```'}
        ],
        stream=False,
        temperature=0.01
    )
    result = completion.choices[0].message.content
    result_json_list = extract_from_code_block(result)
    if len(result_json_list) > 0:
        result_json_str = result_json_list[0]
        result_json = extract_json_from_str(result_json_str)
    else:
        return {}
    
def generate_dependece_fusion(json_data_1, json_data_2):
    global fusion_prompt, client
    completion = client.chat.completions.create(
        model="qwen-plus",
        messages=[
            {'role': 'system', 'content': fusion_prompt},
            {'role': 'user', 'content': f'```first json\n{json.dumps(json_data_1)}```\n\n```second json\n{json.dumps(json_data_2)}```'}
        ],
        stream=False,
        temperature=0.01
    )
    result = completion.choices[0].message.content
    result_json_list = extract_from_code_block(result)
    if len(result_json_list) > 0:
        result_json_str = result_json_list[0]
        result_json = extract_json_from_str(result_json_str)
        return result_json
    else:
        return {}
    
def find_index(lst, target):
    for i, value in enumerate(lst):
        if value == target:
            return i
    return -1
    
def main():
    if len(sys.argv) < 2:
        print("please provide at least one parameter as the json path")
        return
    
    json_arg_idx = [idx for idx, arg in enumerate(sys.argv) if arg.endswith(".json")]

    if len(json_arg_idx) == 0:
        print("no json path in args")
        return
    if len(json_arg_idx) > 2:
        print(f"{len(json_arg_idx)} json paths in arg, only 1 and 2 is accepted.")
        return
    
    split_signal = "+"

    json_path_list =[]

    file_path_1 = sys.argv[json_arg_idx[0]]
    if not os.path.exists(file_path_1):
        print(f"error: file {file_path_1} doesn't exist")
        return
    
    json_path_list.append(file_path_1)
    
    key_list_list = []
    if len(json_arg_idx) == 1:
        key_list_1 = sys.argv[json_arg_idx[0]+1:]
        key_list_1 = ["name", "description"] if len(key_list_1) == 0 else key_list_1
        key_list_list.append(key_list_1)
    else:
        file_path_2 = sys.argv[json_arg_idx[1]]
        if not os.path.exists(file_path_2):
            print(f"error: file {file_path_2} doesn't exist")
            return
        json_path_list.append(file_path_2)
        key_list_1 = sys.argv[json_arg_idx[0]+1:json_arg_idx[1]]
        key_list_1 = ["name", "description"] if len(key_list_1) == 0 else key_list_1
        key_list_list.append(key_list_1)
        key_list_2 = sys.argv[json_arg_idx[1]+1:]
        key_list_2 = ['name', "description"] if len(key_list_2) == 0 else key_list_2
        key_list_list.append(key_list_2)
        mix_key_arg_list = sys.argv[1:json_arg_idx[0]]
        if len(mix_key_arg_list) == 0:
            mix_key_list_1 = ["name", "latent_techniques"]
            mix_key_list_2 = ['name', "targeted_tasks"]
        elif find_index(mix_key_arg_list, split_signal) == -1:
            mix_key_list_1 = mix_key_arg_list
            mix_key_list_2 = ['name', "targeted_tasks"]
        else:
            split_idx = find_index(mix_key_arg_list, split_signal)
            mix_key_list_1 = mix_key_arg_list[0:split_idx]
            mix_key_list_1 = ["name", "latent_techniques"] if len(mix_key_list_1) == 0 else mix_key_list_1
            mix_key_list_2 = mix_key_arg_list[split_idx+1:]
            mix_key_list_2 = ['name', "targeted_tasks"] if len(mix_key_list_2) == 0 else mix_key_list_2

    data_list = []
    for file_path, key_list in zip(json_path_list, key_list_list):
        with open(file_path, encoding='utf-8') as f:
            data = json.load(f)
        data_list.append(data)
        cleaned_data= []
        for item in data:
            cleaned_data.append({k: v for k, v in item.items() if k in key_list})
    
        result = generate_dependece_graph(cleaned_data)
    
        base_name = os.path.basename(file_path)
        new_file_name = base_name.replace(".json", "_dependence.json")
        save_path = os.path.join("./data/", new_file_name)
    
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
    
    if len(json_arg_idx) == 1:
        return

    cleaned_data_1 = []
    for item in data_list[0]:
        cleaned_data_1.append({k: v for k, v in item.items() if k in mix_key_list_1})

    cleaned_data_2 = []
    for item in data_list[1]:
        cleaned_data_2.append({k: v for k, v in item.items() if k in mix_key_list_2})

    result_fusion = generate_dependece_fusion(cleaned_data_1, cleaned_data_2)

    fusion_save_path = "./data/"
    for file_path in json_path_list:
        base_name = os.path.basename(file_path).split(".")[0]
        fusion_save_path += base_name+"_"
    fusion_save_path = fusion_save_path + "dependence.json"

    with open(fusion_save_path, "w", encoding='utf-8') as f:
        json.dump(result_fusion, f, indent=4)
    

if __name__ == "__main__":
    main()