from __future__ import annotations

from apify_client import ApifyClient

from .config import load_apify_token


def make_client() -> ApifyClient:
    return ApifyClient(load_apify_token())


def call_actor_items(actor_id: str, actor_input: dict) -> tuple[list[dict], dict]:
    client = make_client()
    run = client.actor(actor_id).call(run_input=actor_input)
    dataset_id = run.get("defaultDatasetId")
    if not dataset_id:
        return [], run
    return list(client.dataset(dataset_id).iterate_items()), run

