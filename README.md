Internship AI Project
Project Overview
This repository contains deliverables from my internship at Zoho Corporation, focused on building an end-to-end Retrieval-Augmented Generation (RAG) pipeline for code intelligence and semantic search in React projects. The main goal was to design a system enabling efficient retrieval of code components—including their dependencies—using modern AI tools and graph-based modeling.

Architecture & Workflow
AST Parsing: React code is parsed into Abstract Syntax Trees (AST) with Tree-Sitter for accurate structural representation.

Embeddings: Code (and ASTs) are embedded with Qwen3-Embedding-8B for robust semantic search.

Vector Storage: Embedded objects are stored in a Weaviate vector database, including graph references to model dependencies.

Graph Retrieval (GraphRAG): Dependencies are retrieved using graph traversal (BFS), allowing contextual queries for code generation with LLMs.

LLM Integration: LangChain provides a bridge to large language models for code generation and intelligent retrieval.

Key Features
End-to-end pipeline for semantic code search and dependency-aware retrieval

Graph-based modeling and BFS traversal for React component relationships

Integration with best-in-class AI frameworks (Weaviate, Qwen, LangChain)

Designed for extensibility with other embedding models and codebases

Technologies Used
Python

Weaviate (Vector Database)

Qwen3-Embedding-8B (Embedding Model)

Tree-Sitter (AST Parsing for JS/JSX)

LangChain (LLM/Prompt Framework)

Docker (Local Dev/Test)

Visual Studio Code

Setup Instructions (High-Level)
Clone the repository

Set up a local or cloud Weaviate instance (see docker-compose1.yml)

Install required Python packages (see code files for dependencies)

Run pipeline scripts (react_ast.py, ast_relationship.py, weviatedb.py) per documentation/comments

Internship Context
This project was completed as part of a 35-day internship at Zoho Corporation, integrating production-level AI retrieval systems, graph algorithms, and developer tooling for code intelligence.
