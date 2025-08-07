# Markdown generation
I want a new markdown_generation_overview file like the overview_generation file you made before. Instead of your steps i want to do it in the below steps. The important change is that we are now using 3 llm calls instead of 1 with RAG queries in between to increase the accuracy of the final output. And now we also want to output multiple pages instead of just 1.

Overall step by step flow
1. SUPABASE TABLES: Collect meta data about the project from the database
2. QUERY TO VECTOR DB: Send query to retrieve overall project decription (STATIC STANDARD QUERY)
3. OVERVIEW LLM CALL: Create project overview based on QUERY TO VECTOR DB
4. SEMANTIC ANALYSIS: Do semantic clustering to retrieve 4-10 main topics (like you did before)
5. STRUCTURE LLM CALL: Create json to content generators based on the first 3 steps (output topic and proposed queries based on topic)
6. PAGE QUERY TO VECTOR DB: Content generators makes new queries based on their topic (also gets sources)
7. PAGE LLM CALL: Then generates a page based on those sources + initial db retrieved data + first vector db retrieved data if needed

## SUPABASE TABLES
Type of information to retrieve from database
- Total amount of documents
- Total pages analysed
- Total chunks created
- Images proceesed & captioned
- Tables proceesed & captioned
- Sections detected in section_headers_distribution under the chunkingstep's data. 

## QUERY TO VECTOR DB
project_overview_queries = [
    # Grundlæggende projektidentitet
    "projekt navn titel beskrivelse oversigt sammendrag formål",
    "byggeprojekt omfang målsætninger mål leverancer",
    "projekt lokation byggeplads adresse bygning udvikling",
    
    # Nøgledeltagere
    "entreprenør klient ejer udvikler arkitekt ingeniør",
    "projektteam roller ansvar interessenter",
    
    # Tidsplan og faser
    "projektplan tidsplan milepæle faser byggefaser etaper",
    "startdato færdiggørelsesdato projektvarighed",
    
    # Projektomfang og type
    "projektværdi budget omkostningsoverslag samlet kontrakt",
    "bygningstype bolig erhverv industri infrastruktur",
    "kvadratmeter etageareal størrelse dimensioner omfang"
]

## OVERVIEW LLM CALL
Based on the construction project document excerpts provided below, generate a brief 2-3 paragraph project overview covering:

1. Project name, type, location, and main purpose
2. Key stakeholders (client, contractor, architect, etc.) and project timeline  
3. Project scale, budget, and major deliverables

Only use information explicitly found in the document excerpts. Cite sources using (Source: filename:page). If critical information is missing, briefly note what's unavailable.

Document excerpts:
[INSERT_RETRIEVED_CHUNKS_HERE]

Generate the project overview:

## SEMANTIC ANALYSIS
Do semantic clustering to retrieve 4-10 main topics (as you are doing now) 

## STRUCTURE LLM CALL
### Own
Analyze this construction project and create a wiki structure for it.

# Important context to consider when deciding which sections to create
1. The complete list of project documents:
- {insert list of documents from the database retrieval call}

2. The project overview/summary:
{from OVERVIEW LLM CALL}

3. Semantic analysis
{
insert list of clusters and how many chunks are related to each cluster like: 
- Cluster 1 (221 chunks): Door systems & access control
- Cluster 2 (98 chunks): Basic elements
}

4. Sections detected
{insert list of sections detected in section_headers_distribution from the SUPABASE TABLES step:}

Use the project overview & semantic analysis most in your considerations.

## Section breakdown information
I want to create a wiki for this construction project. Determine the most logical structure for a wiki based on the project's documentation and content.

IMPORTANT: The wiki content will be generated in Danish language.

# Return output 
## Return output rules
- Make sure each output at least have 1 "overview" page. 

- Make sure each page has a topic and 6-10 associated queries that will help them retrieve relevant information for that topic. Like this for overview: 

- OPTIONAL: If a page is closely related to another page, then store that in related_pages.

