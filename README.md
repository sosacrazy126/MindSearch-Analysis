<div id="top"></div>

<div align="center">

<picture>
  <source srcset="assets/logo.svg" media="(prefers-color-scheme: light)">
  <source srcset="assets/logo-darkmode.svg" media="(prefers-color-scheme: dark)">
  <img src="assets/logo.svg" alt="Logo" width="50%">
</picture>

[📃 Paper](https://arxiv.org/abs/2407.20183) | [💻 Demo](https://internlm-chat.intern-ai.org.cn/)

English

<https://github.com/user-attachments/assets/44ffe4b9-be26-4b93-a77b-02fed16e33fe>

</div>
</p>

# MindSearch: Mimicking Human Minds Elicits Deep AI Searcher

<div align="center">

[![Demo](https://img.shields.io/badge/Demo-Hugging%20Face-orange)](https://huggingface.co/spaces/internlm/MindSearch)
[![Demo](https://img.shields.io/badge/Demo-ModelScope-purple)](https://modelscope.cn/studios/Shanghai_AI_Laboratory/MindSearch)
[![license](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](https://github.com/InternLM/MindSearch/blob/main/LICENSE)

English

[Paper](https://arxiv.org/abs/2407.20183)

https://github.com/user-attachments/assets/b2c9f1d1-0e17-42de-8e88-f861a8d96f19

</div>

## 🎉 News
- **2024-07-30**: We release the MindSearch paper on arXiv and the project on GitHub.

## 📖 Introduction

MindSearch is an open-source AI Search Engine Framework that mimics human minds to provide deep AI search capabilities. It breaks down user queries into sub-questions, uses a WebSearchGraph to systematically browse the web, and provides comprehensive answers with credible references.

### Key Features
- 🧠 **Human-like Search Strategy**: Decomposes complex queries into manageable sub-questions
- 🔍 **Deep Web Exploration**: Systematically browses and analyzes web content
- 📊 **Structured Knowledge Graph**: Builds a WebSearchGraph for organized information retrieval
- 🎯 **Credible References**: Provides answers with proper citations and sources
- 🚀 **High Performance**: Efficient parallel search processing

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone https://github.com/InternLM/MindSearch
cd MindSearch
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables
Create a `.env` file in the root directory:
```bash
cp .env.example .env
```

Edit the `.env` file and add your API keys:
```bash
OPENAI_API_KEY=your_openai_api_key_here
# Optional: Add other search engine API keys
WEB_SEARCH_API_KEY=your_search_api_key_here
```

## 🚀 Quick Start

### Step 1: Setup FastAPI Server

```bash
python -m mindsearch.app --model_format gpt4 --search_engine DuckDuckGoSearch
```

**Parameters:**
- `--model_format`: Format of the model
  - `gpt4` for GPT-4 (default)
  - Other models can be configured in [models.py](./mindsearch/agent/models.py)
- `--search_engine`: Search engine to use
  - `DuckDuckGoSearch` (default, no API key required)
  - `BingSearch` (requires Bing API key)
  - `BraveSearch` (requires Brave API key)
  - `GoogleSearch` (requires Google Serper API key)
  - `TencentSearch` (requires Tencent API credentials)

### Step 2: Test the API

You can test the API using the provided example script:

```bash
python backend_example.py
```

Or use curl:

```bash
curl -X POST "http://localhost:8002/generate" \
  -H "Content-Type: application/json" \
  -d '{"inputs": "What is the weather like in New York today?"}'
```

### Step 3: Run Terminal Interface (Optional)

For a simple terminal interface:

```bash
python -m mindsearch.terminal
```

## 🖥️ Frontend Setup (Optional)

### React Frontend

1. Configure the backend URL:
```bash
HOST="127.0.0.1"
PORT=8002
sed -i -r "s/target:\s*\"\"/target: \"${HOST}:${PORT}\"/" frontend/React/vite.config.ts
```

2. Install and run:
```bash
cd frontend/React
npm install
npm start
```

Visit http://localhost:5173 to access the web interface.

## 📚 Documentation

### API Endpoints

- `POST /generate`: Main endpoint for search queries
  - Request body: `{"inputs": "your question here"}`
  - Returns: Streaming response with search progress and final answer

### Configuration

The system can be configured through:
- Command-line arguments when starting the server
- Environment variables in `.env` file
- Direct modification of configuration files

### Model Support

Currently supported models:
- OpenAI GPT-4 (default)
- Additional models can be added in `mindsearch/agent/models.py`

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 📖 Citation

If you find this project useful in your research, please consider citing:

```bibtex
@article{chen2024mindsearch,
  title={MindSearch: Mimicking Human Minds Elicits Deep AI Searcher},
  author={Chen, Zehui and Liu, Kuikun and Wang, Qiuchen and Liu, Jiangning and Zhang, Wenwei and Chen, Kai and Zhao, Feng},
  journal={arXiv preprint arXiv:2407.20183},
  year={2024}
}
```

## 🙏 Acknowledgments

MindSearch is built on top of [Lagent](https://github.com/InternLM/lagent) and uses various open-source models and tools. We thank all the contributors and maintainers of these projects.

## 📞 Contact

For questions and support, please open an issue on GitHub or contact us through the official channels.
