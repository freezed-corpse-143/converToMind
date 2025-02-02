import string
import random
import time
import os
import sys
import json
import zipfile

os.makedirs("./data", exist_ok=True)

def generate_random_string(length=32):
    characters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

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

def get_current_timestamp():
    return int(time.time() * 1000)

def find_path_to_node(tree, node_id, path=None):
    if path is None:
        path = []
    path.append(tree["id"])  # 将当前节点 ID 加入路径
    if tree["id"] == node_id:
        return path
    for child in tree.get("children", []):
        result = find_path_to_node(child, node_id, path.copy())  # 递归查找子节点
        if result:
            return result
    return None

def find_last_common_ancestor(path_1, path_2):
    last_common_ancestor = None
    for id_1, id_2 in zip(path_1, path_2):
        if id_1 == id_2:
            last_common_ancestor = id_1
        else:
            break
    return last_common_ancestor

def compare_nodes_vertical_position(tree, id_1, id_2):
    path_1 = find_path_to_node(tree, id_1)
    path_2 = find_path_to_node(tree, id_2)

    if not path_1 or not path_2:
        return False

    if len(path_1) != len(path_2):
        raise Exception("id_1 isn't in the same level with id_2")

    last_common_ancestor_id = find_last_common_ancestor(path_1, path_2)

    last_common_ancestor = find_node_in_tree(tree, last_common_ancestor_id)

    # 找到两个节点在公共祖先的 children 中的索引
    index_1 = next((i for i, child in enumerate(last_common_ancestor["children"]) if child["id"] == path_1[path_1.index(last_common_ancestor_id) + 1]), None)
    index_2 = next((i for i, child in enumerate(last_common_ancestor["children"]) if child["id"] == path_2[path_2.index(last_common_ancestor_id) + 1]), None)

    # 比较索引
    if index_1 is not None and index_2 is not None and index_1 < index_2:
        return 1
    return -1

def find_node_level(tree, node_id):
    def dfs(node, current_level):
        if node['id'] == node_id:
            return current_level
        for child in node['children']:
            result = dfs(child, current_level + 1)
            if result != -1:
                return result
        return -1

    return dfs(tree, 1)


def transform_line(tree, right=True):
    id_text = {}
    for node in tree['nodes']:
        id_text[node['id']] = node['text']

    style = {
        "text-underline": False,
        "text-line-through": False,
        "line-type": "line"
    }
    result = []
    for edge in tree['additional_edges']:
        source_id = edge['fromId']
        target_id = edge['toId']
        line_id = edge['id']
        source_level = find_node_level(tree['structure'], source_id)
        target_level = find_node_level(tree['structure'], target_id)
        id_text[line_id] = ""
        if source_level == target_level:
            source_is_up = compare_nodes_vertical_position(tree['structure'], source_id, target_id)
            line = {
                "data": {
                    "id": line_id,
                    "fromId": source_id,
                    "fromAngle": 90 * source_is_up,
                    "toId": target_id,
                    "toAngle": -90 * source_is_up,
                    "relativeControl1": {
                        "x": 0,
                        "y": 12 * source_is_up
                    },
                    "relativeControl2": {
                        "x": 0,
                        "y": -12 * source_is_up
                    },
                    "text": "",
                    "html": ""
                },
                "style": style
            }
            result.append(line)
            continue
        source_is_left = 1 if source_level < target_level else -1
        source_is_left *= 1 if right else -1
        line = {
            "data": {
                "id": line_id,
                "fromId": source_id,
                "fromAngle": 90-90*source_is_left,
                "toId": target_id,
                "toAngle": 90+90*source_is_left,
                "relativeControl1": {
                    "x": 75*source_is_left,
                    "y": 0
                },
                "relativeControl2": {
                    "x": -75*source_is_left,
                    "y": 0
                },
                "text": "",
                "html": ""
            },
            "style": style
        }
        result.append(line)
    return result