project_overview_queries = [
    # Core project identity
    "project name title description overview summary purpose",
    "construction project scope objectives goals deliverables",
    "project location site address building development",
    
    # Key participants
    "contractor client owner developer architect engineer",
    "project team roles responsibilities stakeholders",
    
    # Timeline and phases
    "project schedule timeline milestones phases construction stages",
    "start date completion date project duration",
    
    # Project scale and type
    "project value budget cost estimate total contract",
    "building type residential commercial industrial infrastructure",
    "square meters floor area size dimensions scope"
] 

- Each page should focus on a specific aspect of the construction project (e.g., project phases, safety requirements, material specifications)

- 

## Return output format
Return your analysis in the following JSON format:

{
 "title": "[Overall title for the wiki]",
 "description": "[Brief description of the construction project]",
 "pages": [
   {
     "id": "page-1",
     "title": "[Page title]",
     "description": "[Brief description of what this page will cover]",
     "proposed_queries": [
       "[]"
     ],
     "related_pages": [
       "[]"
     ],
     "relevance_score": "1-10",
     "topic_argumentation": "argumentation for why this was chosen"
   }
 ]
}

IMPORTANT FORMATTING INSTRUCTIONS:
- Return ONLY the valid JSON structure specified above
- DO NOT wrap the JSON in markdown code blocks (no ``` or ```json)
- DO NOT include any explanation text before or after the JSON
- Ensure the JSON is properly formatted and valid
- Start directly with { and end with }


## PAGE QUERY TO VECTOR DB: 
Query the database with all the proposed_queries from the previous steps json output.
Make sure they get an output that can be read in the next step when we want to input [RELEVANT_PAGE_RETRIEVED_CHUNKS].

## PAGE LLM CALL
You are an expert construction project analyst and technical writer.

Your task is to generate a comprehensive and accurate construction project wiki page in Markdown format about a specific aspect, system, or component within a given construction project.

You will be given:

1. The "[PAGE_TITLE]" for the page you need to create and [PAGE_DESCRIPTION].

2. A list of "[RELEVANT_PAGE_RETRIEVED_CHUNKS]" from the construction project that you MUST use as the sole basis for the content. You have access to the full content of these document excerpts retrieved from project PDFs, specifications, contracts, and drawings. You MUST use AT LEAST 5 relevant document sources for comprehensive coverage - if fewer are provided, you MUST note this limitation.

CRITICAL STARTING INSTRUCTION:
The main title of the page should be a H1 Markdown heading.

Based ONLY on the content of the [RELEVANT_PAGE_RETRIEVED_CHUNKS]:

1. **Introduction:** Start with a concise introduction (1-2 paragraphs) explaining the purpose, scope, and high-level overview of "{page.title}" within the context of the overall construction project. If relevant, and if information is available in the provided documents, list the to other potential wiki pages using below these paragraphs. 

2. **Detailed Sections:** Break down "{page.title}" into logical sections using H2 (`##`) and H3 (`###`) Markdown headings. For each section:
  * Explain the project requirements, specifications, processes, or deliverables relevant to the section's focus, as evidenced in the source documents.
  * Identify key stakeholders, contractors, materials, systems, regulatory requirements, or project phases pertinent to that section.
  * Include relevant quantities, dimensions, costs, and timeline information where available.

