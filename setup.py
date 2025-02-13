from setuptools import setup, find_packages

setup(
    name="ai-checklist",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True,
    install_requires=[
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "python-dotenv",
        "openai",
        "httpx",
        "python-multipart",
        "alembic",
        "gunicorn",
        "psycopg2-binary",
        "redis>=5.0.1",
        "crewai==0.11.0",
        "langchain==0.1.6",
        "duckduckgo-search==4.4.3",
    ],
    python_requires=">=3.11",
) 