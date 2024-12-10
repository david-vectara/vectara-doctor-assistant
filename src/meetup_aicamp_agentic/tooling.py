from pydantic import Field, BaseModel
from typing_extensions import Annotated
from typing import Optional, List
from vectara.factory import Factory
from vectara.types import QueryFullResponse
from pathlib import Path
import sqlite3
from vectara.corpora.types import SearchCorpusParameters
from vectara.types import GenerationParameters
from vectara.utils import render_markdown
from IPython.display import display, Markdown
import json
import re

from llama_index.agent.openai import OpenAIAgent

from llama_index.llms.openai import OpenAI
from llama_index.core.tools import FunctionTool

import nest_asyncio

output_dir = Path("../output")
db_file = output_dir / "patient.db"

CORPUS_KEY = None
client = None

class Patient(BaseModel):
    id: int = Field(description="The patient Id used for other lookups")
    first_name: str = Field(description="The patients first name"),
    last_name: str = Field(description="The patients last name"),
    sex: str = Field(description="The patients biological sex, M=Male, F=Female")
    dob: str = Field(description="The patients date of birth in format yyyy-mm-dd"),
    address: str = Field(description="The patients current residential address")


def initialize():
    global CORPUS_KEY
    global client

    client = Factory(profile="lab").build()

    lab_name, key = client.lab_helper._build_lab_name_and_key("Consumer Medicine Information")
    CORPUS_KEY = key


def find_patients_by_name(first_name: Optional[Annotated[str, Field(description="The first name of the patient")]] = None,
                          last_name: Optional[Annotated[str, Field(description="The last name of the patient")]] = None
                          ) -> List[Patient]:
    """Finds patients by their first name and/or last name and returns their details such as patient ID"""
    con = sqlite3.connect(db_file)

    def dict_factory(cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d
    con.row_factory = dict_factory

    cur = con.cursor()
    try:
        query_parts = ["SELECT *\nFROM patient p"]

        conditions = []

        # Potential SQL Injection attack here - not for production!!
        if first_name:
            conditions.append(f"p.first_name = '{first_name}'")
        if last_name:
            conditions.append(f"p.last_name = '{last_name}'")

        if conditions:
            query_parts.append("\nWHERE ")
            query_parts.append("\nAND ".join(conditions))

        query = "".join(query_parts)

        print(f"Query is:\n{query}")

        cur.execute(query)
        results = cur.fetchall()
        pydantic_results = []
        for result in results:
            pydantic_results.append(Patient.model_validate(result))
        return pydantic_results
    finally:
        cur.close()
        con.close()

def get_ailments_and_medication(
        patient_id: Annotated[int, Field(description="The ID of the patient from the doctors patient database.")]
):
    """Function which returns the ailments and medications for a given patient by ID."""
    con = sqlite3.connect(db_file)
    cur = con.cursor()
    try:
        cur.execute(f"SELECT * FROM patient_ailments WHERE patient_id = {patient_id}")
        results = cur.fetchall()
        return results
    finally:
        cur.close()
        con.close()


def get_medicine_information(medicine_name: Annotated[str, Field(description="The name the medicine is sold as")],
                             query: Annotated[str, Field(description="A question about the medicine that we want "
                                                                     "answered")],
                             result_structure: Annotated[str,
                             Field(description="Instructions about the structure for the response, for example"
                                               " the default is to 'use JSON' but this can be more explicit or a "
                                               "different format.")] = "use JSON."
                             ) -> Annotated[QueryFullResponse,
                                            Field(description="object containing both the response summary but also has"
                                                              " the citations available in the search_results field")]:
    # Returns information about the given medicine based on the query and will use the indicated result_structure.
    global CORPUS_KEY

    if not CORPUS_KEY:
        raise Exception("Not yet initialized, call initialize first")

    prompt_text = """
    [
      {"role": "system", "content": "You are a doctor who is providing advice to patients at the end of their clinical visits."},
      #foreach ($qResult in $vectaraQueryResults)
         {"role": "user", "content": "Give me the $vectaraIdxWord[$foreach.index] search result."},
         {"role": "assistant", "content": "${qResult.getText()}" },
      #end
      {"role": "user", "content": "Generate an answer about MEDICINE_NAME for the query '${vectaraQuery}' based on the above results. For the response structure RESULT_STRUCTURE"}
    ]
        """

    prompt_text = re.sub("MEDICINE_NAME", medicine_name.lower().strip(), prompt_text)
    prompt_text = re.sub("RESULT_STRUCTURE", result_structure, prompt_text)

    print(prompt_text)

    generation = GenerationParameters.parse_obj({
        "generation_preset_name": "vectara-summary-ext-v1.3.0",
        "max_used_search_results": 5,
        "max_response_characters": 300,
        "response_language": "auto",
        "prompt_text": prompt_text
    })

    search_corpus = SearchCorpusParameters.parse_obj({
        "lexical_interpolation": 0.025,
        "semantics": "default",
        "offset": 0,
        "limit": 10,
        "reranker": {
            "type": "customer_reranker",
            "reranker_id": "rnk_272725719"
        },
        "context_configuration": {
            "sentences_before": 2,
            "sentences_after": 2,
            "start_tag": "<b>",
            "end_tag": "</b>"
        },
    })

    query_response = client.corpora.query(CORPUS_KEY, query=query, search=search_corpus, generation=generation)
    return query_response


def build_agent() -> OpenAIAgent:
    initialize()

    nest_asyncio.apply()

    # Create the LLM
    # TODO Hide the API KEY
    llm = OpenAI(
        model="gpt-4o-2024-11-20",
        # uses OPENAI_API_KEY env var by default
        # api_key = ""
    )

    # Create the tools.
    find_patients_by_name_tool = FunctionTool.from_defaults(fn=find_patients_by_name, return_direct=False)
    get_ailments_and_medication_tool = FunctionTool.from_defaults(fn=get_ailments_and_medication, return_direct=False)
    get_medicine_information_tool = FunctionTool.from_defaults(fn=get_medicine_information, return_direct=False)

    # Create the Agent.
    agent = OpenAIAgent.from_tools([find_patients_by_name_tool, get_ailments_and_medication_tool, get_medicine_information_tool], llm=llm, verbose=True,
                                   system_prompt="You are an assistant for a doctor, provide concise information from responses in english but provide citations when requested from the full responses in Chat history. If a name is ambiguous, ask if it is a last name. Give advice as an agent for the doctor themselves.")
    return agent
