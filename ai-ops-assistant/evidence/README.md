# Recorded local verification

Recorded on 10 October 2026. These files are outputs from actual commands, using only the fictional corpus included in the project.

| Evidence | Result |
| --- | --- |
| [Windows test output](pytest-windows.txt) | 48 tests passed on Python 3.13.5 |
| [Windows evaluation](evaluation.json) | 20 positive questions, 6 out-of-scope questions |
| [Windows demo](demo.json) | Four offline answers and an actual official-SDK MCP stdio call |
| [Linux container evaluation](evaluation-linux-container.json) | Same corpus version and metrics as the Windows run |
| [Linux container demo](demo-linux-container.json) | Actual MCP subprocess call from the packaged installation |
| [Container verification](container-verification.json) | Built and ran on Linux/Python 3.13.16; API, HTML, input rejection and preserved exception verified |

The evaluation recorded document Recall@1 **1.0**, section Recall@1 **0.95**, section Recall@3 **1.0**, section MRR@3 **0.96667**, and negative abstention **1.0**. These scores are measured on a small hand-authored synthetic fixture drawn from the same documents. They are not estimates for unseen questions or production accuracy.

The general English rollback question retrieves the relevant decision section third, despite finding the correct document first. Three results include it; a limit of two can omit it. This illustrates a limitation of the lexical baseline. Review returned evidence rather than treating its ranking as a final decision.

The container ran as UID 10001 with a read-only root filesystem and dropped capabilities. It exposed an ephemeral port on loopback and was stopped after verification. No public deployment, private documents, API secrets or external message sending was involved.

The optional Ollama adapter was exercised through HTTP transport fixtures and failure cases. A real Ollama model, embeddings, vector search and fine-tuning were not evaluated. GitHub CI outcomes are separate from these local checks.
