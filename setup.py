from setuptools import setup, find_packages

setup(
    name="mindsearch",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "duckduckgo_search==5.3.1b1",
        "einops",
        "fastapi",
        "gradio==5.7.1",
        "janus",
        "lagent==0.5.0rc2",
        "matplotlib",
        "pydantic==2.6.4",
        "python-dotenv",
        "pyvis",
        "schemdraw",
        "sse-starlette",
        "termcolor",
        "transformers==4.41.0",
        "uvicorn",
        "tenacity",
    ],
    python_requires=">=3.8",
    description="MindSearch - AI-powered search and reasoning system",
)