def transform_tree(tree, right=True):
    id_text = {}
    for node in tree['nodes']:
        id_text[node['id']] = node['text']
    level = 0
    def transform_node(node, id_text, level, right=True):
        data = {
            "id": node["id"],
            "expanded": True,  
            "text": f"{id_text[node['id']]}",  
            "html": f"<p>{id_text[node['id']]}</p>",  
        }
        if level == 1:
            data['mindLayoutSplitIndex'] = len(node['children']) if right else 0
        elif level == 2:
            data["timeSnippet"] = ""
        style = {
            "text-underline": False,
            "text-line-through": False
        }
        
        new_node = {
            "data": data,
            "style": style
        }

        if "children" in node and node["children"]:
            new_node["children"] = [transform_node(child, id_text, level+1, right) for child in node["children"]]

        return new_node

    return transform_node(tree['structure'], id_text, level+1, right)

def convert_tree_to_gitmind(json_data, right=True):
    random_id = generate_random_string()
    
    current_time = get_current_timestamp()
    
    transformed_root = transform_tree(json_data, right)
    transformed_rel_lines = transform_line(json_data, right)
    
    gitmind_data = {
        "id": random_id,
        "created": current_time,
        "modified": current_time,
        "autoIncrementId": 0,
        "version": "2.1.3",
        "style": {
            "content": {
                "can-line-wrap": True
            },
            "layout": {
                "broadcast-margins": False,
                "avoid-overlay": False
            },
            "theme": {
                "colorTheme": "rainbow-yellow",
                "structTheme": "mind-arc"
            }
        },
        "root": transformed_root,
        "floatRoots": [],
        "relLines": transformed_rel_lines,
        "watermark": {
            "id": random_id,
            "show": False
        }
    }
    return gitmind_data


def transform_mix_line(json_data):
    result = []
    for edge in json_data:
        source_is_left = edge['right']
        result.append({
            "data": {
                "id": edge['id'],
                "fromId": edge['fromId'],
                "fromAngle": 90-90*source_is_left,
                "toId": edge['toId'],
                "toAngle": 90+90*source_is_left,
                "relativeControl1": {
                    "x": 75*source_is_left,
                    "y": 0
                },
                "relativeControl2": {
                    "x": -75*source_is_left,
                    "y": 0
                },
                "text": "",
                "html": ""
            },
            "style": {
                "text-underline": False,
                "text-line-through": False,
                "line-type": "line"
            }
        })
    return result

def main():
    if len(sys.argv) < 2:
        print("please provide at least one parameter as the json path")
        return
    
    file_path_list = sys.argv[1:]
    if len(file_path_list) not in [1, 3]:
        print("only 1 or 3 json json paths are supported.")
        return
    
    data_list = []
    for idx, file_path in enumerate(file_path_list):
        if not os.path.exists(file_path):
            print(f"error:{idx} arg {file_path} doesn't exist")
            return
        if not file_path.endswith("_tree.json"):
            print(f"error:{idx} arg {file_path} should end with '_tree.json'")
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data_list.append(data)
    
    end_idx = 1 if len(file_path_list) == 1 else 2
    for idx in range(end_idx):
        result = convert_tree_to_gitmind(data_list[idx])
        base_name = os.path.basename(file_path_list[idx])
        output_name = base_name.replace("_tree.json", ".gmind")
        
        with zipfile.ZipFile(f"./data/{output_name}", 'w') as zipf:
            zipf.writestr("content.json", json.dumps(result))

    if len(file_path_list) == 1:
        return
    
    gitmind_0 = convert_tree_to_gitmind(data_list[0])
    gitmind_1 = convert_tree_to_gitmind(data_list[1], right=False)
    mix_lines = transform_mix_line(data_list[-1])

    gitmind_1['root']['data']['position'] = {
        "x": 2000,
        "y": 0
    }

    gitmind_0['floatRoots'].append(gitmind_1['root'])
    gitmind_0['relLines'].extend(gitmind_1['relLines'])
    gitmind_0['relLines'].extend(mix_lines)
    
    base_name = os.path.basename(file_path_list[-1])

    output_name = base_name.replace("_tree.json", ".gmind")
    with zipfile.ZipFile(f"./data/{output_name}", 'w') as zipf:
        zipf.writestr("content.json", json.dumps(gitmind_0))


if __name__ == "__main__":
    main()