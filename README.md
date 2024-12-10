# Vectara Doctor Assistant

This repository shows how easy it is to build a Vectara Assistant with LLama-Index and the
vectara SDK.

<img src="notebooks/images/doctor-hologram.png" width="800" />


## Pre-requisites
It is expected you are familiar with LLMs generally and a notebook environment.

## Getting Started
In order to run these, you will need to do two things:

1. Setup Vectara YAML Lab Profile. See [examples/01_getting_started/00_setup_authentication.ipynb](https://github.com/vectara/python-sdk/blob/main/examples/01_getting_started/00_setup_authentication.ipynb) in the Vectara Python SDK
2. Input your OpenAI API Key as an env variable OPENAI_API_KEY.

Once this is done load up the notebooks located in the correspondingly named folder.

## Goal
This workshop lab is designed to familiarise you with Vectara within an Agentic setting with a purpose
in mind. 

> Imagine you are a doctor working with patient data. You have many sources of information much of it unstructured plus
> PII concerns. You need a way to interface with your patient database alongside unstructured sources of data. You want
> to take advantage of Generative AI, but want to do so in a setting that ensures the information is grounded, trusted and
> can be updated.

## Methodology
Since we're working with information that is going to be saved in a public repository, we can't use real
PII data, so instead we're using the following approach:

1. Use the Faker library to create some "Patients"
2. Ingest real consumer medicine information documents from the Therapeutic Goods Administration (TGA)
3. "Bridge" the fake and real information using RAG for Synthetic Data generation: Grounded Fake data
4. Build a domain model with this information with Patients -> Ailments -> Medication
5. Build an Agentic "Tool Layer":
   1. A patient lookup tool powered by an RDBMS
   2. An Ailment-Medication lookup tool powered by an RDBMS
   3. A RAG powered medication information lookup tool powered by Vectara with the TGA medication reports

## Domain Model
As discussed above, we are building the following domain model.

## References
Under the covers, the code uses the following technologies:

1. Vectara APIs: We use this to create a medication corpus, load data and perform queries. We make use of Filter 
   Attributes to control information based on a "medication_name"
2. Vectara Python-SDK: We use the Python SDK to simplify the process of corpus creation, uploading PDFs and running
   