# Question-answering system based on a custom knowledge base and RAG

Large language models (LLMs) are powerful, but they lack knowledge about specific, private, or up-to-date documents, and may generate hallucinated answers. This project requires you to build a question-answering system based on a custom knowledge base using the Retrieval-Augmented Generation (RAG) paradigm, in which every answer must be grounded in retrieved sources and must explicitly cite those sources.

The system should be able to answer questions based on a specific set of documents that you provide. The main challenge of the project is not the chatbot interface, but the backend data pipeline used to prepare the knowledge and support retrieval, as well as the mechanisms that ensure answers are faithful to the sources.

## Assignment requirements

1. **Data preparation:** Collect a set of documents, such as course notes, product manuals, or government policy documents. Write a script to load, chunk, and generate vector embeddings for these documents using an open-source embedding model or API. Compare at least two chunking strategies, such as different chunk sizes, or chunking with and without overlap, and report the impact of these strategies on retrieval quality.

2. **Knowledge base storage:** Store the document chunks and their corresponding vector embeddings in a vector database.

3. **Retrieval mechanism:** For a user's question, first convert the question into a vector embedding, then retrieve the most relevant document chunks from the vector database based on semantic similarity.

4. **Evidence-based answer generation:** Pass the original question and the retrieved document chunks to an LLM API. Use prompts to require the LLM to generate answers based only on the provided context, and to cite the source document and specific chunk for each claim. If the knowledge base does not contain the answer, the system should state this explicitly rather than guess.

5. **Evaluation:** Build a small test set containing at least 20 question-answer pairs, and report the system's retrieval hit rate and answer accuracy.

## References

1. Lewis, P., et al. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. Advances in Neural Information Processing Systems, 33. (Retrieval-augmented generation for knowledge-intensive natural language processing tasks.)
2. Gao, Y., et al. (2023). Retrieval-augmented generation for large language models: A survey. arXiv:2312.10997. (Retrieval-augmented generation for large language models: A survey.)
3. LangChain Documentation. (2025). Question Answering over Documents. (LangChain documentation: question answering over documents.)
