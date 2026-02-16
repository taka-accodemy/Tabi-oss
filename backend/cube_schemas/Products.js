cube(`Products`, {
  sql: `SELECT * FROM products`,
  
  dimensions: {
    id: {
      sql: `id`,
      type: `string`,
      primaryKey: true,
    },
    
    name: {
      sql: `name`,
      type: `string`,
    },
    
    category: {
      sql: `category`,
      type: `string`,
    },
    
    brand: {
      sql: `brand`,
      type: `string`,
    },
    
    price: {
      sql: `price`,
      type: `number`,
      format: `currency`,
    },
    
    description: {
      sql: `description`,
      type: `string`,
    },
    
    createdAt: {
      sql: `created_at`,
      type: `time`,
    },
    
    updatedAt: {
      sql: `updated_at`,
      type: `time`,
    },
  },
  
  measures: {
    count: {
      type: `count`,
      drillMembers: [id, name, category, brand],
    },
    
    averagePrice: {
      sql: `price`,
      type: `avg`,
      format: `currency`,
    },
    
    minPrice: {
      sql: `price`,
      type: `min`,
      format: `currency`,
    },
    
    maxPrice: {
      sql: `price`,
      type: `max`,
      format: `currency`,
    },
    
    totalSales: {
      sql: `${Sales.totalAmount}`,
      type: `sum`,
      format: `currency`,
    },
    
    totalQuantitySold: {
      sql: `${Sales.totalQuantity}`,
      type: `sum`,
    },
    
    salesCount: {
      sql: `${Sales.count}`,
      type: `sum`,
    },
  },
  
  joins: {
    Sales: {
      sql: `${CUBE}.id = ${Sales}.product_id`,
      relationship: `hasMany`,
    },
  },
  
  preAggregations: {
    main: {
      measures: [count, averagePrice],
      dimensions: [category, brand],
      refreshKey: {
        every: `1 day`,
      },
    },
    
    salesSummary: {
      measures: [totalSales, totalQuantitySold, salesCount],
      dimensions: [name, category],
      refreshKey: {
        every: `1 hour`,
      },
    },
  },
});