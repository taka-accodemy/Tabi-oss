# Open Core SaaS Monorepo Structure

```
/
├── apps/
│   └── api/                # Application Entry Point
│       ├── package.json    # Dependencies: @tabi/core (required), @tabi/enterprise (optional/dynamic)
│       └── src/
│           └── main.ts     # Startup logic with Dynamic Import for SaaS mode
├── packages/
│   ├── core/               # OSS Core Logic (MIT)
│   │   ├── package.json
│   │   └── src/            # Interfaces (ITenantResolver) & Base impls
│   └── enterprise/         # Proprietary SaaS Logic
│       ├── package.json    # Depends on @tabi/core
│       └── src/            # MultiTenantResolver, BillingService, etc.
├── infrastructure/         # Terraform configurations
├── .github/
│   └── workflows/
│       └── sync-oss.yaml   # Syncs packages/core to public repo
├── Dockerfile.oss          # Builds ONLY apps/api + packages/core
├── Dockerfile.saas         # Builds EVERYTHING
├── pnpm-workspace.yaml     # Defines monorepo workspace
└── package.json            # Root configuration
```
