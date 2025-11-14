import os
import time
from dotenv import load_dotenv
import requests

load_dotenv()
api_key = os.getenv("IAM_API_KEY")
url = os.getenv("URL")
presto_url = os.getenv("PRESTO_URL")
crn = os.getenv("CRN")


async def get_token():
    response = requests.post(
        "https://iam.cloud.ibm.com/identity/token",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        },
        data={
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": f"{api_key}"
        }
    )
    if response.status_code == 200:
        return response.json().get("access_token", "")
    else:
        return None


async def _get_headers():
    token = await get_token()
    if token:
        return {
            "Content-Type": "application/json",
            "AuthInstanceId": f"{crn}",
            "Authorization": f"Bearer {token}"
        }
    return None


async def get_presto_engine_id():
    headers = await _get_headers()
    if headers:
        response = requests.get(f"{url}/presto_engines", headers=headers)
        if response.status_code == 200:
            return response.json()["presto_engines"][0]["engine_id"]
    return None


async def get_catalog_name():
    headers = await _get_headers()
    if headers:
        response = requests.get(f"{url}/catalogs", headers=headers)
        if response.status_code == 200:
            for catalog in response.json()["catalogs"]:
                if "supa" in catalog.get("catalog_name", ""):
                    return catalog.get("catalog_name", "")
    return None


async def get_schemas(engine_id: str, catalog_name: str):
    headers = await _get_headers()
    if headers:
        response = requests.get(f"{url}/catalogs/{catalog_name}/schemas?engine_id={engine_id}", headers=headers)
        if response.status_code == 200:
            return response.json()["response"]["schemas"]
    return None


async def get_tables(engine_id: str, catalog_name: str, schema: str):
    headers = await _get_headers()
    if headers:
        response = requests.get(
            f"{url}/catalogs/{catalog_name}/schemas/{schema}/tables?engine_id={engine_id}", headers=headers
        )
        if response.status_code == 200:
            print(response.json())
    return None


async def run_sql_query(query: str):
    headers = {"Content-Type": "application/json", "x-Presto-User": "admin"}
    auth = ("ibmlhapikey", api_key)

    print(f"Submitting query: {query}")
    r = requests.post(f"{presto_url}/v1/statement", headers=headers, auth=auth, data=query)
    r.raise_for_status()

    results = []
    columns = []

    def _consume_chunk(chunk: dict):
        nonlocal columns, results
        if "columns" in chunk and not columns:
            columns = [c["name"] for c in chunk["columns"]]
        if "data" in chunk:
            results.extend(chunk["data"])
        return chunk.get("nextUri")

    next_uri = _consume_chunk(r.json())

    while next_uri:
        r2 = requests.get(next_uri, headers=headers, auth=auth)
        r2.raise_for_status()
        next_uri = _consume_chunk(r2.json())
        time.sleep(1)

    if results:
        matrix = [columns] + results
        return matrix
    else:
        return None
