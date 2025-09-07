from setuptools import setup, find_packages
import os

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="paypal-api",
    version="1.0.0",
    description="API REST para integración con PayPal, permitiendo pagos y suscripciones mediante servicios de PayPal.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Equipo EPC",
    author_email="soporte@paypal.com",
    url="https://developer.paypal.com/",
    packages=find_packages(
        include=["paypal_api", "paypal_api.*"],
        exclude=["tests", "tests.*", "alembic", "alembic.*", "venv", "venv.*"]
    ),
    include_package_data=True,
    package_data={},
    exclude_package_data={"": ["alembic/*", "alembic.ini"]},
    install_requires=[
        "fastapi==0.104.1",
        "uvicorn[standard]==0.24.0",
        "python-multipart==0.0.6",
        "python-jose[cryptography]==3.3.0",
        "passlib[bcrypt]==1.7.4",
        "structlog"
    ],
    extras_require={
        "dev": [
            "pytest==7.4.3",
            "pytest-cov==4.1.0",
            "pytest-mock==3.12.0",
            "pytest-asyncio==0.21.1",
            "httpx==0.25.2",
            "black==23.11.0",
            "flake8==6.1.0",
            "mypy==1.7.1",
            "pre-commit==3.6.0"
        ]
    },
    python_requires=">=3.11",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Framework :: FastAPI",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "console_scripts": [
            # No script CLI principal, se ejecuta con uvicorn
        ]
    },
    license="MIT",
    keywords="paypal fastapi pagos api rest subscriptions",
    project_urls={
        "Documentación": "https://developer.paypal.com/",
        "Código": "https://github.com/paypal/PayPal-Python-SDK"
    },
)