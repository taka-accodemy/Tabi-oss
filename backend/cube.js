module.exports = {
  // Database configuration
  dbType: process.env.CUBEJS_DB_TYPE || 'postgres',
  
  // API configuration
  apiSecret: process.env.CUBEJS_API_SECRET || 'SECRET',
  
  // Schema path
  schemaPath: 'cube_schemas',
  
  // Database connection
  driverFactory: ({ dataSource }) => {
    if (dataSource === 'default') {
      return {};
    }
  },
  
  // Context to add user info to queries
  contextToAppId: ({ authInfo }) => {
    return `CUBE_APP_${authInfo.userId || 'anonymous'}`;
  },
  
  // Pre-aggregations configuration
  preAggregationsSchema: process.env.CUBEJS_PRE_AGGREGATIONS_SCHEMA || 'pre_aggregations',
  
  // Cache configuration
  cacheAndQueueDriver: process.env.CUBEJS_CACHE_AND_QUEUE_DRIVER || 'memory',
  
  // JWT configuration
  jwt: {
    algorithms: ['HS256'],
    issuer: process.env.CUBEJS_JWT_ISSUER || 'cubejs',
    audience: process.env.CUBEJS_JWT_AUDIENCE || 'cubejs',
  },
  
  // Query rewrite for security
  queryRewrite: (query, { authInfo }) => {
    // Add user-specific filters if needed
    if (authInfo.userRole === 'customer') {
      query.filters = query.filters || [];
      query.filters.push({
        member: 'Customers.id',
        operator: 'equals',
        values: [authInfo.userId],
      });
    }
    
    return query;
  },
  
  // Scheduled refresh configuration
  scheduledRefreshTimer: process.env.CUBEJS_SCHEDULED_REFRESH_TIMER || 60,
  
  // Security context
  checkAuth: async (req, auth) => {
    // In production, implement proper JWT validation
    if (process.env.NODE_ENV === 'production') {
      // Validate JWT token
      try {
        const jwt = require('jsonwebtoken');
        const token = req.headers.authorization?.replace('Bearer ', '');
        
        if (!token) {
          throw new Error('No token provided');
        }
        
        const decoded = jwt.verify(token, process.env.CUBEJS_API_SECRET);
        req.authInfo = decoded;
      } catch (error) {
        throw new Error('Invalid token');
      }
    } else {
      // Development mode - allow all requests
      req.authInfo = { userId: 'dev_user', userRole: 'admin' };
    }
  },
  
  // Logging configuration
  logger: (msg, params) => {
    console.log(`${new Date().toISOString()} [CUBE] ${msg}`, params);
  },
  
  // Telemetry
  telemetry: process.env.CUBEJS_TELEMETRY !== 'false',
  
  // External database configuration
  externalDbType: process.env.CUBEJS_EXTERNAL_DB_TYPE,
  externalDriverFactory: process.env.CUBEJS_EXTERNAL_DB_TYPE ? () => ({}) : undefined,
  
  // Orchestrator configuration
  orchestratorOptions: {
    redisPrefix: process.env.CUBEJS_REDIS_PREFIX || 'CUBEJS_CACHE',
    queryCacheOptions: {
      refreshKeyRenewalThreshold: 30,
      backgroundRenew: true,
    },
  },
};