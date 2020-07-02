import json
import os
from typing import Union

import jinja2
from airflow import DAG

CURRENT_DIR = os.path.dirname(__file__)


def generate_diagram_from_dag(dag: DAG, diagram_file: Union[str, bytes, int]):
    """
    Auto-generates a diagrams file from a given dag.

    :param dag: The airflow dag to generate the diagrams file from.
    :type dag: DAG
    :param diagram_file: The file to where the diagram code will be written.
    :type diagram_file: Union[str, bytes, int]
    """
    _render_script_to_file(
        jinja_context=dict(
            diagram_imports=_get_diagram_imports(dag.tasks),
            diagram_name=dag.dag_id,
            diagram_nodes=_get_diagram_nodes(dag.roots),
            diagram_edges=_get_diagram_edges(dag.roots),
        ),
        diagram_file=diagram_file
    )


def _render_script_to_file(jinja_context, diagram_file):
    template_loader = jinja2.FileSystemLoader(searchpath=CURRENT_DIR)
    template_env = jinja2.Environment(
        loader=template_loader,
        undefined=jinja2.StrictUndefined
    )
    template = template_env.get_template('diagram.jinja2')
    template.stream(**jinja_context).dump(diagram_file)


def _load_mapping():
    with open(f"{CURRENT_DIR}/mapping.json") as json_file:
        return json.load(json_file)


def _get_diagram_node(task_type):
    mapping = _load_mapping()
    for airflow_operator_type, diagrams_node in mapping.items():
        if airflow_operator_type == task_type:
            return diagrams_node
    raise Exception(
        f"Missing Mapping for {task_type}. "
        "You are welcome to add the mapping to the mapping.json file <3."
    )


def _get_diagram_imports(tasks):
    unique_task_types = {
        task.task_type
        for task in tasks
    }
    return [
        _get_diagram_node(task_type)
        for task_type in unique_task_types
    ]


def _get_diagram_nodes(roots):
    nodes = []
    for edge in _get_diagram_edges(roots):
        if edge["source"] not in nodes:
            nodes.append(edge["source"])
        if edge["target"] not in nodes:
            nodes.append(edge["target"])
    return nodes


def _get_diagram_edges(roots):
    edges = []

    def get_downstream(task):
        for downstream_task in task.downstream_list:
            edge = {
                'source': {
                    'type': _get_diagram_node(task.task_type)['name'],
                    'id': task.task_id
                },
                'target': {
                    'type': _get_diagram_node(downstream_task.task_type)['name'],
                    'id': downstream_task.task_id
                }
            }
            if edge not in edges:
                edges.append(edge)
                get_downstream(downstream_task)

    for t in roots:
        get_downstream(t)

    return edges
