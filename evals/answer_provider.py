import sys

sys.path.insert(0, ".")  # promptfoo runs from the project root, so `import rag` works

from rag.answer import answer_query


def call_api(prompt, options, context):
    return {"output": answer_query(prompt)}
