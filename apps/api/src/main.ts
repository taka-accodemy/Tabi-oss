import express from 'express';
import cors from 'cors';
import { ITenantResolver, SingleTenantResolver } from '@tabi/core';

async function bootstrap() {
  const app = express();
  app.use(cors());
  app.use(express.json());
  
  const port = process.env.PORT || 8080;
  const mode = process.env.APP_MODE || 'oss';

  console.log(`Starting Tabi API in ${mode.toUpperCase()} mode...`);

  let tenantResolver: ITenantResolver;

  if (mode === 'saas') {
    try {
      const { MultiTenantResolver } = require('@tabi/enterprise');
      tenantResolver = new MultiTenantResolver();
    } catch (e) {
      console.error('Failed to load Enterprise module:', e);
      process.exit(1);
    }
  } else {
    tenantResolver = new SingleTenantResolver();
  }

  app.get('/', async (req, res) => {
    try {
      const tenant = await tenantResolver.resolve({ headers: req.headers as any });
      res.json({
        status: 'ok',
        mode,
        resolvedTenant: tenant
      });
    } catch (e: any) {
      res.status(500).json({ status: 'error', message: e.message });
    }
  });

  app.get('/health', (req, res) => {
    res.json({ status: 'up' });
  });

  console.log(`Tabi API attempting to listen on port ${port}...`);
  try {
    app.listen(Number(port), '0.0.0.0', () => {
      console.log(`Tabi API successfully listening on 0.0.0.0:${port}`);
    });
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

bootstrap().catch(err => {
  console.error('Fatal error during bootstrap:', err);
  process.exit(1);
});
