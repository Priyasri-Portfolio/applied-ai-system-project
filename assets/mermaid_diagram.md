flowchart TD
    A([Human Owner\nPet profile + tasks]) --> B

    subgraph AGENT[" Agentic Pipeline — agent.py "]
        direction TB
        B[Step 1 · Analyzer\nValidate profile and tasks]
        B --> C
        C[Step 2 · Retriever\nRAG — search knowledge base]
        C --> D
        D[Step 3 · Planner\nCall Groq LLM with rules]
        D --> E
        E{Step 4 · Evaluator\nSafety guardrail checks}
        E -->|Pass| F
        E -->|Fail — inject violations| D
    end

    subgraph KB[" Knowledge Base — data/petcare_rules.txt "]
        direction LR
        G[Feeding rules]
        H[Exercise limits]
        I[Medication rules]
        J[Health conditions]
    end

    C --> KB

    F([Final Schedule Output])
    F --> K[Human Review]
    K -->|Accept| L([Execute Tasks])
    K -->|Revise| A

    subgraph TESTS[" Test Harness — tests/test_evaluator.py "]
        M[8 preset scenarios] --> N[Pass / Fail summary]
    end

    TESTS -. tests .-> E