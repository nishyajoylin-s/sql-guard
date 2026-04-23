from __future__ import annotations

BACKEND_TEMPLATES: dict[str, dict] = {
    "thoughtspot": {
        "name": "thoughtspot",
        "url": "",
        "method": "POST",
        "question_field": "query_string",
        "sql_field": "contents[0].query_sql",
        "result_field": "contents[0].data_rows",
        "auth_header": "",
    },
    "fabric": {
        "name": "fabric",
        "url": "",
        "method": "POST",
        "question_field": "userQuestion",
        "sql_field": "sqlQuery",
        "result_field": "results",
        "auth_header": "",
    },
    "vanna": {
        "name": "vanna",
        "url": "",
        "method": "POST",
        "question_field": "question",
        "sql_field": "sql",
        "result_field": "results",
        "auth_header": "",
    },
    "dataherald": {
        "name": "dataherald",
        "url": "",
        "method": "POST",
        "question_field": "prompt",
        "sql_field": "sql",
        "result_field": "response",
        "auth_header": "",
    },
    "custom": {
        "name": "my-backend",
        "url": "",
        "method": "POST",
        "question_field": "question",
        "sql_field": "sql",
        "result_field": "result",
        "auth_header": "",
    },
}

SETUP_INSTRUCTIONS: dict[str, str] = {
    "thoughtspot": (
        "Change this URL in your app:\n"
        "  Before: https://<your-instance>.thoughtspot.cloud/api/rest/2.0/searchdata\n"
        "  After:  http://localhost:{port}/proxy/thoughtspot"
    ),
    "fabric": (
        "Change this URL in your app:\n"
        "  Before: https://<your-workspace>.fabric.microsoft.com/api/...\n"
        "  After:  http://localhost:{port}/proxy/fabric"
    ),
    "vanna": (
        "Change this URL in your app:\n"
        "  Before: http://localhost:8000/api/v0/generate_sql\n"
        "  After:  http://localhost:{port}/proxy/vanna"
    ),
    "dataherald": (
        "Change this URL in your app:\n"
        "  Before: https://api.dataherald.com/api/v1/nl-generations\n"
        "  After:  http://localhost:{port}/proxy/dataherald"
    ),
    "custom": (
        "Change your backend URL in your app to:\n"
        "  http://localhost:{port}/proxy/my-backend"
    ),
}