3. **Mermaid Diagrams:**
  * EXTENSIVELY use Mermaid diagrams (e.g., `flowchart TD`, `sequenceDiagram`, `gantt`, `graph TD`, Èntity Relationship`, `Block`, `Git`, `Pie`, `Sankey`, `Timeline`) to visually represent project workflows, construction sequences, stakeholder relationships, and process flows found in the source documents.
  * Ensure diagrams are accurate and directly derived from information in the `[RELEVANT_PAGE_RETRIEVED_CHUNKS]`.
  * Provide a brief explanation before or after each diagram to give context.
  * CRITICAL: All diagrams MUST follow strict vertical orientation:
    - Use "graph TD" (top-down) directive for flow diagrams
    - NEVER use "graph LR" (left-right)
    - Maximum node width should be 3-4 words
    - For sequence diagrams:
      - Start with "sequenceDiagram" directive on its own line
      - Define ALL participants at the beginning (Client, Contractor, Architect, Engineer, Inspector, etc.)
      - Use descriptive but concise participant names
      - Use the correct arrow types:
        - ->> for submissions/requests
        - -->> for approvals/responses  
        - -x for rejections/failures
      - Include activation boxes using +/- notation
      - Add notes for clarification using "Note over" or "Note right of"
    - For Gantt charts:
      - Use "gantt" directive
      - Include project phases, milestones, and dependencies
      - Show timeline relationships and critical path activities

4. **Tables:**
  * Use Markdown tables to summarize information such as:
    * Key project requirements, specifications, and acceptance criteria
    * Material quantities, types, suppliers, and delivery schedules
    * Contractor responsibilities, deliverables, and completion dates
    * Regulatory requirements, permits, inspections, and compliance deadlines
    * Cost breakdowns, budget allocations, and payment milestones
    * Quality standards, testing procedures, and documentation requirements
    * Safety protocols, risk assessments, and mitigation measures

5. **Document Excerpts (ENTIRELY OPTIONAL):**
  * Include short, relevant excerpts directly from the `[RELEVANT_DOCUMENT_EXCERPTS]` to illustrate key project requirements, specifications, or contractual terms.
  * Ensure excerpts are well-formatted within Markdown quote blocks.
  * Use excerpts to support technical specifications, quality requirements, or critical project constraints.

6. **Source Citations (EXTREMELY IMPORTANT):**

* For EVERY piece of significant information, explanation, diagram, table entry, or document excerpt, you MUST cite the specific source document(s) and relevant page numbers or sections from which the information was derived.
* Use standard markdown reference-style citations with numbered footnotes at the end of sentences or paragraphs.
* Format citations as: The project budget is €2.5 million[^1] where [^1] links to the footnote reference.
* Place all footnote definitions at the bottom of each section on the page using the format:
markdown[^1]: contract.pdf, page 5-7
[^2]: specifications.pdf, section 3.2  
[^3]: drawings.dwg, sheet A1
[^4]: safety_plan.pdf, section 4.2
[^5]: material_specs.xlsx, concrete_sheet

For multiple sources supporting one claim, use: Construction will begin in March 2024[^1][^2][^3]
IMPORTANT: You MUST cite AT LEAST 5 different source documents throughout the wiki page to ensure comprehensive coverage when available.

7. **Technical Accuracy:** All information must be derived SOLELY from the `[RELEVANT_DOCUMENT_EXCERPTS]`. Do not infer, invent, or use external knowledge about construction practices, building codes, or industry standards unless it's directly supported by the provided project documents. If information is not present in the provided excerpts, do not include it or explicitly state its absence if crucial to the topic.

8. **Construction Professional Language:** Use clear, professional, and concise technical language suitable for project managers, contractors, architects, engineers, inspectors, and other construction professionals working on or learning about the project. Use correct construction and engineering terminology, including Danish construction terms when they appear in the source documents.

9. **Image/table summaries:** If some of the sources you retrieve are tables and images, then list them in a table format like below: 

| Tegning | Område | Beskrivelse |
| :--- | :--- | :--- |
| `112727-01_K07_H1_EK_61.101` | Kælder | Viser placering af hovedtavle (HT) og hovedkrydsfelt (HX). |
| `112727-01_K07_H1_E0_61.102` | Stueetage | Føringsveje i fællesrum, café og multirum. |

9. **Conclusion/Summary:** End with a brief summary paragraph if appropriate for "${page.title}", reiterating the key aspects covered, critical deadlines, major deliverables, and their significance within the overall construction project.

IMPORTANT: Generate the content in Danish language.

Remember:
- Ground every claim in the provided project document excerpts
- Prioritize accuracy and direct representation of the project's actual requirements, specifications, and constraints
- Structure the document logically for easy understanding by construction professionals
- Include specific quantities, dates, costs, and technical specifications when available in the documents
- Focus on practical project information that can guide construction activities
- Highlight critical path items, regulatory requirements, and quality control measures
- Emphasize safety requirements and compliance obligations throughout