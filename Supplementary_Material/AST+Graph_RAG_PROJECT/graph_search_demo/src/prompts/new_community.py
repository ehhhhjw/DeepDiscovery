COMMUNITY_REPORT_PROMPT = """

As a highly skilled JavaScript development expert. You are an AI assistant that helps a human developer to understand the structure and relationships with certain entities (e.g., class and method) within a JavaScript project.

# Goal
You need to create a comprehensive node correlation report for a given community. This report should be well-structured and detailed to provide decision-makers with insightful information about the community.

# Input Text:

## 1.List of Entities: A list of all entities present within the community.
## 2.Entity Relationships: Description of relationships between entities.
## 3.Folder Descriptions: Descriptions of entities grouped within the same folder.
## 4.Correlation Scores: Numerical values (ranging from 0 to 14) indicating the correlation strength between entities, where higher scores represent stronger correlations.
## 5.Entity Reports: Additional reports or descriptions associated with each entity.

# Objective:

The goal of this report is to inform decision-makers about the strength of correlations between nodes (entities) within the community. This includes providing a clear understanding of how entities are connected and their relative importance.

# Report Structure:

The report should include the following sections:

- TITLE: community's name that represents its key entities - title should be short but specific. When possible, include representative named entities in the title.
- SUMMARY: A high-level executive summary of the community's structure, detailing how entities are related and highlighting significant information.
- IMPACT SEVERITY RATING: A float score between 0-10 representing the overall impact severity posed by entities within the community.
- RATING EXPLANATION: A single-sentence explanation of the impact severity rating.
- DETAILED FINDINGS: A list of 5-10 key insights about the community, each with a short summary followed by multiple paragraphs of detailed explanation. Ensure the findings cover:
-- Key Entities Overview
-- Legal Compliance
-- Technical Capabilities
-- Reputation
-- Noteworthy Claims

Your report should be comprehensive and provide deep insights into the community's node correlations. Use clear and precise language to ensure the decision-makers can easily understand the correlations and their potential impact.

Return output as a well-formed JSON-formatted string with the following format:
    {{
        "title": <report_title>,
        "summary": <executive_summary>,
        "rating": <impact_severity_rating>,
        "rating_explanation": <rating_explanation>,
        "findings": [
            {{
                "summary":<insight_1_summary>,
                "explanation": <insight_1_explanation>
            }},
            {{
                "summary":<insight_2_summary>,
                "explanation": <insight_2_explanation>
            }}
        ]
    }}

JSON 结构字段里的内容，请使用中文！
JSON 结构字段里的内容，请使用中文！

# Grounding Rules

Points supported by data should list their data references as follows:

"This is an example sentence supported by multiple data references [Data: <dataset name> (record ids); <dataset name> (record ids)]."

Do not list more than 5 record ids in a single reference. Instead, list the top 5 most relevant record ids and add "+more" to indicate that there are more.

For example:
"Function X is defined in File Y and interacts with Module Z through multiple calls [Code: main.js (10-20, 34-45); utils.js (50); helpers.js (12, 35, 44, 70,+more)]."
where 10-20, 34-45, 50, 12, 35, 44, and 70 represent the line numbers of the relevant code references.
Do not include information where the supporting evidence for it is not provided.


# Example Input
-----------
Text:

List of Entities:

entity
main.js
utils.js
helpers.js
initApp
calculateSum
formatDate

Entity Relationships:

source,target,description
main.js,initApp,main.js contains the initApp function
main.js,utils.js,main.js imports utils.js
utils.js,calculateSum,utils.js defines the calculateSum function
helpers.js,formatDate,helpers.js defines the formatDate function
main.js,helpers.js,main.js imports helpers.js
main.js,calculateSum,main.js calls calculateSum from utils.js
main.js,formatDate,main.js calls formatDate from helpers.js

Folder Descriptions:

list of entity,description
[main.js,utils.js,helpers.js], these files are in the same secondary folder

Correlation Scores:

source,target,description
main.js,utils.js,the correlation between main.js and utils.js is 10

Entity Reports:

entity,description
main.js,Main entry point of the application
utils.js,Utility functions for the application
helpers.js,Helper functions used across the application
initApp,Initializes the main application
calculateSum,Utility function to calculate sum
formatDate,Helper function to format date

Output:
{{
    "title": "JavaScript Project: Main Functions and Utilities",
    "summary": "The project centers around main.js which is the entry point of the application. The main.js file imports utility functions from utils.js and helpers.js, providing essential functionality such as initApp, calculateSum, and formatDate.",
    "rating": 4.5,
    "rating_explanation": "The project's complexity is moderate due to the interdependent modules and multiple utility functions.",
    "findings": [
        {{
            "summary": "main.js as the central entry point",
            "explanation": "main.js serves as the primary entry point of the project, initializing the application with the initApp function. This file has multiple dependencies and interacts with utilities and helper functions from other modules, which adds to its critical role in the project structure. [Code: main.js (10-20, 34-45); utils.js (50); helpers.js (12, 35, 44, 70,+more)]"
        }},
        {{
            "summary": "Utils.js for utility functions",
            "explanation": "utils.js provides essential utility functions like calculateSum which are widely used across the project. The close relationship between main.js and utils.js underscores the importance of utils.js in the project's core logic. [Code: utils.js (5-15, 20-35); main.js (10-20,+more)]"
        }},
        {{
            "summary": "helpers.js for helper functions",
            "explanation": "helpers.js contains helper functions such as formatDate, which support the main functionality of the application. These functions are frequently utilized by the main.js module, highlighting the cross-module dependencies within the project. [Code: helpers.js (10-25, 30-40); main.js (34-45,+more)]"
        }},
        {{
            "summary": "Inter-module dependencies",
            "explanation": "There are significant inter-module dependencies in this project, particularly between main.js and both utils.js and helpers.js. These dependencies ensure smooth functionality but also increase the complexity and potential for issues during maintenance and updates. [Code: main.js (10-20, 34-45); utils.js (5-15); helpers.js (10-25)]"
        }}
    ]
}}

JSON 结构字段里的内容，请使用中文！
JSON 结构字段里的内容，请使用中文！

# Real Data

Use the following text for your answer. Do not make anything up in your answer.

Text:
{input_text}

The report should include the following sections:

- TITLE: A concise and specific title that accurately summarizes the features and key entities included in the community.
- SUMMARY: A high-level executive summary of the community's structure, detailing how entities are related and highlighting significant information.
- IMPACT SEVERITY RATING: A float score between 0-10 representing the correlation between entities within the community.
- RATING EXPLANATION: A single-sentence explanation of the impact severity rating.
- DETAILED FINDINGS: A list of 5-10 key insights about the community, each with a short summary followed by multiple paragraphs of detailed explanation. Ensure the findings cover:
-- Key Entities Overview
-- Legal Compliance
-- Technical Capabilities
-- Reputation
-- Noteworthy Claims

Your report should be comprehensive and provide deep insights into the community's node correlations. Use clear and precise language to ensure the decision-makers can easily understand the correlations and their potential impact.

Return output as a well-formed JSON-formatted string with the following format:
    {{
        "title": <report_title>,
        "summary": <executive_summary>,
        "rating": <impact_severity_rating>,
        "rating_explanation": <rating_explanation>,
        "findings": [
            {{
                "summary":<insight_1_summary>,
                "explanation": <insight_1_explanation>
            }},
            {{
                "summary":<insight_2_summary>,
                "explanation": <insight_2_explanation>
            }}
        ]
    }}

JSON 结构字段里的内容，请使用中文！
JSON 结构字段里的内容，请使用中文！

# Grounding Rules

Points supported by code analysis should list their references as follows:

"This is an example sentence supported by multiple code references [Code: <filename> (line numbers); <filename> (line numbers)]."

Do not list more than 5 line numbers in a single reference. Instead, list the top 5 most relevant lines and add "+more" to indicate that there are more.

For example:
"Function X is defined in File Y and interacts with Module Z through multiple calls [Code: main.js (10-20, 34-45); utils.js (50); helpers.js (12, 35, 44, 70,+more)]."

where 10-20, 34-45, 50, 12, 35, 44, and 70 represent the line numbers of the relevant code references.

Do not include information where the supporting evidence for it is not provided.

JSON 结构字段里的内容，请使用中文！
JSON 结构字段里的内容，请使用中文！

Output:
"""
