from setuptools import setup, find_packages

setup(
    name="ai-checklist",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "fastapi==0.104.1",
        "uvicorn==0.15.0",
        "sqlalchemy==1.4.54",
        "python-dotenv==0.19.2",
        "openai==1.7.1",
        "httpx==0.24.1",
        "python-multipart==0.0.6",
        "alembic==1.7.7",
        "gunicorn==20.1.0",
        "redis==5.0.1",
        "pydantic==2.4.2",
        "langchain-core==0.1.22",
        "langchain-community==0.0.18",
        "langchain==0.1.0",
        "crewai==0.10.0",
        "duckduckgo-search==4.1.1",
    ],
    python_requires=">=3.11",
) 