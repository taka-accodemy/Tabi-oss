# Tabi OSS - Open Source ChatBI Platform

Tabi OSS is the open-source core of the Tabi platform. It provides a natural language business intelligence interface using Cube.js and LLMs.

> [!NOTE]
> This is the **Open Source version**. For enterprise features like Multi-Tenancy, SSO, and Audit Logs, please check our [SaaS version](https://tabi.example.com).

## 🚀 Key Features (OSS)
- **Natural Language to SQL**: Query your database using plain English or Japanese.
- **Cube.js Integration**: Leverage a predefined semantic layer for accurate results.
- **Multi-Database Support**: PostgreSQL, BigQuery, and AWS Iceberg.
- **Interactive Chat UI**: A modern React-based interface for data exploration.

## 🛠 Quick Start

### 1. Prerequisites
- Docker & Docker Compose
- Node.js 20+

### 2. Setup
```bash
git clone https://github.com/taka-accodemy/Tabi-oss.git
cd Tabi-oss
cp .env.template .env
```

### 3. Run with Docker
```bash
# Start the core services
docker-compose up -d
```

## 🏗 Differences from SaaS Version
| Feature | OSS Version | SaaS Version |
|---------|-------------|--------------|
| Tenancy | Single-Tenant | Multi-Tenant |
| Auth | Basic / Local | SSO (OIDC/SAML) |
| Billing | N/A | Integrated Stripe |
| Support | Community | Priority / SLA |

## 📄 License
This core is licensed under the **MIT License**.
(Note: Some underlying components may follow LGPLv3).

## 🤝 Contributing
Contributions are welcome! Please feel free to submit Pull Requests.
