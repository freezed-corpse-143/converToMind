import json
import uuid
from collections import defaultdict, deque
import os
import sys

os.makedirs("./data", exist_ok=True)

def find_edge_in_tree(tree, source_id, target_id):
    node = find_node_in_tree(tree, source_id)
    if not node:
        return False
    if len(node['children']) == 0:
        return False
    return any(child['id'] == target_id for child in node['children'])

def find_node_in_tree(tree, node_id):
    if len(tree) == 0:
        return {}
    
    if tree['id'] == node_id:
        return tree
    
    for child in tree.get('children', []):
        result = find_node_in_tree(child, node_id)
        if result:
            return result
    return {}

class HexIdGenerator:
    _generated_ids = set()

    @classmethod
    def generate_hex_id(cls):
        while True:
            new_id = uuid.uuid4().hex[:10]

            if new_id not in cls._generated_ids:
                cls._generated_ids.add(new_id)
                return new_id

    @classmethod
    def clear_generated_ids(cls):
        cls._generated_ids.clear()

def generate_tree(dependencies, root_name="root"):

    node_id = {}
    for node in set([item for sublist in [[d['source'], d['target']] for d in dependencies] for item in sublist]):
        new_id = HexIdGenerator.generate_hex_id()
        node_id[node] = new_id

    dep_dict = defaultdict(list)
    for item in dependencies:
        source_id = node_id[item['source']]
        target_id = node_id[item['target']]
        if target_id not in dep_dict[source_id]:
            dep_dict[source_id].append(target_id)
    
    in_degree = defaultdict(int)
    for source, targets in dep_dict.items():
        for target in targets:
            in_degree[target] += 1
    roots = [node for node in dep_dict.keys() if in_degree[node] == 0]
    
    if len(roots) == 0:
        raise Exception("can't find root in directed node")

    if len(roots) > 1:
        virtual_root_id = HexIdGenerator.generate_hex_id()
        node_id[root_name] = virtual_root_id
        dep_dict[virtual_root_id] = roots
        roots = [virtual_root_id]
    
    tree = {'id': roots[0], 'children': []}
    nodes_queue = deque(roots)

    visited_node_ids = roots
    while nodes_queue:
        current_id = nodes_queue.popleft()
        current_node = find_node_in_tree(tree, current_id)
        children = []
        for child_id in dep_dict.get(current_id, []):
            if child_id not in visited_node_ids:
                visited_node_ids.append(child_id)
                children.append({'id': child_id, 'children': []})
                nodes_queue.append(child_id)
        current_node['children'] = children
    
    additional_edges = []
    for source, targets in dep_dict.items():
        for target in targets:
            found = find_edge_in_tree(tree, source_id=source, target_id=target)
            if not found:
                line_id = HexIdGenerator.generate_hex_id()
                additional_edges.append({"id": line_id, "fromId": source, "toId": target})

    output = {
        "structure": tree,
        "additional_edges": additional_edges,
        "nodes": [{"id": id, "text": text} for text, id in node_id.items()]
    }
    return output


def main():
    HexIdGenerator.clear_generated_ids()
    if len(sys.argv) < 2:
        print("please provide at least one parameter as the json path")
        return
    file_path_list = sys.argv[1:]
    if len(file_path_list) not in [1, 3]:
        print("only 1 or 3 json json paths are supported.")
        return
    end_idx = 1 if len(file_path_list) == 1 else 2
    
    data_list = []
    for file_path in file_path_list:
        if not file_path.endswith("_dependence.json"):
            print(f"error: {file_path} should end with '_dependence.json'")
            return

        if not os.path.exists(file_path):
            print(f"error：file {file_path} doesn't exist")
            return
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data_list.append(data)
    
    node_set_list = [set() for _ in range(end_idx)]
    total_node_id = dict()
    root_name_list = [os.path.basename(path).split("_")[0] for path in file_path_list]
    for idx in range(end_idx):
        data = data_list[idx]
        root_name = root_name_list[idx]
        node_set = node_set_list[idx]
        file_path = file_path_list[idx]
        result = generate_tree(data, root_name)
        for node in result['nodes']:
            node_set.add(node['text'])
            total_node_id[node['text']] = node['id']
        base_name = os.path.basename(file_path)
        output_name = base_name.replace("dependence", "tree")
        with open(f'./data/{output_name}', 'w', encoding="utf-8") as f:
            json.dump(result, f, indent=4)
    
    if len(file_path_list) == 1:
        return
    
    result = []
    for edge in data_list[-1]:
        source = edge['source']
        target = edge['target']
        if source not in total_node_id or target not in total_node_id:
            continue
        if source in node_set_list[0] and target not in node_set_list[1]:
            continue
        if source in node_set_list[1] and target not in node_set_list[0]:
            continue
        right = 1 if source in node_set_list[0] else -1
        
        result.append({
            "id":  HexIdGenerator.generate_hex_id(),
            "fromId": total_node_id[source],
            "toId": total_node_id[target],
            "right": right
        })
    base_name = os.path.basename(file_path_list[-1])
    output_name = base_name.replace("dependence", "tree")
    with open(f"./data/{output_name}", 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4)

if __name__ == "__main__":
    main()